"""
Orchestrator Agent Example.

This example demonstrates how the orchestrator agent can coordinate multiple
specialized agents to solve complex tasks.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Configurar la ruta para encontrar los módulos del proyecto
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Intentar cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # Cargar .env desde la raíz del proyecto
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path)
    print(f"✅ Variables de entorno cargadas desde: {dotenv_path}")
except ImportError:
    print("⚠️ python-dotenv no está instalado. Las variables de entorno no se cargarán desde .env")
    print("   Instala con: pip install python-dotenv")

# Configurar logging con más detalle
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar a DEBUG para ver más detalles
    format='[%(asctime)s] %(levelname)s - %(name)s: %(message)s'
)

# Importar módulos necesarios
from agents import (
    EchoAgent, 
    CodeAgent, 
    SystemAgent, 
    OrchestratorAgent,
    communicator
)
from models.core.model_manager import ModelManager
from agents.test_sender import TestSenderAgent
from agents.agent_communication import send_agent_request

async def verify_agent_communication(agent_id, message="Test message", communicator=None, sender=None):
    """Verifica que un agente responda a los mensajes."""
    print(f"Verificando comunicación con {agent_id}...")
    try:
        # Usar el remitente proporcionado o "test_sender" como fallback
        sender_id = sender.id if sender else "test_sender"
        
        # Usar la función send_agent_request del módulo
        response = await send_agent_request(
            sender_id=sender_id,
            receiver_id=agent_id,
            content=message,
            timeout=15.0  # Aumentar timeout para modelos más lentos
        )
        
        if response:
            print(f"  ✓ Agente {agent_id} respondió: {response.content[:50]}...")
            return True
        else:
            print(f"  ✗ No se recibió respuesta del agente {agent_id}")
            return False
    except Exception as e:
        print(f"  ✗ Error verificando agente {agent_id}: {str(e)}")
        return False

async def run_orchestrator_example():
    """Ejecuta un ejemplo de uso del orquestador."""
    print("\n==== Ejemplo de Agente Orquestador ====\n")
    
    # Verificar variables de entorno cargadas
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        if key in os.environ:
            masked_value = os.environ[key][:8] + "..." + os.environ[key][-4:]
            print(f"✅ {key} configurada: {masked_value}")
        else:
            print(f"❌ {key} no está configurada")
    
    # Preferir modelo de Gemini o local
    # Orden de preferencia: Gemini > Modelos locales > Otros
    preferred_models = [
        "gemini-2.0-flash",  # Gemini (menor latencia)
        "gemini-pro",        # Gemini alternativo
        "mistral-7b-instruct", # Modelo local
        "phi-2",             # Modelo local pequeño
        "gpt-3.5-turbo-16k"  # Fallback a OpenAI
    ]
    
    # Usar el primer modelo disponible según la preferencia y API keys configuradas
    preferred_model = None
    
    # Si GOOGLE_API_KEY está configurada, preferir Gemini
    if "GOOGLE_API_KEY" in os.environ:
        preferred_model = "gemini-2.0-flash"
        print(f"✅ GOOGLE_API_KEY está configurada, usando modelo: {preferred_model}")
    # Si no hay GOOGLE_API_KEY pero hay modelos locales, usar esos
    elif os.path.exists(os.path.join(project_root, "models", "local")):
        preferred_model = "mistral-7b-instruct"
        print(f"✅ Modelos locales disponibles, usando: {preferred_model}")
    # Si hay OPENAI_API_KEY, usar GPT como fallback
    elif "OPENAI_API_KEY" in os.environ:
        preferred_model = "gpt-3.5-turbo-16k"
        print(f"✅ OPENAI_API_KEY está configurada, usando modelo: {preferred_model}")
    else:
        # Si nada más está disponible, usar Gemini y confiar en la lógica de fallback
        preferred_model = "gemini-2.0-flash"
        print(f"⚠️ No se detectaron API keys válidas, usando modelo predeterminado: {preferred_model}")
        print("   Es posible que se use modo fallback si la API key no está disponible.")
    
    # Override con la variable de entorno PREFERRED_MODEL si está configurada
    preferred_model = os.environ.get("PREFERRED_MODEL", preferred_model)
    print(f"Modelo preferido final: {preferred_model}")
    
    # Buscar y cargar la configuración de modelos
    config_path = None
    model_config_paths = [
        os.path.join(project_root, "config", "models.json"),
        os.path.join(project_root, "examples", "models", "model_config.json")
    ]
    
    for path in model_config_paths:
        if os.path.exists(path):
            config_path = path
            print(f"Usando configuración de modelos: {path}")
            break
    
    if not config_path:
        print("ADVERTENCIA: No se encontró ningún archivo de configuración de modelos.")
        print("Se utilizará la configuración predeterminada mínima.")
    
    # Crear el gestor de modelos con la configuración encontrada
    model_manager = ModelManager(config_path)
    
    # Listar los modelos disponibles
    available_models = model_manager.list_available_models()
    print(f"Modelos disponibles ({len(available_models)}):")
    for model in available_models:
        model_type = model.get("model_type", "unknown")
        local = model.get("local", False)
        model_name = model.get("name", "unnamed")
        print(f"  - {model_name} (tipo: {model_type}, {'local' if local else 'cloud'})")
    
    # Iniciar el sistema de comunicación
    print("Iniciando sistema de comunicación...")
    await communicator.start()
    
    # Aumentar timeout para evitar problemas de comunicación con modelos lentos
    communicator.request_timeout = 60  # 60 segundos en lugar de 30 por defecto
    
    # Crear agentes especializados
    print("Creando agentes...")
    echo_agent = EchoAgent("echo1", {
        "name": "Echo Agent",
        "description": "Simple echo agent for testing"
    })
    
    # Configurar el modelo para el CodeAgent
    # Primero intentará usar el modelo preferido, luego buscará alternativas
    code_agent = CodeAgent("code1", {
        "name": "Code Assistant",
        "description": "Specialized agent for code generation and analysis",
        "model": preferred_model,  # Intentar usar el modelo preferido
        "model_manager": model_manager
    })
    
    system_agent = SystemAgent("system1", {
        "name": "System Controller",
        "description": "Agent for system operations",
        "os_access": True
    })
    
    # Crear agente de prueba para comunicación
    test_agent = TestSenderAgent("test_sender", {
        "name": "Test Sender",
        "description": "Agent for testing communication between agents"
    })
    
    # Crear orquestador
    orchestrator = OrchestratorAgent("orchestrator", {
        "name": "Task Orchestrator",
        "description": "Coordinates specialized agents for complex tasks",
        "max_concurrent_tasks": 3
    })
    
    # Registrar todos los agentes con el comunicador
    print("Registrando agentes con el comunicador...")
    communicator.register_agent(echo_agent)
    communicator.register_agent(code_agent)
    communicator.register_agent(system_agent)
    communicator.register_agent(orchestrator)
    communicator.register_agent(test_agent)  # Registrar el agente de prueba
    
    # Verificar comunicación con cada agente usando el agente de prueba
    print("\nVerificando comunicación con agentes usando TestSenderAgent...")
    echo_ok = await verify_agent_communication("echo1", "Mensaje de prueba", communicator, test_agent)
    code_ok = await verify_agent_communication("code1", "Prueba de comunicación", communicator, test_agent)
    system_ok = await verify_agent_communication("system1", "Verificando comunicación", communicator, test_agent)
    orchestrator_ok = await verify_agent_communication("orchestrator", "Prueba de orquestador", communicator, test_agent)
    
    if not (echo_ok and code_ok and system_ok and orchestrator_ok):
        print("⚠️ Algunos agentes no están respondiendo correctamente.")
        print("Continuando de todos modos, pero pueden ocurrir errores...")
    
    # Registrar agentes especializados con el orquestador
    print("Registrando agentes con el orquestador...")
    await orchestrator.register_available_agent("echo1", echo_agent.get_capabilities())
    await orchestrator.register_available_agent("code1", code_agent.get_capabilities())
    await orchestrator.register_available_agent("system1", system_agent.get_capabilities())
    
    # Mostrar agentes disponibles
    agent_status = await orchestrator._get_agent_status()
    print(f"Agentes disponibles: {agent_status['idle']}")
    
    # Ejemplo 1: Tarea simple que involucra el agente de eco
    print("\n--- Ejemplo 1: Tarea Simple de Eco ---")
    task1 = "Repite este mensaje: Hola, Mundo Orquestado!"
    
    try:
        print(f"Tarea: {task1}")
        response1 = await orchestrator.process(task1)
        
        print(f"Estado: {response1.status}")
        print(f"Resultado: {response1.content}")
    except Exception as e:
        print(f"Error en Ejemplo 1: {str(e)}")
    
    # Ejemplo 2: Tarea que involucra generación de código
    print("\n--- Ejemplo 2: Generación de Código ---")
    task2 = "Genera un script en Python que calcule los primeros 10 números de la secuencia Fibonacci"
    
    try:
        print(f"Tarea: {task2}")
        # Enviamos directamente al CodeAgent para mejorar la respuesta
        code_agent = communicator.find_agent("code1")
        if code_agent:
            # Preparar el contexto con valores específicos
            specific_context = {
                "language": "python",
                "task": "generate",
                "from_example": True
            }
            response2 = await code_agent.process(task2, specific_context)
        else:
            # Si no encontramos el CodeAgent, usar el orquestador como fallback
            response2 = await orchestrator.process(task2)
        
        print(f"Estado: {response2.status}")
        print(f"Resultado:")
        print("-" * 50)
        print(response2.content)
        print("-" * 50)
    except Exception as e:
        print(f"Error en Ejemplo 2: {str(e)}")
    
    # Ejemplo 3: Prueba directa de EchoAgent
    print("\n--- Ejemplo 3: Prueba Directa de EchoAgent ---")
    task3 = "Esta es una prueba directa para el EchoAgent"
    
    try:
        print(f"Enviando directamente a EchoAgent: {task3}")
        echo_response = await echo_agent.process(task3)
        print(f"Respuesta directa: {echo_response.content}")
    except Exception as e:
        print(f"Error en prueba directa de EchoAgent: {str(e)}")
    
    # Limpiar recursos
    print("\nDeteniendo sistema de comunicación...")
    await communicator.stop()
    
    return 0

if __name__ == "__main__":
    try:
        result = asyncio.run(run_orchestrator_example())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\nEjemplo interrumpido por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError durante la ejecución del ejemplo: {str(e)}")
        sys.exit(2) 