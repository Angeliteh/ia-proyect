"""
Componentes principales del sistema Text-to-Speech.

Este subpaquete contiene las clases fundamentales para gestionar la conversión
de texto a voz y la integración con agentes.
"""

from tts.core.tts_manager import TTSManager
from tts.core.simple_tts_manager import SimpleTTSManager
from tts.core.agent_tts_interface import AgentTTSInterface
from tts.core.file_manager import TTSFileManager

__all__ = ['TTSManager', 'SimpleTTSManager', 'AgentTTSInterface', 'TTSFileManager'] 