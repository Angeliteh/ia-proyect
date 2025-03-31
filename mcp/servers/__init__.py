"""
Implementaciones de servidores MCP.

Este módulo contiene las implementaciones concretas de servidores MCP
para diferentes propósitos y protocolos de transporte.

Servidores disponibles:
- EchoServer: Servidor simple de eco para pruebas
- FilesystemServer: Servidor para acceso al sistema de archivos
- BraveSearchServer: Servidor para búsquedas web usando Brave Search API

Los servidores MCP implementan la clase base MCPServerBase y proporcionan
funcionalidades específicas a través del protocolo MCP.
"""

# Importar servidores disponibles
try:
    from .echo_server import EchoServer
except ImportError:
    pass

try:
    from .filesystem_server import FilesystemServer
except ImportError:
    pass

try:
    from .brave_search_server import BraveSearchServer
except ImportError:
    pass

# Definir los componentes públicos
__all__ = []

# Agregar dinámicamente los servidores disponibles
if 'EchoServer' in globals():
    __all__.append('EchoServer')

if 'FilesystemServer' in globals():
    __all__.append('FilesystemServer')
    
if 'BraveSearchServer' in globals():
    __all__.append('BraveSearchServer') 