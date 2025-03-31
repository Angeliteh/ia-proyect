"""
Ejemplo del servidor MCP para SQLite.

Este ejemplo demuestra:
1. Cómo crear un servidor SQLite MCP
2. Cómo conectar un cliente a dicho servidor
3. Cómo realizar operaciones básicas con la base de datos a través del protocolo MCP
4. Cómo gestionar tablas y registros

Para ejecutar el ejemplo:
    python examples/mcp/sqlite_mcp_example.py
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

logger = logging.getLogger("sqlite_mcp_example")

# Importamos los componentes necesarios
try:
    from mcp.core import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPRegistry
    from mcp.servers import SQLiteServer
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
    """Ejecuta el ejemplo del servidor SQLite MCP."""
    # Crear un servidor SQLite en memoria para el ejemplo
    server = SQLiteServer(
        name="sqlite_example",
        db_path=":memory:",
        description="Servidor SQLite para ejemplo"
    )
    
    logger.info(f"Servidor SQLite creado: {server.name}")
    
    # Crear un cliente directo que se conecte al servidor
    client = SimpleDirectClient(server)
    
    try:
        # Conectar al servidor
        client.connect()
        logger.info("Cliente conectado al servidor SQLite")
        
        # 1. Verificar conexión con PING
        print_section_header("PING")
        ping_result = await client.ping_async()
        logger.info(f"Ping resultado: {ping_result}")
        
        # 2. Obtener capacidades
        print_section_header("CAPACIDADES")
        capabilities = await client.get_capabilities_async()
        
        if not capabilities:
            logger.warning("No se pudieron obtener las capacidades del servidor.")
            logger.warning("Obteniendo capacidades directamente del servidor...")
            capabilities = server.capabilities
            
        logger.info(f"Nombre del servidor: {capabilities.get('name', 'Desconocido')}")
        logger.info(f"Descripción: {capabilities.get('description', 'Sin descripción')}")
        logger.info("Acciones soportadas:")
        for action in capabilities.get('supported_actions', []):
            logger.info(f"  • {action}")
        logger.info("Recursos soportados:")
        for resource in capabilities.get('supported_resources', []):
            logger.info(f"  • {resource}")
        
        # 3. Crear una tabla de usuarios
        print_section_header("CREAR TABLA")
        create_table_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="table",
            resource_path="/users",
            data={
                "schema": {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "name": "TEXT NOT NULL",
                    "email": "TEXT",
                    "age": "INTEGER",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                }
            }
        )
        
        create_response = await client.send_message_async(create_table_message)
        if create_response.success:
            logger.info(f"✓ Tabla creada: {create_response.data.get('message')}")
        else:
            logger.error(f"✗ Error: {create_response.error.message if hasattr(create_response, 'error') else 'Error desconocido'}")
            return
        
        # 4. Verificar que la tabla existe listando todas las tablas
        print_section_header("LISTAR TABLAS")
        list_response = await client.list_resources_async(MCPResource.DATABASE, "/")
        if list_response.success:
            tables = list_response.data.get('tables', [])
            logger.info(f"Tablas en la base de datos: {', '.join(tables)}")
        else:
            logger.error(f"✗ Error: {list_response.error.message}")
            return
        
        # 5. Insertar registros en la tabla
        print_section_header("INSERTAR REGISTROS")
        
        # Usuarios de ejemplo
        users = [
            {"name": "Juan Pérez", "email": "juan@example.com", "age": 30},
            {"name": "María García", "email": "maria@example.com", "age": 25},
            {"name": "Carlos López", "email": "carlos@example.com", "age": 42}
        ]
        
        for user in users:
            insert_message = MCPMessage(
                action=MCPAction.CREATE,
                resource_type="record",
                resource_path="/users",
                data={"data": user}
            )
            
            insert_response = await client.send_message_async(insert_message)
            if insert_response.success:
                logger.info(f"✓ Usuario creado: {user['name']} (ID: {insert_response.data.get('id')})")
            else:
                logger.error(f"✗ Error: {insert_response.error.message}")
        
        # 6. Listar todos los registros de la tabla
        print_section_header("LISTAR REGISTROS")
        list_records_message = MCPMessage(
            action=MCPAction.LIST,
            resource_type="table",
            resource_path="/users",
            data={"limit": 10, "offset": 0}
        )
        
        list_records_response = await client.send_message_async(list_records_message)
        if list_records_response.success:
            users = list_records_response.data.get('items', [])
            total = list_records_response.data.get('total', 0)
            logger.info(f"Total de usuarios: {total}")
            
            for user in users:
                logger.info(f"  • ID: {user['id']}, Nombre: {user['name']}, Email: {user['email']}, Edad: {user['age']}")
        else:
            logger.error(f"✗ Error: {list_records_response.error.message}")
        
        # 7. Buscar registros por un criterio
        print_section_header("BUSCAR REGISTROS")
        search_response = await client.search_resources_async("table", "García")
        if search_response.success:
            results = search_response.data.get('results', [])
            count = search_response.data.get('count', 0)
            logger.info(f"Resultados encontrados: {count}")
            
            for user in results:
                logger.info(f"  • ID: {user['id']}, Nombre: {user['name']}, Email: {user['email']}")
        else:
            logger.error(f"✗ Error: {search_response.error.message}")
        
        # 8. Obtener un registro específico por ID
        print_section_header("OBTENER REGISTRO POR ID")
        get_message = MCPMessage(
            action=MCPAction.GET,
            resource_type="table",
            resource_path="/users",
            data={"id": 2}
        )
        
        get_response = await client.send_message_async(get_message)
        if get_response.success:
            user = get_response.data
            logger.info(f"Usuario encontrado: ID={user['id']}, Nombre={user['name']}, Email={user['email']}, Edad={user['age']}")
        else:
            logger.error(f"✗ Error: {get_response.error.message}")
        
        # 9. Actualizar un registro
        print_section_header("ACTUALIZAR REGISTRO")
        update_message = MCPMessage(
            action=MCPAction.UPDATE,
            resource_type="record",
            resource_path="/users",
            data={
                "id": 1,
                "data": {
                    "name": "Juan Pérez Actualizado",
                    "age": 31
                }
            }
        )
        
        update_response = await client.send_message_async(update_message)
        if update_response.success:
            logger.info(f"✓ Registro actualizado: {update_response.data.get('message')}")
        else:
            logger.error(f"✗ Error: {update_response.error.message}")
        
        # 10. Verificar la actualización
        print_section_header("VERIFICAR ACTUALIZACIÓN")
        get_updated_message = MCPMessage(
            action=MCPAction.GET,
            resource_type="table",
            resource_path="/users",
            data={"id": 1}
        )
        
        get_updated_response = await client.send_message_async(get_updated_message)
        if get_updated_response.success:
            user = get_updated_response.data
            logger.info(f"Usuario actualizado: ID={user['id']}, Nombre={user['name']}, Email={user['email']}, Edad={user['age']}")
        else:
            logger.error(f"✗ Error: {get_updated_response.error.message}")
        
        # 11. Ejecutar una consulta SQL personalizada
        print_section_header("CONSULTA SQL")
        query_message = MCPMessage(
            action=MCPAction.QUERY,
            resource_type=MCPResource.DATABASE,
            resource_path="/",
            data={
                "query": "SELECT id, name, age FROM users WHERE age > ?",
                "params": [25],
                "type": "select"
            }
        )
        
        query_response = await client.send_message_async(query_message)
        if query_response.success:
            rows = query_response.data.get('rows', [])
            count = query_response.data.get('count', 0)
            logger.info(f"Resultados de la consulta: {count}")
            
            for row in rows:
                logger.info(f"  • ID: {row['id']}, Nombre: {row['name']}, Edad: {row['age']}")
        else:
            logger.error(f"✗ Error: {query_response.error.message}")
        
        # 12. Obtener el esquema de la tabla
        print_section_header("ESQUEMA DE TABLA")
        schema_message = MCPMessage(
            action=MCPAction.SCHEMA,
            resource_type="table",
            resource_path="/users"
        )
        
        schema_response = await client.send_message_async(schema_message)
        if schema_response.success:
            schema = schema_response.data
            logger.info(f"Esquema de la tabla: {schema['name']}")
            logger.info("Columnas:")
            
            for column in schema['columns']:
                pk = "PK" if column['pk'] else ""
                null = "NOT NULL" if column['notnull'] else "NULL"
                default = f"DEFAULT {column['default_value']}" if column['default_value'] else ""
                logger.info(f"  • {column['name']} ({column['type']}) {pk} {null} {default}")
        else:
            logger.error(f"✗ Error: {schema_response.error.message}")
        
        # 13. Eliminar un registro
        print_section_header("ELIMINAR REGISTRO")
        delete_message = MCPMessage(
            action=MCPAction.DELETE,
            resource_type="record",
            resource_path="/users",
            data={"id": 3}
        )
        
        delete_response = await client.send_message_async(delete_message)
        if delete_response.success:
            logger.info(f"✓ Registro eliminado: {delete_response.data.get('message')}")
        else:
            logger.error(f"✗ Error: {delete_response.error.message}")
        
        # 14. Verificar la eliminación listando todos los registros
        print_section_header("VERIFICAR ELIMINACIÓN")
        verify_response = await client.list_resources_async("table", "/users")
        if verify_response.success:
            users = verify_response.data.get('items', [])
            total = verify_response.data.get('total', 0)
            logger.info(f"Total de usuarios después de eliminar: {total}")
            
            for user in users:
                logger.info(f"  • ID: {user['id']}, Nombre: {user['name']}")
        else:
            logger.error(f"✗ Error: {verify_response.error.message}")
        
    except Exception as e:
        logger.error(f"Error en el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cerrar la conexión del cliente
        client.disconnect()
        logger.info("Cliente desconectado del servidor")
        
        # Cerrar la conexión de la base de datos
        await server.close()
        logger.info("Conexión a la base de datos cerrada")

if __name__ == "__main__":
    try:
        # Ejecutar el ejemplo con asyncio
        asyncio.run(run_example())
    except KeyboardInterrupt:
        logger.info("Ejemplo interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error ejecutando el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc() 