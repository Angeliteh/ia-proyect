"""
Componentes core para el gestor de modelos.

Este paquete contiene las clases e interfaces base para
el sistema de gestión de modelos.
"""

from .resource_detector import ResourceDetector
from .model_manager import (
    ModelInterface, 
    ModelInfo, 
    ModelOutput, 
    ModelType,
    ModelManager
)

__all__ = [
    "ResourceDetector",
    "ModelInterface",
    "ModelInfo",
    "ModelOutput",
    "ModelType",
    "ModelManager"
] 