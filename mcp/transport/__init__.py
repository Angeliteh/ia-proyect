"""
Componentes de transporte para MCP.

Este módulo proporciona mecanismos de transporte para la comunicación
entre clientes y servidores MCP, incluyendo HTTP, WebSockets, etc.
"""

try:
    from .http import HttpTransport
except ImportError:
    pass

try:
    from .http import MCPHttpServer
except ImportError:
    pass

__all__ = []

# Agregar dinámicamente los transportes disponibles
if 'HttpTransport' in globals():
    __all__.append('HttpTransport')

if 'MCPHttpServer' in globals():
    __all__.append('MCPHttpServer') 