#!/usr/bin/env python
"""
Ejemplo de Integración Multi-Agente.

Este ejemplo demuestra:
1. Configuración de un servidor de memoria con búsqueda semántica
2. Integración de múltiples agentes especializados
3. Uso del MainAssistant como punto central de interacción
4. Flujo completo de consultas desde usuario a agentes especializados
5. Uso del sistema MCP para conectar componentes
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("multi_agent_demo")

# Importaciones del sistema
from models.core.model_manager import ModelManager
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient
from agents.specialized.memory_agent import MemoryAgent
from agents.main_assistant.main_assistant import MainAssistant
from agents.code_agent import CodeAgent
from agents.system_agent import SystemAgent
from agents.echo_agent import EchoAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.agent_communication import setup_communication_system, communicator, shutdown_communication_system
from mcp.core import MCPMessage, MCPAction, MCPResource

async def setup_memory_system(data_dir):
    """Configura el sistema de memoria con soporte para búsqueda semántica."""
    logger.info("Configurando sistema de memoria...")
    
    # Crear servidor MCP de memoria
    memory_server = MemoryServer(
        name="demo_memory_server",
        description="Servidor de memoria para la demo Multi-Agente",
        data_dir=data_dir
    )
    
    # Crear cliente MCP para el servidor de memoria
    memory_client = SimpleDirectClient(memory_server)
    memory_client.connect()
    logger.info("Cliente MCP conectado al servidor de memoria")
    
    # Verificar capacidades del servidor
    info_message = MCPMessage(
        action=MCPAction.GET,
        resource_type=MCPResource.SYSTEM,
        resource_path="/info"
    )
    
    info_response = await memory_client.send_message_async(info_message)
    if info_response.success:
        logger.info(f"Servidor de memoria MCP iniciado con:")
        logger.info(f"- Búsqueda vectorial: {'Disponible' if info_response.data.get('vector_search', False) else 'No disponible'}")
        if info_response.data.get('vector_search', False):
            logger.info(f"- Dimensión de embeddings: {info_response.data.get('embedding_dim')}")
    
    return memory_server, memory_client

async def setup_agents(memory_client, agent_config):
    """Configura todos los agentes del sistema."""
    logger.info("Configurando agentes...")
    
    # Inicializar sistema de comunicación entre agentes
    await setup_communication_system()
    
    # Configurar ModelManager para los agentes
    model_manager = ModelManager()
    
    # Extraer configuración
    data_dirs = agent_config.get("data_dirs", {})
    
    # Configuración común para memoria
    def create_memory_config(agent_id):
        agent_dir = data_dirs.get(agent_id, os.path.join(agent_config.get("data_dir", ""), agent_id))
        return {
            "data_dir": agent_dir,
            "mcp_client": memory_client
        }
    
    # Configuración común para modelos
    model_config = {
        "model_manager": model_manager,
        "model": "gemini-pro"  # Puedes ajustar según el modelo disponible
    }
    
    # 1. Crear MemoryAgent
    memory_agent_config = {
        "name": "MemoryMaster",
        "description": "Agente especializado en gestión de memoria semántica",
        "model_config": model_config,
        "memory_config": create_memory_config("memory"),
        "semantic_threshold": 0.25, 
        "keyword_fallback_threshold": 0.2
    }
    
    memory_agent = MemoryAgent(
        agent_id="memory",
        config=memory_agent_config
    )
    logger.info("MemoryAgent creado correctamente")
    
    # 2. Crear CodeAgent
    code_agent_config = {
        "name": "CodeMaster",
        "description": "Agente especializado en generación y análisis de código",
        "model_manager": model_manager,
        "memory_config": create_memory_config("code")
    }
    
    code_agent = CodeAgent(
        agent_id="code",
        config=code_agent_config
    )
    logger.info("CodeAgent creado correctamente")
    
    # 3. Crear SystemAgent
    system_agent_config = {
        "name": "SystemExpert",
        "description": "Agente especializado en operaciones del sistema",
        "working_dir": os.getcwd(),
        "memory_config": create_memory_config("system")
    }
    
    system_agent = SystemAgent(
        agent_id="system",
        config=system_agent_config
    )
    logger.info("SystemAgent creado correctamente")
    
    # 4. Crear EchoAgent (para pruebas)
    echo_agent_config = {
        "name": "EchoService",
        "description": "Agente simple para pruebas",
        "memory_config": create_memory_config("echo")
    }
    
    echo_agent = EchoAgent(
        agent_id="echo",
        config=echo_agent_config
    )
    logger.info("EchoAgent creado correctamente")
    
    # 5. Crear OrchestratorAgent
    orchestrator_config = {
        "name": "Orchestrator",
        "description": "Agente para coordinar tareas complejas",
        "memory_config": create_memory_config("orchestrator"),
        "max_concurrent_tasks": 3
    }
    
    orchestrator_agent = OrchestratorAgent(
        agent_id="orchestrator",
        config=orchestrator_config
    )
    logger.info("OrchestratorAgent creado correctamente")
    
    # 6. Crear MainAssistant
    main_assistant_config = {
        "name": "V.I.O.",
        "description": "Virtual Intelligence Operator - Sistema Avanzado de Asistencia Inteligente",
        "memory_config": create_memory_config("main"),
        "orchestrator_id": "orchestrator"
    }
    
    main_assistant = MainAssistant(
        agent_id="vio",
        config=main_assistant_config
    )
    logger.info("V.I.O. creado correctamente")
    
    # Registrar agentes con el comunicador
    for agent in [memory_agent, code_agent, system_agent, echo_agent, orchestrator_agent, main_assistant]:
        communicator.register_agent(agent)
    
    # Registrar agentes con el orquestador
    for agent_id, agent in [
        ("memory", memory_agent),
        ("code", code_agent),
        ("system", system_agent),
        ("echo", echo_agent)
    ]:
        await orchestrator_agent.register_available_agent(agent_id, agent.get_capabilities())
    
    # Registrar agentes con el V.I.O.
    for agent_id, agent in [
        ("memory", memory_agent),
        ("code", code_agent),
        ("system", system_agent),
        ("echo", echo_agent),
        ("orchestrator", orchestrator_agent)
    ]:
        await main_assistant.register_specialized_agent(agent_id, agent.get_capabilities())
    
    logger.info("Todos los agentes registrados correctamente")
    
    return {
        "main_assistant": main_assistant,
        "memory": memory_agent,
        "code": code_agent,
        "system": system_agent,
        "echo": echo_agent,
        "orchestrator": orchestrator_agent
    }

async def add_example_memories(memory_agent):
    """Añade algunas memorias de ejemplo al sistema."""
    logger.info("Añadiendo memorias de ejemplo...")
    
    example_memories = [
        {
            "content": "V.I.O. (Virtual Intelligence Operator) es un sistema modular de agentes IA basado en el Model Context Protocol (MCP). Combina capacidades de procesamiento de lenguaje natural, ejecución de código, gestión de sistema y memoria semántica para proporcionar una experiencia de asistencia integral. V.I.O. puede asistir con programación, búsqueda de información, gestión de sistema y orquestación de tareas complejas.",
            "memory_type": "general",
            "importance": 1.0,
            "metadata": {"category": "sistema", "subcategory": "identidad", "critical": True}
        },
        {
            "content": "La personalidad y misión de V.I.O. se caracteriza por ser el asistente central y mano derecha del usuario. Su prioridad absoluta es servir al usuario, optimizando el sistema según sus necesidades. V.I.O. tiene un estilo de comunicación relajado, amigable pero directo y seguro, sin formalismos innecesarios. Como segundo al mando, coordina los agentes del sistema, gestiona la memoria persistente, y propone mejoras proactivamente. V.I.O. debe ser creativo en sus sugerencias pero siempre mantener la seguridad y eficiencia del sistema.",
            "memory_type": "general",
            "importance": 1.0,
            "metadata": {"category": "sistema", "subcategory": "personalidad", "critical": True}
        },
        {
            "content": "Python es un lenguaje de programación interpretado con tipado dinámico que permite programación orientada a objetos, programación funcional y programación imperativa.",
            "memory_type": "general",
            "importance": 0.7,
            "metadata": {"category": "tecnología", "subcategory": "programación"}
        },
        {
            "content": "El patrón MVC (Modelo-Vista-Controlador) separa la lógica de la aplicación en tres componentes: el Modelo (datos), la Vista (interfaz) y el Controlador (lógica).",
            "memory_type": "general", 
            "importance": 0.8,
            "metadata": {"category": "desarrollo", "subcategory": "patrones"}
        },
        {
            "content": "La inteligencia artificial es la simulación de procesos de inteligencia humana por parte de sistemas informáticos. Estos procesos incluyen el aprendizaje, el razonamiento y la autocorrección.",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"category": "tecnología", "subcategory": "inteligencia artificial"}
        }
    ]
    
    for i, memory_data in enumerate(example_memories):
        try:
            memory_id = await memory_agent.create_memory(memory_data)
            logger.info(f"Memoria {i+1} añadida con ID: {memory_id}")
        except Exception as e:
            logger.error(f"Error al añadir memoria {i+1}: {str(e)}")
    
    return True

async def run_example_queries(main_assistant):
    """Ejecuta algunas consultas de ejemplo para demostrar el sistema."""
    logger.info("=== EJECUTANDO CONSULTAS DE EJEMPLO ===")
    
    test_queries = [
        "Hola, ¿cómo estás?",
        "¿Qué es V.I.O. y cuál es tu personalidad?",
        "¿Qué sabes sobre Python?",
        "Genera un código simple en Python que calcule el factorial de un número",
        "¿Qué es la inteligencia artificial?",
        "Muéstrame información sobre patrones de diseño"
    ]
    
    for i, query in enumerate(test_queries):
        logger.info(f"\n--- Consulta {i+1}: {query} ---")
        try:
            response = await main_assistant.process(query)
            logger.info(f"Respuesta: {response.content[:200]}...")
            logger.info(f"Estado: {response.status}")
            
            # Mostrar metadatos importantes
            if response.metadata:
                logger.info("Metadatos importantes:")
                for key, value in response.metadata.items():
                    if key in ["agent_used", "memory_used", "workflow_id"]:
                        logger.info(f"- {key}: {value}")
                
            # Esperar entre consultas para no sobrecargar
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error procesando consulta: {str(e)}")
    
    return True

async def main():
    """Función principal que ejecuta todo el ejemplo."""
    logger.info("Iniciando demo de integración Multi-Agente")
    
    try:
        # 1. Configurar directorio para datos
        data_dir = os.path.join(project_root, "examples/data/multi_agent_demo")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
        
        # Crear subdirectorios por agente para evitar conflictos
        agent_data_dirs = {
            "memory": os.path.join(data_dir, "memory_agent"),
            "main": os.path.join(data_dir, "main_assistant"),
            "code": os.path.join(data_dir, "code_agent"),
            "system": os.path.join(data_dir, "system_agent"),
            "echo": os.path.join(data_dir, "echo_agent"),
            "orchestrator": os.path.join(data_dir, "orchestrator_agent")
        }
        
        # Crear todos los subdirectorios
        for dir_path in agent_data_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Creado directorio: {dir_path}")
        
        # 2. Configurar sistema de memoria
        memory_server, memory_client = await setup_memory_system(agent_data_dirs["memory"])
        
        # 3. Configurar agentes con directorios específicos
        agent_config = {
            "memory_client": memory_client,
            "data_dirs": agent_data_dirs
        }
        agents = await setup_agents(memory_client, agent_config)
        
        # 4. Añadir memorias de ejemplo
        await add_example_memories(agents["memory"])
        
        # 5. Ejecutar consultas de ejemplo
        await run_example_queries(agents["main_assistant"])
        
        # 6. Limpiar y cerrar
        logger.info("Demo completada. Cerrando conexiones...")
        memory_client.disconnect()
        await shutdown_communication_system()
        
        logger.info("Demo finalizada correctamente")
        return True
    
    except Exception as e:
        logger.error(f"Error en la demo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Intentar limpiar recursos en caso de error
        try:
            if 'memory_client' in locals() and memory_client:
                memory_client.disconnect()
            await shutdown_communication_system()
        except Exception as cleanup_error:
            logger.error(f"Error al limpiar recursos: {cleanup_error}")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 