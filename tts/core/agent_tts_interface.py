import logging
from typing import Optional, Dict, Any, Union
import os

# Importaciones para diferentes gestores de TTS
TTS_MANAGER_AVAILABLE = False
SIMPLE_TTS_MANAGER_AVAILABLE = False

try:
    from tts.core.tts_manager import TTSManager
    TTS_MANAGER_AVAILABLE = True
except ImportError:
    pass

try:
    from tts.core.simple_tts_manager import SimpleTTSManager
    SIMPLE_TTS_MANAGER_AVAILABLE = True
except ImportError:
    pass

class AgentTTSInterface:
    """
    Interfaz para integrar el sistema TTS con los agentes.
    
    Esta clase proporciona una capa de abstracción entre los agentes y el sistema TTS,
    permitiendo a los agentes generar respuestas de voz de manera sencilla.
    """
    
    def __init__(self, tts_manager=None, use_simple_tts=True):
        """
        Inicializa la interfaz TTS para agentes.
        
        Args:
            tts_manager: Instancia de gestor TTS para utilizar. Si no se proporciona,
                        se creará una nueva instancia según la disponibilidad.
            use_simple_tts: Si es True, se usará SimpleTTSManager en lugar de TTSManager
                            cuando sea posible (para pruebas sin costo).
        """
        self.logger = logging.getLogger(__name__)
        
        # Si se proporciona un gestor, usarlo directamente
        if tts_manager is not None:
            self.tts_manager = tts_manager
        else:
            # Determinar qué gestor usar basándose en la disponibilidad y preferencia
            if use_simple_tts and SIMPLE_TTS_MANAGER_AVAILABLE:
                self.logger.info("Usando SimpleTTSManager (gTTS) para conversión de texto a voz")
                self.tts_manager = SimpleTTSManager()
            elif TTS_MANAGER_AVAILABLE:
                self.logger.info("Usando TTSManager (MAYA/ElevenLabs) para conversión de texto a voz")
                self.tts_manager = TTSManager()
            else:
                raise ImportError("No se encontró ningún gestor de TTS disponible")
        
        # Configuración por defecto para agentes
        self.default_voice_name = "María" if use_simple_tts else "Bella"
        
        # Inicializar automáticamente para verificar conexión
        try:
            voices = self.tts_manager.list_voices()
            self.logger.info(f"Interfaz TTS inicializada correctamente con {len(voices)} voces disponibles")
        except Exception as e:
            self.logger.error(f"Error al inicializar la interfaz TTS: {str(e)}")
        
    def process_response(self, 
                         text: str, 
                         agent_name: str,
                         tts_params: Optional[Dict[str, Any]] = None,
                         play_immediately: bool = False) -> Dict[str, Any]:
        """
        Procesa una respuesta de agente convirtiéndola en voz.
        
        Args:
            text: Texto de la respuesta a convertir en voz.
            agent_name: Nombre del agente que realiza la respuesta.
            tts_params: Parámetros adicionales para la generación de TTS.
            play_immediately: Si es True, reproduce el audio inmediatamente.
            
        Returns:
            Diccionario con información sobre el audio generado.
        """
        # Inicializar parámetros
        params = tts_params or {}
        
        # Seleccionar voz según el agente (se puede personalizar por agente)
        voice_name = params.get("voice_name", self.get_voice_for_agent(agent_name))
        
        # IMPORTANTE: Eliminar la clave voice_name de los parámetros para evitar duplicación
        # ya que la pasaremos explícitamente
        if "voice_name" in params:
            params = params.copy()  # Crear una copia para no modificar el original
            del params["voice_name"]
            
        # Procesar el texto antes de enviarlo a TTS
        processed_text = self._preprocess_text(text, agent_name)
        
        try:
            # Verificar si nos pasan una ruta específica para guardar el audio
            output_dir = params.get("output_dir")
            output_file = None
            
            if output_dir:
                # Asegurarse de que el directorio existe
                os.makedirs(output_dir, exist_ok=True)
                
                # Crear un nombre de archivo basado en el agente y timestamp
                import time
                timestamp = int(time.time())
                output_file = os.path.join(output_dir, f"{agent_name.lower()}_{timestamp}.mp3")
                
                # Eliminar output_dir de params para no pasar parámetros innecesarios
                params = params.copy()
                del params["output_dir"]
            
            # Generar el audio
            audio_file = self.tts_manager.text_to_speech(
                text=processed_text,
                voice_name=voice_name,
                output_file=output_file,
                **params
            )
            
            # Reproducir automáticamente si se ha solicitado
            if play_immediately:
                self.tts_manager.play_audio(audio_file)
            
            return {
                "success": True,
                "audio_file": audio_file,
                "agent": agent_name,
                "text": text,
                "voice": voice_name
            }
            
        except Exception as e:
            self.logger.error(f"Error al procesar respuesta TTS para {agent_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "agent": agent_name,
                "text": text
            }

    def _preprocess_text(self, text: str, agent_name: str) -> str:
        """
        Preprocesa el texto antes de enviarlo al sistema TTS.
        
        Args:
            text: Texto original a preprocesar.
            agent_name: Nombre del agente.
            
        Returns:
            Texto preprocesado.
        """
        # Se puede implementar cualquier preprocesamiento necesario
        # Por ejemplo, añadir pausas, formatear números, etc.
        
        # Ejemplo simple: añadir un prefijo de agente si no está ya incluido
        if not text.startswith(f"{agent_name}:") and not text.startswith(f"Soy {agent_name}"):
            text = f"Soy {agent_name}. {text}"
            
        return text
    
    def get_voice_for_agent(self, agent_name: str) -> str:
        """
        Obtiene el nombre de la voz asociada a un agente específico.
        
        Args:
            agent_name: Nombre del agente.
            
        Returns:
            Nombre de la voz para este agente.
        """
        # Mapeo de voces por agente (esto podría cargarse desde configuración)
        agent_voices = {
            "EchoAgent": "Carlos",
            "Echo TTS": "Carlos",
            "CodeAgent": "John",
            "SystemAgent": "María",
            "OrchestratorAgent": "Sarah"
        }
        
        # Devolver la voz asignada o usar la voz por defecto
        return agent_voices.get(agent_name, self.default_voice_name) 