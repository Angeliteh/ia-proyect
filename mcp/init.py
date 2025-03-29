"""
Inicialización del subsistema MCP.

Este módulo proporciona funciones para inicializar y configurar
el subsistema MCP (Model Context Protocol) en la aplicación.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union

from .core.registry import MCPRegistry
from .core.protocol import MCPError, MCPErrorCode

logger = logging.getLogger("mcp.init")

async def initialize_mcp(config_path: Optional[str] = None) -> MCPRegistry:
    """
    Inicializa el subsistema MCP.
    
    Args:
        config_path: Ruta al archivo de configuración YAML (opcional)
        
    Returns:
        Instancia del registro MCP inicializado
        
    Raises:
        MCPError: Si ocurre un error durante la inicialización
    """
    try:
        registry = MCPRegistry()
        
        # Si se proporcionó una ruta de configuración, cargarla
        if config_path:
            if not os.path.exists(config_path):
                # Intentar buscar en rutas relativas
                alt_paths = [
                    os.path.join("config", "mcp_config.yaml"),
                    os.path.join(os.path.dirname(__file__), "..", "config", "mcp_config.yaml")
                ]
                
                for path in alt_paths:
                    if os.path.exists(path):
                        config_path = path
                        break
                else:
                    raise FileNotFoundError(f"No se encontró el archivo de configuración MCP: {config_path}")
            
            logger.info(f"Cargando configuración MCP desde: {config_path}")
            registry.load_config_from_file(config_path)
        else:
            logger.warning("No se proporcionó archivo de configuración MCP. Usando valores por defecto.")
        
        logger.info("Subsistema MCP inicializado correctamente")
        return registry
        
    except Exception as e:
        logger.exception("Error inicializando subsistema MCP")
        raise MCPError(
            code=MCPErrorCode.SERVER_ERROR,
            message=f"Error inicializando subsistema MCP: {str(e)}"
        )

async def shutdown_mcp() -> None:
    """
    Cierra el subsistema MCP y todos sus servidores.
    """
    try:
        registry = MCPRegistry()
        registry.shutdown_all_servers()
        logger.info("Subsistema MCP cerrado correctamente")
    except Exception as e:
        logger.exception("Error cerrando subsistema MCP")
        raise MCPError(
            code=MCPErrorCode.SERVER_ERROR,
            message=f"Error cerrando subsistema MCP: {str(e)}"
        )

def get_registry() -> MCPRegistry:
    """
    Obtiene la instancia del registro MCP.
    
    Returns:
        Instancia del registro MCP
    """
    return MCPRegistry() 