"""
Ejemplo simplificado del MemoryAgent.

Este ejemplo demuestra:
1. Cómo configurar un MemoryAgent básico
2. Cómo almacenar memorias con embeddings
3. Cómo realizar búsquedas semánticas y por palabras clave
4. Cómo responder preguntas basadas en memoria

Para ejecutar:
    python examples/memory/memory_agent_simple.py
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

logger = logging.getLogger("memory_agent_test")

# Importaciones del sistema
from models.core.model_manager import ModelManager
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient
from agents.specialized.memory_agent import MemoryAgent


async def test_memory_agent():
    """Prueba simplificada del MemoryAgent."""
    logger.info("Iniciando prueba simplificada del MemoryAgent")
    
    # 1. Configurar directorio para datos
    data_dir = os.path.join(project_root, "examples/data/memory_agent_simple")
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
    
    # 2. Crear un servidor MCP de memoria con capacidad vectorial
    logger.info("Creando servidor de memoria MCP")
    memory_server = MemoryServer(
        name="memory_test",
        description="Servidor de memoria para pruebas del agente",
        data_dir=data_dir
    )
    
    # 3. Crear un cliente MCP para el servidor de memoria
    memory_client = SimpleDirectClient(memory_server)
    memory_client.connect()
    logger.info("Cliente MCP conectado al servidor de memoria")
    
    # 4. Configurar ModelManager para el agente
    model_manager = ModelManager()
    
    # 5. Configurar y crear el agente de memoria
    logger.info("Creando agente de memoria especializado")
    memory_agent_config = {
        "name": "MemoryMaster",
        "description": "Agente especializado en gestión de memoria semántica",
        "model_manager": model_manager,
        "memory_config": {
            "data_dir": data_dir,
            "mcp_client": memory_client
        },
        "semantic_threshold": 0.2  # Umbral para búsqueda semántica
    }
    
    try:
        memory_agent = MemoryAgent("memory_test", memory_agent_config)
        logger.info("MemoryAgent creado correctamente")
        
        # Verificar que el agente tiene memoria configurada
        if memory_agent.has_memory():
            logger.info("Memory Agent tiene memoria configurada correctamente")
        else:
            logger.error("Memory Agent no tiene memoria configurada, abortando prueba")
            return
            
        # 6. Almacenar algunas memorias de ejemplo
        logger.info("\n=== ALMACENANDO MEMORIAS DE EJEMPLO ===")
        example_facts = [
            {
                "content": "Python es un lenguaje de programación interpretado, de alto nivel y propósito general.",
                "memory_type": "fact",
                "importance": 0.8,
                "metadata": {"category": "programming", "tags": ["python", "language"]}
            },
            {
                "content": "Los modelos de lenguaje transformers revolucionaron el procesamiento de lenguaje natural.",
                "memory_type": "fact", 
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["nlp", "transformers"]}
            },
            {
                "content": "Las redes neuronales convolucionales son muy efectivas para el análisis de imágenes.",
                "memory_type": "fact", 
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["neural networks", "computer vision"]}
            },
            {
                "content": "Los embeddings vectoriales representan el significado semántico de textos o imágenes.",
                "memory_type": "fact",
                "importance": 0.8,
                "metadata": {"category": "ai", "tags": ["embeddings", "nlp"]}
            }
        ]
        
        for i, fact in enumerate(example_facts):
            logger.info(f"Almacenando memoria #{i+1}: {fact['content'][:40]}...")
            
            context = {
                "action": "remember",
                "content": fact["content"],
                "memory_type": fact["memory_type"],
                "importance": fact["importance"],
                "metadata": fact["metadata"]
            }
            
            response = await memory_agent.process(
                query=fact["content"],
                context=context
            )
            
            logger.info(f"Respuesta: {response.content}")
        
        logger.info(f"Almacenadas {len(example_facts)} memorias")
        
        # 7. Realizar búsqueda semántica
        logger.info("\n=== BÚSQUEDA SEMÁNTICA ===")
        query = "inteligencia artificial y procesamiento de lenguaje"
        logger.info(f"Consultando: '{query}'")
        
        semantic_context = {
            "action": "recall",
            "semantic": True,
            "limit": 2
        }
        
        response = await memory_agent.process(query, semantic_context)
        logger.info(f"Resultados de búsqueda semántica:\n{response.content}")
        
        # 8. Realizar búsqueda por palabras clave
        logger.info("\n=== BÚSQUEDA POR PALABRAS CLAVE ===")
        query = "python programación"
        logger.info(f"Consultando: '{query}'")
        
        keyword_context = {
            "action": "recall",
            "semantic": False,
            "limit": 2
        }
        
        response = await memory_agent.process(query, keyword_context)
        logger.info(f"Resultados de búsqueda por palabras clave:\n{response.content}")
        
        # 9. Responder a una pregunta usando la memoria
        logger.info("\n=== PREGUNTA BASADA EN MEMORIA ===")
        question = "¿Qué son los embeddings vectoriales y para qué sirven?"
        logger.info(f"Pregunta: '{question}'")
        
        qa_context = {
            "action": "answer"
        }
        
        response = await memory_agent.process(question, qa_context)
        logger.info(f"Respuesta basada en memoria:\n{response.content}")
        
        logger.info("Prueba completada con éxito")
        
    except Exception as e:
        logger.error(f"Error en la prueba del MemoryAgent: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(test_memory_agent()) 