"""
Implementación de modelos Anthropic.

Este módulo proporciona una implementación de la interfaz ModelInterface
para modelos de Anthropic accesibles a través de su API.
"""

import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

import httpx
 
# Importar las clases base
from ..core.model_manager import ModelInterface, ModelInfo, ModelOutput

class AnthropicModel(ModelInterface):
    """
    Implementación de la interfaz ModelInterface para modelos Anthropic.
    
    Esta clase permite interactuar con modelos de Anthropic a través de su API,
    proporcionando métodos para generación de texto, tokenización y embeddings.
    
    Attributes:
        model_info: Información del modelo.
        api_key: Clave de API para autenticación con Anthropic.
        client: Cliente HTTP asíncrono para realizar peticiones a la API.
        logger: Logger para esta clase.
    """
    
    # Lista de modelos válidos de Anthropic
    VALID_MODELS = [
        "claude-instant-1",
        "claude-2",
        "claude-2.0",
        "claude-2.1", 
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20240620"
    ]
    
    def __init__(self, model_info: ModelInfo):
        """
        Inicializa el modelo Anthropic.
        
        Args:
            model_info: Información del modelo Anthropic a utilizar
            
        Raises:
            ValueError: Si no se encuentra la clave de API o el modelo no es compatible
        """
        self.model_info = model_info
        self.logger = logging.getLogger("models.anthropic")
        
        # Verificar que sea un modelo Anthropic
        if model_info.model_type != "anthropic":
            raise ValueError(f"Tipo de modelo no compatible: {model_info.model_type}")
        
        # Verificar que el modelo esté en la lista de modelos válidos
        if model_info.name not in self.VALID_MODELS:
            self.logger.warning(
                f"El modelo '{model_info.name}' no está en la lista de modelos válidos de Anthropic. "
                f"Modelos válidos conocidos: {', '.join(self.VALID_MODELS)}"
            )
        
        # Obtener la API key
        api_key_env = model_info.api_key_env or "ANTHROPIC_API_KEY"
        self.api_key = os.environ.get(api_key_env)
        
        # Depuración: mostrar primeros 5 caracteres de la API key si existe
        if self.api_key:
            self.logger.info(f"API key encontrada con prefijo: {self.api_key[:5]}...")
        else:
            self.logger.error(f"No se encontró la API key en la variable de entorno {api_key_env}")
            raise ValueError(
                f"No se encontró la clave de API en la variable de entorno {api_key_env}. "
                "Asegúrate de configurar ANTHROPIC_API_KEY en tu archivo .env con el formato: "
                "ANTHROPIC_API_KEY=sk-ant-xxxx..."
            )
        
        # Verificar formato básico de la API key de Anthropic
        if not self.api_key.startswith("sk-ant"):
            self.logger.warning(
                "El formato de la API key parece incorrecto. "
                "Las API keys de Anthropic deben comenzar con 'sk-ant'"
            )
        
        # Crear cliente HTTP con encabezados corregidos según la documentación de Anthropic
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "x-api-key": self.api_key,            # Encabezado correcto según documentación
                "anthropic-version": "2023-06-01",    # Versión de la API
                "Content-Type": "application/json"
            }
        )
        
        self.logger.info(f"Modelo Anthropic '{model_info.name}' inicializado correctamente")
        
        # Mapeo de modelos Anthropic a sus endpoints API
        self.api_endpoint = "https://api.anthropic.com/v1/messages"
    
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
        Genera texto a partir de un prompt utilizando el modelo Anthropic.
        
        Args:
            prompt: Texto de entrada para el modelo
            max_tokens: Número máximo de tokens a generar
            temperature: Temperatura para la generación
            top_p: Valor de top-p para muestreo nucleus
            stream: Si se debe devolver la salida en streaming
            stop_sequences: Secuencias que detienen la generación
            
        Returns:
            Salida del modelo o generador asíncrono si stream=True
        """
        # Verificar que el prompt no esté vacío
        if not prompt or not prompt.strip():
            self.logger.error("El prompt no puede estar vacío")
            raise ValueError("El prompt no puede estar vacío para la API de Anthropic")
        
        payload = {
            "model": self.model_info.name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        if stop_sequences:
            payload["stop_sequences"] = stop_sequences
        
        # Log para depuración
        self.logger.info(f"Enviando solicitud a {self.api_endpoint}")
        self.logger.info(f"Payload: modelo={self.model_info.name}, max_tokens={max_tokens}")
        
        if stream:
            return self._generate_stream(payload)
        else:
            try:
                response = await self.client.post(self.api_endpoint, json=payload)
                
                # Depuración adicional para errores 401
                if response.status_code == 401:
                    self.logger.error(f"Error 401 Unauthorized. Detalles: {response.text}")
                    self.logger.error(f"Encabezados enviados: {self.client.headers}")
                    raise ValueError(
                        "Error 401: Unauthorized - La API key no es válida o ha expirado. "
                        "Por favor, verifica que tu ANTHROPIC_API_KEY sea correcta en el archivo .env."
                    )
                
                # Manejo específico para errores 400 Bad Request
                if response.status_code == 400:
                    self.logger.error(f"Error 400 Bad Request. Detalles: {response.text}")
                    
                    error_message = "Error 400: Bad Request - Solicitud incorrecta."
                    
                    # Intentar extraer detalles del error
                    try:
                        error_data = response.json()
                        if "error" in error_data and "message" in error_data["error"]:
                            error_detail = error_data["error"]["message"]
                            error_message += f" Detalle: {error_detail}"
                            
                            # Diagnóstico basado en el mensaje de error
                            if "credit balance is too low" in error_detail:
                                error_message += (
                                    "\n\nTu saldo de créditos en Anthropic es demasiado bajo. "
                                    "Visita https://console.anthropic.com/settings/billing para actualizar "
                                    "o comprar créditos."
                                )
                            elif "model" in error_detail and "not found" in error_detail:
                                error_message += (
                                    f"\n\nEl modelo '{self.model_info.name}' no fue encontrado. "
                                    f"Verifica que el nombre del modelo sea correcto. "
                                    f"Modelos conocidos: {', '.join(self.VALID_MODELS)}"
                                )
                            elif "messages" in error_detail and "required" in error_detail:
                                error_message += (
                                    "\n\nEl formato de los mensajes es incorrecto. "
                                    "Asegúrate de que el prompt no esté vacío."
                                )
                            elif "text content blocks must be non-empty" in error_detail:
                                error_message += (
                                    "\n\nEl contenido del mensaje está vacío. "
                                    "Asegúrate de proporcionar un prompt no vacío."
                                )
                    except Exception as e:
                        self.logger.error(f"Error al procesar el mensaje de error: {e}")
                    
                    raise ValueError(error_message)
                
                # Manejo específico para errores 429 Rate Limit
                if response.status_code == 429:
                    self.logger.error(f"Error 429 Rate Limit. Detalles: {response.text}")
                    raise ValueError(
                        "Error 429: Rate Limit - Has excedido el límite de solicitudes. "
                        "Espera un momento antes de realizar más solicitudes."
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Extraer texto generado
                text = data["content"][0]["text"]
                
                # Contar tokens aproximadamente
                tokens_used = len(text.split()) * 1.3  # Aproximación
                
                # Extraer metadatos interesantes
                metadata = {
                    "model": data["model"],
                    "id": data["id"],
                    "stop_reason": data.get("stop_reason", "unknown")
                }
                
                return ModelOutput(
                    text=text,
                    tokens=int(tokens_used),
                    metadata=metadata
                )
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Error HTTP generando texto con Anthropic: {e}")
                raise ValueError(f"Error HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                self.logger.error(f"Error generando texto con Anthropic: {e}")
                raise
    
    async def _generate_stream(self, payload: Dict[str, Any]) -> AsyncGenerator[ModelOutput, None]:
        """
        Genera texto en modo streaming.
        
        Args:
            payload: Payload para la petición a la API
            
        Yields:
            Fragmentos de texto generados por el modelo
        """
        try:
            async with self.client.stream("POST", self.api_endpoint, json=payload) as response:
                # Manejo específico para errores 400 Bad Request
                if response.status_code == 400:
                    error_text = await response.aread()
                    self.logger.error(f"Error 400 Bad Request en streaming. Detalles: {error_text}")
                    
                    error_message = "Error 400: Bad Request - Solicitud incorrecta."
                    
                    try:
                        error_data = json.loads(error_text)
                        if "error" in error_data and "message" in error_data["error"]:
                            error_message += f" Detalle: {error_data['error']['message']}"
                    except:
                        error_message += f" Respuesta: {error_text}"
                    
                    raise ValueError(error_message)
                
                response.raise_for_status()
                
                # Acumuladores para construir la respuesta completa
                text_accumulated = ""
                tokens = 0
                
                async for chunk in response.aiter_bytes():
                    try:
                        # Procesar chunk de datos
                        chunk_text = chunk.decode("utf-8")
                        
                        # Los chunks tienen formato "data: {...}\n\n"
                        for line in chunk_text.split("\n\n"):
                            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                                json_str = line[6:]  # Eliminar "data: "
                                chunk_data = json.loads(json_str)
                                
                                if "delta" in chunk_data and "text" in chunk_data["delta"]:
                                    new_text = chunk_data["delta"]["text"]
                                    text_accumulated += new_text
                                    tokens += 1  # Aproximación
                                    
                                    yield ModelOutput(
                                        text=new_text,  # Solo el nuevo texto
                                        tokens=1,
                                        metadata={
                                            "model": self.model_info.name,
                                            "accumulated_text_length": len(text_accumulated),
                                            "is_complete": False
                                        }
                                    )
                    except Exception as e:
                        self.logger.error(f"Error procesando chunk en streaming: {e}")
                
                # Marcar fin del stream
                yield ModelOutput(
                    text="",
                    tokens=0,
                    metadata={
                        "model": self.model_info.name,
                        "accumulated_text_length": len(text_accumulated),
                        "is_complete": True,
                        "total_tokens": tokens
                    }
                )
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Error HTTP en streaming con Anthropic: {e}")
            raise ValueError(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            self.logger.error(f"Error en streaming con Anthropic: {e}")
            raise
    
    def tokenize(self, text: str) -> List[int]:
        """
        Tokeniza un texto.
        
        Note:
            Esta es una implementación simplificada ya que Anthropic no proporciona
            un tokenizador público oficial.
        
        Args:
            text: Texto a tokenizar
            
        Returns:
            Lista de IDs de token (simplificada)
        """
        self.logger.warning("Tokenización precisa no disponible para Anthropic. Usando aproximación.")
        
        # Esta es una aproximación muy simple
        return [1] * self.count_tokens(text)
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto.
        
        Note:
            Esta es una implementación aproximada ya que Anthropic no proporciona
            un contador de tokens oficial público.
        
        Args:
            text: Texto para contar tokens
            
        Returns:
            Número aproximado de tokens
        """
        # Estimación aproximada: Anthropic usa aproximadamente 4 caracteres por token
        token_count = len(text) // 4 + 1
        return token_count
    
    async def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto.
        
        Note:
            Anthropic no ofrece una API de embeddings pública.
            Esta implementación devuelve un error.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Vector de embeddings
            
        Raises:
            NotImplementedError: API de embeddings no disponible
        """
        self.logger.error("Anthropic no proporciona una API de embeddings pública.")
        raise NotImplementedError(
            "Anthropic no proporciona una API de embeddings pública. "
            "Considera usar OpenAI o modelos locales para embeddings."
        )
    
    async def close(self):
        """Cierra el cliente HTTP."""
        if self.client:
            await self.client.aclose()
            self.logger.info(f"Cliente HTTP para modelo '{self.model_info.name}' cerrado") 