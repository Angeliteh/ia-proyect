"""
Implementación del Model Context Protocol (MCP).

Este paquete implementa el estándar MCP desarrollado por Anthropic,
proporcionando una infraestructura para que los modelos de IA puedan
acceder a datos externos de forma unificada a través de un protocolo
común.

El MCP define un formato estándar para solicitudes y respuestas entre
clientes (modelos o agentes) y servidores (fuentes de datos o herramientas).
"""

# Importar funciones de inicialización
from mcp.core.init import (
    initialize_mcp, 
    async_initialize_mcp,
    shutdown_mcp, 
    get_registry,
    is_mcp_initialized
)

# Importar el gestor principal
from mcp.core.mcp_manager import MCP

# Importar el monitor de recursos
from mcp.utils.resource_monitor import ResourceMonitor

# Importar clases principales del protocolo
from mcp.core.protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError, 
    MCPErrorCode
)

# Importar clases base
from mcp.core.server_base import MCPServerBase
from mcp.core.client_base import MCPClientBase
from mcp.core.registry import MCPRegistry

# Importar conectores
from mcp.connectors.http_client import MCPHttpClient

# Definir los componentes públicos del paquete
__all__ = [
    # Funciones de inicialización
    'initialize_mcp',
    'async_initialize_mcp',
    'shutdown_mcp',
    'get_registry',
    'is_mcp_initialized',
    
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
    'MCPRegistry',
    
    # Conectores
    'MCPHttpClient',
    
    # Gestor principal
    'MCP'
]

# Versión del paquete
__version__ = '0.1.0' 