"""
Base Protocol for Model Context Protocol (MCP).

Este módulo define las clases e interfaces base para implementar
el Model Context Protocol (MCP) según el estándar de Anthropic.
"""

import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Union

class MCPMethod(str, Enum):
    """Métodos estándar definidos por el protocolo MCP."""
    
    # Métodos para descubrimiento y configuración
    LIST_TOOLS = "list_tools"
    LIST_SERVERS = "list_servers"
    GET_SERVER_INFO = "get_server_info"
    
    # Métodos para operaciones con herramientas
    CALL_TOOL = "call_tool"
    
    # Métodos para gestión de contexto
    GET_CONTEXT = "get_context"
    PUT_CONTEXT = "put_context"

class MCPResponseStatus(str, Enum):
    """Estados de respuesta del protocolo MCP."""
    
    SUCCESS = "success"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"

class MCPRequest:
    """
    Representa una solicitud según el protocolo MCP.
    
    Attributes:
        method: Método MCP a invocar
        params: Parámetros para el método
        id: Identificador único de la solicitud
    """
    
    def __init__(
        self, 
        method: Union[MCPMethod, str], 
        params: Dict[str, Any] = None, 
        request_id: str = None
    ):
        """
        Inicializa una solicitud MCP.
        
        Args:
            method: Método MCP a invocar
            params: Parámetros para el método
            request_id: Identificador único de la solicitud
        """
        self.method = method if isinstance(method, str) else method.value
        self.params = params or {}
        self.id = request_id
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la solicitud a un diccionario para serialización."""
        return {
            "jsonrpc": "2.0",
            "method": self.method,
            "params": self.params,
            "id": self.id
        }
    
    def to_json(self) -> str:
        """Convierte la solicitud a una cadena JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPRequest':
        """Crea una instancia desde un diccionario."""
        return cls(
            method=data.get("method"),
            params=data.get("params", {}),
            request_id=data.get("id")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPRequest':
        """Crea una instancia desde una cadena JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)

class MCPResponse:
    """
    Representa una respuesta según el protocolo MCP.
    
    Attributes:
        result: Resultado de la operación
        error: Información de error, si ocurrió
        id: Identificador de la solicitud correspondiente
        status: Estado de la respuesta
    """
    
    def __init__(
        self, 
        result: Any = None, 
        error: Dict[str, Any] = None, 
        response_id: str = None,
        status: MCPResponseStatus = MCPResponseStatus.SUCCESS
    ):
        """
        Inicializa una respuesta MCP.
        
        Args:
            result: Resultado de la operación
            error: Información de error, si ocurrió
            response_id: Identificador de la solicitud correspondiente
            status: Estado de la respuesta
        """
        self.result = result
        self.error = error
        self.id = response_id
        self.status = status.value if isinstance(status, MCPResponseStatus) else status
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la respuesta a un diccionario para serialización."""
        response_dict = {
            "jsonrpc": "2.0",
            "id": self.id
        }
        
        if self.error is not None:
            response_dict["error"] = self.error
        else:
            response_dict["result"] = self.result
            
        return response_dict
    
    def to_json(self) -> str:
        """Convierte la respuesta a una cadena JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPResponse':
        """Crea una instancia desde un diccionario."""
        return cls(
            result=data.get("result"),
            error=data.get("error"),
            response_id=data.get("id"),
            status=MCPResponseStatus.ERROR if "error" in data else MCPResponseStatus.SUCCESS
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """Crea una instancia desde una cadena JSON."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def error_response(
        cls, 
        message: str, 
        code: int = -32603, 
        response_id: str = None, 
        status: MCPResponseStatus = MCPResponseStatus.ERROR
    ) -> 'MCPResponse':
        """
        Crea una respuesta de error.
        
        Args:
            message: Mensaje de error
            code: Código de error
            response_id: Identificador de la solicitud
            status: Estado de la respuesta
            
        Returns:
            Instancia MCPResponse con información de error
        """
        return cls(
            error={
                "code": code,
                "message": message
            },
            response_id=response_id,
            status=status
        )

class MCPTool:
    """
    Representa una herramienta disponible en un servidor MCP.
    
    Attributes:
        name: Nombre de la herramienta
        description: Descripción de la herramienta
        input_schema: Esquema de entrada JSON Schema
        output_schema: Esquema de salida JSON Schema
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa una herramienta MCP.
        
        Args:
            name: Nombre de la herramienta
            description: Descripción de la herramienta
            input_schema: Esquema de entrada JSON Schema
            output_schema: Esquema de salida JSON Schema
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {"type": "string"}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la herramienta a un diccionario para serialización."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema
        }

class MCPInterface(ABC):
    """Interfaz base para clientes y servidores MCP."""
    
    def __init__(self):
        """Inicializa la interfaz MCP."""
        self.logger = logging.getLogger(f"mcp.{self.__class__.__name__}")
    
    @abstractmethod
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Maneja una solicitud MCP.
        
        Args:
            request: Solicitud MCP
            
        Returns:
            Respuesta MCP
        """
        pass 