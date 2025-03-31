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
        
        # Procesamos el mensaje de forma sincrónica
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self.server.process_message(message))
            return response
        finally:
            loop.close()
            self.logger.info(f"Respuesta recibida: success={(response.success if 'response' in locals() else False)}")

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