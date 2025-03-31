"""
Módulo del servidor MCP para el sistema de memoria.

Este módulo proporciona acceso al sistema de memoria de agentes
a través del protocolo MCP.
"""

from .memory_server import MemoryServer

# Exportar las clases para que sean accesibles cuando
# se importa el paquete
__all__ = ["MemoryServer"] 