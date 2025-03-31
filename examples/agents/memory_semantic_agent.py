"""
Ejemplo de integración de MainAssistant con MemoryAgent usando búsqueda semántica.

Este ejemplo demuestra:
1. Cómo configurar un MemoryAgent con capacidades de búsqueda vectorial
2. Cómo integrar el MemoryAgent con MainAssistant para delegación
3. Cómo almacenar y recuperar memorias usando varias estrategias de búsqueda

Para ejecutar:
    python examples/agents/memory_semantic_agent.py
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("memory_semantic_example")

# Importaciones del sistema
from models.core.model_manager import ModelManager
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient
from agents.specialized.memory_agent import MemoryAgent
from agents.main_assistant.main_assistant import MainAssistant
from agents.agent_communication import setup_communication_system, communicator
# Importaciones para MCP - movidas arriba para disponibilidad
from mcp.core import MCPMessage, MCPAction, MCPResource

async def run_example():
    """Ejecutar el ejemplo de integración de MemoryAgent con MainAssistant."""
    logger.info("Iniciando ejemplo de MemoryAgent con búsqueda semántica")
    
    try:
        # 1. Configurar directorio para datos
        data_dir = os.path.join(project_root, "examples/data/memory_agent")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
        
        # 2. Crear un servidor MCP de memoria con capacidad vectorial
        memory_server = MemoryServer(
            name="memory_agent_example",
            description="Servidor de memoria para el ejemplo de agente de memoria",
            data_dir=data_dir
        )
        
        # 3. Crear un cliente MCP para el servidor de memoria
        memory_client = SimpleDirectClient(memory_server)
        memory_client.connect()
        logger.info("Cliente MCP conectado al servidor de memoria")
        
        # 4. Crear un sistema de comunicación para los agentes
        comm_system = await setup_communication_system()
        
        # 5. Configurar ModelManager para los agentes
        model_manager = ModelManager()
        
        # 6. Configurar y crear el agente de memoria
        logger.info("Configurando agente de memoria con directorio de datos: %s", data_dir)
        memory_agent_config = {
            "name": "MemoryMaster",
            "description": "Agente especializado en gestión de memoria semántica",
            "model_config": {
                "model_manager": model_manager,
                "model": "gemini-pro"
            },
            "memory_config": {
                "data_dir": data_dir,
                "mcp_client": memory_client
            },
            "semantic_threshold": 0.25,  # Umbral reducido para permitir más resultados
            "keyword_fallback_threshold": 0.2
        }
        
        # Verificar que existe el directorio de datos
        os.makedirs(data_dir, exist_ok=True)
        
        try:
            logger.info("Creando MemoryAgent...")
            memory_agent = MemoryAgent(
                agent_id="memory",
                config=memory_agent_config
            )
            logger.info("MemoryAgent creado correctamente")
            
            # Verificar que el agente tiene memoria configurada
            if memory_agent.has_memory():
                logger.info("Memory Agent tiene memoria configurada correctamente")
                
                # Verificar componentes de memoria
                if hasattr(memory_agent, 'memory_manager'):
                    logger.info(f"- MemoryManager disponible: {memory_agent.memory_manager}")
                    if hasattr(memory_agent.memory_manager, '_specialized_memories'):
                        systems = list(memory_agent.memory_manager._specialized_memories.keys())
                        logger.info(f"- Sistemas de memoria especializados: {systems}")
            else:
                logger.warning("Memory Agent no tiene memoria configurada")
                logger.info("Saltando el resto de pruebas...")
                return
        except Exception as e:
            logger.error(f"Error al crear MemoryAgent: {e}")
            raise
        
        # 7. Configurar y crear el asistente principal
        try:
            logger.info("Creando MainAssistant...")
            main_assistant_config = {
                "name": "Asistente Principal",
                "description": "Asistente principal que delega tareas de memoria",
                "memory_config": memory_agent_config["memory_config"],
                "model_config": memory_agent_config["model_config"]
            }
            main_assistant = MainAssistant(
                agent_id="main_assistant",
                config=main_assistant_config
            )
            logger.info("MainAssistant creado correctamente")
        except Exception as e:
            logger.error(f"Error al crear MainAssistant: {e}")
            raise
        
        # 8. Registrar agentes en el sistema de comunicación
        try:
            # Intentar usar el método de registro en BaseAgent (si existe)
            main_assistant.register_agent(memory_agent)
            logger.info("Agente de memoria registrado con MainAssistant usando método BaseAgent")
        except AttributeError:
            # Fallback: usar API directa del comunicador
            communicator.register_agent(memory_agent)
            communicator.register_agent(main_assistant)
            logger.info("Agentes registrados directamente con el comunicador")
        
        # 9. Registrar el agente de memoria con el asistente principal
        try:
            registration_result = await main_assistant.register_specialized_agent(
                "memory", memory_agent.get_capabilities()
            )
            logger.info(f"Agente de memoria registrado con el asistente principal: {registration_result}")
            
            # Verificar si el agente está en los agentes especializados del MainAssistant
            if hasattr(main_assistant, 'specialized_agents') and 'memory' in main_assistant.specialized_agents:
                logger.info("Verificado: El agente de memoria está en la lista de agentes especializados")
            else:
                logger.warning("Advertencia: El agente no aparece en la lista de agentes especializados")
        except Exception as e:
            logger.warning(f"No se pudo registrar con MainAssistant: {e}")
            logger.warning("Continuando sin integración con MainAssistant")
        
        # 10. Verificar capacidades del servidor de memoria
        info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.SYSTEM,
            resource_path="/info"
        )
        
        info_response = await memory_client.send_message_async(info_message)
        if info_response.success:
            vector_search = info_response.data.get('vector_search', False)
            embedding_dim = info_response.data.get('embedding_dim')
            
            logger.info(f"Servidor de memoria MCP:")
            logger.info(f"- Búsqueda vectorial: {'Disponible' if vector_search else 'No disponible'}")
            if vector_search:
                logger.info(f"- Dimensión de embeddings: {embedding_dim}")
        
        # 11. Almacenar memorias de ejemplo para demostrar búsqueda
        example_memories = [
            # MEMORIAS ORIGINALES
            # Memoria sobre programación específica en Python
            {
                "content": "Python es un lenguaje de programación interpretado con tipado dinámico que permite programación orientada a objetos, programación funcional y programación imperativa. Fue creado por Guido van Rossum en 1991.",
                "memory_type": "general",
                "importance": 0.7,
                "metadata": {"category": "tecnología", "subcategory": "programación"}
            },
            # Memoria sobre Madrid (tema no relacionado con tecnología)
            {
                "content": "Madrid es la capital de España y la ciudad más poblada del país. Ubicada en el centro de la península ibérica, alberga instituciones como el Museo del Prado y el Palacio Real.",
                "memory_type": "general",
                "importance": 0.5,
                "metadata": {"category": "geografía", "subcategory": "ciudades"}
            },
            # Memoria sobre redes neuronales
            {
                "content": "Las redes neuronales son modelos computacionales inspirados en el cerebro humano, compuestos por capas de neuronas artificiales. Se utilizan para tareas como clasificación de imágenes, procesamiento de lenguaje natural y reconocimiento de patrones.",
                "memory_type": "general",
                "importance": 0.8,
                "metadata": {"category": "tecnología", "subcategory": "inteligencia artificial"}
            },
            # Memoria específica sobre transformers - ASEGURARNOS que esta se guarda bien
            {
                "content": "Los transformers son arquitecturas de redes neuronales basadas en mecanismos de atención que revolucionaron el procesamiento del lenguaje natural. Fueron introducidos en el paper 'Attention is All You Need' y son la base de modelos como BERT, GPT y T5.",
                "memory_type": "general",
                "importance": 0.9,
                "metadata": {"category": "tecnología", "subcategory": "transformers"}
            },
            # Memoria sobre aprendizaje por refuerzo
            {
                "content": "El aprendizaje por refuerzo es un tipo de aprendizaje automático donde un agente aprende a tomar decisiones interactuando con un entorno. El agente recibe recompensas por acciones correctas y penalizaciones por acciones incorrectas.",
                "memory_type": "general",
                "importance": 0.6,
                "metadata": {"category": "tecnología", "subcategory": "inteligencia artificial"}
            },
            # Memoria sobre procesamiento de lenguaje natural
            {
                "content": "El procesamiento de lenguaje natural (NLP) es un campo de la inteligencia artificial que se enfoca en la interacción entre las computadoras y el lenguaje humano. Incluye tareas como análisis de sentimiento, traducción automática, generación de texto y comprensión de lenguaje.",
                "memory_type": "general",
                "importance": 0.8,
                "metadata": {"category": "tecnología", "subcategory": "procesamiento de lenguaje natural"}
            },
            # Memoria sobre la arquitectura transformer en detalle
            {
                "content": "La arquitectura transformer utiliza mecanismos de auto-atención para procesar secuencias de texto. Sus componentes principales son: embedding de tokens, codificación posicional, capas de atención multi-cabeza, capas feed-forward, normalización de capas y conexiones residuales. Esta arquitectura permite procesar texto en paralelo y capturar dependencias a larga distancia.",
                "memory_type": "general",
                "importance": 0.9,
                "metadata": {"category": "tecnología", "subcategory": "transformers"}
            },
            
            # MEMORIAS AGREGADAS PREVIAMENTE
            {
                "content": "Los transformers revolucionaron el campo del procesamiento de lenguaje natural desde su introducción en 2017. Su arquitectura basada en atención eliminó la necesidad de procesamiento secuencial que limitaba a las RNN y LSTM.",
                "memory_type": "general",
                "importance": 0.95,
                "metadata": {"category": "tecnología", "subcategory": "transformers", "priority": "high"}
            },
            {
                "content": "La arquitectura transformer se ha aplicado con éxito en modelos como GPT (Generative Pre-trained Transformer) de OpenAI, BERT (Bidirectional Encoder Representations from Transformers) de Google, y T5 (Text-to-Text Transfer Transformer).",
                "memory_type": "general",
                "importance": 0.9,
                "metadata": {"category": "tecnología", "subcategory": "transformers", "examples": ["GPT", "BERT", "T5"]}
            },
            
            # NUEVAS MEMORIAS - MÁS DIVERSIDAD
            # Más sobre transformers con diferentes enfoques
            {
                "content": "Los modelos transformer pueden clasificarse en encoder-only (como BERT), decoder-only (como GPT), o encoder-decoder (como T5). Cada arquitectura tiene ventajas específicas según la tarea a realizar.",
                "memory_type": "general", 
                "importance": 0.85,
                "metadata": {"category": "tecnología", "subcategory": "transformers", "topic": "arquitecturas"}
            },
            {
                "content": "A diferencia de RNNs y LSTMs, los transformers procesan todas las palabras de una secuencia simultáneamente, lo que permite un entrenamiento más rápido y eficiente en GPUs.",
                "memory_type": "general",
                "importance": 0.8,
                "metadata": {"category": "tecnología", "subcategory": "transformers", "comparison": "RNN vs Transformer"}
            },
            {
                "content": "El mecanismo de atención en los transformers permite que el modelo asigne diferentes pesos de importancia a diferentes palabras en una secuencia, independientemente de su posición relativa.",
                "memory_type": "general",
                "importance": 0.9,
                "metadata": {"category": "tecnología", "subcategory": "transformers", "component": "attention"}
            },
            
            # Temas diversos para probar la diferenciación
            {
                "content": "El aprendizaje profundo (deep learning) es un subconjunto del machine learning que utiliza redes neuronales con múltiples capas. Permite el aprendizaje de representaciones cada vez más abstractas de los datos.",
                "memory_type": "general",
                "importance": 0.8,
                "metadata": {"category": "tecnología", "subcategory": "inteligencia artificial", "topic": "deep learning"}
            },
            {
                "content": "Los gatos domésticos (Felis catus) son mamíferos carnívoros de la familia Felidae. Son animales de compañía populares, conocidos por su agilidad, comportamiento independiente y capacidad para cazar roedores.",
                "memory_type": "general",
                "importance": 0.4,
                "metadata": {"category": "biología", "subcategory": "mamíferos", "topic": "felinos"}
            },
            {
                "content": "Barcelona es una ciudad española, capital de la comunidad autónoma de Cataluña. Es la segunda ciudad más poblada de España y un importante centro cultural, financiero y turístico, famosa por obras arquitectónicas como la Sagrada Familia.",
                "memory_type": "general",
                "importance": 0.5,
                "metadata": {"category": "geografía", "subcategory": "ciudades", "país": "España"}
            },
            
            # Más ejemplos específicos sobre IA
            {
                "content": "ChatGPT es un modelo de lenguaje desarrollado por OpenAI basado en la arquitectura GPT. Utiliza aprendizaje por refuerzo con retroalimentación humana (RLHF) para generar respuestas conversacionales de alta calidad.",
                "memory_type": "general",
                "importance": 0.9,
                "metadata": {"category": "tecnología", "subcategory": "IA generativa", "modelo": "ChatGPT"}
            },
            {
                "content": "Claude es un asistente de IA desarrollado por Anthropic, diseñado con un enfoque en seguridad y alineación con valores humanos. Utiliza la técnica Constitutional AI para evitar respuestas dañinas.",
                "memory_type": "general",
                "importance": 0.85,
                "metadata": {"category": "tecnología", "subcategory": "IA generativa", "modelo": "Claude"}
            },
            {
                "content": "El Procesamiento de Lenguaje Natural (NLP) ha avanzado significativamente en los últimos años, pasando de modelos basados en n-gramas y reglas, a arquitecturas sofisticadas como Word2Vec, ELMo, y finalmente transformers como BERT y GPT.",
                "memory_type": "general", 
                "importance": 0.85,
                "metadata": {"category": "tecnología", "subcategory": "NLP", "topic": "evolución"}
            }
        ]

        logger.info(f"Almacenando {len(example_memories)} memorias de ejemplo...")
        memory_ids = []

        # Crear cada memoria usando MCP
        for i, memory_data in enumerate(example_memories):
            try:
                create_msg = MCPMessage(
                    action=MCPAction.CREATE,
                    resource_type=MCPResource.MEMORY,
                    resource_path="/",
                    data={
                        "content": memory_data["content"],
                        "memory_type": memory_data["memory_type"],
                        "importance": memory_data["importance"],
                        "metadata": memory_data["metadata"],
                        "generate_embedding": True  # Generar embedding para búsqueda semántica
                    }
                )
                
                # Usar send_message_async con await
                response = await memory_client.send_message_async(create_msg)
                if response.success:
                    memory_id = response.data.get('id')
                    memory_ids.append(memory_id)
                    logger.info(f"Memoria {i+1}/{len(example_memories)} almacenada con ID: {memory_id}")
                else:
                    logger.error(f"Error al crear memoria {i+1}: {response.error}")
            except Exception as e:
                logger.error(f"Excepción al crear memoria {i+1}: {e}")

        # 10. Verificar que las memorias se almacenaron correctamente
        logger.info(f"Se almacenaron {len(memory_ids)} memorias. Verificando...")

        # NUEVO: Listar todas las memorias para verificar
        try:
            list_msg = MCPMessage(
                action=MCPAction.LIST,
                resource_type=MCPResource.MEMORY,
                resource_path="/",
                data={"limit": 100}
            )
            list_response = await memory_client.send_message_async(list_msg)
            if list_response.success:
                memories = list_response.data.get('items', [])
                logger.info(f"Hay {len(memories)} memorias almacenadas en total")
                
                # Mostrar información sobre las memorias con 'transformers'
                transformer_memories = [m for m in memories if "transformer" in m.get('content', '').lower()]
                logger.info(f"De las cuales {len(transformer_memories)} contienen 'transformer' en su contenido:")
                
                for i, memory in enumerate(transformer_memories):
                    shortened_content = memory.get('content', '')[:50] + '...' if len(memory.get('content', '')) > 50 else memory.get('content', '')
                    logger.info(f"  {i+1}. ID: {memory.get('id')} - {shortened_content}")
            else:
                logger.error(f"Error al listar memorias: {list_response.error}")
        except Exception as e:
            logger.error(f"Excepción al listar memorias: {e}")

        # Realizar algunas pruebas de búsqueda
        test_queries = [
            # Consultas originales
            "lenguajes de programación",
            "ciudades de España",
            "inteligencia artificial y aprendizaje",
            "transformers y procesamiento de lenguaje",
            "información sobre transformers",
            "arquitectura de modelos de lenguaje",
            "transformers revolución nlp",
            "mecanismos de atención", 
            "ejemplos de modelos transformer",
            
            # Nuevas consultas más específicas
            "diferencias entre modelos encoder-only y decoder-only",
            "ventajas de transformers sobre rnn", 
            "modelos de lenguaje basados en atención",
            "BERT vs GPT arquitectura",
            "aplicaciones de transformers en NLP",
            "comparativa ciudades españolas",
            "qué sabes sobre gatos",
            "modelos de lenguaje conversacionales",
            "evolución del procesamiento de lenguaje natural"
        ]

        logger.info("Realizando pruebas de búsqueda semántica...")
        for query in test_queries:
            logger.info(f"\nBúsqueda: '{query}'")
            search_msg = MCPMessage(
                action=MCPAction.SEARCH,
                resource_type=MCPResource.VECTOR,
                resource_path="/",
                data={
                    "query": query,
                    "threshold": 0.25  # Umbral reducido para permitir más resultados
                }
            )
            
            try:
                # Usar send_message_async con await
                response = await memory_client.send_message_async(search_msg)
                if response.success:
                    results = response.data.get('results', [])
                    
                    if not results:
                        logger.info("  No se encontraron resultados.")
                    else:
                        logger.info(f"  Se encontraron {len(results)} resultados:")
                        
                        # Mostrar resultados
                        for i, item in enumerate(results[:3]):  # Mostrar solo los primeros 3
                            content = item.get('content', '')
                            score = item.get('score', 0)
                            
                            # Truncar contenido para log
                            if len(content) > 100:
                                content = content[:97] + "..."
                                
                            logger.info(f"  {i+1}. Score: {score:.2f} - {content}")
                else:
                    logger.error(f"Error en búsqueda '{query}': {response.error}")
            except Exception as e:
                logger.error(f"Excepción en búsqueda '{query}': {e}")
        
        # 12. Realizar pruebas de consulta a través del MainAssistant
        await test_assistant_delegations(main_assistant)
        
        logger.info("Ejemplo completado")
        
    except Exception as e:
        logger.error(f"Error durante la ejecución del ejemplo: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def test_assistant_delegations(main_assistant: MainAssistant):
    """Probar delegación de consultas del asistente principal al agente de memoria."""
    logger.info("\n=== PRUEBAS DE DELEGACIÓN DEL ASISTENTE PRINCIPAL ===")
    
    try:
        # 1. Preguntar al MainAssistant algo que debería delegar al MemoryAgent
        query = "¿Qué sabes sobre redes neuronales y aprendizaje automático?"
        logger.info(f"\nConsulta al MainAssistant: '{query}'")
        
        response = await main_assistant.process(query)
        logger.info(f"Respuesta del MainAssistant:\n{response.content}")
        
        # 2. Solicitar almacenar un nuevo hecho
        query = "Por favor recuerda que los transformers revolucionaron el procesamiento de lenguaje natural desde 2017"
        logger.info(f"\nSolicitud para recordar: '{query}'")
        
        response = await main_assistant.process(query)
        logger.info(f"Respuesta del MainAssistant:\n{response.content}")
        
        # 3. Verificar que se haya almacenado preguntando por ello
        query = "Busca en tu memoria información sobre transformers y procesamiento de lenguaje"
        logger.info(f"\nVerificación de recuerdo: '{query}'")
        
        response = await main_assistant.process(query)
        logger.info(f"Respuesta del MainAssistant:\n{response.content}")
        
    except Exception as e:
        logger.error(f"Error en pruebas de delegación del asistente: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(run_example()) 