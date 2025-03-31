import os
import tempfile
import logging
from typing import Optional, Dict, Any, List
import uuid
import time

# Importamos las bibliotecas para gTTS y reproducción
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    
try:
    import pygame
    PYGAME_AVAILABLE = True
    pygame.mixer.init()
except ImportError:
    PYGAME_AVAILABLE = False

class SimpleTTSManager:
    """
    Gestor simplificado de Text-to-Speech que utiliza gTTS (Google Text-to-Speech).
    
    Esta clase proporciona una interfaz similar a TTSManager pero usa
    gTTS para pruebas sin costo.
    """
    
    def __init__(self):
        """
        Inicializa el gestor de TTS simple.
        """
        # Verificar que gTTS está disponible
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS no está instalado. Ejecuta: pip install gtts")
        
        # Configurar logger
        self.logger = logging.getLogger(__name__)
        
        # Lista de voces disponibles (simulada para compatibilidad)
        self._available_voices = self._create_simulated_voices()
        
        # Crear directorio temporal para archivos de audio si no existe
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.logger.info("SimpleTTSManager inicializado correctamente")
    
    def _create_simulated_voices(self) -> List[Dict[str, Any]]:
        """
        Crea una lista de voces simuladas para compatibilidad con la interfaz.
        
        Nota: gTTS no tiene soporte para selección de voces como ElevenLabs,
        pero simulamos la selección para mantener la compatibilidad con la interfaz.
        
        Returns:
            Lista de diccionarios con voces simuladas
        """
        # Crear algunas voces simuladas usando los diferentes idiomas de gTTS
        voices = [
            {
                "voice_id": "es-female-1",
                "name": "María",
                "labels": {"gender": "female", "language": "es"},
                "lang_code": "es"
            },
            {
                "voice_id": "en-female-1",
                "name": "Sarah",
                "labels": {"gender": "female", "language": "en"},
                "lang_code": "en"
            },
            {
                "voice_id": "en-male-1",
                "name": "John",
                "labels": {"gender": "male", "language": "en"},
                "lang_code": "en"
            },
            {
                "voice_id": "es-male-1",
                "name": "Carlos",
                "labels": {"gender": "male", "language": "es"},
                "lang_code": "es"
            },
            {
                "voice_id": "fr-female-1",
                "name": "Sophie",
                "labels": {"gender": "female", "language": "fr"},
                "lang_code": "fr"
            },
            {
                "voice_id": "de-female-1",
                "name": "Helga",
                "labels": {"gender": "female", "language": "de"},
                "lang_code": "de"
            }
        ]
        return voices
    
    @property
    def available_voices(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de voces disponibles (simuladas).
        
        Returns:
            Lista de diccionarios con información sobre las voces disponibles.
        """
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
                "gender": voice.get("labels", {}).get("gender", "unknown"),
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
    
    def get_lang_code_by_voice_id(self, voice_id: str) -> str:
        """
        Obtiene el código de idioma asociado a un ID de voz.
        
        Args:
            voice_id: ID de la voz
            
        Returns:
            Código de idioma (por defecto 'es' si no se encuentra)
        """
        for voice in self.available_voices:
            if voice.get("voice_id") == voice_id:
                return voice.get("lang_code", "es")
        return "es"  # Por defecto español
    
    def text_to_speech(self, 
                      text: str, 
                      voice_id: Optional[str] = None,
                      voice_name: Optional[str] = None,
                      output_file: Optional[str] = None,
                      **kwargs) -> str:
        """
        Convierte texto a voz utilizando gTTS.
        
        Args:
            text: Texto a convertir en voz.
            voice_id: ID de la voz a utilizar.
            voice_name: Nombre de la voz (alternativa a voice_id).
            output_file: Ruta donde guardar el archivo de audio generado.
            **kwargs: Parámetros adicionales (ignorados para compatibilidad)
            
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
                voice_id = "es-female-1"  # Voz por defecto
        
        # Obtener el código de idioma para la voz seleccionada
        lang_code = self.get_lang_code_by_voice_id(voice_id)
        
        # Si no se especifica un archivo de salida, crear uno temporal
        if not output_file:
            # Crear un nombre de archivo único
            filename = f"tts_output_{uuid.uuid4().hex}.mp3"
            output_file = os.path.join(self.temp_dir, filename)
        
        try:
            # Crear el objeto gTTS y guardar el audio
            self.logger.info(f"Generando audio para texto: '{text[:50]}...' (idioma: {lang_code})")
            tts = gTTS(text=text, lang=lang_code, slow=False)
            tts.save(output_file)
            
            self.logger.info(f"Audio generado correctamente: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error al generar audio: {str(e)}")
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
            if PYGAME_AVAILABLE:
                # Usar pygame para reproducir el audio (multiplataforma)
                self.logger.info(f"Reproduciendo audio con pygame: {audio_file}")
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # Esperar a que termine la reproducción
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            
            else:
                # Alternativa usando comandos del sistema
                if os.name == 'posix':  # Linux/Mac
                    os.system(f"afplay {audio_file} 2>/dev/null || (command -v mpg123 && mpg123 {audio_file}) || (command -v play && play {audio_file})")
                elif os.name == 'nt':  # Windows
                    os.system(f'powershell -c "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak([System.IO.File]::ReadAllText(\'{audio_file}\'));"')
                else:
                    self.logger.warning(f"Reproducción de audio no implementada para este sistema operativo: {os.name}")
        
        except Exception as e:
            self.logger.error(f"Error al reproducir audio: {str(e)}") 