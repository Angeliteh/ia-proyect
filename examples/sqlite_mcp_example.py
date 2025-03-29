#!/usr/bin/env python
"""
Ejemplo de uso del servidor MCP para SQLite.

Este script demuestra cómo utilizar el servidor MCP para SQLite
para realizar operaciones de base de datos a través del protocolo MCP.
"""

import os
import sys
import logging
import asyncio
import argparse
import time

# Agregar el directorio padre al path para poder importar los módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Importación directa de los módulos locales
from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
from mcp.core.init import initialize_mcp, async_initialize_mcp, shutdown_mcp, get_registry
from mcp.connectors.http_client import MCPHttpClient
from mcp_servers.sqlite import SQLiteMCPServer, run_http_server

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("sqlite_mcp_example")

async def test_sqlite_server():
    """
    Prueba el servidor SQLite MCP directamente.
    """
    logger.info("Iniciando prueba directa del servidor SQLite MCP")
    
    # Inicializar MCP
    await async_initialize_mcp()
    
    try:
        # Crear servidor SQLite
        db_path = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(db_path, exist_ok=True)
        
        logger.info(f"Usando directorio de bases de datos: {db_path}")
        sqlite_server = SQLiteMCPServer(db_path=db_path)
        
        # Crear base de datos de prueba
        test_db = "test_example.db"
        db_create_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="database",
            resource_path=f"/{test_db}",
            data={"db_name": test_db}
        )
        
        logger.info(f"Creando base de datos {test_db}...")
        db_response = await sqlite_server.process_message(db_create_message)
        
        if db_response.success:
            logger.info(f"Base de datos creada: {db_response.data.get('database')}")
        else:
            if "ya existe" in db_response.error.message:
                logger.info(f"Base de datos {test_db} ya existe, continuando...")
            else:
                logger.error(f"Error creando base de datos: {db_response.error.message}")
                return
        
        # Crear tabla de prueba
        table_name = "users"
        table_create_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="table",
            resource_path=f"/{test_db}/{table_name}",
            data={
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "name", "type": "TEXT", "not_null": True},
                    {"name": "email", "type": "TEXT"},
                    {"name": "age", "type": "INTEGER"}
                ]
            }
        )
        
        logger.info(f"Creando tabla {table_name}...")
        table_response = await sqlite_server.process_message(table_create_message)
        
        if table_response.success:
            logger.info(f"Tabla creada: {table_response.data.get('table')}")
        else:
            if "ya existe" in table_response.error.message:
                logger.info(f"Tabla {table_name} ya existe, continuando...")
            else:
                logger.error(f"Error creando tabla: {table_response.error.message}")
        
        # Insertar datos de prueba
        insert_query = f"""
        INSERT INTO {table_name} (id, name, email, age) VALUES 
        (1, 'Usuario 1', 'user1@example.com', 25),
        (2, 'Usuario 2', 'user2@example.com', 30),
        (3, 'Usuario 3', 'user3@example.com', 35)
        """
        
        insert_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="query",
            resource_path="/query",
            data={
                "db_name": test_db,
                "query": insert_query
            }
        )
        
        logger.info("Insertando datos de prueba...")
        insert_response = await sqlite_server.process_message(insert_message)
        
        if insert_response.success:
            logger.info(f"Datos insertados: {insert_response.data.get('affected_rows')} filas afectadas")
        else:
            logger.error(f"Error insertando datos: {insert_response.error.message}")
        
        # Consultar datos
        select_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type="query",
            resource_path="/query",
            data={
                "db_name": test_db,
                "query": f"SELECT * FROM {table_name}"
            }
        )
        
        logger.info("Consultando datos...")
        select_response = await sqlite_server.process_message(select_message)
        
        if select_response.success:
            results = select_response.data.get("results", [])
            logger.info(f"Se obtuvieron {len(results)} resultados")
            
            print("\n--- Resultados de la consulta ---")
            for row in results:
                print(f"ID: {row['id']}, Nombre: {row['name']}, Email: {row['email']}, Edad: {row['age']}")
        else:
            logger.error(f"Error consultando datos: {select_response.error.message}")
        
        # Obtener información de la tabla
        table_info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type="table",
            resource_path=f"/{test_db}/{table_name}"
        )
        
        logger.info(f"Obteniendo información de la tabla {table_name}...")
        table_info_response = await sqlite_server.process_message(table_info_message)
        
        if table_info_response.success:
            table_info = table_info_response.data
            print("\n--- Información de la tabla ---")
            print(f"Nombre: {table_info.get('name')}")
            print(f"Registros: {table_info.get('row_count')}")
            print("Columnas:")
            for column in table_info.get("columns", []):
                print(f"  - {column.get('name')} ({column.get('type')})")
        else:
            logger.error(f"Error obteniendo información de la tabla: {table_info_response.error.message}")
        
        # Listar bases de datos
        list_db_message = MCPMessage(
            action=MCPAction.LIST,
            resource_type="database",
            resource_path="/"
        )
        
        logger.info("Listando bases de datos...")
        list_db_response = await sqlite_server.process_message(list_db_message)
        
        if list_db_response.success:
            databases = list_db_response.data.get("databases", [])
            print("\n--- Bases de datos disponibles ---")
            for db in databases:
                print(f"Nombre: {db.get('name')}, Tamaño: {db.get('size_mb')} MB")
        else:
            logger.error(f"Error listando bases de datos: {list_db_response.error.message}")
        
    except Exception as e:
        logger.error(f"Error en la prueba: {e}")
    
    finally:
        # Limpiar
        try:
            await shutdown_mcp()
        except:
            pass  # Ignora errores durante el cierre
        logger.info("Prueba finalizada")

