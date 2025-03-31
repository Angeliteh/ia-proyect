#!/usr/bin/env python
"""
Error Handling Tests for the AI Agent System

Este script proporciona pruebas para verificar cómo el sistema maneja diferentes
tipos de errores y situaciones excepcionales, asegurando que sea robusto y
capaz de recuperarse de fallos.
"""

import os
import sys
import asyncio
import logging
import argparse
import time
from pathlib import Path

# Añadir la ruta del proyecto al PATH
current_dir = Path(__file__).resolve().parent
project_dir = str(current_dir.parent.parent)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("error_tests")

# Intentar importar los módulos requeridos
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

class UnavailableAgent(EchoAgent):
    """Un agente que simula estar no disponible o con fallos."""
    
    def __init__(self, agent_id, config=None):
        super().__init__(agent_id, config or {})
        self.fail_count = 0
        self.max_fails = config.get("max_fails", 2)
        
    async def process(self, query, context=None):
        """
        Procesa una consulta, simulando fallos según la configuración.
        
        Args:
            query: La consulta a procesar
            context: Contexto adicional opcional
            
        Returns:
            AgentResponse: La respuesta del agente o un error
        """
        from agents.base import AgentResponse
        
        # Simular no disponibilidad temporal
        if self.fail_count < self.max_fails:
            self.fail_count += 1
            logger.warning(f"Agente {self.agent_id} no disponible (fallo {self.fail_count}/{self.max_fails})")
            # Retornar respuesta de error
            return AgentResponse(
                content=f"Error: Agente {self.agent_id} temporalmente no disponible",
                status="error",
                agent_id=self.agent_id,
                metadata={
                    "error": {
                        "type": "unavailable",
                        "message": "Agente temporalmente no disponible"
                    }
                }
            )
        
        # Después de ciertos fallos, volver a responder normalmente
        logger.info(f"Agente {self.agent_id} disponible nuevamente después de {self.fail_count} fallos")
        return await super().process(query, context)

async def setup_agents(test_scenario=None):
    """
    Configura y registra los agentes necesarios para las pruebas.
    
    Args:
        test_scenario: Escenario de prueba específico a configurar
        
    Returns:
        dict: Diccionario con las instancias de los agentes
    """
    logger.info(f"Configurando agentes para escenario: {test_scenario}")
    
    # Inicializar sistema de comunicación
    await setup_communication_system()
    
    # Configuraciones básicas
    agents = {}
    
    # Crear EchoAgent regular
    echo_config = {
        "name": "Echo Service",
        "description": "Servicio simple que devuelve lo que recibe.",
        "use_tts": True
    }
    echo_agent = EchoAgent("echo_service", echo_config)
    agents["echo"] = echo_agent
    
    # Crear SystemAgent
    system_config = {
        "name": "System Manager",
        "description": "Agente para interactuar con el sistema.",
        "working_dir": os.getcwd(),
        "use_tts": True
    }
    system_agent = SystemAgent("system_manager", system_config)
    agents["system"] = system_agent
    
    # Para el escenario de agente no disponible
    if test_scenario == "agent_unavailable":
        # Crear un agente inestable que fallará inicialmente
        unstable_config = {
            "name": "Unstable Echo",
            "description": "Agente de eco inestable que falla temporalmente.",
            "max_fails": 2,  # Fallará dos veces antes de recuperarse
            "use_tts": True
        }
        unstable_agent = UnavailableAgent("unstable_echo", unstable_config)
        agents["unstable"] = unstable_agent
        
        # Registrar con el comunicador
        communicator.register_agent(unstable_agent)
    
    # Para el escenario de solicitud inválida, usar configuración base
    
    # Registrar los agentes estándar con el comunicador
    communicator.register_agent(echo_agent)
    communicator.register_agent(system_agent)
    
    # Crear MainAssistant con configuración según el escenario
    main_config = {
        "name": "Asistente Principal",
        "description": "Asistente principal para pruebas de manejo de errores.",
        "use_tts": True,
        "retry_count": 3,  # Intentará hasta 3 veces
        "retry_delay": 1.0  # 1 segundo entre intentos
    }
    
    main_assistant = MainAssistant("main_assistant", main_config)
    agents["main"] = main_assistant
    
    # Registrar el MainAssistant con el comunicador
    communicator.register_agent(main_assistant)
    
    # Registrar agentes especializados con el MainAssistant
    await main_assistant.register_specialized_agent("echo_service", echo_agent.get_capabilities())
    await main_assistant.register_specialized_agent("system_manager", system_agent.get_capabilities())
    
    if test_scenario == "agent_unavailable":
        await main_assistant.register_specialized_agent("unstable_echo", unstable_agent.get_capabilities())
    
    # Asegurar que los agentes están listos para recibir mensajes
    for agent_id, agent in agents.items():
        await agent.register_with_communicator()
    
    logger.info("Todos los agentes configurados correctamente")
    return agents

