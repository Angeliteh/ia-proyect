# Sistema Text-to-Speech (TTS)

Este módulo proporciona capacidades de Text-to-Speech (TTS) a todo el sistema de agentes de IA, permitiendo a los agentes comunicarse mediante voz además de texto.

## Características principales

- **Arquitectura modular**: Sistema extensible que permite múltiples implementaciones de TTS
- **Múltiples proveedores**: Soporte para Google TTS (gTTS) y MAYA/ElevenLabs
- **Gestión inteligente de archivos**: Sistema de limpieza automática y caché
- **Personalización de voces**: Asignación de voces específicas por agente
- **Selección de idioma**: Soporte para múltiples idiomas 
- **Integración con agentes**: Todos los agentes pueden usar TTS mediante la `AgentTTSInterface`
- **Reproducción automática**: Reproducción de audio usando pygame

## Arquitectura

El sistema TTS se compone de los siguientes elementos principales:

### Estructura de directorios

```
tts/
├── core/                    # Componentes centrales
│   ├── __init__.py          # Exporta las clases principales
│   ├── agent_tts_interface.py  # Interfaz para integración con agentes
│   ├── simple_tts_manager.py   # Implementación basada en gTTS (Google)
│   ├── tts_manager.py       # Implementación con MAYA/ElevenLabs
│   └── file_manager.py      # Gestión de archivos de audio
├── temp/                    # Directorio para archivos temporales
│   └── .tts_file_registry.json   # Registro de archivos generados
└── __init__.py              # Inicialización del módulo
```

### Componentes principales

#### 1. AgentTTSInterface

Interfaz que conecta cada agente con el sistema TTS, permitiendo que cualquier agente pueda generar respuestas de voz.

```python
class AgentTTSInterface:
    def __init__(self, agent_id, tts_manager=None, default_voice=None):
        # ...
    
    def process_response_with_tts(self, response_text):
        # Convierte el texto en audio y lo reproduce
```

#### 2. SimpleTTSManager

Implementación de TTS basada en Google Text-to-Speech (gTTS), ideal para desarrollo y pruebas.

```python
class SimpleTTSManager:
    def __init__(self, temp_dir=None, default_lang="es", ...):
        # ...
    
    def text_to_speech(self, text, voice_name=None, language=None):
        # Genera un archivo de audio a partir del texto
    
    def play_audio(self, file_path):
        # Reproduce el archivo de audio generado
```

#### 3. TTSManager

Implementación premium con MAYA/ElevenLabs para producción (mayor calidad).

#### 4. TTSFileManager

Sistema de gestión de archivos temporales que implementa:

- **Limpieza automática** de archivos antiguos
- **Control de espacio** en disco
- **Sistema de caché** para reutilizar audios previos
- **Registro persistente** de archivos generados

```python
class TTSFileManager:
    def __init__(self, temp_dir=None, max_size_mb=100, max_age_hours=24, ...):
        # ...
    
    def register_file(self, file_path, text_hash, metadata=None):
        # Registra un nuevo archivo generado
    
    def cleanup_old_files(self, max_age_hours=None):
        # Elimina archivos antiguos
    
    def cleanup_by_size(self, max_size_mb=None):
        # Elimina archivos si se supera el límite de tamaño
    
    def get_from_cache(self, text_hash):
        # Recupera un archivo desde la caché
```

## Guía de uso

### Uso básico

```python
from tts.core import SimpleTTSManager

# Crear el gestor TTS
tts_manager = SimpleTTSManager()

# Generar audio a partir de texto
audio_file = tts_manager.text_to_speech(
    text="Hola, soy un asistente virtual.",
    voice_name="Carlos"  # Opcional, usa la voz predeterminada si no se especifica
)

# Reproducir el audio
tts_manager.play_audio(audio_file)
```

### Integración con agentes

```python
from tts.core import AgentTTSInterface
from agents import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, agent_id, **kwargs):
        super().__init__(agent_id, **kwargs)
        
        # Configurar TTS para este agente
        self.tts = AgentTTSInterface(
            agent_id=self.agent_id,
            default_voice="Carlos"  # Voz personalizada para este agente
        )
    
    async def process(self, query, **kwargs):
        # Procesar la consulta normalmente
        response = await super().process(query, **kwargs)
        
        # Si TTS está habilitado, procesar la respuesta con voz
        if kwargs.get("use_tts", True):
            self.tts.process_response_with_tts(response.content)
        
        return response
```

### Personalización de voces

```python
# Configuración de voces específicas por agente
agent_voices = {
    "main_assistant": "Carlos",
    "echo_agent": "Jorge", 
    "code_agent": "Enrique",
    "system_agent": "Diego"
}

# Crear un MainAssistant con TTS y voces personalizadas
from agents import MainAssistant

assistant = MainAssistant(
    agent_id="main_assistant",
    config={
        "use_tts": True,
        "default_voice": "Carlos",
        "agent_voices": agent_voices
    }
)
```

### Gestión de archivos temporales

```python
from tts.core import TTSFileManager

# Crear gestor de archivos
file_manager = TTSFileManager(
    temp_dir="tts/temp",
    max_size_mb=50,          # Limitar a 50MB
    max_age_hours=12,        # Eliminar archivos más antiguos de 12 horas
    enable_auto_cleanup=True # Activar limpieza automática
)

# Limpiar archivos manualmente
deleted_files = file_manager.cleanup_old_files(max_age_hours=6)
print(f"Se eliminaron {len(deleted_files)} archivos antiguos")

# Verificar y controlar el tamaño total
size_mb = file_manager.get_total_size_mb()
if size_mb > 40:
    cleaned_files = file_manager.cleanup_by_size(max_size_mb=30)
    print(f"Espacio liberado: {sum(f['size_bytes'] for f in cleaned_files) / (1024*1024):.2f} MB")
```

### Ejemplo completo

Consulta el script de ejemplo en `examples/tts/tts_echo_test.py` para ver una implementación completa que demuestra todas las características:

```bash
# Ejecutar el ejemplo completo
python examples/tts/tts_echo_test.py --voice "Carlos" --query "Hola, esto es una prueba de Text-to-Speech"
```

## Voces disponibles

El sistema utiliza las voces de Google Text-to-Speech en español, que incluyen:

- **Carlos** (voz masculina, recomendada)
- **Jorge** (voz masculina alternativa)
- **Enrique** (voz masculina alternativa)
- **Diego** (voz masculina alternativa)
- **Sofía** (voz femenina)
- **Francisca** (voz femenina alternativa)

Para listado completo: 

```python
from tts.core import SimpleTTSManager

tts = SimpleTTSManager()
for voice in tts.get_available_voices():
    print(f"- {voice}")
```

## Requisitos

- **pygame**: Para reproducción de audio
- **gTTS**: Para generación de voz con Google TTS
- **Opcional**: API key de MAYA/ElevenLabs para voces de mayor calidad

## Implementación futura

- Sistema de streaming para respuestas largas
- Caché semántica (para frases similares)
- Panel de configuración de voces
- Integración con modelos de TTS locales
- Generación asíncrona de audio

## Licencia

MIT 