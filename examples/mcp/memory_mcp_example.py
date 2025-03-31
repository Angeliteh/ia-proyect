"""
Ejemplo del servidor MCP para el sistema de memoria.

Este ejemplo demuestra:
1. Cómo crear un servidor de memoria MCP
2. Cómo conectar un cliente a dicho servidor
3. Cómo realizar operaciones básicas con la memoria a través del protocolo MCP
4. Cómo integrar el sistema de memoria con agentes

Para ejecutar el ejemplo:
    python examples/mcp/memory_mcp_example.py
"""

import asyncio
import logging
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional

# Aseguramos que el directorio raíz del proyecto esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("memory_mcp_example")

# Importamos los componentes necesarios
try:
    from mcp.core import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPRegistry
    from mcp_servers.memory import MemoryServer
    from mcp.clients import SimpleDirectClient
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    sys.exit(1)

def print_section_header(title):
    """Imprime un encabezado de sección con formato."""
    separator = "=" * 80
    logger.info("\n" + separator)
    logger.info(f"  {title}")
    logger.info(separator)

async def run_example():
    """Ejecuta el ejemplo del servidor de memoria MCP."""
    # Crear un directorio temporal para los datos de memoria
    data_dir = os.path.join(project_root, "examples/mcp/data/memory")
    os.makedirs(data_dir, exist_ok=True)
    
    # Crear un servidor de memoria para el ejemplo
    server = MemoryServer(
        name="memory_example",
        description="Servidor de memoria para ejemplo MCP",
        data_dir=data_dir
    )
    
    logger.info(f"Servidor de memoria creado: {server.name}")
    
    # Crear un cliente directo que se conecte al servidor
    client = SimpleDirectClient(server)
    
    try:
        # Conectar al servidor
        client.connect()
        logger.info("Cliente conectado al servidor de memoria")
        
        # 1. Verificar conexión con PING
        print_section_header("PING")
        ping_result = await client.ping_async()
        logger.info(f"Ping resultado: {ping_result}")
        
        # 2. Obtener capacidades
        print_section_header("CAPACIDADES")
        capabilities = await client.get_capabilities_async()
        
        if not capabilities:
            logger.warning("No se pudieron obtener las capacidades del servidor.")
            capabilities = server.capabilities
            
        logger.info(f"Nombre del servidor: {capabilities.get('name', 'Desconocido')}")
        logger.info(f"Descripción: {capabilities.get('description', 'Sin descripción')}")
        logger.info("Acciones soportadas:")
        for action in capabilities.get('supported_actions', []):
            logger.info(f"  • {action}")
        logger.info("Recursos soportados:")
        for resource in capabilities.get('supported_resources', []):
            logger.info(f"  • {resource}")
        
        # 3. Obtener información del sistema
        print_section_header("INFORMACIÓN DEL SISTEMA")
        info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.SYSTEM,
            resource_path="/info"
        )
        
        info_response = await client.send_message_async(info_message)
        if info_response.success:
            logger.info(f"Servidor: {info_response.data.get('server')}")
            logger.info(f"Descripción: {info_response.data.get('description')}")
            logger.info(f"Tipos de memoria: {info_response.data.get('memory_types', [])}")
            logger.info(f"Directorio de datos: {info_response.data.get('data_dir')}")
        else:
            logger.error(f"✗ Error: {info_response.error.message if hasattr(info_response, 'error') else 'Error desconocido'}")
        
        # 4. Crear memorias
        print_section_header("CREAR MEMORIAS")
        
        # 4.1 Crear memoria general
        create_memory_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "content": "Este es un recuerdo importante para probar el sistema de memoria.",
                "memory_type": "general",
                "importance": 0.8,
                "metadata": {
                    "source": "mcp_example",
                    "tags": ["test", "important", "memory"]
                }
            }
        )
        
        create_response = await client.send_message_async(create_memory_message)
        
        if create_response.success:
            memory_id = create_response.data.get('id')
            logger.info(f"✓ Memoria creada: {memory_id}")
            logger.info(f"  Mensaje: {create_response.data.get('message')}")
        else:
            logger.error(f"✗ Error: {create_response.error.message}")
            return
        
        # 4.2 Crear memoria en memoria a largo plazo
        create_lt_memory_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type=MCPResource.MEMORY,
            resource_path="/long_term",
            data={
                "content": {
                    "fact": "El sistema de memoria MCP permite almacenar información persistente"
                },
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {
                    "source": "mcp_example",
                    "category": "system_knowledge"
                }
            }
        )
        
        create_lt_response = await client.send_message_async(create_lt_memory_message)
        
        if create_lt_response.success:
            lt_memory_id = create_lt_response.data.get('id')
            logger.info(f"✓ Memoria a largo plazo creada: {lt_memory_id}")
        else:
            logger.error(f"✗ Error: {create_lt_response.error.message}")
            
        # 4.3 Crear memoria episódica
        create_ep_memory_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type=MCPResource.MEMORY,
            resource_path="/episodic",
            data={
                "content": "El usuario ejecutó el ejemplo de memoria MCP correctamente",
                "memory_type": "episode",
                "importance": 0.7,
                "metadata": {
                    "source": "mcp_example",
                    "timestamp": "2023-06-15T14:30:00",
                    "actors": ["user", "system"]
                }
            }
        )
        
        create_ep_response = await client.send_message_async(create_ep_memory_message)
        
        if create_ep_response.success:
            ep_memory_id = create_ep_response.data.get('id')
            logger.info(f"✓ Memoria episódica creada: {ep_memory_id}")
        else:
            logger.error(f"✗ Error: {create_ep_response.error.message}")
        
        # 5. Obtener memoria específica
        print_section_header("OBTENER MEMORIA")
        
        get_memory_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.MEMORY,
            resource_path=f"/{memory_id}"
        )
        
        get_response = await client.send_message_async(get_memory_message)
        
        if get_response.success:
            logger.info(f"Memoria recuperada:")
            logger.info(f"  ID: {get_response.data.get('id')}")
            logger.info(f"  Contenido: {get_response.data.get('content')}")
            logger.info(f"  Tipo: {get_response.data.get('memory_type')}")
            logger.info(f"  Importancia: {get_response.data.get('importance')}")
            logger.info(f"  Metadata: {get_response.data.get('metadata')}")
        else:
            logger.error(f"✗ Error: {get_response.error.message}")
        
        # 6. Listar memorias
        print_section_header("LISTAR MEMORIAS")
        
        list_memories_message = MCPMessage(
            action=MCPAction.LIST,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "limit": 10,
                "offset": 0
            }
        )
        
        list_response = await client.send_message_async(list_memories_message)
        
        if list_response.success:
            memories = list_response.data.get('items', [])
            total = list_response.data.get('total', 0)
            logger.info(f"Total de memorias: {total}")
            
            for memory in memories:
                content_str = str(memory['content'])
                if len(content_str) > 50:
                    content_str = content_str[:50] + "..."
                logger.info(f"  • ID: {memory['id']}, Tipo: {memory['memory_type']}, Contenido: {content_str}")
        else:
            logger.error(f"✗ Error: {list_response.error.message}")
        
        # 7. Buscar memorias
        print_section_header("BUSCAR MEMORIAS")
        
        search_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "query": "importante",
                "limit": 5
            }
        )
        
        search_response = await client.send_message_async(search_message)
        
        if search_response.success:
            results = search_response.data.get('results', [])
            count = search_response.data.get('count', 0)
            logger.info(f"Resultados encontrados: {count}")
            
            for memory in results:
                content_str = str(memory['content'])
                if len(content_str) > 50:
                    content_str = content_str[:50] + "..."
                logger.info(f"  • ID: {memory['id']}, Tipo: {memory['memory_type']}, Contenido: {content_str}")
        else:
            logger.error(f"✗ Error: {search_response.error.message}")
        
        # 8. Actualizar memoria
        print_section_header("ACTUALIZAR MEMORIA")
        
        update_message = MCPMessage(
            action=MCPAction.UPDATE,
            resource_type=MCPResource.MEMORY,
            resource_path=f"/{memory_id}",
            data={
                "content": "Este es un recuerdo actualizado con información adicional.",
                "importance": 0.9
            }
        )
        
        update_response = await client.send_message_async(update_message)
        
        if update_response.success:
            logger.info(f"✓ Memoria actualizada: {update_response.data.get('id')}")
            logger.info(f"  Mensaje: {update_response.data.get('message')}")
            
            # Verificar la actualización
            get_updated_message = MCPMessage(
                action=MCPAction.GET,
                resource_type=MCPResource.MEMORY,
                resource_path=f"/{memory_id}"
            )
            
            get_updated_response = await client.send_message_async(get_updated_message)
            
            if get_updated_response.success:
                logger.info(f"Memoria actualizada recuperada:")
                logger.info(f"  Contenido: {get_updated_response.data.get('content')}")
                logger.info(f"  Importancia: {get_updated_response.data.get('importance')}")
        else:
            logger.error(f"✗ Error: {update_response.error.message}")
        
        # 9. Realizar consulta avanzada
        print_section_header("CONSULTA AVANZADA")
        
        query_message = MCPMessage(
            action=MCPAction.QUERY,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "query": {
                    "min_importance": 0.8
                },
                "limit": 10
            }
        )
        
        query_response = await client.send_message_async(query_message)
        
        if query_response.success:
            results = query_response.data.get('results', [])
            count = query_response.data.get('count', 0)
            logger.info(f"Memorias importantes encontradas: {count}")
            
            for memory in results:
                logger.info(f"  • ID: {memory['id']}, Importancia: {memory['importance']}, Tipo: {memory['memory_type']}")
        else:
            logger.error(f"✗ Error: {query_response.error.message}")
        
        # 10. Eliminar memoria
        print_section_header("ELIMINAR MEMORIA")
        
        delete_message = MCPMessage(
            action=MCPAction.DELETE,
            resource_type=MCPResource.MEMORY,
            resource_path=f"/{memory_id}"
        )
        
        delete_response = await client.send_message_async(delete_message)
        
        if delete_response.success:
            logger.info(f"✓ Memoria eliminada: {delete_response.data.get('id')}")
            logger.info(f"  Mensaje: {delete_response.data.get('message')}")
            
            # Verificar la eliminación
            get_deleted_message = MCPMessage(
                action=MCPAction.GET,
                resource_type=MCPResource.MEMORY,
                resource_path=f"/{memory_id}"
            )
            
            get_deleted_response = await client.send_message_async(get_deleted_message)
            
            if get_deleted_response.success:
                logger.error(f"✗ La memoria debería haber sido eliminada pero se recuperó: {memory_id}")
            else:
                logger.info(f"✓ Confirmado: La memoria {memory_id} fue eliminada correctamente")
        else:
            logger.error(f"✗ Error: {delete_response.error.message}")
            
        # 11. Ejemplo de uso con un agente
        print_section_header("EJEMPLO DE USO CON AGENTE")
        
        logger.info("Simulando un agente que usa el sistema de memoria...")
        
        class MemoryAgent:
            def __init__(self, memory_client):
                self.memory_client = memory_client
                self.name = "MemoryAgent"
                
            async def remember(self, content, memory_type="observation", importance=0.5, metadata=None):
                """Almacena una nueva memoria."""
                metadata = metadata or {}
                metadata["agent"] = self.name
                
                create_message = MCPMessage(
                    action=MCPAction.CREATE,
                    resource_type=MCPResource.MEMORY,
                    resource_path="/",
                    data={
                        "content": content,
                        "memory_type": memory_type,
                        "importance": importance,
                        "metadata": metadata
                    }
                )
                
                response = await self.memory_client.send_message_async(create_message)
                if response.success:
                    return response.data.get('id')
                return None
                
            async def recall(self, query_term, memory_type=None, limit=5):
                """Busca en las memorias."""
                search_data = {
                    "query": query_term,
                    "limit": limit
                }
                
                if memory_type:
                    search_data["memory_type"] = memory_type
                
                search_message = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type=MCPResource.MEMORY,
                    resource_path="/",
                    data=search_data
                )
                
                response = await self.memory_client.send_message_async(search_message)
                if response.success:
                    return response.data.get('results', [])
                return []
        
        # Crear y usar un agente de memoria
        agent = MemoryAgent(client)
        
        # El agente observa y recuerda algo
        observation = "El usuario parece estar probando el sistema de memoria con un ejemplo de MCP"
        memory_id = await agent.remember(
            content=observation,
            memory_type="observation",
            importance=0.7,
            metadata={"context": "testing", "sentiment": "neutral"}
        )
        
        if memory_id:
            logger.info(f"✓ Agente creó una memoria: {memory_id}")
            
            # El agente intenta recordar algo relacionado
            memories = await agent.recall("usuario")
            
            if memories:
                logger.info(f"Agente recordó {len(memories)} memorias relevantes:")
                for i, memory in enumerate(memories):
                    content_str = str(memory['content'])
                    if len(content_str) > 50:
                        content_str = content_str[:50] + "..."
                    logger.info(f"  {i+1}. {content_str}")
            else:
                logger.info("El agente no encontró memorias relevantes")
        else:
            logger.error("✗ El agente no pudo crear una memoria")
        
        print_section_header("EJEMPLO COMPLETADO")
        logger.info("El ejemplo del servidor de memoria MCP se ha completado correctamente")
        
    except Exception as e:
        logger.error(f"Error en el ejemplo: {str(e)}")
    finally:
        # Cerrar cliente
        client.disconnect()
        logger.info("Cliente desconectado")

if __name__ == "__main__":
    asyncio.run(run_example()) 