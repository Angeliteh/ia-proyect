"""
Cliente MCP para conexión HTTP con servidores.

Este cliente utiliza el protocolo HTTP para comunicarse con servidores MCP
que estén expuestos a través de una API web.
"""

import asyncio
import uuid
import logging
from typing import Dict, Any, Optional, Union

from mcp.core import (
    MCPClientBase, 
    MCPMessage, 
    MCPResponse,
    MCPAction, 
    MCPResource
)
from mcp.transport.http import HttpTransport

class HttpClient(MCPClientBase):
    """
    Cliente MCP para conectarse a servidores a través de HTTP.
    
    Este cliente implementa la comunicación con servidores MCP remotos
    utilizando el protocolo HTTP como transporte.
    
    Attributes:
        server_url: URL del servidor MCP (pasado como server_name a la clase base)
        transport: Objeto HttpTransport para manejar comunicaciones
        connected: Si el cliente está conectado
        logger: Logger para este cliente
        
    Note:
        Importante: El parámetro server_url se pasa como server_name a la clase base MCPClientBase
        pero no se guarda como atributo de instancia. Se recomienda acceder a este valor mediante
        self.server_name para mantener consistencia.
    """
    
    def __init__(
        self, 
        server_url: str,
        timeout: int = 30,
        retry_attempts: int = 3,
        headers: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None
    ):
        """
        Inicializa un cliente HTTP para MCP.
        
        Args:
            server_url: URL del servidor MCP (ej: 'http://localhost:8080/api/mcp')
                        Se pasa como server_name a la clase base MCPClientBase.
            timeout: Tiempo de espera en segundos para operaciones HTTP
            retry_attempts: Número de intentos de reconexión
            headers: Cabeceras HTTP adicionales
            api_key: Clave API opcional para autenticación
        
        Note:
            Para conservar consistencia, el parámetro server_url se pasa como server_name
            a la clase base, y debe accederse mediante self.server_name en subclases.
        """
        super().__init__(server_url=server_url, timeout=timeout, retry_attempts=retry_attempts)
        
        # Configurar cabeceras HTTP
        if headers is None:
            headers = {}
            
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        # Crear el transporte HTTP
        self.transport = HttpTransport(
            base_url=server_url,
            timeout=timeout,
            headers=headers
        )
        
        self.connected = False
        self.logger = logging.getLogger("mcp.clients.http")
        self.logger.info(f"Cliente HTTP MCP inicializado para {server_url}")
        
    async def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP remoto.
        
        Returns:
            True si la conexión se estableció correctamente
        
        Note:
            Usa self.server_name internamente para mantener consistencia con la clase base.
        """
        try:
            if await self.transport.connect():
                self.connected = True
                self.logger.info(f"Cliente conectado a {self.server_name}")
                return True
        except Exception as e:
            self.logger.error(f"Error conectando a {self.server_name}: {str(e)}")
            
        return False
        
    async def disconnect(self) -> bool:
        """
        Cierra la conexión con el servidor MCP.
        
        Returns:
            True si la desconexión fue exitosa
        
        Note:
            Usa self.server_name internamente para mantener consistencia con la clase base.
        """
        try:
            if await self.transport.disconnect():
                self.connected = False
                self.logger.info(f"Cliente desconectado de {self.server_name}")
                return True
        except Exception as e:
            self.logger.error(f"Error desconectando de {self.server_name}: {str(e)}")
            
        self.connected = False
        return False
        
    async def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje al servidor MCP y espera la respuesta.
        
        Args:
            message: Mensaje a enviar. 
                    Nota: si contiene acciones personalizadas, debe usarse una
                    subclase de MCPMessage que permita valores no definidos en MCPAction.
            
        Returns:
            Respuesta del servidor
        
        Raises:
            ValueError: Si hay un problema con el mensaje (acción o tipo de recurso no válido)
        """
        if not self.connected:
            self.logger.warning("Cliente no conectado, intentando conectar automáticamente")
            if not await self.connect():
                return MCPResponse.error_response(
                    message_id=message.id,
                    code="CONNECTION_ERROR",
                    message="No se pudo establecer conexión con el servidor"
                )
                
        # Implementar reintentos si es necesario
        attempts = 0
        max_attempts = self.retry_attempts + 1
        
        while attempts < max_attempts:
            try:
                self.logger.debug(f"Enviando mensaje: {message.action} - {message.resource_path}")
                response = await self.transport.send_message(message)
                return response
            except Exception as e:
                attempts += 1
                self.logger.error(f"Error enviando mensaje (intento {attempts}/{max_attempts}): {str(e)}")
                
                if attempts >= max_attempts:
                    break
                    
                # Esperar antes de reintentar
                await asyncio.sleep(1.0 * attempts)
                
        return MCPResponse.error_response(
            message_id=message.id,
            code="SEND_ERROR",
            message=f"Error enviando mensaje después de {max_attempts} intentos"
        )
    
    # Métodos de conveniencia para operaciones comunes
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servidor MCP.
        
        Returns:
            Diccionario con las capacidades del servidor
        """
        message = MCPMessage.create_capabilities()
        response = await self.send_message(message)
        
        if response.success:
            return response.data
        else:
            self.logger.error(f"Error obteniendo capacidades: {response.error.message}")
            return {}
            
    async def ping(self) -> bool:
        """
        Envía un ping al servidor para verificar conectividad.
        
        Returns:
            True si el servidor respondió correctamente
        """
        message = MCPMessage.create_ping()
        response = await self.send_message(message)
        return response.success
        
    async def get_resource(
        self, 
        resource_type: Union[str, MCPResource], 
        resource_path: str
    ) -> MCPResponse:
        """
        Obtiene un recurso del servidor.
        
        Args:
            resource_type: Tipo de recurso (ej: 'file', MCPResource.FILE)
            resource_path: Ruta del recurso
            
        Returns:
            Respuesta del servidor
        """
        message = MCPMessage.create_get(
            resource_type=resource_type,
            resource_path=resource_path
        )
        return await self.send_message(message)
        
    async def list_resources(
        self, 
        resource_type: Union[str, MCPResource], 
        resource_path: str
    ) -> MCPResponse:
        """
        Lista recursos del servidor.
        
        Args:
            resource_type: Tipo de recurso (ej: 'directory', MCPResource.DIRECTORY)
            resource_path: Ruta base para listar
            
        Returns:
            Respuesta del servidor
        """
        message = MCPMessage.create_list(
            resource_type=resource_type,
            resource_path=resource_path
        )
        return await self.send_message(message)
        
    async def search_resources(
        self, 
        resource_type: Union[str, MCPResource], 
        query: str,
        **search_params
    ) -> MCPResponse:
        """
        Busca recursos en el servidor.
        
        Args:
            resource_type: Tipo de recurso a buscar
            query: Consulta de búsqueda
            **search_params: Parámetros adicionales de búsqueda
            
        Returns:
            Respuesta del servidor
        """
        message = MCPMessage.create_search(
            resource_type=resource_type,
            query=query,
            **search_params
        )
        return await self.send_message(message)
        
    # Sincronización de métodos asíncronos para compatibilidad
    
    def connect_sync(self) -> bool:
        """Versión sincrónica de connect()"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.connect())
        finally:
            loop.close()
            
    def disconnect_sync(self) -> bool:
        """Versión sincrónica de disconnect()"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.disconnect())
        finally:
            loop.close()
            
    def send_message_sync(self, message: MCPMessage) -> MCPResponse:
        """Versión sincrónica de send_message()"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.send_message(message))
        finally:
            loop.close() 