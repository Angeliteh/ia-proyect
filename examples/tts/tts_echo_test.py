#!/usr/bin/env python
"""
TTS Echo Agent Test

Este ejemplo demuestra cómo utilizar el sistema Text-to-Speech (TTS) con EchoAgent.
El script crea una instancia de EchoAgent con TTS habilitado y envía una consulta
que será convertida a voz usando gTTS (Google Text-to-Speech).
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("tts_test")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Cargar variables de entorno
load_dotenv()

# Importar los componentes necesarios
try:
    from agents.echo_agent import EchoAgent
    from tts.core.simple_tts_manager import SimpleTTSManager
    from tts.core.agent_tts_interface import AgentTTSInterface
    logger.info("Módulos importados correctamente")
except ImportError as e:
    logger.error(f"Error al importar módulos: {e}")
    sys.exit(1)

async def run_tts_test(query: str, list_voices: bool = False, voice_name: str = None, play_audio: bool = True, use_maya: bool = False):
    """
    Ejecuta una prueba del sistema TTS con EchoAgent.
    
    Args:
        query: Consulta a enviar al agente
        list_voices: Si es True, lista las voces disponibles
        voice_name: Nombre de la voz a utilizar (opcional)
        play_audio: Si es True, reproduce el audio generado
        use_maya: Si es True, usa MAYA/ElevenLabs en lugar de gTTS
    """
    logger.info("Iniciando prueba de TTS con EchoAgent")
    
    # Crear el gestor TTS correspondiente
    if use_maya:
        try:
            from tts.core.tts_manager import TTSManager
            tts_manager = TTSManager()
        except ImportError:
            logger.error("No se pudo importar TTSManager (MAYA). Asegúrate de tener las dependencias instaladas.")
            return
    else:
        tts_manager = SimpleTTSManager()
    
    # Si se solicita listar voces
    if list_voices:
        try:
            voices = tts_manager.list_voices()
            print("\n=== Voces disponibles ===")
            for voice in voices:
                print(f"ID: {voice['id']}")
                print(f"Nombre: {voice['name']}")
                print(f"Género: {voice['gender']}")
                print(f"Idioma: {voice.get('language', 'No especificado')}")
                print("-------------------")
            return
        except Exception as e:
            logger.error(f"Error al listar voces: {e}")
            return
    
    # Crear la interfaz TTS con el gestor seleccionado
    tts_interface = AgentTTSInterface(tts_manager=tts_manager, use_simple_tts=not use_maya)
    
    # Configurar EchoAgent con TTS habilitado
    echo_agent = EchoAgent(
        agent_id="echo_tts_test",
        config={
            "name": "Echo TTS",
            "description": "Agente de eco con capacidades de TTS",
            "use_tts": True  # Habilitar TTS
        }
    )
    
    # Asignar la interfaz TTS al agente manualmente
    echo_agent.tts_interface = tts_interface
    
    # Verificar que el agente tiene TTS habilitado
    if not echo_agent.has_tts():
        logger.error("El agente no tiene TTS habilitado. Verifica la configuración.")
        return
    
    logger.info(f"Enviando consulta al agente: '{query}'")
    
    # Crear contexto con parámetros TTS
    context = {
        "use_tts": True,
        "play_audio": play_audio,
        "tts_params": {}
    }
    
    # Si se especifica un nombre de voz, añadirlo al contexto
    if voice_name:
        context["tts_params"]["voice_name"] = voice_name
        logger.info(f"Usando voz: {voice_name}")
    
    # Procesar la consulta
    response = await echo_agent.process(query, context)
    
    # Mostrar información de la respuesta
    print("\n=== Respuesta del agente ===")
    print(f"Contenido: {response.content}")
    print(f"Estado: {response.status}")
    
    # Mostrar información de TTS
    if "tts" in response.metadata:
        tts_info = response.metadata["tts"]
        print("\n=== Información de TTS ===")
        print(f"Éxito: {tts_info.get('success', False)}")
        
        if tts_info.get("success", False):
            print(f"Archivo de audio: {tts_info.get('audio_file')}")
            print(f"Voz utilizada: {tts_info.get('voice')}")
            
            # Si se ha generado audio pero no se ha reproducido automáticamente, ofrecer reproducirlo
            if not play_audio:
                print("\nPara reproducir el audio generado manualmente, ejecuta:")
                print(f"python -c \"import pygame; pygame.mixer.init(); pygame.mixer.music.load('{tts_info.get('audio_file')}'); pygame.mixer.music.play(); import time; time.sleep(5)\"")
        else:
            print(f"Error: {tts_info.get('error', 'Error desconocido')}")
    else:
        print("\nNo se ha generado información de TTS en la respuesta")

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(description="Prueba de Text-to-Speech con EchoAgent")
    parser.add_argument("--query", default="Hola, soy un agente inteligente con capacidad de voz gracias a Google Text-to-Speech. ¿En qué puedo ayudarte hoy?", 
                        help="Consulta a enviar al agente")
    parser.add_argument("--list-voices", action="store_true", help="Listar voces disponibles")
    parser.add_argument("--voice", help="Nombre de la voz a utilizar")
    parser.add_argument("--no-play", action="store_true", help="No reproducir el audio automáticamente")
    parser.add_argument("--use-maya", action="store_true", help="Usar MAYA/ElevenLabs en lugar de gTTS")
    
    args = parser.parse_args()
    
    # Ejecutar el test de forma asíncrona
    asyncio.run(run_tts_test(
        query=args.query,
        list_voices=args.list_voices,
        voice_name=args.voice,
        play_audio=not args.no_play,
        use_maya=args.use_maya
    ))

if __name__ == "__main__":
    main() 