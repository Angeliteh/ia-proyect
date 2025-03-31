"""
Componentes principales del sistema Text-to-Speech.

Este subpaquete contiene las clases fundamentales para gestionar la conversión
de texto a voz y la integración con agentes.
"""

from tts.core.tts_manager import TTSManager
from tts.core.agent_tts_interface import AgentTTSInterface

__all__ = ['TTSManager', 'AgentTTSInterface'] 