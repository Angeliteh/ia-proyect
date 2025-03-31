"""
Cliente MCP para conexión directa con servidores.

Este cliente se conecta directamente (en memoria) con una instancia
de servidor MCP, útil para pruebas y uso local.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional

from mcp.core import (
    MCPClientBase, 
    MCPServerBase, 
    MCPMessage, 
    MCPResponse, 
    MCPError, 
    MCPErrorCode
)

class SimpleDirectClient(MCPClientBase):
    """
    Un cliente MCP simple para comunicarse con servidores MCP locales.
    
    Este cliente implementa comunicación en memoria con una instancia de servidor,
    sin necesidad de transporte de red, útil para pruebas y desarrollo.
    """
    
    def __init__(self, server_instance: MCPServerBase, server_name: str = None):
        """
        Inicializa un cliente MCP simple.
        
        Args:
            server_instance: Instancia del servidor MCP a conectar
            server_name: Nombre opcional del servidor
        """
        super().__init__(server_name=server_name or server_instance.name)
        self.server = server_instance
        self.connected = False
        
    def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP.
        
        Returns:
            True si la conexión se estableció correctamente
        """
        self.connected = True
        self.logger.info(f"Cliente conectado al servidor: {self.server_name}")
        return True
        
    def disconnect(self) -> bool:
        """
        Cierra la conexión con el servidor MCP.
        
        Returns:
            True si la desconexión fue exitosa
        """
        self.connected = False
        self.logger.info(f"Cliente desconectado del servidor: {self.server_name}")
        return True
        
    def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje al servidor MCP y espera la respuesta.
        
        Esta implementación maneja tanto contextos sincrónicos como asincrónicos,
        adaptándose al entorno en el que se ejecuta.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        if not self.connected:
            raise MCPError(
                code=MCPErrorCode.CONNECTION_ERROR,
                message="No hay conexión con el servidor"
            )
        
        self.logger.info(f"Enviando mensaje: {message.action} - {message.resource_path}")
        
        # Determinar si estamos en un contexto que ya tiene un bucle de eventos
        try:
            loop = asyncio.get_running_loop()
            is_in_async_context = True
        except RuntimeError:
            # No estamos en un contexto asíncrono, creamos un nuevo bucle
            is_in_async_context = False
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            # Si estamos en un contexto asíncrono, usamos await directamente
            if is_in_async_context:
                # Creamos una tarea para procesamiento asíncrono
                # Nota: Esto se debe ejecutar desde una corrutina
                future = loop.create_future()
                
                async def process_async():
                    try:
                        response = await self.server.process_message(message)
                        future.set_result(response)
                    except Exception as e:
                        future.set_exception(e)
                
                # Programamos la tarea pero no esperamos
                asyncio.create_task(process_async())
                
                # Este método debe ser llamado desde una corrutina para trabajar
                # Si no, dará error de "coroutine was never awaited"
                response = None  # Inicializamos por si hay error
                
                # Creamos un resultado de error para casos donde hay problemas de contexto
                error_response = MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.SERVER_ERROR,
                    message="Error de contexto asíncrono: Este método debe ser llamado con 'await' desde una corrutina"
                )
                
                try:
                    # Intenta obtener el resultado de la tarea
                    response = future.result()
                except asyncio.InvalidStateError:
                    # La tarea no se ha completado todavía
                    self.logger.error("Error: El mensaje debe ser enviado con 'await' en contexto asíncrono")
                    return error_response
                except Exception as e:
                    self.logger.error(f"Error procesando mensaje: {str(e)}")
                    return error_response
                
                return response
            else:
                # Si no estamos en contexto asíncrono, usamos run_until_complete
                try:
                    response = loop.run_until_complete(self.server.process_message(message))
                    return response
                finally:
                    loop.close()
        except Exception as e:
            self.logger.error(f"Error enviando mensaje: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error enviando mensaje: {str(e)}"
            )
        finally:
            self.logger.info(f"Respuesta recibida: success={(response.success if 'response' in locals() else False)}")

    async def send_message_async(self, message: MCPMessage) -> MCPResponse:
        """
        Versión asíncrona explícita para enviar mensajes al servidor.
        
        Esta versión es más segura para usar en contextos asíncronos y
        evita los problemas de bucles de eventos anidados.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            Respuesta del servidor
        """
        if not self.connected:
            raise MCPError(
                code=MCPErrorCode.CONNECTION_ERROR,
                message="No hay conexión con el servidor"
            )
        
        self.logger.info(f"Enviando mensaje async: {message.action} - {message.resource_path}")
        
        try:
            # Procesamos el mensaje de forma asíncrona
            response = await self.server.process_message(message)
            self.logger.info(f"Respuesta async recibida: success={response.success}")
            return response
        except Exception as e:
            self.logger.error(f"Error async enviando mensaje: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error enviando mensaje: {str(e)}"
            )

    def send_echo(self, data: Dict[str, Any], path: str = "/echo") -> MCPResponse:
        """
        Envía un mensaje de eco personalizado utilizando un método alternativo.
        
        Args:
            data: Datos a enviar en el eco
            path: Ruta del recurso
            
        Returns:
            Respuesta del servidor
        """
        # En lugar de crear un objeto MCPMessage, creamos manualmente un mensaje
        # personalizado que el servidor pueda manejar
        from mcp.core.protocol import MCPMessage as RawMCPMessage
        
        # Creamos una instancia directa de MCPMessage sin usar los constructores que validan
        message = RawMCPMessage.__new__(RawMCPMessage)
        message.id = str(uuid.uuid4())
        message.action = "echo"  # Asignamos directamente la acción como string
        message.resource_type = "test"
        message.resource_path = path
        message.data = data
        message.auth_token = None
        
        return self.send_message(message) 