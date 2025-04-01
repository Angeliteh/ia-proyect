import logging
from typing import Optional, Dict, Any, Union
import os
import json

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

# Estado global de TTS (activo/inactivo)
_TTS_GLOBALLY_ENABLED = True
_TTS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tts_config.json')

def load_tts_config():
    """Carga la configuración del TTS desde archivo"""
    global _TTS_GLOBALLY_ENABLED
    try:
        if os.path.exists(_TTS_CONFIG_PATH):
            with open(_TTS_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                _TTS_GLOBALLY_ENABLED = config.get('enabled', True)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error cargando config TTS: {str(e)}")

def save_tts_config():
    """Guarda la configuración del TTS en archivo"""
    try:
        config = {'enabled': _TTS_GLOBALLY_ENABLED}
        os.makedirs(os.path.dirname(_TTS_CONFIG_PATH), exist_ok=True)
        with open(_TTS_CONFIG_PATH, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        logging.getLogger(__name__).error(f"Error guardando config TTS: {str(e)}")

def is_tts_enabled() -> bool:
    """Comprueba si el TTS está globalmente habilitado"""
    return _TTS_GLOBALLY_ENABLED

def disable_tts():
    """Desactiva el TTS globalmente"""
    global _TTS_GLOBALLY_ENABLED
    _TTS_GLOBALLY_ENABLED = False
    save_tts_config()
    logging.getLogger(__name__).info("TTS desactivado globalmente")

def enable_tts():
    """Activa el TTS globalmente"""
    global _TTS_GLOBALLY_ENABLED
    _TTS_GLOBALLY_ENABLED = True
    save_tts_config()
    logging.getLogger(__name__).info("TTS activado globalmente")

# Cargar la configuración inicial
load_tts_config()

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
        # Si el TTS está globalmente desactivado, devolver respuesta de texto solamente
        if not _TTS_GLOBALLY_ENABLED:
            return {
                "success": False,
                "disabled": True,
                "agent": agent_name,
                "text": text
            }
        
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
        # Simplificar el texto eliminando prefijos formales o repetitivos
        # Reducir prefijos formales en el texto para evitar repeticiones
        # Eliminar prefijos comunes que hacen el diálogo menos natural
        prefixes_to_remove = [
            f"Soy {agent_name}. ",
            f"Soy {agent_name}, ",
            f"{agent_name}: ",
            "Hola, soy tu asistente. ",
            "Como tu asistente, ",
            "En mi rol de asistente, "
        ]
        
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        
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
            "OrchestratorAgent": "Sarah",
            "V.I.O.": "Carlos",  # Voz específica para V.I.O.
            "main_assistant": "Carlos"
        }
        
        # Devolver la voz asignada o usar la voz por defecto
        return agent_voices.get(agent_name, self.default_voice_name) 