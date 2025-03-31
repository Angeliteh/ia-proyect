#!/usr/bin/env python
"""
Main Assistant Example.

This example demonstrates how to use the MainAssistant as a central
point of interaction with the user, coordinating with specialized agents.
"""

import os
import sys
import asyncio
import logging
import argparse
import time
import json
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
project_dir = str(current_dir.parent.parent.parent)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("main_assistant_example")

# Try to import the required modules
try:
    from agents import (
        MainAssistant,
        EchoAgent,
        CodeAgent,
        SystemAgent,
        OrchestratorAgent,
        setup_communication_system,
        shutdown_communication_system,
        communicator
    )
    from models import ModelManager
    logger.info("Módulos importados correctamente")
except ImportError as e:
    logger.error(f"Error al importar módulos: {e}")
    sys.exit(1)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = os.path.join(project_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Variables de entorno cargadas desde {env_path}")
except ImportError:
    logger.warning("python-dotenv no instalado. Las variables de entorno podrían no cargarse correctamente.")

async def setup_agents() -> dict:
    """
    Configura y registra los agentes necesarios para la demostración.
    
    Returns:
        Diccionario con las instancias de los agentes
    """
    logger.info("Configurando agentes...")
    
    # Inicializar sistema de comunicación
    await setup_communication_system()
    
    # Configurar un gestor de modelos para el CodeAgent
    models_config = {
        "models": [
            {
                "name": "gemini-2.0-flash",
                "model_type": "gemini",
                "local": False,
                "api_key_env": "GOOGLE_API_KEY",
                "context_length": 8192
            }
        ]
    }
    
    # Write temporary config file
    config_path = os.path.join(current_dir, "temp_model_config.json")
    with open(config_path, "w") as f:
        json.dump(models_config, f, indent=2)
    
    # Load model manager with our config
    model_manager = ModelManager(config_path)
    
    # Clean up temporary file
    os.remove(config_path)
    
    # Crear EchoAgent
    echo_config = {
        "name": "Echo Service",
        "description": "Servicio simple que devuelve lo que recibe, útil para pruebas.",
        "use_tts": True
    }
    echo_agent = EchoAgent("echo_service", echo_config)
    
    # Crear CodeAgent
    code_config = {
        "name": "Code Assistant",
        "description": "Asistente de programación que puede generar y analizar código.",
        "model_manager": model_manager,
        "default_model": "gemini-2.0-flash",
        "use_tts": True
    }
    code_agent = CodeAgent("code_assistant", code_config)
    
    # Crear SystemAgent
    system_config = {
        "name": "System Manager",
        "description": "Agente para interactuar con el sistema de archivos y ejecutar comandos.",
        "working_dir": os.getcwd(),
        "allowed_executables": ["notepad", "calc", "explorer"],
        "use_tts": True
    }
    system_agent = SystemAgent("system_manager", system_config)
    
    # Crear OrchestratorAgent
    orchestrator_config = {
        "name": "Orchestrator",
        "description": "Orquestador que coordina tareas complejas entre agentes especializados.",
        "max_concurrent_tasks": 3,
        "use_tts": True
    }
    orchestrator_agent = OrchestratorAgent("orchestrator", orchestrator_config)
    
    # Registrar manualmente todos los agentes con el comunicador
    communicator.register_agent(echo_agent)
    communicator.register_agent(code_agent)
    communicator.register_agent(system_agent)
    communicator.register_agent(orchestrator_agent)
    
    # Registrar agentes disponibles con el orquestador
    await orchestrator_agent.register_available_agent("echo_service", echo_agent.get_capabilities())
    await orchestrator_agent.register_available_agent("code_assistant", code_agent.get_capabilities())
    await orchestrator_agent.register_available_agent("system_manager", system_agent.get_capabilities())
    
    # Crear MainAssistant
    main_assistant_config = {
        "name": "Jarvis",
        "description": "Asistente principal que centraliza todas las interacciones con el usuario.",
        "orchestrator_id": "orchestrator",
        "use_tts": True,
        "default_voice": "Carlos"
    }
    main_assistant = MainAssistant("main_assistant", main_assistant_config)
    
    # Registrar el MainAssistant con el comunicador
    communicator.register_agent(main_assistant)
    
    # Registrar agentes especializados con el MainAssistant
    await main_assistant.register_specialized_agent("echo_service", echo_agent.get_capabilities())
    await main_assistant.register_specialized_agent("code_assistant", code_agent.get_capabilities())
    await main_assistant.register_specialized_agent("system_manager", system_agent.get_capabilities())
    await main_assistant.register_specialized_agent("orchestrator", orchestrator_agent.get_capabilities())
    
    # IMPORTANTE: Asegurarnos que los agentes están preparados para recibir mensajes
    await echo_agent.register_with_communicator()
    await code_agent.register_with_communicator()
    await system_agent.register_with_communicator()
    await orchestrator_agent.register_with_communicator() 
    await main_assistant.register_with_communicator()
    
    logger.info("Todos los agentes configurados correctamente")
    
    return {
        "main": main_assistant,
        "echo": echo_agent,
        "code": code_agent,
        "system": system_agent,
        "orchestrator": orchestrator_agent
    }

async def test_direct_queries(main_assistant):
    """
    Prueba consultas directas que el MainAssistant puede manejar sin delegación.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Probando consultas directas ===")
    
    # Prueba de saludo
    query = "Hola, buen día"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    logger.info(f"TTS: {response.metadata.get('tts', {})}")
    
    # Dar tiempo para escuchar la respuesta de voz
    await asyncio.sleep(3)
    
    # Prueba de pregunta de identidad
    query = "¿Quién eres y qué puedes hacer?"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    
    # Dar tiempo para escuchar la respuesta de voz
    await asyncio.sleep(5)

async def test_echo_delegation(main_assistant):
    """
    Prueba la delegación al EchoAgent.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Probando delegación a EchoAgent ===")
    
    query = "Echo: repite este mensaje importante"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    
    # Dar tiempo para escuchar la respuesta de voz
    await asyncio.sleep(3)

async def test_code_delegation(main_assistant):
    """
    Prueba la delegación al CodeAgent.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Probando delegación a CodeAgent ===")
    
    query = "Escribe un programa simple en Python para calcular el factorial de un número"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    
    # Dar tiempo para escuchar la respuesta de voz o parte de ella
    await asyncio.sleep(10)

async def test_system_delegation(main_assistant):
    """
    Prueba la delegación al SystemAgent.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Probando delegación a SystemAgent ===")
    
    query = "Muestra información sobre el directorio actual"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    
    # Dar tiempo para escuchar la respuesta de voz
    await asyncio.sleep(5)

async def test_orchestrator_delegation(main_assistant):
    """
    Prueba la delegación al OrchestratorAgent para tareas complejas.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Probando delegación a OrchestratorAgent ===")
    
    query = "Necesito un análisis del sistema actual y luego generar un script para monitorizar el uso de memoria"
    logger.info(f"Usuario: {query}")
    response = await main_assistant.process(query)
    logger.info(f"Asistente: {response.content}")
    
    # Las tareas del orquestador pueden tomar más tiempo
    await asyncio.sleep(15)

async def run_interactive_session(main_assistant):
    """
    Ejecuta una sesión interactiva con el MainAssistant.
    
    Args:
        main_assistant: Instancia de MainAssistant
    """
    logger.info("=== Iniciando sesión interactiva ===")
    logger.info("Escribe 'salir' para terminar la sesión")
    
    while True:
        try:
            query = input("\nTú: ")
            if query.lower() in ["salir", "exit", "quit", "q"]:
                break
                
            # Añadir timestamp a la solicitud
            context = {"timestamp": time.time()}
            
            # Procesar solicitud
            logger.info("Enviando solicitud al asistente...")
            response = await main_assistant.process(query, context)
            
            print(f"\n{main_assistant.config['name']}: {response.content}")
            
            # Si hay metadatos de TTS, mostrar información
            tts_info = response.metadata.get("tts", {})
            if tts_info.get("success"):
                logger.info(f"Audio generado: {tts_info.get('audio_file')}")
                
            # Dar tiempo para escuchar la respuesta completa
            await asyncio.sleep(2)
            
        except KeyboardInterrupt:
            logger.info("Sesión terminada por el usuario")
            break
        except Exception as e:
            logger.error(f"Error en la sesión interactiva: {e}")

async def main():
    """Función principal que ejecuta el ejemplo."""
    parser = argparse.ArgumentParser(description="Ejemplo de MainAssistant")
    parser.add_argument("--interactive", action="store_true", help="Ejecutar en modo interactivo")
    parser.add_argument("--test", choices=["all", "direct", "echo", "code", "system", "orchestrator"],
                        default="direct", help="Tipo de prueba a ejecutar")
    args = parser.parse_args()
    
    try:
        # Configurar agentes
        agents = await setup_agents()
        main_assistant = agents["main"]
        
        if args.interactive:
            # Modo interactivo
            await run_interactive_session(main_assistant)
        else:
            # Ejecutar pruebas específicas
            if args.test == "all" or args.test == "direct":
                await test_direct_queries(main_assistant)
                
            if args.test == "all" or args.test == "echo":
                await test_echo_delegation(main_assistant)
                
            if args.test == "all" or args.test == "code":
                await test_code_delegation(main_assistant)
                
            if args.test == "all" or args.test == "system":
                await test_system_delegation(main_assistant)
                
            if args.test == "all" or args.test == "orchestrator":
                await test_orchestrator_delegation(main_assistant)
        
    except Exception as e:
        logger.error(f"Error en la ejecución: {e}")
    finally:
        # Cerrar sistema de comunicación
        await shutdown_communication_system()
        logger.info("Sistema de comunicación cerrado correctamente")

if __name__ == "__main__":
    asyncio.run(main()) 