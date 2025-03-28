"""
Paquete MCP (Model Context Protocol).

Este paquete implementa el Model Context Protocol (MCP) según el estándar de Anthropic,
proporcionando componentes para la comunicación entre modelos de IA y fuentes de datos.
"""

# Importar componentes principales
from .protocol import (
    MCPMethod,
    MCPResponseStatus,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPInterface
)

# Exportar componentes principales
__all__ = [
    'MCPMethod',
    'MCPResponseStatus',
    'MCPRequest',
    'MCPResponse',
    'MCPTool',
    'MCPInterface'
] 