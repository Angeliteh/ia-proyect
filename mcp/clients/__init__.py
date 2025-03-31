"""
Implementaciones de clientes MCP.

Este módulo contiene las implementaciones concretas de clientes MCP
para diferentes propósitos y protocolos de transporte.

Clientes disponibles:
- SimpleDirectClient: Cliente simple para conexión directa (en memoria)
- HttpClient: Cliente para conexión HTTP
- BraveSearchClient: Cliente específico para Brave Search API

Los clientes MCP implementan la clase base MCPClientBase y proporcionan
métodos para comunicarse con servidores MCP.
"""

# Importar clientes disponibles
try:
    from .direct_client import SimpleDirectClient
except ImportError:
    pass

try:
    from .http_client import HttpClient
except ImportError:
    pass

try:
    from .brave_search_client import BraveSearchClient
except ImportError:
    pass

# Definir los componentes públicos
__all__ = []

# Agregar dinámicamente los clientes disponibles
if 'SimpleDirectClient' in globals():
    __all__.append('SimpleDirectClient')

if 'HttpClient' in globals():
    __all__.append('HttpClient')
    
if 'BraveSearchClient' in globals():
    __all__.append('BraveSearchClient') 