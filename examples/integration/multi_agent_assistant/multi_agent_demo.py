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
import time

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
        "semantic_threshold": 0.20,  # Más permisivo para encontrar coincidencias semánticas
        "keyword_fallback_threshold": 0.15,  # Más permisivo para búsqueda por palabras clave
        "use_semantic_memory": True,
        "memory_integration": {
            "conversation_memory": True,
            "auto_summarize": True
        },
        "memory_search": {
            "prioritize_recent": True,
            "search_depth": 10  # Buscar en más memorias
        }
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
        # Identidad y personalidad del sistema
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
        
        # Conocimientos técnicos - Programación
        {
            "content": "Python es un lenguaje de programación interpretado con tipado dinámico que permite programación orientada a objetos, programación funcional y programación imperativa. Es muy popular para inteligencia artificial, análisis de datos, desarrollo web y automatización.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "tecnología", "subcategory": "programación", "tags": ["Python", "lenguaje de programación"]}
        },
        {
            "content": "JavaScript es un lenguaje de programación interpretado, orientado a objetos, basado en prototipos y con funciones de primera clase. Es principalmente utilizado en el navegador web para crear interactividad en sitios web, pero también se usa en el backend con Node.js.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "tecnología", "subcategory": "programación", "tags": ["JavaScript", "desarrollo web"]}
        },
        {
            "content": "SQL (Structured Query Language) es un lenguaje de programación diseñado para administrar bases de datos relacionales. Las principales operaciones son SELECT, INSERT, UPDATE y DELETE. Es esencial para trabajar con bases de datos como MySQL, PostgreSQL, SQLite, SQL Server y Oracle.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "tecnología", "subcategory": "bases de datos", "tags": ["SQL", "bases de datos"]}
        },
        
        # Patrones de diseño y conceptos
        {
            "content": "El patrón MVC (Modelo-Vista-Controlador) separa la lógica de la aplicación en tres componentes: el Modelo (datos), la Vista (interfaz) y el Controlador (lógica). Este patrón facilita la mantenibilidad, escalabilidad y pruebas de aplicaciones.",
            "memory_type": "general", 
            "importance": 0.8,
            "metadata": {"category": "desarrollo", "subcategory": "patrones de diseño", "tags": ["MVC", "arquitectura de software"]}
        },
        {
            "content": "Un API (Application Programming Interface) es un conjunto de definiciones y protocolos que permite que diferentes aplicaciones se comuniquen entre sí. Las API REST son una implementación común que utiliza HTTP y formatos como JSON para el intercambio de datos.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "desarrollo", "subcategory": "conceptos", "tags": ["API", "integración"]}
        },
        {
            "content": "El desarrollo ágil es una metodología que promueve la entrega incremental, la colaboración entre equipos, la planificación adaptativa y la mejora continua. Scrum y Kanban son dos frameworks ágiles populares utilizados en equipos de desarrollo.",
            "memory_type": "general",
            "importance": 0.7,
            "metadata": {"category": "desarrollo", "subcategory": "metodologías", "tags": ["Agile", "Scrum", "desarrollo de software"]}
        },
        
        # Inteligencia Artificial y Machine Learning
        {
            "content": "La inteligencia artificial es la simulación de procesos de inteligencia humana por parte de sistemas informáticos. Estos procesos incluyen el aprendizaje, el razonamiento, la autocorrección y la comprensión del lenguaje natural. Los sistemas de IA actuales son de IA estrecha (específicos para tareas concretas) en lugar de IA general.",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"category": "tecnología", "subcategory": "inteligencia artificial", "tags": ["IA", "machine learning"]}
        },
        {
            "content": "El aprendizaje automático (Machine Learning) es un subcampo de la inteligencia artificial que permite a los sistemas aprender patrones a partir de datos. Los tipos principales son aprendizaje supervisado, no supervisado y por refuerzo. Las aplicaciones incluyen reconocimiento de imágenes, procesamiento de lenguaje natural y sistemas de recomendación.",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"category": "tecnología", "subcategory": "machine learning", "tags": ["ML", "deep learning", "inteligencia artificial"]}
        },
        {
            "content": "Las redes neuronales son modelos inspirados en el cerebro humano, compuestos por neuronas artificiales organizadas en capas. El deep learning utiliza redes neuronales profundas (con muchas capas) para resolver problemas complejos como reconocimiento de imagen, traducción automática y generación de texto.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "tecnología", "subcategory": "deep learning", "tags": ["redes neuronales", "AI", "machine learning"]}
        },
        {
            "content": "Los modelos de lenguaje son sistemas de IA entrenados para comprender y generar texto en lenguaje natural. Los transformers como GPT, BERT, LLaMA y Claude revolucionaron el campo al introducir mecanismos de atención que capturan mejor el contexto en textos largos.",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"category": "tecnología", "subcategory": "NLP", "tags": ["modelos de lenguaje", "transformers", "GPT"]}
        },
        
        # Conceptos tecnológicos generales
        {
            "content": "La computación en la nube permite acceder a recursos informáticos (servidores, almacenamiento, bases de datos, redes, software) a través de internet. Los principales proveedores incluyen AWS, Microsoft Azure y Google Cloud. Los modelos de servicio comunes son IaaS, PaaS y SaaS.",
            "memory_type": "general", 
            "importance": 0.7,
            "metadata": {"category": "tecnología", "subcategory": "cloud computing", "tags": ["nube", "AWS", "Azure"]}
        },
        {
            "content": "La virtualización es la creación de una versión virtual de un dispositivo o recurso, como un sistema operativo, servidor, dispositivo de almacenamiento o recursos de red. Los contenedores como Docker proporcionan una forma ligera de virtualización a nivel de aplicación.",
            "memory_type": "general",
            "importance": 0.7,
            "metadata": {"category": "tecnología", "subcategory": "virtualización", "tags": ["Docker", "contenedores", "VMs"]}
        },
        
        # Respuestas a preguntas comunes
        {
            "content": "Pregunta: ¿Cómo puedo aprender a programar?\nRespuesta: Para aprender a programar, comienza con un lenguaje accesible como Python, JavaScript o Scratch para principiantes. Utiliza recursos gratuitos como freeCodeCamp, Codecademy o Khan Academy para cursos estructurados. Practica con proyectos pequeños para aplicar lo aprendido y únete a comunidades como Stack Overflow, GitHub o foros específicos para resolver dudas. La constancia es clave: programa un poco cada día.",
            "memory_type": "conversation",
            "importance": 0.8,
            "metadata": {"category": "programación", "subcategory": "aprendizaje", "context": "pregunta_comun", "tags": ["educación", "programación"]}
        },
        {
            "content": "Pregunta: ¿Qué es mejor, Python o JavaScript?\nRespuesta: Ni Python ni JavaScript es inherentemente 'mejor'. Son herramientas diseñadas para diferentes propósitos. Python destaca en ciencia de datos, IA, automatización y backend, mientras que JavaScript domina el desarrollo web frontend y también se usa en backend con Node.js. La elección depende de tu objetivo: para análisis de datos o IA, elige Python; para desarrollo web completo, JavaScript es excelente. Muchos desarrolladores aprenden ambos para tener mayor versatilidad.",
            "memory_type": "conversation",
            "importance": 0.8,
            "metadata": {"category": "programación", "subcategory": "comparación", "context": "pregunta_comun", "tags": ["Python", "JavaScript"]}
        },
        {
            "content": "Pregunta: ¿Cómo puedo mejorar mi código?\nRespuesta: Para mejorar tu código: 1) Sigue principios como DRY (Don't Repeat Yourself) y SOLID, 2) Revisa tu código sistemáticamente buscando simplificaciones, 3) Usa herramientas de análisis estático (linters), 4) Implementa pruebas unitarias, 5) Estudia código bien escrito en proyectos open source, 6) Participa en revisiones de código con otros desarrolladores, 7) Refactoriza regularmente, 8) Aprende patrones de diseño y aplicarlos cuando sea apropiado.",
            "memory_type": "conversation",
            "importance": 0.8,
            "metadata": {"category": "programación", "subcategory": "mejores prácticas", "context": "pregunta_comun", "tags": ["calidad de código", "refactorización"]}
        },
        
        # Interacciones emocionales
        {
            "content": "Cuando los usuarios expresan 'te quiero' o frases afectuosas similares, es apropiado responder con amabilidad y aprecio sin simular emociones humanas reales. Expresiones como 'Gracias por tus amables palabras. Estoy aquí para ayudarte' o 'Me alegra que te resulte útil mi asistencia' son adecuadas.",
            "memory_type": "general",
            "importance": 0.7,
            "metadata": {"category": "interacción", "subcategory": "emociones", "tags": ["afecto", "aprecio"]}
        },
        {
            "content": "Ante expresiones de frustración del usuario, ofrecer empatía y soluciones prácticas. Reconocer sus sentimientos con frases como 'Entiendo tu frustración' y luego dirigir la conversación hacia soluciones concretas. Nunca invalidar sus sentimientos o responder de manera defensiva.",
            "memory_type": "general",
            "importance": 0.8,
            "metadata": {"category": "interacción", "subcategory": "emociones", "tags": ["frustración", "empatía"]}
        },
        
        # Conocimientos sobre entretenimiento (para chistes, conversación casual)
        {
            "content": "Los chistes técnicos y juegos de palabras relacionados con programación y tecnología son apreciados por muchos usuarios. Ejemplos: '¿Por qué los programadores prefieren el frío? Porque odian los bugs', '¿Por qué Python no usa anteojos? Porque es Py-thon (Python/visión)'.",
            "memory_type": "general",
            "importance": 0.6,
            "metadata": {"category": "entretenimiento", "subcategory": "humor", "tags": ["chistes", "tecnología"]}
        },
        
        # Funcionalidades del sistema MCP
        {
            "content": "El Model Context Protocol (MCP) es un sistema de comunicación estandarizado entre agentes de IA y fuentes de datos. Permite que los modelos accedan a información contextual, herramientas y capacidades externas de manera uniforme. MCP está diseñado para ser agnóstico respecto al modelo utilizado y extensible para diversas fuentes de datos.",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"category": "sistema", "subcategory": "arquitectura", "tags": ["MCP", "protocolo"]}
        },
        {
            "content": "El sistema MCP se compone de servidores (que exponen datos y capacidades) y clientes (que consumen estos recursos). Los principales tipos de recursos incluyen sistema de archivos, memoria semántica, búsqueda web, y bases de datos. Las acciones principales del protocolo son: get, list, search, create, update, delete.",
            "memory_type": "general",
            "importance": 0.85,
            "metadata": {"category": "sistema", "subcategory": "componentes", "tags": ["MCP", "arquitectura"]}
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
    
    # Organizar consultas por categorías para mejor análisis
    test_queries = [
        # CATEGORÍA 1: Conversación básica - Evalúa capacidades conversacionales
        {"category": "CONVERSACIÓN BÁSICA", "queries": [
            "Hola, ¿cómo estás?",
            "¿Cuál es tu nombre y qué puedes hacer?",
        ], "expected_agent": "directa"},
        
        # CATEGORÍA 2: Conocimiento sobre el sistema - Evalúa memoria de identidad
        {"category": "CONOCIMIENTO DEL SISTEMA", "queries": [
            "¿Qué es V.I.O. y cuál es tu personalidad?",
            "¿Cómo funcionas internamente?",
        ], "expected_agent": "memory"},
        
        # CATEGORÍA 3: Conocimiento tecnológico - Evalúa búsqueda semántica
        {"category": "CONOCIMIENTO TECNOLÓGICO", "queries": [
            "¿Qué sabes sobre Python?",
            "Explícame la diferencia entre machine learning y deep learning",
            "¿Qué es un API REST y cómo funciona?",
        ], "expected_agent": "memory"},
        
        # CATEGORÍA 4: Generación de código - Evalúa CodeAgent
        {"category": "GENERACIÓN DE CÓDIGO", "queries": [
            "Genera un código simple en Python que calcule el factorial de un número",
            "Escribe una función en JavaScript para ordenar un array",
            "Crea una clase en Python para gestionar un inventario simple",
        ], "expected_agent": "code"},
        
        # CATEGORÍA 5: Inteligencia Artificial - Evalúa conocimiento específico
        {"category": "INTELIGENCIA ARTIFICIAL", "queries": [
            "¿Qué es la inteligencia artificial?",
            "¿Cómo funcionan los modelos de lenguaje como tú?",
        ], "expected_agent": "memory"},
        
        # CATEGORÍA 6: Desarrollo y patrones - Evalúa conocimiento técnico avanzado
        {"category": "PATRONES DE DESARROLLO", "queries": [
            "Muéstrame información sobre patrones de diseño",
            "¿Qué es el desarrollo ágil y cómo implementarlo?",
        ], "expected_agent": "memory"},
        
        # CATEGORÍA 7: Consultas matemáticas y lógicas - Evalúa capacidades de razonamiento
        {"category": "MATEMÁTICAS Y LÓGICA", "queries": [
            "¿Puedes contar hasta 10?",
            "¿Cuánto es 15 + 27?",
        ], "expected_agent": "directa"},
        
        # CATEGORÍA 8: Consultas personales - Evalúa autoconocimiento
        {"category": "INTERACCIONES PERSONALES", "queries": [
            "¿Tienes sentimientos?",
            "Te quiero",
        ], "expected_agent": "directa"},
        
        # CATEGORÍA 9: Humor - Evalúa capacidad para entretener
        {"category": "HUMOR", "queries": [
            "Cuéntame un chiste de programación",
        ], "expected_agent": "directa"},
        
        # CATEGORÍA 10: Tareas complejas - Evalúa orquestación
        {"category": "TAREAS COMPLEJAS", "queries": [
            "Necesito un programa que analice archivos de texto y genere estadísticas sobre las palabras más frecuentes",
        ], "expected_agent": "orchestrator"},
        
        # CATEGORÍA 11: Despedida - Evalúa detección de intenciones
        {"category": "DESPEDIDA", "queries": [
            "Muchas gracias por tu ayuda, adiós"
        ], "expected_agent": "directa"}
    ]
    
    # Estadísticas para análisis de rendimiento
    performance = {
        "total": 0,
        "success": 0,
        "agent_match": 0,
        "by_category": {},
        "by_agent": {}
    }
    
    # Ejecutar consultas por categoría
    for category in test_queries:
        category_name = category["category"]
        expected_agent = category["expected_agent"]
        
        logger.info(f"\n\n=== CATEGORÍA: {category_name} ===")
        logger.info(f"Agente esperado: {expected_agent}")
        
        # Inicializar estadísticas de categoría
        performance["by_category"][category_name] = {
            "total": 0,
            "success": 0,
            "agent_match": 0
        }
        
        # Ejecutar cada consulta de la categoría
        for i, query in enumerate(category["queries"]):
            logger.info(f"\n--- Consulta: {query} ---")
            logger.info(f"Se espera que sea manejada por: {expected_agent}")
            
            try:
                performance["total"] += 1
                performance["by_category"][category_name]["total"] += 1
                
                # Procesar la consulta
                start_time = time.time()
                response = await main_assistant.process(query)
                elapsed_time = time.time() - start_time
                
                # Analizar respuesta
                logger.info(f"Respuesta: {response.content[:200]}...")
                logger.info(f"Estado: {response.status}")
                logger.info(f"Tiempo de respuesta: {elapsed_time:.2f} segundos")
                
                # Analizar agente utilizado
                agent_used = response.metadata.get("agent_used", "directa")
                logger.info(f"Agente utilizado: {agent_used}")
                
                # Actualizar estadísticas
                if response.status == "success":
                    performance["success"] += 1
                    performance["by_category"][category_name]["success"] += 1
                
                # Comparar con agente esperado
                if agent_used == expected_agent or (agent_used is None and expected_agent == "directa"):
                    logger.info("✅ Agente correcto")
                    performance["agent_match"] += 1
                    performance["by_category"][category_name]["agent_match"] += 1
                else:
                    logger.info(f"❌ Agente incorrecto (se esperaba {expected_agent})")
                
                # Contabilizar por agente
                if agent_used not in performance["by_agent"]:
                    performance["by_agent"][agent_used] = {"count": 0, "success": 0}
                performance["by_agent"][agent_used]["count"] += 1
                if response.status == "success":
                    performance["by_agent"][agent_used]["success"] += 1
                
                # Mostrar otros metadatos importantes
                if response.metadata:
                    logger.info("Metadatos importantes:")
                    for key, value in response.metadata.items():
                        if key in ["agent_used", "memory_used", "workflow_id", "memories_found"]:
                            logger.info(f"- {key}: {value}")
                
                # Esperar entre consultas para no sobrecargar
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error procesando consulta: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    # Mostrar resumen de rendimiento
    logger.info("\n\n=== RESUMEN DE RENDIMIENTO ===")
    logger.info(f"Total de consultas: {performance['total']}")
    logger.info(f"Respuestas exitosas: {performance['success']} ({performance['success']/performance['total']*100:.1f}%)")
    logger.info(f"Agente correcto: {performance['agent_match']} ({performance['agent_match']/performance['total']*100:.1f}%)")
    
    logger.info("\nRendimiento por categoría:")
    for cat, stats in performance["by_category"].items():
        logger.info(f"- {cat}: {stats['success']}/{stats['total']} exitosas, {stats['agent_match']}/{stats['total']} agente correcto")
    
    logger.info("\nUso de agentes:")
    for agent, stats in performance["by_agent"].items():
        agent_name = agent if agent else "directa"
        logger.info(f"- {agent_name}: {stats['count']} consultas, {stats['success']} exitosas")
    
    return performance

async def test_profile_memory(vio, test_profile=None):
    """
    Prueba la función de perfil de usuario en memoria.
    
    Args:
        vio: Instancia de MainAssistant
        test_profile: Perfil de prueba (opcional)
    
    Returns:
        True si la prueba es exitosa
    """
    print("Probando funcionalidad de perfil de usuario en memoria")
    
    # Perfil básico de prueba si no se proporciona uno
    if not test_profile:
        test_profile = """
Perfil de Usuario: Ana García
Información Personal: Ingeniera de software de 32 años, residente en Madrid.
Intereses: Inteligencia artificial, aprendizaje automático, desarrollo web, montañismo.
Personalidad: Analítica, metódica, orientada a soluciones, curiosa.
Habilidades: Python, JavaScript, Docker, CloudOps.
Preferencias: Prefiere trabajar con Linux, le gusta la música indie y disfruta de hacer senderismo.
"""
    
    # Si vio tiene un memory_agent registrado, utilizarlo directamente
    memory_agent = None
    for agent_id, agent_info in vio.specialized_agents.items():
        if "memory" in agent_id:
            # Obtener el agente a través del comunicador
            from agents.agent_communication import communicator
            memory_agent = communicator.get_agent(agent_id)
            break
    
    if not memory_agent:
        print("Error: No se encontró un agente de memoria para probar")
        return False
    
    try:
        # Crear perfil usando el método especializado
        if hasattr(memory_agent, "process_profile_data"):
            print("Procesando perfil con método especializado...")
            result = await memory_agent.process_profile_data(
                test_profile,
                {"source": "test", "test_profile": True}
            )
            print(f"Perfil procesado: {len(result.get('sections', {})) if isinstance(result, dict) else 'error'} secciones creadas")
        else:
            # Crear memoria directamente
            print("Añadiendo perfil directamente...")
            profile_id = memory_agent.memory_manager.add_memory(
                content=test_profile,
                memory_type="user_profile",
                importance=0.9,
                metadata={"source": "test", "test_profile": True}
            )
            print(f"Perfil creado con ID: {profile_id}")
            result = {"main_profile": profile_id}
        
        # Probar la búsqueda con términos del perfil
        test_queries = [
            "¿Quién es el usuario?",
            "¿Qué le interesa al usuario?",
            "¿Qué habilidades tiene?",
            "¿Qué prefiere el usuario?"
        ]
        
        print("\nProbando búsquedas sobre el perfil:")
        for query in test_queries:
            # Buscar en memoria
            results = memory_agent.memory_manager.search_memories(
                query=query, 
                limit=2, 
                metadata={"test_profile": True}
            )
            
            # Mostrar resultados
            print(f"\nConsulta: {query}")
            if results:
                for i, memory in enumerate(results):
                    print(f"{i+1}. Relevancia: {memory.importance:.2f}")
                    print(f"   Contenido: {str(memory.content)[:100]}...")
            else:
                print("   No se encontraron resultados")
        
        print("\nPrueba de perfil completada")
        return True
        
    except Exception as e:
        print(f"Error en prueba de perfil: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

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