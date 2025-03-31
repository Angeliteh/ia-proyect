"""
Base para servidores MCP.

Este módulo define la clase base para implementar servidores MCP.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union

# Importar clases del protocolo MCP
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp.protocol import (
    MCPMethod, 
    MCPResponseStatus, 
    MCPRequest, 
    MCPResponse, 
    MCPTool, 
    MCPInterface
)

class MCPServer(MCPInterface):
    """
    Clase base para implementar servidores MCP que exponen herramientas.
    
    Los servidores MCP proporcionan un conjunto de herramientas que pueden
    ser utilizadas por los clientes MCP para realizar operaciones específicas.
    
    Attributes:
        name: Nombre del servidor
        description: Descripción del servidor
        tools: Diccionario de herramientas disponibles
        logger: Logger para el servidor
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Inicializa un servidor MCP.
        
        Args:
            name: Nombre del servidor
            description: Descripción del servidor
        """
        super().__init__()
        self.name = name
        self.description = description
        self.tools: Dict[str, MCPTool] = {}
        self.handlers: Dict[str, Callable] = {
            MCPMethod.LIST_TOOLS: self.list_tools,
            MCPMethod.GET_SERVER_INFO: self.get_server_info,
            MCPMethod.CALL_TOOL: self.call_tool
        }
        
        self.logger = logging.getLogger(f"mcp_server.{name}")
        self.logger.info(f"Servidor MCP '{name}' inicializado")
    
    def register_tool(self, tool: MCPTool, handler: Callable):
        """
        Registra una herramienta en el servidor.
        
        Args:
            tool: Definición de la herramienta
            handler: Función que implementa la funcionalidad de la herramienta
        """
        self.tools[tool.name] = tool
        self.handlers[f"tool.{tool.name}"] = handler
        self.logger.info(f"Herramienta '{tool.name}' registrada")
    
    async def list_tools(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Retorna la lista de herramientas disponibles en este servidor.
        
        Args:
            params: Parámetros de la solicitud (no utilizado)
            
        Returns:
            Diccionario con la lista de herramientas
        """
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
    
    async def get_server_info(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Retorna información sobre este servidor.
        
        Args:
            params: Parámetros de la solicitud (no utilizado)
            
        Returns:
            Diccionario con información del servidor
        """
        return {
            "name": self.name,
            "description": self.description,
            "toolCount": len(self.tools)
        }
    
    async def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoca una herramienta específica.
        
        Args:
            params: Parámetros de la solicitud, debe incluir 'tool' y 'args'
            
        Returns:
            Resultado de la invocación de la herramienta
            
        Raises:
            ValueError: Si la herramienta no existe o los parámetros son inválidos
        """
        tool_name = params.get("tool")
        args = params.get("args", {})
        
        if not tool_name:
            raise ValueError("No se especificó el nombre de la herramienta")
            
        if tool_name not in self.tools:
            raise ValueError(f"Herramienta '{tool_name}' no encontrada")
            
        handler = self.handlers.get(f"tool.{tool_name}")
        if not handler:
            raise ValueError(f"No hay controlador para la herramienta '{tool_name}'")
            
        self.logger.info(f"Invocando herramienta '{tool_name}'")
        try:
            result = await handler(args)
            return {"result": result}
        except Exception as e:
            self.logger.error(f"Error invocando herramienta '{tool_name}': {e}")
            raise ValueError(f"Error invocando herramienta: {str(e)}")
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Maneja una solicitud MCP.
        
        Args:
            request: Solicitud MCP
            
        Returns:
            Respuesta MCP
        """
        try:
            method = request.method
            params = request.params
            
            handler = self.handlers.get(method)
            if not handler:
                return MCPResponse.error_response(
                    f"Método no soportado: {method}",
                    code=-32601,
                    response_id=request.id,
                    status=MCPResponseStatus.NOT_FOUND
                )
                
            result = await handler(params)
            return MCPResponse(result=result, response_id=request.id)
            
        except ValueError as e:
            return MCPResponse.error_response(
                str(e),
                code=-32602,
                response_id=request.id,
                status=MCPResponseStatus.BAD_REQUEST
            )
        except Exception as e:
            self.logger.error(f"Error manejando solicitud: {e}")
            return MCPResponse.error_response(
                str(e),
                code=-32603,
                response_id=request.id,
                status=MCPResponseStatus.ERROR
            )
    
    def start_server(self, host: str = "localhost", port: int = 8080):
        """
        Inicia el servidor MCP en el puerto especificado.
        
        Esta es una implementación simple que debe ser extendida
        por las subclases para proporcionar el protocolo de transporte.
        
        Args:
            host: Host para escuchar
            port: Puerto para escuchar
        """
        self.logger.info(f"Iniciando servidor MCP '{self.name}' en {host}:{port}")
        # Esta implementación debe ser proporcionada por las subclases 