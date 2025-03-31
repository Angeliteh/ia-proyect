"""
Adaptadores y conectores genéricos para MCP.

Este módulo proporciona conectores para integrar 
diferentes tipos de recursos con el protocolo MCP.
"""

try:
    from .filesystem import FilesystemConnector
except ImportError:
    pass

__all__ = []

# Agregar dinámicamente los conectores disponibles
if 'FilesystemConnector' in globals():
    __all__.append('FilesystemConnector') 