async def test_agent_unavailable():
    """
    Prueba el comportamiento cuando un agente solicitado no está disponible temporalmente.
    Esta prueba verifica que el sistema puede:
    1. Detectar que un agente no está disponible
    2. Intentar la operación nuevamente (retry)
    3. Recuperarse cuando el agente vuelve a estar disponible
    """
    logger.info("=== Iniciando prueba de agente no disponible ===")
    
    # Configurar agentes para este escenario
    agents = await setup_agents("agent_unavailable")
    main_assistant = agents["main"]
    unstable_agent = agents["unstable"]
    
    # Primer intento - Debería fallar pero ser manejado por el MainAssistant
    query = "Unstable: repite este mensaje"
    logger.info(f"Enviando consulta que será delegada al agente inestable: '{query}'")
    
    # El MainAssistant debería intentar delegar esto al agente inestable
    response1 = await main_assistant.process(query)
    
    logger.info(f"Respuesta 1: {response1.content}")
    logger.info(f"Metadatos 1: {response1.metadata}")
    
    # Verificar que el MainAssistant detectó el problema
    if "error" in response1.metadata:
        logger.info("✅ El MainAssistant detectó el problema con el agente inestable")
    else:
        logger.warning("❌ El MainAssistant no detectó el problema con el agente inestable")
    
    # Segundo intento - El agente inestable debería seguir fallando
    logger.info("Enviando la misma consulta por segunda vez")
    response2 = await main_assistant.process(query)
    
    logger.info(f"Respuesta 2: {response2.content}")
    logger.info(f"Metadatos 2: {response2.metadata}")
    
    # Tercer intento - El agente inestable debería funcionar ahora
    logger.info("Enviando la misma consulta por tercera vez")
    response3 = await main_assistant.process(query)
    
    logger.info(f"Respuesta 3: {response3.content}")
    logger.info(f"Metadatos 3: {response3.metadata}")
    
    # Verificar si el tercer intento fue exitoso
    if "error" not in response3.metadata:
        logger.info("✅ El agente inestable se recuperó y procesó la consulta correctamente")
    else:
        logger.warning("❌ El agente inestable no se recuperó como se esperaba")
    
    return "agent_unavailable_test_completed"

