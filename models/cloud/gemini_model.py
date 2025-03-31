"""
Modelo de IA utilizando Google Gemini.

Este módulo implementa la interfaz de modelo para la API de Google Gemini,
permitiendo utilizar modelos como gemini-pro y gemini-ultra.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

import google.generativeai as genai
from google.generativeai.types import AsyncGenerateContentResponse, HarmCategory, HarmBlockThreshold, GenerationConfig

from ..core.model_manager import ModelInterface, ModelOutput, ModelInfo

logger = logging.getLogger("models.cloud.gemini")

class GeminiModel(ModelInterface):
    """
    Implementación de ModelInterface para Google Gemini.
    
    Attributes:
        model_info: Información del modelo
        model_name: Nombre del modelo en la API de Gemini
    """
    
    def __init__(self, model_info: ModelInfo):
        """
        Inicializa el modelo de Gemini.
        
        Args:
            model_info: Información del modelo a utilizar
        """
        self.model_info = model_info
        self.model_name = model_info.name  # gemini-2.0-flash, etc.
        
        # Configurar la API de Gemini
        api_key = os.environ.get(model_info.api_key_env, "")
        if not api_key:
            raise ValueError(f"No se encontró la API key de Google en la variable de entorno {model_info.api_key_env}")
        
        # Configurar la API
        genai.configure(api_key=api_key)
        
        try:
            # Inicializar el modelo de Gemini
            self.model = genai.GenerativeModel(self.model_name)
            # Probar que el modelo esté disponible
            logger.info(f"Modelo Gemini inicializado: {self.model_name}")
        except Exception as e:
            # Para pruebas - mostrar modelos disponibles
            logger.error(f"Error al inicializar el modelo {self.model_name}: {str(e)}")
            try:
                available_models = genai.list_models()
                model_names = [model.name for model in available_models]
                logger.info(f"Modelos disponibles: {model_names}")
                
                # Buscar una alternativa si el modelo solicitado no está disponible
                if model_names:
                    fallback_model = model_names[0]
                    logger.info(f"Usando modelo alternativo: {fallback_model}")
                    self.model = genai.GenerativeModel(fallback_model)
                    self.model_name = fallback_model
                else:
                    raise ValueError("No hay modelos Gemini disponibles")
            except Exception as inner_e:
                logger.error(f"Error al listar modelos disponibles: {str(inner_e)}")
                raise ValueError(f"No se pudo inicializar el modelo Gemini: {str(e)}")
    
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
        Genera texto utilizando el modelo de Gemini.
        
        Args:
            prompt: Texto de entrada para la generación
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación
            top_p: Valor de top_p para la generación
            stream: Si se debe usar streaming para la generación
            stop_sequences: Secuencias de texto que detienen la generación
            
        Returns:
            ModelOutput con el texto generado o un generador de ModelOutput
        """
        if not prompt:
            raise ValueError("El prompt no puede estar vacío")
        
        # Configurar parámetros de generación
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_tokens,
            stop_sequences=stop_sequences
        )
        
        # Configurar umbral de seguridad lo más permisivo posible
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        try:
            if stream:
                # Crear un generador que acumule los chunks y los devuelva como ModelOutput
                async def stream_to_model_output():
                    text_accumulated = ""
                    tokens = 0
                    async for chunk in self.generate_stream(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        stop_sequences=stop_sequences
                    ):
                        text_accumulated += chunk
                        tokens += 1  # Aproximación simple
                        yield ModelOutput(
                            text=chunk,
                            tokens=1,
                            metadata={
                                "model": self.model_name,
                                "accumulated_text": text_accumulated,
                                "is_complete": False
                            }
                        )
                
                return stream_to_model_output()
            else:
                # Generación completa
                response = await self.model.generate_content_async(
                    contents=prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Obtener el texto generado
                generated_text = ""
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
                
                # Contar tokens (aproximado)
                token_count = len(generated_text.split())
                
                # Devolver el resultado
                return ModelOutput(
                    text=generated_text,
                    tokens=token_count,
                    metadata={
                        "model": self.model_name,
                        "finish_reason": self._get_finish_reason(response),
                        "usage": {
                            "prompt_tokens": len(prompt.split()),
                            "completion_tokens": token_count,
                            "total_tokens": len(prompt.split()) + token_count
                        }
                    }
                )
        
        except Exception as e:
            error_msg = f"Error generando texto con Gemini: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    async def generate_stream(
        self, 
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera texto en streaming utilizando el modelo de Gemini.
        
        Args:
            prompt: Texto de entrada para la generación
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación
            top_p: Valor de top_p para la generación
            stop_sequences: Secuencias de texto que detienen la generación
            
        Yields:
            Fragmentos de texto generados secuencialmente
        """
        # Configurar parámetros de generación
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_tokens,
            stop_sequences=stop_sequences
        )
        
        # Configurar umbral de seguridad lo más permisivo posible
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        try:
            # Generar contenido en streaming
            response = await self.model.generate_content_async(
                contents=prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True
            )
            
            # Procesar el stream de respuesta
            async for chunk in response:
                if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, 'text'):
                            yield part.text
                            
        except Exception as e:
            error_msg = f"Error en streaming con Gemini: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _get_finish_reason(self, response: AsyncGenerateContentResponse) -> str:
        """
        Obtiene la razón de finalización a partir de la respuesta.
        
        Args:
            response: Respuesta de la API de Gemini
            
        Returns:
            Motivo de finalización (stop, length, content_filter, etc.)
        """
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                return str(candidate.finish_reason)
            if hasattr(candidate, 'finish_details'):
                return str(candidate.finish_details)
        return "unknown"
    
    def tokenize(self, text: str) -> List[int]:
        """
        Tokeniza un texto. No implementado completamente para Gemini.
        
        Args:
            text: Texto a tokenizar
            
        Returns:
            Lista de tokens (aproximada)
        """
        # La API de Gemini no proporciona una función directa para tokenización
        # Se devuelve una aproximación basada en espacios como ejemplo
        return [0] * len(text.split())
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto. Aproximación para Gemini.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Número aproximado de tokens
        """
        # Aproximación basada en palabras
        return len(text.split())
    
    async def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Lista de valores que representan el embedding
        """
        try:
            # Verificar si el modelo soporta embeddings
            if hasattr(genai, 'embed_content'):
                embedding_model = "models/embedding-001"  # Modelo de embedding de Google
                result = await genai.embed_content_async(
                    model=embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                
                if hasattr(result, 'embedding'):
                    return result.embedding
                
            # Fallback: devolver lista vacía si no está disponible
            logger.warning("Embeddings no disponibles para este modelo de Gemini")
            return []
            
        except Exception as e:
            error_msg = f"Error generando embeddings con Gemini: {str(e)}"
            logger.error(error_msg)
            return [] 