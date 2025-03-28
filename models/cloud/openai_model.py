"""
Implementación de modelos OpenAI.

Este módulo proporciona una implementación de la interfaz ModelInterface
para modelos de OpenAI accesibles a través de su API.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

import httpx

# Importar las clases base
from ..core.model_manager import ModelInterface, ModelInfo, ModelOutput

class OpenAIModel(ModelInterface):
    """
    Implementación de la interfaz ModelInterface para modelos OpenAI.
    
    Esta clase permite interactuar con modelos de OpenAI a través de su API,
    proporcionando métodos para generación de texto, tokenización y embeddings.
    
    Attributes:
        model_info: Información del modelo.
        api_key: Clave de API para autenticación con OpenAI.
        client: Cliente HTTP asíncrono para realizar peticiones a la API.
        logger: Logger para esta clase.
    """
    
    def __init__(self, model_info: ModelInfo):
        """
        Inicializa el modelo OpenAI.
        
        Args:
            model_info: Información del modelo OpenAI a utilizar
            
        Raises:
            ValueError: Si no se encuentra la clave de API o el modelo no es compatible
        """
        self.model_info = model_info
        self.logger = logging.getLogger("models.openai")
        
        # Verificar que sea un modelo OpenAI
        if model_info.model_type != "openai":
            raise ValueError(f"Tipo de modelo no compatible: {model_info.model_type}")
        
        # Obtener la API key
        api_key_env = model_info.api_key_env or "OPENAI_API_KEY"
        self.api_key = os.environ.get(api_key_env)
        
        # Depuración: mostrar primeros 5 caracteres de la API key si existe
        if self.api_key:
            self.logger.info(f"API key encontrada con prefijo: {self.api_key[:5]}...")
        else:
            self.logger.error(f"No se encontró la API key en la variable de entorno {api_key_env}")
            raise ValueError(
                f"No se encontró la clave de API en la variable de entorno {api_key_env}. "
                "Asegúrate de configurar OPENAI_API_KEY en tu archivo .env con el formato: "
                "OPENAI_API_KEY=sk-xxxx..."
            )
        
        # Verificar formato básico de la API key de OpenAI
        if not self.api_key.startswith("sk-"):
            self.logger.warning(
                "El formato de la API key parece incorrecto. "
                "Las API keys de OpenAI deben comenzar con 'sk-'"
            )
        
        # Crear cliente HTTP
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        self.logger.info(f"Modelo OpenAI '{model_info.name}' inicializado correctamente")
        
        # Mapeo de modelos OpenAI a sus endpoints API
        self.api_endpoints = {
            "chat": "https://api.openai.com/v1/chat/completions",
            "embeddings": "https://api.openai.com/v1/embeddings",
            "moderations": "https://api.openai.com/v1/moderations"
        }
    
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
        Genera texto a partir de un prompt utilizando el modelo OpenAI.
        
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
        payload = {
            "model": self.model_info.name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        if stop_sequences:
            payload["stop"] = stop_sequences
        
        # Log para depuración
        self.logger.info(f"Enviando solicitud a {self.api_endpoints['chat']}")
        self.logger.info(f"Payload: modelo={self.model_info.name}, max_tokens={max_tokens}")
        
        if stream:
            return self._generate_stream(payload)
        else:
            try:
                response = await self.client.post(self.api_endpoints["chat"], json=payload)
                
                # Manejo de errores específicos
                if response.status_code == 401:
                    self.logger.error(f"Error 401 Unauthorized. Detalles: {response.text}")
                    self.logger.error(f"Encabezados enviados: {self.client.headers}")
                    raise ValueError(
                        "Error 401: Unauthorized - La API key no es válida o ha expirado. "
                        "Por favor, verifica que tu OPENAI_API_KEY sea correcta en el archivo .env. "
                        "Si acabas de agregar fondos a tu cuenta, es posible que necesites crear una nueva API key."
                    )
                
                if response.status_code == 429:
                    self.logger.error(f"Error 429 Too Many Requests. Detalles: {response.text}")
                    error_message = "Error 429: Too Many Requests - Has excedido el límite de solicitudes permitidas."
                    
                    # Intentar extraer más detalles del mensaje de error
                    try:
                        error_data = response.json()
                        if "error" in error_data and "message" in error_data["error"]:
                            error_message += f" Detalle: {error_data['error']['message']}"
                            
                            # Detectar si es un problema de créditos
                            if "exceeded your current quota" in error_data["error"]["message"]:
                                error_message += (
                                    "\nEs posible que necesites agregar fondos a tu cuenta de OpenAI. "
                                    "Visita https://platform.openai.com/account/billing para verificar tu saldo."
                                )
                    except:
                        pass
                    
                    raise ValueError(error_message)
                
                response.raise_for_status()
                data = response.json()
                
                # Extraer texto generado
                text = data["choices"][0]["message"]["content"]
                
                # Extraer uso de tokens
                tokens_prompt = data["usage"]["prompt_tokens"]
                tokens_completion = data["usage"]["completion_tokens"]
                tokens_total = data["usage"]["total_tokens"]
                
                # Extraer metadatos interesantes
                metadata = {
                    "model": data["model"],
                    "id": data["id"],
                    "finish_reason": data["choices"][0]["finish_reason"],
                    "tokens_prompt": tokens_prompt,
                    "tokens_total": tokens_total
                }
                
                return ModelOutput(
                    text=text,
                    tokens=tokens_completion,
                    metadata=metadata
                )
                
            except httpx.HTTPStatusError as e:
                self.logger.error(f"Error HTTP generando texto con OpenAI: {e}")
                raise ValueError(f"Error HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                self.logger.error(f"Error generando texto con OpenAI: {e}")
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
            async with self.client.stream("POST", self.api_endpoints["chat"], json=payload) as response:
                # Verificar errores comunes
                if response.status_code == 401:
                    self.logger.error(f"Error 401 Unauthorized en streaming. Detalles: {await response.aread()}")
                    raise ValueError(
                        "Error 401: Unauthorized - La API key no es válida o ha expirado. "
                        "Por favor, verifica que tu OPENAI_API_KEY sea correcta en el archivo .env."
                    )
                
                if response.status_code == 429:
                    error_text = await response.aread()
                    self.logger.error(f"Error 429 Too Many Requests en streaming. Detalles: {error_text}")
                    raise ValueError(
                        "Error 429: Too Many Requests - Has excedido el límite de solicitudes permitidas. "
                        "Intenta agregar fondos a tu cuenta de OpenAI o espera antes de realizar más solicitudes."
                    )
                
                response.raise_for_status()
                
                # Acumuladores para construir la respuesta completa
                text_accumulated = ""
                tokens = 0
                
                async for chunk in response.aiter_text():
                    try:
                        # Eliminar "data: " y convertir a JSON
                        if chunk.startswith("data: "):
                            if chunk.strip() == "data: [DONE]":
                                continue
                                
                            json_str = chunk[6:]  # Eliminar "data: "
                            chunk_data = asyncio.run(asyncio.to_thread(lambda: eval(json_str)))
                            
                            # Extraer texto generado
                            if (
                                "choices" in chunk_data and
                                len(chunk_data["choices"]) > 0 and
                                "delta" in chunk_data["choices"][0] and
                                "content" in chunk_data["choices"][0]["delta"]
                            ):
                                new_text = chunk_data["choices"][0]["delta"]["content"]
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
            self.logger.error(f"Error HTTP en streaming con OpenAI: {e}")
            raise ValueError(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            self.logger.error(f"Error en streaming con OpenAI: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta los tokens en un texto.
        
        Note:
            Esta es una implementación aproximada ya que OpenAI no proporciona
            un contador de tokens oficial público para todos los clientes.
        
        Args:
            text: Texto para contar tokens
            
        Returns:
            Número aproximado de tokens
        """
        try:
            # Intentamos importar tiktoken para un conteo preciso
            import tiktoken
            
            try:
                encoding = tiktoken.encoding_for_model(self.model_info.name)
                return len(encoding.encode(text))
            except KeyError:
                # Si el modelo específico no está registrado, usamos cl100k_base que es común para modelos nuevos
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
                
        except ImportError:
            # Estimación aproximada: ~4 caracteres por token en inglés
            # y ~2.5 caracteres por token en otros idiomas 
            self.logger.warning(
                "No se encontró tiktoken. Usando estimación aproximada de tokens. "
                "Instala tiktoken para un conteo más preciso: pip install tiktoken"
            )
            words = text.split()
            # Aproximadamente 0.75 tokens por palabra
            return max(1, int(len(words) * 0.75))
    
    async def embed(self, text: str) -> List[float]:
        """
        Genera embeddings para un texto.
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            Vector de embedding
        """
        try:
            payload = {
                "model": "text-embedding-ada-002",  # Modelo de embeddings por defecto
                "input": text
            }
            
            response = await self.client.post(self.api_endpoints["embeddings"], json=payload)
            
            # Manejo de errores específicos
            if response.status_code == 401:
                self.logger.error(f"Error 401 Unauthorized al generar embeddings. Detalles: {response.text}")
                raise ValueError(
                    "Error 401: Unauthorized - La API key no es válida o ha expirado. "
                    "Por favor, verifica que tu OPENAI_API_KEY sea correcta en el archivo .env."
                )
            
            if response.status_code == 429:
                self.logger.error(f"Error 429 Too Many Requests al generar embeddings. Detalles: {response.text}")
                raise ValueError(
                    "Error 429: Too Many Requests - Has excedido el límite de solicitudes permitidas. "
                    "Intenta agregar fondos a tu cuenta de OpenAI o espera antes de realizar más solicitudes."
                )
            
            response.raise_for_status()
            data = response.json()
            
            embeddings = data["data"][0]["embedding"]
            return embeddings
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Error HTTP generando embeddings: {e}")
            raise ValueError(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            self.logger.error(f"Error generando embeddings: {e}")
            raise
    
    async def tokenize(self, text: str) -> List[int]:
        """
        Tokeniza un texto.
        
        Note:
            OpenAI no proporciona acceso al tokenizador directamente a través de su API,
            por lo que esta implementación usa una aproximación.
        
        Args:
            text: Texto a tokenizar
            
        Returns:
            Lista de IDs de token (simplificada)
        """
        self.logger.warning("Tokenización precisa no disponible para OpenAI. Usando aproximación.")
        
        # Aproximación muy simple
        words = text.split()
        return list(range(len(words)))
    
    async def close(self):
        """Cierra recursos utilizados por el modelo."""
        if self.client:
            await self.client.aclose()
            self.logger.info(f"Cliente HTTP para modelo '{self.model_info.name}' cerrado") 