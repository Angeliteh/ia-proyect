"""
Base para clientes MCP.

Este módulo define la clase base para implementar clientes MCP.
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

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

class MCPClient(MCPInterface):
    """
    Clase base para implementar clientes MCP que se conectan a servidores MCP.
    
    Los clientes MCP se conectan a servidores MCP para utilizar las herramientas
    y datos que estos exponen.
    
    Attributes:
        server_url: URL del servidor MCP
        server_info: Información sobre el servidor
        tools: Herramientas disponibles en el servidor
        timeout: Tiempo máximo para esperar respuestas
        logger: Logger para el cliente
    """
    
    def __init__(
        self, 
        server_url: str, 
        timeout: int = 30,
        retry_attempts: int = 3
    ):
        """
        Inicializa un cliente MCP.
        
        Args:
            server_url: URL del servidor MCP
            timeout: Tiempo máximo (en segundos) para esperar respuestas
            retry_attempts: Número de intentos de reconexión
        """
        super().__init__()
        self.server_url = server_url
        self.server_info = None
        self.tools: Dict[str, MCPTool] = {}
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        
        self.logger = logging.getLogger(f"mcp_client.{server_url.replace('://', '_').replace('/', '_')}")
        self.logger.info(f"Cliente MCP inicializado para servidor '{server_url}'")
    
    @abstractmethod
    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """
        Envía una solicitud al servidor MCP.
        
        Esta es una implementación abstracta que debe ser proporcionada
        por las subclases para el protocolo de transporte específico.
        
        Args:
            request: Solicitud MCP a enviar
            
        Returns:
            Respuesta MCP del servidor
        """
        pass
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Maneja una solicitud pasándola al servidor MCP.
        
        Args:
            request: Solicitud MCP
            
        Returns:
            Respuesta MCP del servidor
        """
        try:
            return await self._send_request(request)
        except Exception as e:
            self.logger.error(f"Error enviando solicitud al servidor: {e}")
            return MCPResponse.error_response(
                f"Error de comunicación con el servidor: {str(e)}",
                code=-32000,
                response_id=request.id,
                status=MCPResponseStatus.ERROR
            )
    
    async def list_tools(self) -> List[MCPTool]:
        """
        Obtiene la lista de herramientas disponibles en el servidor.
        
        Returns:
            Lista de herramientas disponibles
            
        Raises:
            ConnectionError: Si no se puede conectar al servidor
        """
        request = MCPRequest(method=MCPMethod.LIST_TOOLS, request_id=str(uuid.uuid4()))
        response = await self.handle_request(request)
        
        if response.error:
            self.logger.error(f"Error al listar herramientas: {response.error}")
            raise ConnectionError(f"Error al listar herramientas: {response.error}")
            
        tools_data = response.result.get("tools", [])
        tools = []
        
        for tool_data in tools_data:
            tool = MCPTool(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data["inputSchema"],
                output_schema=tool_data.get("outputSchema", {"type": "string"})
            )
            self.tools[tool.name] = tool
            tools.append(tool)
            
        return tools
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre el servidor.
        
        Returns:
            Información del servidor
            
        Raises:
            ConnectionError: Si no se puede conectar al servidor
        """
        request = MCPRequest(method=MCPMethod.GET_SERVER_INFO, request_id=str(uuid.uuid4()))
        response = await self.handle_request(request)
        
        if response.error:
            self.logger.error(f"Error al obtener información del servidor: {response.error}")
            raise ConnectionError(f"Error al obtener información del servidor: {response.error}")
            
        self.server_info = response.result
        return response.result
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Any:
        """
        Invoca una herramienta en el servidor.
        
        Args:
            tool_name: Nombre de la herramienta a invocar
            args: Argumentos para la herramienta
            
        Returns:
            Resultado de la invocación
            
        Raises:
            ValueError: Si la herramienta no existe
            ConnectionError: Si no se puede conectar al servidor
        """
        if not self.tools:
            await self.list_tools()
            
        if tool_name not in self.tools:
            raise ValueError(f"Herramienta '{tool_name}' no encontrada en el servidor")
            
        request = MCPRequest(
            method=MCPMethod.CALL_TOOL,
            params={
                "tool": tool_name,
                "args": args or {}
            },
            request_id=str(uuid.uuid4())
        )
        
        response = await self.handle_request(request)
        
        if response.error:
            self.logger.error(f"Error al invocar herramienta '{tool_name}': {response.error}")
            raise ConnectionError(f"Error al invocar herramienta: {response.error}")
            
        return response.result.get("result") 