async def test_invalid_request():
    """
    Prueba el comportamiento cuando se recibe una solicitud mal formada o inválida.
    Esta prueba verifica que el sistema puede:
    1. Identificar consultas inválidas o sin sentido
    2. Proporcionar una respuesta útil incluso con entrada problemática
    3. Mantener el funcionamiento normal después de procesar una consulta inválida
    """
    logger.info("=== Iniciando prueba de solicitud inválida ===")
    
    # Configurar agentes con configuración básica
    agents = await setup_agents("invalid_request")
    main_assistant = agents["main"]
    
    # Lista de consultas inválidas o problemáticas para probar
    invalid_queries = [
        "",  # Cadena vacía
        "   ",  # Solo espacios
        "!@#$%^&*()",  # Solo caracteres especiales
        "a" * 1000,  # Cadena muy larga
        "código code code\u0000null\u0000byte",  # Caracteres nulos
        None,  # None literal (debería ser manejado antes de llegar al procesamiento)
    ]
    
    for i, query in enumerate(invalid_queries):
        if query is None:
            logger.info(f"Prueba {i+1}: Enviando valor None como consulta")
            # Manejar explícitamente
            query = "" 
        else:
            logger.info(f"Prueba {i+1}: Enviando consulta inválida: '{query[:20]}{'...' if len(str(query)) > 20 else ''}'")
        
        try:
            # Procesar la consulta inválida
            response = await main_assistant.process(query)
            
            logger.info(f"Respuesta: {response.content}")
            logger.info(f"Estado: {response.status}")
            
            # Verificar que el sistema respondió de alguna manera
            if response.content:
                logger.info(f"✅ El sistema generó una respuesta para la consulta inválida {i+1}")
            else:
                logger.warning(f"❌ El sistema no generó contenido para la consulta inválida {i+1}")
                
        except Exception as e:
            # También probamos que incluso si ocurre una excepción, se captura adecuadamente
            logger.warning(f"❌ Excepción no manejada para la consulta {i+1}: {str(e)}")
    
    # Verificar que el sistema sigue funcionando después de consultas inválidas
    valid_query = "Hola, ¿estás funcionando correctamente?"
    logger.info(f"Enviando consulta válida para verificar recuperación: '{valid_query}'")
    
    try:
        response = await main_assistant.process(valid_query)
        logger.info(f"Respuesta a consulta válida: {response.content}")
        
        if response.status == "success":
            logger.info("✅ El sistema se recuperó correctamente después de consultas inválidas")
        else:
            logger.warning("❌ El sistema no se recuperó correctamente después de consultas inválidas")
    except Exception as e:
        logger.error(f"❌ Error crítico: El sistema no se recuperó: {str(e)}")
    
    return "invalid_request_test_completed"

async def test_model_timeout():
    """
    Prueba el comportamiento cuando un modelo de IA tarda demasiado en responder o falla.
    Esta prueba verifica que:
    1. El sistema detecta cuando un modelo excede el tiempo de respuesta
    2. Tiene un mecanismo de timeout para evitar bloqueos indefinidos
    3. Puede ofrecer una respuesta alternativa o degradada en caso de fallo
    """
    logger.info("=== Iniciando prueba de timeout del modelo ===")
    
    # Implementar esta prueba cuando sea necesario
    logger.warning("Prueba de timeout del modelo no implementada completamente")
    return "model_timeout_test_not_implemented"

async def test_message_retry():
    """
    Prueba el mecanismo de reintento de mensajes cuando falla la comunicación.
    Esta prueba verifica que:
    1. El sistema reintenta enviar mensajes que fallan inicialmente
    2. Hay una política de backoff entre reintentos
    3. Eventualmente se detiene después de múltiples fallos
    """
    logger.info("=== Iniciando prueba de reintento de mensajes ===")
    
    # Implementar esta prueba cuando sea necesario
    logger.warning("Prueba de reintento de mensajes no implementada completamente")
    return "message_retry_test_not_implemented"

async def main():
    """Función principal que ejecuta las pruebas según argumentos."""
    parser = argparse.ArgumentParser(description="Pruebas de manejo de errores para el sistema de agentes")
    parser.add_argument("--test", choices=["agent_unavailable", "invalid_request", "model_timeout", "message_retry", "all"], 
                      default="all", help="Tipo de prueba a ejecutar")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar información detallada")
    
    args = parser.parse_args()
    
    if args.verbose:
        # Configurar logging más detallado
        logging.getLogger().setLevel(logging.DEBUG)
        
    try:
        if args.test == "agent_unavailable" or args.test == "all":
            result = await test_agent_unavailable()
            logger.info(f"Resultado de prueba de agente no disponible: {result}")
            
        if args.test == "invalid_request" or args.test == "all":
            result = await test_invalid_request()
            logger.info(f"Resultado de prueba de solicitud inválida: {result}")
            
        if args.test == "model_timeout" or args.test == "all":
            result = await test_model_timeout()
            logger.info(f"Resultado de prueba de timeout del modelo: {result}")
            
        if args.test == "message_retry" or args.test == "all":
            result = await test_message_retry()
            logger.info(f"Resultado de prueba de reintento de mensajes: {result}")
            
    except Exception as e:
        logger.error(f"Error durante las pruebas: {e}")
    finally:
        # Cerrar sistema de comunicación
        await shutdown_communication_system()
        logger.info("Sistema de comunicación cerrado correctamente")

if __name__ == "__main__":
    asyncio.run(main()) 