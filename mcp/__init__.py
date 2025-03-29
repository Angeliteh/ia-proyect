"""
Paquete MCP (Model Context Protocol).

Este paquete implementa el estándar Model Context Protocol (MCP)
desarrollado por Anthropic, que proporciona una forma unificada
para conectar modelos de IA con fuentes de datos y herramientas.
"""

from .init import initialize_mcp, shutdown_mcp, get_registry

# Importar componentes principales para facilitar su uso
from .core.protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError,
    MCPErrorCode
)
from .core.server_base import MCPServerBase
from .core.client_base import MCPClientBase, MCPHttpClient
from .core.registry import MCPRegistry

__all__ = [
    # Funciones de inicialización
    'initialize_mcp',
    'shutdown_mcp',
    'get_registry',
    
    # Clases del protocolo
    'MCPMessage',
    'MCPResponse',
    'MCPAction',
    'MCPResource',
    'MCPError',
    'MCPErrorCode',
    
    # Clases base
    'MCPServerBase',
    'MCPClientBase',
    'MCPHttpClient',
    'MCPRegistry'
]

__version__ = '0.1.0' 