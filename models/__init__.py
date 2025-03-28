"""
Sistema de gestión de modelos de IA.

Este paquete proporciona componentes para gestionar y utilizar
modelos de IA, tanto locales como en la nube.
"""

# Importar componentes principales
from .core import (
    ModelInterface,
    ModelInfo,
    ModelOutput,
    ModelType,
    QuantizationLevel,
    ModelManager,
    ResourceDetector
)

# Importar implementaciones de modelos
from .local import LlamaCppModel
from .cloud import OpenAIModel

# Exportar componentes
__all__ = [
    # Core
    "ModelInterface",
    "ModelInfo", 
    "ModelOutput",
    "ModelType",
    "QuantizationLevel",
    "ModelManager",
    "ResourceDetector",
    
    # Implementaciones
    "LlamaCppModel",
    "OpenAIModel"
]

# Versión del módulo
__version__ = "0.1.0" 