async def test_sqlite_http():
    """
    Prueba el servidor SQLite MCP a través de HTTP.
    """
    logger.info("Iniciando prueba del servidor SQLite MCP a través de HTTP")
    
    # Inicializar MCP
    await async_initialize_mcp()
    
    # Iniciar servidor HTTP
    db_path = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(db_path, exist_ok=True)
    
    logger.info(f"Usando directorio de bases de datos: {db_path}")
    http_server, _ = run_http_server(host="localhost", port=8081, db_path=db_path)
    
    try:
        # Esperar a que el servidor esté listo
        time.sleep(1)
        
        # Crear cliente HTTP
        client = MCPHttpClient(base_url="http://localhost:8081")
        success = client.connect()
        
        if not success:
            logger.error("No se pudo conectar al servidor HTTP")
            return
        
        # Verificar disponibilidad con ping
        logger.info("Enviando ping al servidor...")
        ping_response = client.ping()  # Esto devuelve un MCPResponse, no necesita await
        
        if ping_response.success:
            logger.info("Ping exitoso")
        else:
            logger.error(f"Error en ping: {ping_response.error.message}")
            return
        
        # Obtener capacidades
        logger.info("Obteniendo capacidades del servidor...")
        cap_response = client.get_capabilities()
        
        if cap_response.success:
            actions = cap_response.data.get("actions", [])
            resources = cap_response.data.get("resources", [])
            logger.info(f"Capacidades obtenidas: {len(actions)} acciones, {len(resources)} recursos")
        else:
            logger.error(f"Error obteniendo capacidades: {cap_response.error.message}")
        
        # Listar bases de datos
        logger.info("Listando bases de datos...")
        list_message = MCPMessage(
            action=MCPAction.LIST,
            resource_type="database",
            resource_path="/"
        )
        
        list_response = client.send_message(list_message)
        
        if list_response.success:
            databases = list_response.data.get("databases", [])
            print("\n--- Bases de datos disponibles ---")
            for db in databases:
                print(f"Nombre: {db.get('name')}, Tamaño: {db.get('size_mb')} MB")
        else:
            logger.error(f"Error listando bases de datos: {list_response.error.message}")
        
        # Consultar datos de ejemplo
        db_name = "test_example.db"
        logger.info(f"Consultando datos de la base de datos {db_name}...")
        
        search_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type="query",
            resource_path="/query",
            data={
                "db_name": db_name,
                "query": "SELECT * FROM users WHERE age > ?",
                "params": [25]
            }
        )
        
        search_response = client.send_message(search_message)
        
        if search_response.success:
            results = search_response.data.get("results", [])
            logger.info(f"Se obtuvieron {len(results)} resultados")
            
            print("\n--- Resultados de la consulta (age > 25) ---")
            for row in results:
                print(f"ID: {row['id']}, Nombre: {row['name']}, Email: {row['email']}, Edad: {row['age']}")
        else:
            logger.error(f"Error consultando datos: {search_response.error.message}")
        
    except Exception as e:
        logger.error(f"Error en la prueba HTTP: {e}")
    
    finally:
        # Limpiar
        if 'client' in locals():
            client.disconnect()
        
        # Detener el servidor HTTP
        http_server.shutdown()
        http_server.server_close()
        
        # Cerrar MCP
        try:
            await shutdown_mcp()
        except:
            pass  # Ignora errores durante el cierre
        logger.info("Prueba HTTP finalizada")

async def main():
    """Función principal del ejemplo."""
    # Configurar argumentos
    parser = argparse.ArgumentParser(description="Ejemplo de servidor MCP para SQLite")
    parser.add_argument("--mode", choices=["direct", "http", "both"], default="both",
                      help="Modo de prueba: direct (servidor directo), http (servidor HTTP), both (ambos)")
    args = parser.parse_args()
    
    # Ejecutar pruebas según el modo seleccionado
    if args.mode in ["direct", "both"]:
        await test_sqlite_server()
    
    if args.mode in ["http", "both"]:
        # Esperar un poco si se ejecutaron ambas pruebas
        if args.mode == "both":
            time.sleep(1)
        await test_sqlite_http()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")
    except Exception as e:
        print(f"Error en la aplicación: {e}") 