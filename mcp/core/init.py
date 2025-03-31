"""
Inicialización del sistema MCP.

Este módulo proporciona funciones para inicializar y cerrar
el sistema MCP, así como para acceder al registro global.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any

from .registry import MCPRegistry
from .protocol import MCPError, MCPErrorCode

# Configurar logger
logger = logging.getLogger("mcp.init")

# Variable global para almacenar la instancia del registro
_registry = None

# Variable global para indicar si MCP ha sido inicializado
_mcp_initialized = False

def initialize_mcp(config_path: Optional[str] = None) -> MCPRegistry:
    """
    Inicializa el sistema MCP de forma sincrónica.
    
    Args:
        config_path: Ruta al archivo de configuración YAML (opcional)
    
    Returns:
        MCPRegistry: Instancia del registro MCP
        
    Raises:
        MCPError: Si ocurre un error durante la inicialización
    """
    global _registry, _mcp_initialized
    
    # Evitar inicialización múltiple
    if _mcp_initialized:
        logger.debug("MCP ya está inicializado, ignorando llamada")
        return _registry
    
    logger.info("Inicializando subsistema MCP")
    
    try:
        if _registry is None:
            _registry = MCPRegistry()
            
        # Si se proporcionó una ruta de configuración, cargarla
        if config_path:
            if not os.path.exists(config_path):
                # Intentar buscar en rutas relativas
                alt_paths = [
                    os.path.join("config", "mcp_config.yaml"),
                    os.path.join(os.path.dirname(__file__), "..", "..", "config", "mcp_config.yaml")
                ]
                
                for path in alt_paths:
                    if os.path.exists(path):
                        config_path = path
                        break
                else:
                    raise FileNotFoundError(f"No se encontró el archivo de configuración MCP: {config_path}")
            
            logger.info(f"Cargando configuración MCP desde: {config_path}")
            _registry.load_config_from_file(config_path)
        else:
            logger.warning("No se proporcionó archivo de configuración MCP. Usando valores por defecto.")
            
        # Marcar como inicializado
        _mcp_initialized = True
        
        logger.info("Subsistema MCP inicializado correctamente")
        return _registry
        
    except Exception as e:
        logger.exception("Error inicializando subsistema MCP")
        raise MCPError(
            code=MCPErrorCode.SERVER_ERROR,
            message=f"Error inicializando subsistema MCP: {str(e)}"
        )

def is_mcp_initialized() -> bool:
    """
    Verifica si el sistema MCP ya ha sido inicializado.
    
    Returns:
        bool: True si MCP está inicializado, False en caso contrario
    """
    global _mcp_initialized
    return _mcp_initialized

async def async_initialize_mcp(config_path: Optional[str] = None):
    """
    Inicializa el subsistema MCP de forma asíncrona.
    
    Esta función debe ser llamada antes de utilizar cualquier
    componente asíncrono del sistema MCP.
    
    Args:
        config_path: Ruta al archivo de configuración YAML (opcional)
    """
    global _mcp_initialized
    
    # Inicializar primero de forma sincrónica
    if not _mcp_initialized:
        initialize_mcp(config_path)
    
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
        try:
            await _registry.shutdown_all_servers()
            _registry = None
        except Exception as e:
            logger.error(f"Error cerrando servidores registrados: {e}")
    
    # Marcar como no inicializado
    _mcp_initialized = False
    _registry = None
    
    logger.info("Subsistema MCP cerrado correctamente")

def get_registry() -> Optional[MCPRegistry]:
    """
    Obtiene la instancia del registro MCP.
    
    Returns:
        MCPRegistry: Instancia del registro MCP, o None si MCP no está inicializado
    """
    global _registry
    
    if not _mcp_initialized:
        logger.warning("Intentando obtener registro MCP sin inicializar")
        return None
        
    return _registry 