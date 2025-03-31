"""
Gestor de modelos de IA.

Este módulo proporciona clases para gestionar modelos de IA,
tanto locales como en la nube, con detección de recursos y sistema de fallback.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, AsyncGenerator
from enum import Enum

# Importar detector de recursos
from .resource_detector import ResourceDetector

class ModelType(str, Enum):
    """Tipos de modelos disponibles."""
    LLAMA = "llama"
    MISTRAL = "mistral"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"

class ModelInfo:
    """
    Información sobre un modelo de IA.
    
    Attributes:
        name: Nombre del modelo
        model_type: Tipo de modelo
        local: Si es un modelo local o en la nube
        path: Ruta al archivo del modelo (solo para modelos locales)
        api_key_env: Variable de entorno con la API key (modelos en la nube)
        context_length: Longitud máxima de contexto soportada
        size_gb: Tamaño aproximado del modelo en GB
    """
    
    def __init__(
        self,
        name: str,
        model_type: Union[ModelType, str],
        local: bool = True,
        path: Optional[str] = None,
        api_key_env: Optional[str] = None,
        context_length: int = 4096,
        size_gb: Optional[float] = None
    ):
        self.name = name
        self.model_type = model_type if isinstance(model_type, str) else model_type.value
        self.local = local
        self.path = path
        self.api_key_env = api_key_env
        self.context_length = context_length
        self.size_gb = size_gb
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la información del modelo a un diccionario."""
        return {
            "name": self.name,
            "model_type": self.model_type,
            "local": self.local,
            "path": self.path,
            "api_key_env": self.api_key_env,
            "context_length": self.context_length,
            "size_gb": self.size_gb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Crea una instancia desde un diccionario."""
        return cls(
            name=data["name"],
            model_type=data["model_type"],
            local=data.get("local", True),
            path=data.get("path"),
            api_key_env=data.get("api_key_env"),
            context_length=data.get("context_length", 4096),
            size_gb=data.get("size_gb")
        )

class ModelOutput:
    """
    Salida estandarizada de un modelo de IA.
    
    Attributes:
        text: Texto generado por el modelo
        tokens: Número de tokens generados
        metadata: Metadatos adicionales (opcional)
    """
    
    def __init__(self, text: str, tokens: int = 0, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.tokens = tokens
        self.metadata = metadata or {}

class ModelInterface:
    """
    Interfaz base para modelos de IA.
    
    Esta interfaz define los métodos que deben implementar
    todos los modelos, tanto locales como en la nube.
    """
    
    async def generate(
        self, 
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> ModelOutput:
        """
        Genera texto a partir de un prompt.
        
        Args:
            prompt: Texto de entrada para el modelo
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación (aleatoriedad)
            
        Returns:
            Salida del modelo
        """
        raise NotImplementedError("Los modelos deben implementar generate()")
    
    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Genera texto en tiempo real, devolviendo chunks a medida que se generan.
        
        Args:
            prompt: Texto de entrada para el modelo
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación (aleatoriedad)
            
        Yields:
            Chunks de texto generados
        """
        # Por defecto, si no se implementa streaming, se usa generate()
        response = await self.generate(prompt, max_tokens, temperature)
        yield response.text

class ModelManager:
    """
    Gestor de modelos de IA.
    
    Esta clase gestiona la carga, uso y liberación de modelos de IA,
    tanto locales como en la nube, optimizando el uso de recursos.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el gestor de modelos.
        
        Args:
            config_path: Ruta al archivo de configuración de modelos
        """
        self.logger = logging.getLogger("models.manager")
        self.resource_detector = ResourceDetector()
        
        # Modelos disponibles y cargados
        self.models_info: Dict[str, ModelInfo] = {}
        self.loaded_models: Dict[str, Tuple[ModelInterface, ModelInfo]] = {}
        
        # Mapeo de tipos de modelo a sus implementaciones
        self.model_implementations = {
            ModelType.MISTRAL.value: "models.local.llama_cpp_model.LlamaCppModel",
            ModelType.GEMINI.value: "models.cloud.gemini_model.GeminiModel",
            ModelType.LLAMA.value: "models.local.llama_cpp_model.LlamaCppModel"
        }
        
        # Cargar configuración de modelos
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        else:
            self._load_default_models()
            
        self.logger.info(f"Gestor de modelos inicializado con {len(self.models_info)} modelos configurados")
        
        # Modelo de embedding y cache
        self.embedding_model = None
        self.embedding_cache = {}
    
    def _load_config(self, config_path: str):
        """Carga la configuración de modelos desde un archivo."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            for model_data in config.get("models", []):
                model_info = ModelInfo.from_dict(model_data)
                self.models_info[model_info.name] = model_info
                
            self.logger.info(f"Configuración de modelos cargada desde {config_path}")
        except Exception as e:
            self.logger.error(f"Error cargando configuración de modelos: {e}")
            self._load_default_models()
    
    def _load_default_models(self):
        """
        Carga una configuración mínima predeterminada de modelos locales y en la nube.
        """
        self.logger.warning("Cargando configuración predeterminada de modelos...")
        
        # Modelos locales predeterminados
        local_models = [
            ModelInfo(
                name="mistral-7b-instruct",
                model_type=ModelType.MISTRAL,
                local=True,
                path="models/local/mistral-7b-instruct.Q4_K_M.gguf",
                context_length=32768,
                size_gb=4.0
            )
        ]
        
        # Modelos en la nube predeterminados
        cloud_models = [
            ModelInfo(
                name="gemini-2.0-flash",
                model_type=ModelType.GEMINI,
                local=False,
                api_key_env="GOOGLE_API_KEY",
                context_length=32768
            )
        ]
        
        # Registrar modelos
        for model in local_models + cloud_models:
            self.models_info[model.name] = model
    
    async def load_model(
        self, 
        model_name: str, 
        force_device: Optional[str] = None
    ) -> Tuple[ModelInterface, ModelInfo]:
        """
        Carga un modelo en memoria.
        
        Args:
            model_name: Nombre del modelo a cargar
            force_device: Forzar el uso de un dispositivo específico ('cpu' o 'gpu')
            
        Returns:
            Tupla (instancia del modelo, información del modelo)
        """
        if model_name in self.loaded_models:
            self.logger.info(f"Modelo '{model_name}' ya está cargado")
            return self.loaded_models[model_name]
            
        if model_name not in self.models_info:
            raise ValueError(f"Modelo '{model_name}' no encontrado en la configuración")
            
        model_info = self.models_info[model_name]
        self.logger.info(f"Cargando modelo '{model_name}' ({model_info.model_type})")
        
        try:
            # Obtener la implementación del modelo
            implementation_path = self.model_implementations.get(model_info.model_type)
            if not implementation_path:
                raise ValueError(f"No hay implementación para el tipo de modelo: {model_info.model_type}")
            
            # Importar dinámicamente la implementación
            module_path, class_name = implementation_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            model_class = getattr(module, class_name)
            
            # Si es un modelo local, determinar el dispositivo óptimo
            if model_info.local:
                device = force_device or self.resource_detector.estimate_optimal_device(
                    model_size_gb=model_info.size_gb or 4.0,
                    context_length=model_info.context_length
                )["device"]
                model = model_class(model_info, device=device)
            else:
                model = model_class(model_info)
            
            self.loaded_models[model_name] = (model, model_info)
            return (model, model_info)
            
        except Exception as e:
            self.logger.error(f"Error cargando modelo '{model_name}': {e}")
            raise ValueError(f"Error cargando modelo '{model_name}': {str(e)}")
    
    async def unload_model(self, model_name: str) -> bool:
        """
        Descarga un modelo de la memoria.
        
        Args:
            model_name: Nombre del modelo a descargar
            
        Returns:
            True si se descargó correctamente, False en caso contrario
        """
        if model_name not in self.loaded_models:
            self.logger.warning(f"Modelo '{model_name}' no está cargado")
            return False
            
        try:
            del self.loaded_models[model_name]
            
            # Forzar liberación de memoria en Python
            import gc
            gc.collect()
            
            # En PyTorch, liberar caché CUDA si está disponible
            try:
                import torch # type: ignore
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
                
            self.logger.info(f"Modelo '{model_name}' descargado")
            return True
            
        except Exception as e:
            self.logger.error(f"Error descargando modelo '{model_name}': {e}")
            return False
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        Lista los modelos disponibles.
        
        Returns:
            Lista de información de modelos disponibles
        """
        models = []
        for name, info in self.models_info.items():
            is_loaded = name in self.loaded_models
            model_data = info.to_dict()
            model_data["is_loaded"] = is_loaded
            models.append(model_data)
        return models
    
    def has_embedding_model(self) -> bool:
        """
        Verifica si hay un modelo disponible para generar embeddings.
        
        Returns:
            True si hay un modelo para embeddings disponible, False en caso contrario
        """
        # Por ahora, siempre devolvemos True y usamos el método simple_embedding
        # En un sistema real, se verificaría si hay un modelo adecuado cargado
        return True
        
    def embed_text(self, text: str) -> List[float]:
        """
        Genera un embedding vectorial para un texto.
        
        Args:
            text: Texto para generar el embedding
            
        Returns:
            Vector de embedding (lista de floats)
        """
        # Verificar si tenemos el embedding en caché
        if text in self.embedding_cache:
            return self.embedding_cache[text]
            
        # Función de embedding simple por defecto
        # Esta función es solo para demostración y debería reemplazarse con un modelo real
        import hashlib
        embedding_dim = 768  # Dimensión estándar para demostración
        
        # Función de embedding simple basada en hash de palabras
        words = text.lower().split()
        vector = [0.0] * embedding_dim
        
        for i, word in enumerate(words):
            # Hash de la palabra para generar un valor pseudo-aleatorio
            hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
            # Distribuir el valor en varias posiciones del vector
            for j in range(min(5, embedding_dim)):
                pos = (hash_val + j) % embedding_dim
                vector[pos] += (1.0 / (i + 1)) * (0.9 ** j)
        
        # Normalizar el vector
        norm = sum(v**2 for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
            
        # Guardar en caché para reutilizar
        self.embedding_cache[text] = vector
        
        return vector 