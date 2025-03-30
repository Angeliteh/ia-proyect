#!/usr/bin/env python
"""
Ejemplo de uso del servidor MCP para SQLite

Este script muestra cómo implementar y usar un servidor MCP para
interactuar con bases de datos SQLite a través del protocolo MCP.
"""

import os
import sys
import logging
import asyncio
import argparse
import json
import sqlite3
import tempfile
import time

# Agregar el directorio raíz del proyecto al path para poder importar los módulos
# Ajustamos para manejar la nueva estructura de ejemplos
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/mcp
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

try:
    # Intentar importar los módulos desde el paquete completo
    from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
    from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
    from mcp.connectors.http_client import MCPHttpClient
    from mcp_servers.sqlite.sqlite_server import SQLiteMCPServer, run_http_server
    
    # Alias para compatibilidad
    async def async_initialize_mcp():
        """Inicializa el MCP de forma asíncrona."""
        return initialize_mcp()
    
    print("Módulos MCP importados correctamente desde paquete instalado")
except ImportError as e:
    print(f"Error al importar módulos MCP desde paquete instalado: {e}")
    print("Intentando importación alternativa...")
    
    try:
        # Importación alternativa creando un sistema de módulos mock para el ejemplo
        # Esto permite ejecutar el ejemplo sin necesidad de tener el paquete instalado
        class MockMCP:
            class Protocol:
                class MCPMessage:
                    def __init__(self, action=None, resource_type=None, resource_path=None, data=None):
                        self.action = action
                        self.resource_type = resource_type
                        self.resource_path = resource_path
                        self.data = data
                
                class MCPResponse:
                    def __init__(self, success=True, data=None, error=None):
                        self.success = success
                        self.data = data or {}
                        self.error = error
                
                class MCPAction:
                    GET = "get"
                    LIST = "list"
                    SEARCH = "search"
                    CREATE = "create"
                    UPDATE = "update"
                    DELETE = "delete"
                    QUERY = "query"
                
                class MCPResource:
                    DATABASE = "database"
                    TABLE = "table"
                    SYSTEM = "system"
            
            class Client:
                class MCPHttpClient:
                    def __init__(self, base_url, headers=None):
                        self.base_url = base_url
                        self.headers = headers or {}
                    
                    def connect(self):
                        # En un ejemplo real, esto conectaría con el servidor
                        print(f"Conectando a {self.base_url}...")
                        return True
                    
                    def disconnect(self):
                        # En un ejemplo real, esto desconectaría del servidor
                        print("Desconectando...")
                    
                    def ping(self):
                        # Simulación de ping
                        return MockMCP.Protocol.MCPResponse(success=True)
                    
                    def get_capabilities(self):
                        # Simulación de capabilities
                        return MockMCP.Protocol.MCPResponse(success=True, data={
                            "actions": ["get", "list", "search", "create", "update", "delete", "query"],
                            "resources": ["database", "table"]
                        })
                    
                    def send_message(self, message):
                        # Simulación de envío de mensaje
                        return MockMCP.Protocol.MCPResponse(success=True, data={
                            "result": "Simulación de operación SQLite"
                        })
        
        # Usar la implementación mock para el ejemplo
        MCPMessage = MockMCP.Protocol.MCPMessage
        MCPResponse = MockMCP.Protocol.MCPResponse
        MCPAction = MockMCP.Protocol.MCPAction
        MCPResource = MockMCP.Protocol.MCPResource
        MCPHttpClient = MockMCP.Client.MCPHttpClient
        
        # Funciones mock para initialize_mcp, shutdown_mcp y get_registry
        async def initialize_mcp():
            print("Inicializando MCP mock...")
            return True
        
        async def shutdown_mcp():
            print("Cerrando MCP mock...")
            return True
        
        def get_registry():
            class Registry:
                def register_client(self, name, client):
                    pass
            return Registry()
        
        # Implementación simple de SQLiteMCPServer para el ejemplo
        class SQLiteMCPServer:
            def __init__(self, db_path):
                self.db_path = db_path
                self.connection = sqlite3.connect(db_path)
                print(f"Servidor SQLite inicializado con base de datos: {db_path}")
            
            def handle_action(self, message):
                # Simulación simplificada para el ejemplo
                if message.action == MockMCP.Protocol.MCPAction.QUERY:
                    return MockMCP.Protocol.MCPResponse(success=True, data={
                        "columns": ["id", "name"],
                        "rows": [
                            [1, "Ejemplo 1"],
                            [2, "Ejemplo 2"]
                        ],
                        "row_count": 2
                    })
                return MockMCP.Protocol.MCPResponse(success=True, data={"result": "ok"})
        
        def run_http_server(host, port, db_path):
            print(f"Iniciando servidor mock en {host}:{port} (simulación)")
            return None, SQLiteMCPServer(db_path)
            
        print("Usando implementación mock para demostración")
    except Exception as mock_error:
        print(f"Error al crear mock: {mock_error}")
        print("No se pueden importar los módulos necesarios. Asegúrate de que el proyecto esté configurado correctamente.")
        sys.exit(1)

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
    parser.add_argument("--check-real-modules", action="store_true",
                      help="Verificar si se están usando módulos reales")
    args = parser.parse_args()
    
    # Verificar si se están usando módulos reales
    if args.check_real_modules:
        try:
            from mcp.core.protocol import MCPMessage
            print("USING_REAL_MODULES = True")
            return
        except ImportError:
            print("USING_REAL_MODULES = False")
            return
    
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