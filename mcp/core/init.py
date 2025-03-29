"""
Inicialización del sistema MCP.

Este módulo proporciona funciones para inicializar y cerrar
el sistema MCP, así como para acceder al registro global.
"""

import logging
import asyncio
from typing import Optional

from .registry import MCPRegistry

# Configurar logger
logger = logging.getLogger("mcp.init")

# Variable global para almacenar la instancia del registro
_registry = None

# Variable global para indicar si MCP ha sido inicializado
_mcp_initialized = False

def initialize_mcp() -> MCPRegistry:
    """
    Inicializa el sistema MCP de forma sincrónica.
    
    Returns:
        MCPRegistry: Instancia del registro MCP
    """
    global _registry, _mcp_initialized
    
    # Evitar inicialización múltiple
    if _mcp_initialized:
        logger.debug("MCP ya está inicializado, ignorando llamada")
        return _registry
    
    logger.info("Inicializando subsistema MCP")
    
    if _registry is None:
        from .registry import MCPRegistry
        _registry = MCPRegistry()
    
    # Marcar como inicializado
    _mcp_initialized = True
    
    return _registry

def is_mcp_initialized() -> bool:
    """
    Verifica si el sistema MCP ya ha sido inicializado.
    
    Returns:
        bool: True si MCP está inicializado, False en caso contrario
    """
    global _mcp_initialized
    return _mcp_initialized

async def async_initialize_mcp():
    """
    Inicializa el subsistema MCP de forma asíncrona.
    
    Esta función debe ser llamada antes de utilizar cualquier
    componente asíncrono del sistema MCP.
    """
    global _mcp_initialized
    
    # Inicializar primero de forma sincrónica
    if not _mcp_initialized:
        initialize_mcp()
    
    # Aquí se pueden realizar inicializaciones asíncronas adicionales
    # ...

async def shutdown_mcp():
    """
    Cierra el sistema MCP y libera recursos.
    
    Esta función debe ser llamada cuando ya no se vaya a utilizar
    ningún componente del sistema MCP.
    """
    global _registry, _mcp_initialized
    
    if not _mcp_initialized:
        logger.debug("MCP no estaba inicializado, ignorando cierre")
        return
    
    logger.info("Cerrando subsistema MCP")
    
    # Cerrar todos los servidores registrados
    if _registry:
        # Simplemente desregistramos todos los componentes
        # ya que podríamos no tener la implementación de close_all_servers
        try:
            _registry = None
        except Exception as e:
            logger.error(f"Error cerrando registros: {e}")
    
    # Marcar como no inicializado
    _mcp_initialized = False
    _registry = None

def get_registry() -> Optional[MCPRegistry]:
    """
    Obtiene la instancia del registro MCP.
    
    Returns:
        MCPRegistry: Instancia del registro MCP, o None si MCP no está inicializado
    """
    global _registry
    return _registry 