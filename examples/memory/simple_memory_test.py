"""
Prueba simplificada del servidor de memoria MCP.

Este ejemplo demuestra:
1. Cómo configurar un servidor MemoryServer
2. Cómo conectarse mediante un cliente MCP
3. Cómo almacenar y recuperar memorias
4. Cómo utilizar búsqueda semántica

Para ejecutar:
    python examples/memory/simple_memory_test.py
"""

import os
import sys
import logging
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

logger = logging.getLogger("memory_test")

# Importaciones del sistema
from mcp.core import MCPMessage, MCPAction, MCPResource
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient


def test_memory_server():
    """Prueba básica del servidor de memoria MCP."""
    logger.info("Iniciando prueba simplificada de memoria MCP")
    
    # 1. Configurar directorio para datos
    data_dir = os.path.join(project_root, "examples/data/memory_test")
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
    
    # 2. Crear un servidor MCP de memoria
    memory_server = MemoryServer(
        name="memory_test",
        description="Servidor de memoria para pruebas simplificadas",
        data_dir=data_dir
    )
    
    # 3. Crear un cliente MCP para el servidor de memoria
    memory_client = SimpleDirectClient(memory_server)
    memory_client.connect()
    logger.info("Cliente MCP conectado al servidor de memoria")
    
    # 4. Verificar capacidades del servidor
    info_message = MCPMessage(
        action=MCPAction.GET,
        resource_type=MCPResource.SYSTEM,
        resource_path="/info"
    )
    
    info_response = memory_client.send_message(info_message)
    if info_response.success:
        vector_search = info_response.data.get('vector_search', False)
        embedding_dim = info_response.data.get('embedding_dim')
        
        logger.info(f"Servidor de memoria MCP:")
        logger.info(f"- Búsqueda vectorial: {'Disponible' if vector_search else 'No disponible'}")
        if vector_search:
            logger.info(f"- Dimensión de embeddings: {embedding_dim}")
    
    # 5. Crear algunas memorias de ejemplo
    memories = [
        {
            "content": "Python es un lenguaje de programación interpretado y de alto nivel.",
            "memory_type": "fact",
            "importance": 0.8,
            "metadata": {"category": "programming"}
        },
        {
            "content": "Los modelos de lenguaje transformers revolucionaron el NLP.",
            "memory_type": "fact", 
            "importance": 0.9,
            "metadata": {"category": "ai"}
        },
        {
            "content": "Madrid es la capital de España.",
            "memory_type": "fact",
            "importance": 0.7,
            "metadata": {"category": "geography"}
        }
    ]
    
    memory_ids = []
    for memory_data in memories:
        create_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "content": memory_data["content"],
                "memory_type": memory_data["memory_type"],
                "importance": memory_data["importance"],
                "metadata": memory_data["metadata"],
                "generate_embedding": True
            }
        )
        
        response = memory_client.send_message(create_message)
        if response.success:
            memory_id = response.data.get('id')
            memory_ids.append(memory_id)
            logger.info(f"Memoria creada: {memory_id}")
        else:
            logger.error(f"Error creando memoria: {response.error}")
    
    logger.info(f"Creadas {len(memory_ids)} memorias")
    
    # 6. Recuperar una memoria por ID
    if memory_ids:
        get_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.MEMORY,
            resource_path=f"/{memory_ids[0]}"
        )
        
        response = memory_client.send_message(get_message)
        if response.success:
            logger.info(f"Memoria recuperada: {response.data}")
        else:
            logger.error(f"Error recuperando memoria: {response.error}")
    
    # 7. Realizar búsqueda semántica
    logger.info("\nRealizando búsqueda semántica...")
    search_message = MCPMessage(
        action=MCPAction.SEARCH,
        resource_type="vector",
        resource_path="/",
        data={
            "query": "inteligencia artificial",
            "limit": 2,
            "threshold": 0.2
        }
    )

    response = memory_client.send_message(search_message)
    if response.success:
        results = response.data.get('results', [])
        logger.info(f"Resultados de búsqueda semántica ({len(results)}):")
        for result in results:
            similarity = result.get('similarity', 'N/A')
            content = result.get('content', 'Contenido desconocido')
            logger.info(f"- [{similarity:.2f}] {content}")
    else:
        logger.error(f"Error en búsqueda semántica: {response.error}")
        # Verificar si el ModelManager se inicializó correctamente
        info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.SYSTEM,
            resource_path="/info"
        )
        
        info_response = memory_client.send_message(info_message)
        if info_response.success:
            logger.info(f"Información del servidor después del error: {info_response.data}")
    
    # 8. Realizar búsqueda por palabras clave
    search_message = MCPMessage(
        action=MCPAction.SEARCH,
        resource_type=MCPResource.MEMORY,
        resource_path="/",
        data={
            "query": "lenguaje programación",
            "limit": 2
        }
    )
    
    response = memory_client.send_message(search_message)
    if response.success:
        results = response.data.get('results', [])
        logger.info(f"Resultados de búsqueda por palabras ({len(results)}):")
        for result in results:
            content = result.get('content', 'Contenido desconocido')
            logger.info(f"- {content}")
    else:
        logger.error(f"Error en búsqueda por palabras: {response.error}")
    
    logger.info("Prueba completada con éxito")


if __name__ == "__main__":
    test_memory_server() 