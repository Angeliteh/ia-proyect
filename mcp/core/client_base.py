"""
Clase base para clientes MCP.

Este módulo proporciona la clase base que todos los clientes MCP
deben implementar para comunicarse con servidores MCP.
"""

import abc
import logging
from typing import Dict, Any, Optional, Union

from .protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError,
    MCPErrorCode
)

class MCPClientBase(abc.ABC):
    """
    Clase base abstracta para clientes MCP.
    
    Los clientes MCP se conectan a servidores MCP para acceder a
    recursos como sistemas de archivos, bases de datos, etc.
    
    Attributes:
        server_name: Nombre del servidor al que se conecta
        auth_token: Token de autenticación (opcional)
        connection_info: Información de conexión al servidor
        logger: Logger para esta instancia
    """
    
    def __init__(
        self, 
        server_name: str = None,
        auth_token: Optional[str] = None,
        **connection_info
    ):
        """
        Inicializa un cliente MCP base.
        
        Args:
            server_name: Nombre del servidor al que se conecta
            auth_token: Token de autenticación (opcional)
            **connection_info: Información adicional para la conexión
        """
        self.server_name = server_name or "generic_client"
        self.auth_token = auth_token
        self.connection_info = connection_info
        self.logger = logging.getLogger(f"mcp.client.{self.server_name}")
        self._server_capabilities = None
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP.
        
        Returns:
            True si la conexión se estableció correctamente, False en caso contrario
            
        Raises:
            MCPError: Si ocurre un error al conectar
        """
        pass
    
    @abc.abstractmethod
    def disconnect(self) -> bool:
        """
        Cierra la conexión con el servidor MCP.
        
        Returns:
            True si la desconexión fue exitosa, False en caso contrario
        """
        pass
    
    @abc.abstractmethod
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
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servidor.
        
        Returns:
            Diccionario con las capacidades del servidor
            
        Raises:
            MCPError: Si ocurre un error al obtener las capacidades
        """
        if self._server_capabilities is None:
            message = MCPMessage.create_capabilities_request()
            message.auth_token = self.auth_token
            
            response = self.send_message(message)
            
            if not response.success:
                raise MCPError(
                    code=response.error.code if response.error else MCPErrorCode.SERVER_ERROR,
                    message=f"Error obteniendo capacidades: {response.error.message if response.error else 'Error desconocido'}"
                )
            
            self._server_capabilities = response.data
            
        return self._server_capabilities
    
    def ping(self) -> bool:
        """
        Verifica la disponibilidad del servidor.
        
        Returns:
            True si el servidor está disponible, False en caso contrario
        """
        try:
            message = MCPMessage.create_ping()
            message.auth_token = self.auth_token
            
            response = self.send_message(message)
            return response.success
        except Exception as e:
            self.logger.error(f"Error en ping: {str(e)}")
            return False
    
    def get_resource(self, resource_type: Union[MCPResource, str], resource_path: str, **params) -> MCPResponse:
        """
        Obtiene un recurso del servidor.
        
        Args:
            resource_type: Tipo de recurso
            resource_path: Ruta del recurso
            **params: Parámetros adicionales para la solicitud
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        message = MCPMessage.create_get_request(
            resource_type=resource_type,
            resource_path=resource_path,
            params=params
        )
        message.auth_token = self.auth_token
        
        return self.send_message(message)
    
    def search_resources(self, resource_type: Union[MCPResource, str], query: str, **params) -> MCPResponse:
        """
        Busca recursos en el servidor.
        
        Args:
            resource_type: Tipo de recurso
            query: Consulta de búsqueda
            **params: Parámetros adicionales para la búsqueda
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        all_params = params.copy()
        all_params["query"] = query
        
        message = MCPMessage.create_search_request(
            resource_type=resource_type,
            query=query,
            params=params
        )
        message.auth_token = self.auth_token
        
        return self.send_message(message)
    
    def list_resources(self, resource_type: Union[MCPResource, str], parent_path: str = "/", **params) -> MCPResponse:
        """
        Lista recursos en el servidor.
        
        Args:
            resource_type: Tipo de recurso
            parent_path: Ruta del directorio padre
            **params: Parámetros adicionales para el listado
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        message = MCPMessage(
            action=MCPAction.LIST,
            resource_type=resource_type,
            resource_path=parent_path,
            data=params,
            auth_token=self.auth_token
        )
        
        return self.send_message(message)
    
    # Métodos asincrónicos para clientes que implementen comunicación asíncrona
    
    async def ping_async(self) -> bool:
        """
        Versión asíncrona de ping.
        
        Si el cliente implementa send_message_async, este método facilitará
        la comunicación en entornos asincrónicos.
        
        Returns:
            True si el servidor responde correctamente
        """
        try:
            if hasattr(self, 'send_message_async'):
                message = MCPMessage.create_ping()
                response = await self.send_message_async(message)
                return response.success
            else:
                # Fallback al método sincrónico
                return self.ping()
        except Exception as e:
            self.logger.error(f"Error en ping_async: {str(e)}")
            return False
            
    async def get_capabilities_async(self) -> Dict[str, Any]:
        """
        Versión asíncrona de get_capabilities.
        
        Si el cliente implementa send_message_async, este método facilitará
        la comunicación en entornos asincrónicos.
        
        Returns:
            Diccionario con las capacidades del servidor
        """
        try:
            if hasattr(self, 'send_message_async'):
                message = MCPMessage.create_capabilities_request()
                response = await self.send_message_async(message)
                
                if response.success:
                    return response.data
                else:
                    self.logger.error(f"Error en get_capabilities_async: {response.error.message if hasattr(response, 'error') else 'Respuesta inválida'}")
                    return {}
            else:
                # Fallback al método sincrónico
                return self.get_capabilities()
        except Exception as e:
            self.logger.error(f"Error en get_capabilities_async: {str(e)}")
            return {}
            
    async def get_resource_async(self, resource_type: Union[MCPResource, str], resource_path: str) -> MCPResponse:
        """
        Versión asíncrona de get_resource.
        
        Si el cliente implementa send_message_async, este método facilitará
        la comunicación en entornos asincrónicos.
        
        Args:
            resource_type: Tipo de recurso a obtener
            resource_path: Ruta del recurso
            
        Returns:
            Respuesta con el recurso solicitado
        """
        if hasattr(self, 'send_message_async'):
            message = MCPMessage.create_get_request(resource_type, resource_path)
            return await self.send_message_async(message)
        else:
            # Fallback al método sincrónico
            return self.get_resource(resource_type, resource_path)
            
    async def list_resources_async(self, resource_type: Union[MCPResource, str], resource_path: str) -> MCPResponse:
        """
        Versión asíncrona de list_resources.
        
        Si el cliente implementa send_message_async, este método facilitará
        la comunicación en entornos asincrónicos.
        
        Args:
            resource_type: Tipo de recurso a listar
            resource_path: Ruta base para listar recursos
            
        Returns:
            Respuesta con la lista de recursos
        """
        if hasattr(self, 'send_message_async'):
            message = MCPMessage.create_list_request(resource_type, resource_path)
            return await self.send_message_async(message)
        else:
            # Fallback al método sincrónico
            return self.list_resources(resource_type, resource_path)
            
    async def search_resources_async(self, resource_type: Union[MCPResource, str], query: str) -> MCPResponse:
        """
        Versión asíncrona de search_resources.
        
        Si el cliente implementa send_message_async, este método facilitará
        la comunicación en entornos asincrónicos.
        
        Args:
            resource_type: Tipo de recurso a buscar
            query: Consulta de búsqueda
            
        Returns:
            Respuesta con los resultados de la búsqueda
        """
        if hasattr(self, 'send_message_async'):
            message = MCPMessage.create_search_request(resource_type, query)
            return await self.send_message_async(message)
        else:
            # Fallback al método sincrónico
            return self.search_resources(resource_type, query) 