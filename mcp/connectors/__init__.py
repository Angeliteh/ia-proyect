"""
Módulo de conectores para el Model Context Protocol (MCP).

Este módulo contiene implementaciones de conectores que permiten la comunicación
entre clientes y servidores MCP utilizando diferentes protocolos de transporte
como HTTP, WebSockets, línea de comandos, etc.
"""

from mcp.connectors.http_client import MCPHttpClient

__all__ = ['MCPHttpClient'] 