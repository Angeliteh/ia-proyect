"""
Definiciones del protocolo MCP (Model Context Protocol).

Este módulo contiene las clases y constantes que definen la estructura
del protocolo MCP, usado para la comunicación entre modelos de IA y
servidores de contexto.
""" 

import enum
import json
import uuid
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
import datetime

class MCPAction(str, enum.Enum):
    """Acciones posibles en el protocolo MCP."""
    
    # Operaciones básicas de datos
    GET = "get"           # Obtener un recurso específico
    LIST = "list"         # Listar recursos disponibles
    SEARCH = "search"     # Buscar recursos que coincidan con una consulta
    CREATE = "create"     # Crear un nuevo recurso
    UPDATE = "update"     # Actualizar un recurso existente
    DELETE = "delete"     # Eliminar un recurso
    
    # Operaciones de control
    CONNECT = "connect"   # Establecer conexión con un servidor
    PING = "ping"         # Verificar disponibilidad del servidor
    CAPABILITIES = "capabilities"  # Obtener capacidades del servidor


class MCPResource(str, enum.Enum):
    """Tipos de recursos en el protocolo MCP."""
    
    # Recursos del sistema de archivos
    FILE = "file"         # Archivo individual
    DIRECTORY = "directory"  # Directorio
    
    # Recursos de búsqueda
    WEB_SEARCH = "web_search"  # Búsqueda en la web
    DATABASE = "database"      # Base de datos
    
    # Recursos del sistema
    SYSTEM = "system"     # Información del sistema
    MEMORY = "memory"     # Sistema de memoria


class MCPErrorCode(str, enum.Enum):
    """Códigos de error estándar para el protocolo MCP."""
    
    # Errores generales
    INVALID_REQUEST = "invalid_request"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    
    # Errores de autenticación
    UNAUTHORIZED = "unauthorized"
    INVALID_TOKEN = "invalid_token"
    
    # Errores de servidor
    SERVER_ERROR = "server_error"
    NOT_IMPLEMENTED = "not_implemented"
    SERVICE_UNAVAILABLE = "service_unavailable"


