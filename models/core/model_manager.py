"""
Gestor de modelos de IA.

Este módulo proporciona clases para gestionar modelos de IA,
tanto locales como en la nube.
"""

import os
import json
import logging
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, AsyncGenerator

# Importar detector de recursos
from .resource_detector import ResourceDetector

class ModelType(str, Enum):
    """Tipos de modelos disponibles."""
    
    # Modelos locales
    LLAMA = "llama"
    MISTRAL = "mistral"
    PHI = "phi"
    
    # Modelos en la nube
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"

class QuantizationLevel(str, Enum):
    """Niveles de cuantización para modelos locales."""
    
    # Sin cuantización (float16/float32)
    NONE = "none"  # float16/float32
    
    # GGUF (llama.cpp)
    Q8_0 = "q8_0"    # 8-bit (buena calidad)
    Q6_K = "q6_k"    # 6-bit
    Q5_K = "q5_k"    # 5-bit
    Q4_K_M = "q4_k_m"  # 4-bit (equilibrio calidad/tamaño)
    Q3_K_M = "q3_k_m"  # 3-bit (menor tamaño)
    
    # GPTQ (GPU optimizado)
    GPTQ_8BIT = "gptq_8bit"
    GPTQ_4BIT = "gptq_4bit"

class ModelInfo:
    """
    Información sobre un modelo de IA.
    
    Attributes:
        name: Nombre del modelo
        model_type: Tipo de modelo
        path: Ruta al archivo del modelo (solo para modelos locales)
        api_key_env: Nombre de la variable de entorno con la API key (modelos en la nube)
        context_length: Longitud máxima de contexto soportada
        quantization: Nivel de cuantización (para modelos locales)
        size_gb: Tamaño aproximado del modelo en GB
        parameters: Número de parámetros del modelo en miles de millones
    """
    
    def __init__(
        self,
        name: str,
        model_type: Union[ModelType, str],
        local: bool = True,
        path: Optional[str] = None,
        api_key_env: Optional[str] = None,
        context_length: int = 4096,
        quantization: Union[QuantizationLevel, str] = QuantizationLevel.NONE,
        size_gb: Optional[float] = None,
        parameters: Optional[float] = None
    ):
        """
        Inicializa la información del modelo.
        
        Args:
            name: Nombre del modelo
            model_type: Tipo de modelo
            local: Si es un modelo local o en la nube
            path: Ruta al archivo del modelo (solo para modelos locales)
            api_key_env: Variable de entorno con la API key (modelos en la nube)
            context_length: Longitud máxima de contexto soportada
            quantization: Nivel de cuantización (para modelos locales)
            size_gb: Tamaño aproximado del modelo en GB
            parameters: Número de parámetros del modelo en miles de millones
        """
        self.name = name
        self.model_type = model_type if isinstance(model_type, str) else model_type.value
        self.local = local
        self.path = path
        self.api_key_env = api_key_env
        self.context_length = context_length
        self.quantization = quantization if isinstance(quantization, str) else quantization.value
        self.size_gb = size_gb
        self.parameters = parameters
        
        # Estimar tamaño si no se proporciona
        if self.size_gb is None and self.parameters is not None:
            # Estimación muy aproximada basada en parámetros y cuantización
            if self.quantization == QuantizationLevel.NONE.value:
                self.size_gb = self.parameters * 2  # ~2GB por mil millones de parámetros en FP16
            elif self.quantization in [QuantizationLevel.Q8_0.value]:
                self.size_gb = self.parameters * 1  # ~1GB por mil millones en 8-bit
            elif self.quantization in [QuantizationLevel.Q4_K_M.value]:
                self.size_gb = self.parameters * 0.5  # ~0.5GB por mil millones en 4-bit
            else:
                self.size_gb = self.parameters * 0.75  # Estimación genérica
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la información del modelo a un diccionario."""
        return {
            "name": self.name,
            "model_type": self.model_type,
            "local": self.local,
            "path": self.path,
            "api_key_env": self.api_key_env,
            "context_length": self.context_length,
            "quantization": self.quantization,
            "size_gb": self.size_gb,
            "parameters": self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """
        Crea una instancia desde un diccionario.
        
        Args:
            data: Diccionario con información del modelo
            
        Returns:
            Instancia de ModelInfo
        """
        return cls(
            name=data["name"],
            model_type=data["model_type"],
            local=data.get("local", True),
            path=data.get("path"),
            api_key_env=data.get("api_key_env"),
            context_length=data.get("context_length", 4096),
            quantization=data.get("quantization", QuantizationLevel.NONE.value),
            size_gb=data.get("size_gb"),
            parameters=data.get("parameters")
        )

class ModelOutput:
    """
    Salida estandarizada de un modelo de IA.
    
    Attributes:
        text: Texto generado por el modelo
        tokens: Número de tokens generados
        metadata: Metadatos adicionales específicos del modelo
    """
    
    def __init__(
        self, 
        text: str, 
        tokens: int = 0, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Inicializa la salida del modelo.
        
        Args:
            text: Texto generado por el modelo
            tokens: Número de tokens generados
            metadata: Metadatos adicionales
        """
        self.text = text
        self.tokens = tokens
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la salida a un diccionario."""
        return {
            "text": self.text,
            "tokens": self.tokens,
            "metadata": self.metadata
        }

class ModelInterface(ABC):
    """
    Interfaz abstracta para modelos de IA.
    
    Esta interfaz define los métodos que deben implementar
    todos los modelos, tanto locales como en la nube.
    """
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False,
        stop_sequences: Optional[List[str]] = None
    ) -> Union[ModelOutput, AsyncGenerator[ModelOutput, None]]:
        """
        Genera texto a partir de un prompt.
        
        Args:
            prompt: Texto de entrada para el modelo
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación (aleatoriedad)
            top_p: Valor de top-p para muestreo nucleus
            stream: Si se debe devolver la salida en streaming
            stop_sequences: Secuencias que detienen la generación
            
        Returns:
            Salida del modelo o generador asíncrono si stream=True
        """
        pass
    
    @abstractmethod
    def tokenize(self, text: str) -> List[int]:
        """
        Tokeniza un texto.
        
        Args:
            text: Texto a tokenizar
            
        Returns:
            Lista de tokens (IDs de token)
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto.
        
        Args:
            text: Texto para contar tokens
            
        Returns:
            Número de tokens
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Vector de embeddings
        """
        pass

class ModelManager:
    """
    Gestor de modelos de IA.
    
    Esta clase gestiona la carga, uso y liberación de modelos de IA,
    tanto locales como en la nube, optimizando el uso de recursos.
    
    Attributes:
        models_info: Información sobre los modelos disponibles
        loaded_models: Modelos actualmente cargados en memoria
        resource_detector: Detector de recursos del sistema
        logger: Logger para esta clase
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
        
        # Cargar configuración de modelos
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        else:
            self._load_default_models()
            
        self.logger.info(f"Gestor de modelos inicializado con {len(self.models_info)} modelos configurados")
    
    def _load_config(self, config_path: str):
        """
        Carga la configuración de modelos desde un archivo.
        
        Args:
            config_path: Ruta al archivo de configuración
        """
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
        
        Se utiliza cuando no se proporciona un archivo JSON de configuración.
        """
        self.logger.warning("Cargando configuración predeterminada de modelos...")
        
        # Modelos locales predeterminados (requieren descarga)
        local_models = [
            ModelInfo(
                name="phi-2",
                model_type=ModelType.PHI,
                local=True,
                path="models/local/phi-2.Q4_K_M.gguf",
                context_length=2048,
                parameters=2.7
            )
        ]
        
        # Modelos en la nube predeterminados (reducidos para evitar problemas de límites)
        cloud_models = [
            ModelInfo(
                name="gpt-3.5-turbo-16k",  # Modelo con mayor límite de requests
                model_type=ModelType.OPENAI,
                local=False,
                api_key_env="OPENAI_API_KEY",
                context_length=16385,
                parameters=None
            ),
            ModelInfo(
                name="claude-3-haiku-20240307",  # Modelo más económico de Anthropic (sustituye a claude-instant-1)
                model_type=ModelType.ANTHROPIC,
                local=False,
                api_key_env="ANTHROPIC_API_KEY",
                context_length=100000,
                parameters=None
            )
        ]
        
        # Registrar modelos
        for model in local_models + cloud_models:
            self.models_info[model.name] = model
        
        self.logger.warning(
            "Usando configuración predeterminada mínima. "
            "Para una configuración completa, proporciona un archivo JSON de configuración."
        )
    
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
            
        Raises:
            ValueError: Si el modelo no existe o no se puede cargar
        """
        if model_name in self.loaded_models:
            self.logger.info(f"Modelo '{model_name}' ya está cargado")
            return self.loaded_models[model_name]
            
        if model_name not in self.models_info:
            raise ValueError(f"Modelo '{model_name}' no encontrado en la configuración")
            
        model_info = self.models_info[model_name]
        self.logger.info(f"Cargando modelo '{model_name}' ({model_info.model_type})")
        
        try:
            # Si es un modelo local, determinar el dispositivo óptimo
            if model_info.local:
                device = force_device
                
                # Si no se fuerza un dispositivo, determinar el óptimo
                if device is None:
                    device_info = self.resource_detector.estimate_optimal_device(
                        model_size_gb=model_info.size_gb or 4.0,  # Valor por defecto si no se especifica
                        context_length=model_info.context_length
                    )
                    
                    device = device_info["device"]
                    if "warning" in device_info:
                        self.logger.warning(
                            f"Advertencia al cargar '{model_name}': {device_info['warning']}"
                        )
                
                # Cargar modelo local según su tipo
                if model_info.model_type == ModelType.LLAMA.value:
                    model = await self._load_llama_model(model_info, device)
                elif model_info.model_type == ModelType.MISTRAL.value:
                    model = await self._load_mistral_model(model_info, device)
                elif model_info.model_type == ModelType.PHI.value:
                    model = await self._load_phi_model(model_info, device)
                else:
                    raise ValueError(f"Tipo de modelo local no soportado: {model_info.model_type}")
            else:
                # Cargar modelo en la nube
                if model_info.model_type == ModelType.OPENAI.value:
                    model = await self._load_openai_model(model_info)
                elif model_info.model_type == ModelType.ANTHROPIC.value:
                    model = await self._load_anthropic_model(model_info)
                elif model_info.model_type == ModelType.GEMINI.value:
                    model = await self._load_gemini_model(model_info)
                else:
                    raise ValueError(f"Tipo de modelo en la nube no soportado: {model_info.model_type}")
            
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
            # Eliminar referencias al modelo
            del self.loaded_models[model_name]
            
            # Forzar liberación de memoria en Python
            import gc
            gc.collect()
            
            # En PyTorch, liberar caché CUDA si está disponible
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
                
            self.logger.info(f"Modelo '{model_name}' descargado")
            return True
            
        except Exception as e:
            self.logger.error(f"Error descargando modelo '{model_name}': {e}")
            return False
    
    def list_available_models(self, local_only: bool = False) -> List[Dict[str, Any]]:
        """
        Lista los modelos disponibles.
        
        Args:
            local_only: Si es True, solo lista modelos locales
            
        Returns:
            Lista de información de modelos disponibles
        """
        models = []
        for name, info in self.models_info.items():
            if local_only and not info.local:
                continue
                
            is_loaded = name in self.loaded_models
            
            model_data = info.to_dict()
            model_data["is_loaded"] = is_loaded
            models.append(model_data)
            
        return models
    
    def list_loaded_models(self) -> List[str]:
        """
        Lista los modelos actualmente cargados.
        
        Returns:
            Lista de nombres de modelos cargados
        """
        return list(self.loaded_models.keys())
    
    async def get_model(self, model_name: str) -> ModelInterface:
        """
        Obtiene un modelo ya cargado o lo carga si no lo está.
        
        Args:
            model_name: Nombre del modelo
            
        Returns:
            Instancia del modelo
            
        Raises:
            ValueError: Si el modelo no existe o no se puede cargar
        """
        if model_name in self.loaded_models:
            return self.loaded_models[model_name][0]
            
        model, _ = await self.load_model(model_name)
        return model
    
    # Métodos auxiliares para cargar modelos específicos
    async def _load_llama_model(self, model_info: ModelInfo, device: str) -> ModelInterface:
        """
        Carga un modelo Llama usando llama.cpp.
        
        Args:
            model_info: Información del modelo
            device: Dispositivo a utilizar ('cpu' o 'gpu')
            
        Returns:
            Instancia del modelo
        """
        try:
            # Importar dinámicamente para evitar dependencias innecesarias
            from ..local.llama_cpp_model import LlamaCppModel
            
            # Crear instancia
            model = LlamaCppModel(model_info, device=device)
            return model
        except ImportError as e:
            self.logger.error(f"Error importando LlamaCppModel: {e}")
            raise ValueError(
                "No se pudo cargar el modelo Llama. "
                "Asegúrate de tener instalado llama-cpp-python: pip install llama-cpp-python"
            )
    
    async def _load_mistral_model(self, model_info: ModelInfo, device: str) -> ModelInterface:
        """
        Carga un modelo Mistral usando llama.cpp (misma implementación).
        
        Args:
            model_info: Información del modelo
            device: Dispositivo a utilizar ('cpu' o 'gpu')
            
        Returns:
            Instancia del modelo
        """
        # Mistral utiliza la misma implementación que Llama en llama.cpp
        return await self._load_llama_model(model_info, device)
    
    async def _load_phi_model(self, model_info: ModelInfo, device: str) -> ModelInterface:
        """
        Carga un modelo Phi usando llama.cpp (misma implementación).
        
        Args:
            model_info: Información del modelo
            device: Dispositivo a utilizar ('cpu' o 'gpu')
            
        Returns:
            Instancia del modelo
        """
        # Phi también puede utilizar la implementación de llama.cpp
        return await self._load_llama_model(model_info, device)
    
    async def _load_openai_model(self, model_info: ModelInfo) -> ModelInterface:
        """
        Carga un modelo OpenAI.
        
        Args:
            model_info: Información del modelo
            
        Returns:
            Instancia del modelo
        """
        try:
            # Importar dinámicamente para evitar dependencias innecesarias
            from ..cloud.openai_model import OpenAIModel
            
            # Crear instancia
            model = OpenAIModel(model_info)
            return model
        except ImportError as e:
            self.logger.error(f"Error importando OpenAIModel: {e}")
            raise ValueError(
                "No se pudo cargar el modelo OpenAI. "
                "Asegúrate de tener instalado httpx: pip install httpx"
            )
    
    async def _load_anthropic_model(self, model_info: ModelInfo) -> ModelInterface:
        """
        Carga un modelo Anthropic.
        
        Args:
            model_info: Información del modelo
            
        Returns:
            Instancia del modelo
        """
        try:
            # Importar dinámicamente para evitar dependencias innecesarias
            from ..cloud.anthropic_model import AnthropicModel
            
            # Crear instancia
            model = AnthropicModel(model_info)
            return model
        except ImportError as e:
            self.logger.error(f"Error importando AnthropicModel: {e}")
            raise ValueError(
                "No se pudo cargar el modelo Anthropic. "
                "Asegúrate de tener instalado httpx: pip install httpx"
            )
    
    async def _load_gemini_model(self, model_info: ModelInfo) -> ModelInterface:
        """
        Carga un modelo de Google Gemini.
        
        Args:
            model_info: Información del modelo a cargar
            
        Returns:
            Interfaz del modelo cargado
            
        Raises:
            ImportError: Si no se puede importar la implementación de Gemini
            ValueError: Si no se puede inicializar el modelo
        """
        try:
            from ..cloud.gemini_model import GeminiModel
            
            # Crear instancia del modelo
            model = GeminiModel(model_info)
            return model
        except ImportError as e:
            raise ImportError(f"No se pudo importar la implementación de Gemini: {str(e)}. "
                            "Asegúrate de tener instalado google-generativeai: pip install google-generativeai")
        except Exception as e:
            raise ValueError(f"Error cargando modelo de Gemini: {str(e)}")
    
    def save_config(self, config_path: str):
        """
        Guarda la configuración de modelos en un archivo.
        
        Args:
            config_path: Ruta donde guardar la configuración
        """
        try:
            models_data = [model.to_dict() for model in self.models_info.values()]
            config = {"models": models_data}
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.logger.info(f"Configuración de modelos guardada en {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error guardando configuración de modelos: {e}")
            return False 