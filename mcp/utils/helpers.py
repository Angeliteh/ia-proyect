"""
Funciones de ayuda para el sistema MCP.

Este módulo proporciona funciones de utilidad varias
para el funcionamiento del sistema MCP.
"""

import logging
import os

def create_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Crea y configura un logger con un formato consistente.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (por defecto: INFO)
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evitar configurar múltiples veces el mismo logger
    if not logger.handlers:
        logger.setLevel(level)
        
        # Crear handler para consola si no hay ninguno
        handler = logging.StreamHandler()
        handler.setLevel(level)
        
        # Configurar formato
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Agregar handler al logger
        logger.addHandler(handler)
    
    return logger 