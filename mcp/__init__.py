"""
Implementación del Model Context Protocol (MCP).

Este paquete implementa el estándar MCP desarrollado para facilitar la comunicación
entre modelos de IA y fuentes de datos/herramientas externas, proporcionando 
una infraestructura que permite a los modelos acceder a datos externos de forma 
unificada a través de un protocolo común.

El MCP define un formato estándar para solicitudes y respuestas entre
clientes (modelos o agentes) y servidores (fuentes de datos o herramientas).

Módulos principales:
- core: Componentes fundamentales del protocolo
- servers: Implementaciones de servidores MCP
- clients: Implementaciones de clientes MCP
- transport: Componentes de transporte y comunicación
- connectors: Adaptadores para sistemas externos
"""

# Importar desde el módulo core
from mcp.core import (
    # Clases del protocolo
    MCPMessage,
    MCPResponse,
    MCPAction,
    MCPResource,
    MCPError,
    MCPErrorCode,
    
    # Clases base
    MCPServerBase,
    MCPClientBase,
    
    # Sistema de registro
    MCPRegistry,
    
    # Funciones de inicialización
    initialize_mcp,
    async_initialize_mcp,
    shutdown_mcp,
    get_registry,
    is_mcp_initialized,
    
    # Gestor principal
    MCP
)

# Importar conectores comunes para conveniencia
try:
    from mcp.connectors.http_client import MCPHttpClient
except ImportError:
    # Si no existe, no interrumpir la carga del módulo
    pass

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
    
    # Gestor principal
    'MCP'
]

# Si los conectores están disponibles, incluirlos
if 'MCPHttpClient' in globals():
    __all__.append('MCPHttpClient')

# Versión del paquete
__version__ = '0.1.0' 