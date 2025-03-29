"""
Clase base para clientes MCP.

Este módulo proporciona la clase base que todos los clientes MCP
deben implementar para comunicarse con servidores MCP.
"""

import abc
import logging
import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional, List, Union, Generic, TypeVar, AsyncGenerator

from .protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError,
    MCPErrorCode
)

T = TypeVar('T')

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
        server_name: str,
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
        self.server_name = server_name
        self.auth_token = auth_token
        self.connection_info = connection_info
        self.logger = logging.getLogger(f"mcp.client.{server_name}")
        self._server_capabilities = None
    
    @abc.abstractmethod
    async def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP.
        
        Returns:
            True si la conexión se estableció correctamente, False en caso contrario
            
        Raises:
            MCPError: Si ocurre un error al conectar
        """
        pass
    
    @abc.abstractmethod
    async def disconnect(self) -> None:
        """
        Cierra la conexión con el servidor MCP.
        """
        pass
    
    @abc.abstractmethod
    async def send_message(self, message: MCPMessage) -> MCPResponse:
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
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servidor.
        
        Returns:
            Diccionario con las capacidades del servidor
            
        Raises:
            MCPError: Si ocurre un error al obtener las capacidades
        """
        if self._server_capabilities is None:
            message = MCPMessage(
                action=MCPAction.CAPABILITIES,
                resource_type=MCPResource.SYSTEM,
                resource_path="/capabilities",
                auth_token=self.auth_token
            )
            
            response = await self.send_message(message)
            
            if not response.success:
                raise MCPError(
                    code=response.error.code if response.error else MCPErrorCode.SERVER_ERROR,
                    message=f"Error obteniendo capacidades: {response.error.message if response.error else 'Error desconocido'}"
                )
            
            self._server_capabilities = response.data
            
        return self._server_capabilities
    
    async def ping(self) -> bool:
        """
        Verifica la disponibilidad del servidor.
        
        Returns:
            True si el servidor está disponible, False en caso contrario
        """
        try:
            message = MCPMessage(
                action=MCPAction.PING,
                resource_type=MCPResource.SYSTEM,
                resource_path="/ping",
                auth_token=self.auth_token
            )
            
            response = await self.send_message(message)
            return response.success
        except:
            return False
    
    async def get_resource(self, resource_type: Union[MCPResource, str], resource_path: str, **params) -> MCPResponse:
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
        message = MCPMessage(
            action=MCPAction.GET,
            resource_type=resource_type,
            resource_path=resource_path,
            data=params,
            auth_token=self.auth_token
        )
        
        return await self.send_message(message)
    
    async def search_resources(self, resource_type: Union[MCPResource, str], query: str, **params) -> MCPResponse:
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
        message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=resource_type,
            resource_path="/search",
            data={"query": query, **params},
            auth_token=self.auth_token
        )
        
        return await self.send_message(message)
    
    async def list_resources(self, resource_type: Union[MCPResource, str], parent_path: str = "/", **params) -> MCPResponse:
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
        
        return await self.send_message(message)


class MCPHttpClient(MCPClientBase):
    """
    Cliente MCP que se comunica con un servidor HTTP.
    
    Este cliente se conecta a servidores MCP que exponen una API REST.
    
    Attributes:
        base_url: URL base del servidor
        session: Sesión HTTP para las solicitudes
    """
    
    def __init__(
        self,
        server_name: str,
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Inicializa un cliente MCP HTTP.
        
        Args:
            server_name: Nombre del servidor
            base_url: URL base del servidor
            auth_token: Token de autenticación (opcional)
            timeout: Tiempo de espera para las solicitudes en segundos
        """
        super().__init__(
            server_name=server_name,
            auth_token=auth_token,
            base_url=base_url,
            timeout=timeout
        )
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
    
    async def connect(self) -> bool:
        """
        Establece conexión con el servidor HTTP.
        
        Returns:
            True si la conexión se estableció correctamente, False en caso contrario
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": f"MCP-Client/{self.server_name}"}
            )
        
        try:
            return await self.ping()
        except Exception as e:
            self.logger.exception(f"Error conectando a {self.base_url}")
            raise MCPError(
                code=MCPErrorCode.SERVICE_UNAVAILABLE,
                message=f"No se pudo conectar al servidor: {str(e)}"
            )
    
    async def disconnect(self) -> None:
        """
        Cierra la conexión con el servidor HTTP.
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje al servidor HTTP.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        if not self.session:
            await self.connect()
        
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            # Construir la URL y los datos para la solicitud
            if message.action == MCPAction.GET.value:
                # Para GET, usar la ruta del recurso directamente
                url = f"{self.base_url}/{message.resource_type}{message.resource_path}"
                params = message.data
                method = "GET"
                data = None
            else:
                # Para otras acciones, usar una estructura estándar
                url = f"{self.base_url}/{message.action}/{message.resource_type}"
                params = {}
                method = "POST"
                data = {
                    "resource_path": message.resource_path,
                    "data": message.data
                }
            
            self.logger.debug(f"Enviando solicitud: {method} {url}")
            
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=self.timeout
            ) as response:
                response_data = await response.json()
                
                # Comprobar si la respuesta tiene un formato válido
                if "success" not in response_data:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.SERVER_ERROR,
                        message="Respuesta del servidor con formato inválido",
                        details={"status_code": response.status}
                    )
                
                # Construir respuesta
                return MCPResponse.from_dict({
                    "success": response_data["success"],
                    "message_id": message.id,
                    "data": response_data.get("data"),
                    "error": response_data.get("error")
                })
                
        except aiohttp.ClientError as e:
            self.logger.exception(f"Error de cliente HTTP: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVICE_UNAVAILABLE,
                message=f"Error de conexión: {str(e)}"
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout en la solicitud a {url}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVICE_UNAVAILABLE,
                message=f"Tiempo de espera agotado ({self.timeout}s)"
            )
        except Exception as e:
            self.logger.exception(f"Error enviando mensaje: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error interno del cliente: {str(e)}"
            ) 