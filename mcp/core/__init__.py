"""
Módulo Core del Model Context Protocol (MCP).

Este módulo contiene los componentes fundamentales del protocolo MCP:
1. Definiciones del protocolo (MCPMessage, MCPResponse, etc.)
2. Clases base para servidores y clientes
3. Sistema de registro y gestión
4. Utilidades de inicialización

El módulo core es la base sobre la que se construyen todas las implementaciones
específicas de MCP.
"""

# 1. Importar clases del protocolo
from .protocol import (
    # Mensajería
    MCPMessage,
    MCPResponse,
    
    # Enumeraciones
    MCPAction,
    MCPResource,
    
    # Manejo de errores
    MCPError,
    MCPErrorCode
)

# 2. Importar clases base
from .server_base import MCPServerBase
from .client_base import MCPClientBase

# 3. Importar sistema de registro
from .registry import MCPRegistry

# 4. Importar funciones de inicialización
from .init import (
    initialize_mcp,
    async_initialize_mcp,
    shutdown_mcp,
    get_registry,
    is_mcp_initialized
)

# 5. Importar gestor MCP
from .mcp_manager import MCP

# Definir los componentes públicos del módulo
__all__ = [
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
    
    # Sistema de registro
    'MCPRegistry',
    
    # Funciones de inicialización
    'initialize_mcp',
    'async_initialize_mcp',
    'shutdown_mcp',
    'get_registry',
    'is_mcp_initialized',
    
    # Gestor principal
    'MCP'
] 