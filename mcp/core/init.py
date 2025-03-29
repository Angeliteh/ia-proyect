"""
Inicialización del subsistema MCP.

Este módulo proporciona funciones para inicializar y cerrar
el subsistema MCP, así como para acceder al registro central.
"""

import asyncio
import logging
import os
from typing import Optional

from .registry import MCPRegistry

# Configurar logging
logger = logging.getLogger("mcp.init")

# Variable global para almacenar la instancia del registro
_registry = None

def initialize_mcp() -> MCPRegistry:
    """
    Inicializa el subsistema MCP.
    
    Esta función debe ser llamada antes de usar cualquier
    funcionalidad del MCP. Configura el registro central
    y carga la configuración necesaria.
    
    Returns:
        MCPRegistry: Instancia del registro MCP
    """
    global _registry
    
    logger.info("Inicializando subsistema MCP")
    
    # Crear registro central si no existe
    if _registry is None:
        # Usar el constructor directamente en lugar de get_instance
        # La clase MCPRegistry implementa el patrón singleton en su método __new__
        _registry = MCPRegistry()
        
    return _registry

def shutdown_mcp() -> None:
    """
    Cierra el subsistema MCP.
    
    Esta función debe ser llamada al finalizar el uso del MCP
    para liberar recursos y cerrar conexiones.
    """
    global _registry
    
    logger.info("Cerrando subsistema MCP")
    
    if _registry:
        # Desconectar todos los clientes registrados
        for client_name, client in _registry.get_all_clients().items():
            logger.info(f"Desconectando cliente: {client_name}")
            try:
                client.disconnect()
            except Exception as e:
                logger.error(f"Error desconectando cliente {client_name}: {str(e)}")
                
        # Cerrar todos los servidores
        _registry.shutdown_all_servers()
        
        # Limpiar el registro (no es necesario en realidad por el singleton)
        _registry = None

def get_registry() -> MCPRegistry:
    """
    Obtiene la instancia actual del registro MCP.
    
    Si el subsistema MCP no ha sido inicializado, lo inicializa automáticamente.
    
    Returns:
        MCPRegistry: Instancia del registro MCP
    """
    global _registry
    
    if _registry is None:
        _registry = initialize_mcp()
        
    return _registry 