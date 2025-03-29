"""
Clase base para servidores MCP.

Este módulo proporciona la clase base que todos los servidores MCP
deben implementar para proporcionar funcionalidades específicas.
"""

import abc
import logging
from typing import Dict, Any, Optional, List, Union, AsyncGenerator, Type

from .protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError,
    MCPErrorCode
)

class MCPServerBase(abc.ABC):
    """
    Clase base abstracta para servidores MCP.
    
    Los servidores MCP proporcionan acceso a recursos específicos como
    sistemas de archivos, bases de datos, búsqueda web, etc.
    
    Attributes:
        name: Nombre del servidor
        description: Descripción del servidor
        capabilities: Capacidades del servidor
        logger: Logger para esta instancia
    """
    
    def __init__(
        self, 
        name: str, 
        description: str = "",
        auth_required: bool = False,
        supported_actions: Optional[List[Union[MCPAction, str]]] = None,
        supported_resources: Optional[List[Union[MCPResource, str]]] = None
    ):
        """
        Inicializa un servidor MCP base.
        
        Args:
            name: Nombre único del servidor
            description: Descripción breve del servidor
            auth_required: Si se requiere autenticación para usar el servidor
            supported_actions: Lista de acciones soportadas
            supported_resources: Lista de recursos soportados
        """
        self.name = name
        self.description = description
        self.auth_required = auth_required
        
        # Convertir acciones a strings si son enums
        if supported_actions:
            self.supported_actions = [
                action.value if isinstance(action, MCPAction) else action
                for action in supported_actions
            ]
        else:
            # Por defecto, soporte básico
            self.supported_actions = [
                MCPAction.PING.value,
                MCPAction.CAPABILITIES.value
            ]
        
        # Convertir recursos a strings si son enums
        if supported_resources:
            self.supported_resources = [
                resource.value if isinstance(resource, MCPResource) else resource
                for resource in supported_resources
            ]
        else:
            self.supported_resources = []
        
        # Configurar logger
        self.logger = logging.getLogger(f"mcp.server.{name}")
    
    @property
    def capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servidor.
        
        Returns:
            Diccionario con las capacidades del servidor
        """
        return {
            "name": self.name,
            "description": self.description,
            "auth_required": self.auth_required,
            "supported_actions": self.supported_actions,
            "supported_resources": self.supported_resources
        }
    
    async def process_message(self, message: MCPMessage) -> MCPResponse:
        """
        Procesa un mensaje MCP y retorna una respuesta.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta al mensaje
        """
        # Verificar autenticación si es requerida
        if self.auth_required and not message.auth_token:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.UNAUTHORIZED,
                message="Se requiere autenticación para usar este servidor"
            )
        
        # Verificar acción soportada
        if message.action not in self.supported_actions:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Acción no soportada: {message.action}",
                details={"supported_actions": self.supported_actions}
            )
        
        # Verificar recurso soportado
        if self.supported_resources and message.resource_type not in self.supported_resources:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado: {message.resource_type}",
                details={"supported_resources": self.supported_resources}
            )
        
        # Procesar mensaje según acción
        try:
            self.logger.info(f"Procesando mensaje {message.id} con acción {message.action}")
            
            if message.action == MCPAction.PING.value:
                return await self.handle_ping(message)
            elif message.action == MCPAction.CAPABILITIES.value:
                return await self.handle_capabilities(message)
            else:
                # Delegar a la implementación específica
                return await self.handle_action(message)
                
        except MCPError as e:
            # Errores MCP ya formateados
            return MCPResponse.error_response(
                message_id=message.id,
                code=e.code,
                message=e.message,
                details=e.details
            )
        except Exception as e:
            # Errores no esperados
            self.logger.exception(f"Error procesando mensaje {message.id}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error interno del servidor: {str(e)}"
            )
    
    async def handle_ping(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja el mensaje de ping.
        
        Args:
            message: Mensaje MCP con acción PING
            
        Returns:
            Respuesta confirme que el servidor está disponible
        """
        return MCPResponse.success_response(
            message_id=message.id,
            data={"status": "ok", "server": self.name}
        )
    
    async def handle_capabilities(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja el mensaje de capacidades.
        
        Args:
            message: Mensaje MCP con acción CAPABILITIES
            
        Returns:
            Respuesta con las capacidades del servidor
        """
        return MCPResponse.success_response(
            message_id=message.id,
            data=self.capabilities
        )
    
    @abc.abstractmethod
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja una acción específica del servidor.
        
        Este método debe ser implementado por las clases hijas para
        manejar acciones específicas del tipo de servidor.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta al mensaje
            
        Raises:
            MCPError: Si ocurre un error específico del protocolo
        """
        pass
    
    def validate_auth_token(self, token: str) -> bool:
        """
        Valida un token de autenticación.
        
        Las clases hijas pueden sobrescribir este método para implementar
        validación específica de tokens.
        
        Args:
            token: Token a validar
            
        Returns:
            True si el token es válido, False en caso contrario
        """
        return True  # Por defecto, acepta cualquier token 