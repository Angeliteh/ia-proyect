"""
Núcleo del Model Context Protocol (MCP).

Este módulo contiene las clases e interfaces fundamentales para
implementar el Model Context Protocol (MCP), un estándar para
conectar modelos de IA con diversas fuentes de datos y herramientas.
"""

from .protocol import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPError
from .server_base import MCPServerBase
from .client_base import MCPClientBase
from .registry import MCPRegistry

__all__ = [
    'MCPMessage', 
    'MCPResponse', 
    'MCPAction', 
    'MCPResource', 
    'MCPError',
    'MCPServerBase',
    'MCPClientBase',
    'MCPRegistry'
] 