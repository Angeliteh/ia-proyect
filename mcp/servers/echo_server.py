"""
Servidor MCP de eco para pruebas.

Este servidor simplemente devuelve (eco) los datos que recibe,
y es útil para probar el protocolo MCP.
"""

import asyncio
from typing import Dict, Any

from mcp.core import (
    MCPServerBase, 
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPErrorCode
)

class EchoServer(MCPServerBase):
    """
    Un servidor MCP sencillo que simplemente devuelve (eco) los datos que recibe.
    
    Este servidor es útil para propósitos de prueba y demostración.
    """
    
    def __init__(self, name: str = "echo_server"):
        """
        Inicializa el servidor de eco.
        
        Args:
            name: Nombre del servidor (por defecto: "echo_server")
        """
        super().__init__(
            name=name,
            description="Servidor MCP de eco para pruebas",
            auth_required=False,
            supported_actions=[
                MCPAction.PING,
                MCPAction.CAPABILITIES, 
                MCPAction.GET,
                MCPAction.LIST,
                MCPAction.SEARCH,
                "echo"  # Acción personalizada
            ],
            supported_resources=[
                MCPResource.SYSTEM,
                "test"  # Recurso personalizado
            ]
        )
        # Datos simulados para demostración
        self.test_data = {
            "/test1": {"id": "1", "name": "Test Item 1", "value": "Hello, world!"},
            "/test2": {"id": "2", "name": "Test Item 2", "value": "Hello again!"},
            "/test/nested": {"id": "3", "name": "Nested Item", "value": "I'm nested!"}
        }
        
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja las acciones recibidas por el servidor.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta al mensaje
        """
        # Simular un pequeño retraso para hacer la demo más realista
        await asyncio.sleep(0.1)
        
        self.logger.info(f"EchoServer recibió: {message.action} - {message.resource_path}")
        
        # Acción personalizada de eco
        if message.action == "echo":
            # Simplemente devolvemos los datos recibidos
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "echo": message.data,
                    "message": "¡Eco del servidor!",
                    "path": message.resource_path
                }
            )
            
        # Acción estándar GET
        elif message.action == MCPAction.GET.value:
            # Verificamos si el recurso existe
            if message.resource_path in self.test_data:
                return MCPResponse.success_response(
                    message_id=message.id,
                    data=self.test_data[message.resource_path]
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Recurso no encontrado: {message.resource_path}"
                )
                
        # Acción estándar LIST
        elif message.action == MCPAction.LIST.value:
            # Listamos recursos que comienzan con el path proporcionado
            result = {}
            for path, data in self.test_data.items():
                if path.startswith(message.resource_path):
                    result[path] = data
                    
            return MCPResponse.success_response(
                message_id=message.id,
                data={"items": result}
            )
            
        # Acción estándar SEARCH
        elif message.action == MCPAction.SEARCH.value:
            # Simulamos una búsqueda simple por valor
            query = message.data.get("query", "")
            result = {}
            
            for path, data in self.test_data.items():
                if query.lower() in str(data).lower():
                    result[path] = data
                    
            return MCPResponse.success_response(
                message_id=message.id,
                data={"results": result, "query": query}
            )
            
        # Acción no implementada
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Acción no implementada: {message.action}"
            ) 