"""
Módulo Text-to-Speech que proporciona funcionalidades para convertir texto a voz.

Este módulo utiliza la API de MAYA (ElevenLabs) para convertir texto a voz y
proporciona una interfaz para integrar esta funcionalidad con agentes IA.
"""

import os
import logging

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Verificar que el directorio de archivos temporales existe
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'temp')):
    os.makedirs(os.path.join(os.path.dirname(__file__), 'temp'), exist_ok=True)

# Exportar clases principales
from tts.core.tts_manager import TTSManager
from tts.core.agent_tts_interface import AgentTTSInterface

__all__ = ['TTSManager', 'AgentTTSInterface'] 