class MCPError(Exception):
    """
    Excepción estándar para errores en el protocolo MCP.
    
    Attributes:
        code: Código de error estandarizado
        message: Mensaje descriptivo del error
        details: Detalles adicionales del error (opcional)
    """
    
    def __init__(
        self, 
        code: Union[MCPErrorCode, str], 
        message: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa un error MCP.
        
        Args:
            code: Código de error
            message: Mensaje descriptivo
            details: Detalles adicionales (opcional)
        """
        self.code = code if isinstance(code, str) else code.value
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el error a un diccionario para transmisión.
        
        Returns:
            Diccionario con la información del error
        """
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPError':
        """
        Crea una excepción de error desde un diccionario.
        
        Args:
            data: Diccionario con la información del error
            
        Returns:
            Instancia de MCPError
        """
        return cls(
            code=data.get("code", MCPErrorCode.SERVER_ERROR),
            message=data.get("message", "Error desconocido"),
            details=data.get("details")
        )


class MCPMessage:
    """
    Representa un mensaje en el protocolo MCP.
    
    Un mensaje MCP es la unidad básica de comunicación entre
    clientes y servidores MCP.
    
    Attributes:
        id: Identificador único del mensaje
        action: Acción a realizar
        resource_type: Tipo de recurso
        resource_path: Ruta del recurso
        data: Datos adicionales para la acción
        auth_token: Token de autenticación (opcional)
        timestamp: Marca de tiempo de creación
    """
    
    def __init__(
        self,
        action: Union[MCPAction, str],
        resource_type: Union[MCPResource, str],
        resource_path: str,
        data: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None
    ):
        """
        Inicializa un mensaje MCP.
        
        Args:
            action: Acción a realizar
            resource_type: Tipo de recurso
            resource_path: Ruta del recurso
            data: Datos adicionales para la acción
            auth_token: Token de autenticación (opcional)
            message_id: ID del mensaje (generado automáticamente si no se proporciona)
            timestamp: Marca de tiempo (generada automáticamente si no se proporciona)
        """
        self.id = message_id or str(uuid.uuid4())
        self.action = action if isinstance(action, str) else action.value
        self.resource_type = resource_type if isinstance(resource_type, str) else resource_type.value
        self.resource_path = resource_path
        self.data = data or {}
        self.auth_token = auth_token
        self.timestamp = timestamp or datetime.datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el mensaje a un diccionario para transmisión.
        
        Returns:
            Diccionario con la información del mensaje
        """
        return {
            "id": self.id,
            "action": self.action,
            "resource": {
                "type": self.resource_type,
                "path": self.resource_path
            },
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """
        Convierte el mensaje a una cadena JSON.
        
        Returns:
            Cadena JSON con la información del mensaje
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """
        Crea un mensaje desde un diccionario.
        
        Args:
            data: Diccionario con la información del mensaje
            
        Returns:
            Instancia de MCPMessage
        """
        resource = data.get("resource", {})
        
        return cls(
            action=data.get("action"),
            resource_type=resource.get("type"),
            resource_path=resource.get("path", ""),
            data=data.get("data", {}),
            message_id=data.get("id"),
            timestamp=datetime.datetime.fromisoformat(data.get("timestamp")) 
                if "timestamp" in data else None
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """
        Crea un mensaje desde una cadena JSON.
        
        Args:
            json_str: Cadena JSON con la información del mensaje
            
        Returns:
            Instancia de MCPMessage
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


T = TypeVar('T')

class MCPResponse(Generic[T]):
    """
    Representa una respuesta en el protocolo MCP.
    
    Attributes:
        success: Si la acción se realizó con éxito
        message_id: ID del mensaje al que responde
        data: Datos de la respuesta
        error: Información de error (si success=False)
        timestamp: Marca de tiempo de creación
    """
    
    def __init__(
        self,
        success: bool,
        message_id: str,
        data: Optional[T] = None,
        error: Optional[Union[MCPError, Dict[str, Any]]] = None,
        timestamp: Optional[datetime.datetime] = None
    ):
        """
        Inicializa una respuesta MCP.
        
        Args:
            success: Si la acción se realizó con éxito
            message_id: ID del mensaje al que responde
            data: Datos de la respuesta
            error: Información de error (si success=False)
            timestamp: Marca de tiempo (generada automáticamente si no se proporciona)
        """
        self.success = success
        self.message_id = message_id
        self.data = data
        
        if isinstance(error, dict):
            self.error = MCPError.from_dict(error)
        else:
            self.error = error
            
        self.timestamp = timestamp or datetime.datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la respuesta a un diccionario para transmisión.
        
        Returns:
            Diccionario con la información de la respuesta
        """
        result = {
            "success": self.success,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error.to_dict() if self.error else {
                "code": MCPErrorCode.SERVER_ERROR.value,
                "message": "Error desconocido"
            }
            
        return result
    
    def to_json(self) -> str:
        """
        Convierte la respuesta a una cadena JSON.
        
        Returns:
            Cadena JSON con la información de la respuesta
        """
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """
        Crea una respuesta desde un diccionario.
        
        Args:
            data: Diccionario con la información de la respuesta
            
        Returns:
            Instancia de MCPResponse
        """
        success = data.get("success", False)
        
        return cls(
            success=success,
            message_id=data.get("message_id", ""),
            data=data.get("data") if success else None,
            error=data.get("error") if not success else None,
            timestamp=datetime.datetime.fromisoformat(data.get("timestamp")) 
                if "timestamp" in data else None
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """
        Crea una respuesta desde una cadena JSON.
        
        Args:
            json_str: Cadena JSON con la información de la respuesta
            
        Returns:
            Instancia de MCPResponse
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def success_response(cls, message_id: str, data: T) -> 'MCPResponse[T]':
        """
        Crea una respuesta exitosa.
        
        Args:
            message_id: ID del mensaje al que responde
            data: Datos de la respuesta
            
        Returns:
            Instancia de MCPResponse con success=True
        """
        return cls(success=True, message_id=message_id, data=data)
    
    @classmethod
    def error_response(
        cls, 
        message_id: str, 
        code: Union[MCPErrorCode, str], 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> 'MCPResponse[None]':
        """
        Crea una respuesta de error.
        
        Args:
            message_id: ID del mensaje al que responde
            code: Código de error
            message: Mensaje descriptivo
            details: Detalles adicionales
            
        Returns:
            Instancia de MCPResponse con success=False
        """
        error = MCPError(code=code, message=message, details=details)
        return cls(success=False, message_id=message_id, error=error) 