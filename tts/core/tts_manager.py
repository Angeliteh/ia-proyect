import os
import requests
import json
import tempfile
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class TTSManager:
    """
    Gestor de Text-to-Speech que utiliza la API de MAYA para convertir texto a voz.
    
    Esta clase proporciona métodos para generar audio a partir de texto, usando
    la API de MAYA como servicio principal.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el gestor de TTS.
        
        Args:
            api_key: API key para MAYA TTS. Si no se proporciona, se intentará obtener
                    de la variable de entorno MAYA_TTS_API_KEY.
        """
        self.api_key = api_key or os.getenv("MAYA_TTS_API_KEY")
        if not self.api_key:
            raise ValueError("No se ha proporcionado API key para MAYA TTS. Configúrala en .env")
        
        # Configuración de la API de MAYA
        self.api_base_url = "https://api.elevenlabs.io/v1"
        self.api_tts_endpoint = "/text-to-speech"
        
        # Configurar logger
        self.logger = logging.getLogger(__name__)
        
        # Cargar voces disponibles
        self._available_voices = None
    
    @property
    def available_voices(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de voces disponibles en la API de MAYA.
        
        Returns:
            Lista de diccionarios con información sobre las voces disponibles.
        """
        if self._available_voices is None:
            try:
                # Endpoint para obtener voces
                voices_url = f"{self.api_base_url}/voices"
                
                headers = {
                    "Accept": "application/json",
                    "xi-api-key": self.api_key
                }
                
                response = requests.get(voices_url, headers=headers)
                response.raise_for_status()
                
                # Procesar la respuesta
                voices_data = response.json()
                self._available_voices = voices_data.get("voices", [])
                self.logger.info(f"Cargadas {len(self._available_voices)} voces disponibles")
                
            except Exception as e:
                self.logger.error(f"Error al obtener voces disponibles: {str(e)}")
                self._available_voices = []
        
        return self._available_voices
    
    def list_voices(self) -> List[Dict[str, str]]:
        """
        Devuelve una lista simplificada de las voces disponibles.
        
        Returns:
            Lista de diccionarios con id, nombre y género de cada voz.
        """
        voices = []
        for voice in self.available_voices:
            voices.append({
                "id": voice.get("voice_id", ""),
                "name": voice.get("name", "Unknown"),
                "gender": "female" if "female" in voice.get("labels", {}).get("gender", "").lower() else "male",
                "language": voice.get("labels", {}).get("language", "Unknown")
            })
        return voices
    
    def get_voice_id_by_name(self, name: str) -> Optional[str]:
        """
        Obtiene el ID de una voz por su nombre.
        
        Args:
            name: Nombre de la voz a buscar.
            
        Returns:
            ID de la voz si se encuentra, None en caso contrario.
        """
        for voice in self.available_voices:
            if voice.get("name", "").lower() == name.lower():
                return voice.get("voice_id")
        return None
    
    def text_to_speech(self, 
                      text: str, 
                      voice_id: Optional[str] = None,
                      voice_name: Optional[str] = None,
                      output_file: Optional[str] = None,
                      model_id: str = "eleven_multilingual_v2",
                      stability: float = 0.5,
                      similarity_boost: float = 0.75) -> str:
        """
        Convierte texto a voz utilizando la API de MAYA.
        
        Args:
            text: Texto a convertir en voz.
            voice_id: ID de la voz a utilizar.
            voice_name: Nombre de la voz (alternativa a voice_id).
            output_file: Ruta donde guardar el archivo de audio generado.
            model_id: ID del modelo de voz a utilizar.
            stability: Factor de estabilidad (0.0-1.0).
            similarity_boost: Factor de similitud (0.0-1.0).
            
        Returns:
            Ruta al archivo de audio generado.
        """
        # Si se proporciona el nombre de la voz pero no el ID, buscar el ID
        if not voice_id and voice_name:
            voice_id = self.get_voice_id_by_name(voice_name)
        
        # Si no se ha proporcionado ID ni nombre, usar la primera voz disponible
        if not voice_id:
            if self.available_voices:
                voice_id = self.available_voices[0].get("voice_id")
                self.logger.info(f"Usando voz por defecto: {self.available_voices[0].get('name')}")
            else:
                raise ValueError("No se ha especificado una voz y no hay voces disponibles")
        
        # Configurar la URL de la API
        url = f"{self.api_base_url}{self.api_tts_endpoint}/{voice_id}"
        
        # Preparar los headers
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Preparar el payload
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        # Si no se especifica un archivo de salida, crear uno temporal
        if not output_file:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(temp_dir, f"tts_output_{hash(text)}.mp3")
        
        try:
            # Realizar la solicitud a la API
            self.logger.info(f"Enviando solicitud TTS para texto: '{text[:50]}...'")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Guardar el audio generado
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            self.logger.info(f"Audio generado correctamente: {output_file}")
            return output_file
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la solicitud a MAYA TTS: {str(e)}")
            if hasattr(e, "response") and e.response:
                self.logger.error(f"Código de estado: {e.response.status_code}")
                self.logger.error(f"Respuesta: {e.response.text}")
            raise
    
    def play_audio(self, audio_file: str) -> None:
        """
        Reproduce un archivo de audio.
        
        Args:
            audio_file: Ruta al archivo de audio a reproducir.
        """
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"No se encontró el archivo de audio: {audio_file}")
        
        try:
            # Verificar la extensión del archivo
            _, ext = os.path.splitext(audio_file)
            
            # Usar métodos específicos del SO para reproducir el audio
            if os.name == 'posix':  # Linux/Mac
                os.system(f"afplay {audio_file} 2>/dev/null || (command -v mpg123 && mpg123 {audio_file}) || (command -v play && play {audio_file})")
            elif os.name == 'nt':  # Windows
                if ext.lower() == '.mp3':
                    # Para archivos MP3 en Windows, usar una solución compatible
                    # Opción 1: Usar PowerShell con un reproductor compatible con MP3
                    self.logger.info("Reproduciendo MP3 con Windows Media Player")
                    os.system(f'powershell -c "(New-Object -ComObject WMPlayer.OCX).MediaPlayer.URL = \\"{audio_file}\\";"')
                    os.system(f'powershell -c "Start-Sleep -s 1"')  # Esperar un momento a que comience la reproducción
                    
                    # Opción 2: Alternativa usando mciSendString si lo anterior falla
                    # Nota: Esto requiere permisos suficientes en el sistema
                    try:
                        import ctypes
                        if ctypes.windll:
                            # Intentar solo si tenemos acceso a windll (Windows)
                            winmm = ctypes.windll.winmm
                            # Cerrar cualquier sesión abierta
                            winmm.mciSendStringW(u"close mp3", None, 0, None)
                            # Abrir el archivo
                            winmm.mciSendStringW(u"open \"{0}\" type mpegvideo alias mp3".format(audio_file), None, 0, None)
                            # Reproducir
                            winmm.mciSendStringW(u"play mp3", None, 0, None)
                            # Esperar a que termine
                            import time
                            time.sleep(2)  # Esperar un momento para que comience a reproducirse
                    except (ImportError, AttributeError, Exception) as e:
                        self.logger.debug(f"No se pudo usar mciSendString: {e}")
                else:
                    # Para archivos WAV usar SoundPlayer
                    os.system(f'powershell -c (New-Object Media.SoundPlayer "{audio_file}").PlaySync();')
            else:
                self.logger.warning(f"Reproducción de audio no implementada para este sistema operativo: {os.name}")
        except Exception as e:
            self.logger.error(f"Error al reproducir audio: {str(e)}") 