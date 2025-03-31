"""
Ejemplo simplificado del protocolo MCP (Model Context Protocol).

Este ejemplo demuestra:
1. Cómo implementar un servidor MCP simple (EchoServer)
2. Cómo implementar un cliente MCP simple (SimpleDirectClient)
3. Cómo establecer comunicación cliente-servidor
4. Cómo realizar operaciones básicas del protocolo
"""

import asyncio
import logging
import sys
import os
import uuid
from typing import Dict, Any, Optional

# Aseguramos que el directorio raíz del proyecto esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Importamos los componentes del MCP
try:
    # Clases base y del protocolo
    from mcp import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPError, MCPErrorCode
    
    # Implementaciones específicas
    from mcp.servers import EchoServer
    from mcp.clients import SimpleDirectClient
except ImportError as e:
    print(f"Error al importar módulos MCP: {e}")
    print(f"Ruta de búsqueda actual: {sys.path}")
    sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("mcp_example")

# --------------------- FUNCIÓN PRINCIPAL DE DEMO -----------------------

def run_demo():
    """Ejecuta una demostración de las funcionalidades básicas de MCP."""
    
    logger.info("Iniciando demostración de MCP...")
    
    # Creamos el servidor
    server = EchoServer()
    logger.info(f"Servidor creado: {server.name}")
    
    # Creamos el cliente
    client = SimpleDirectClient(server)
    
    try:
        # Establecemos conexión
        client.connect()
        
        # 1. Enviamos un ping para verificar la conexión
        logger.info("\n--- PING ---")
        ping_message = MCPMessage.create_ping()
        ping_response = client.send_message(ping_message)
        print(f"Ping respuesta: {ping_response.success} - {ping_response.data}")
        
        # 2. Obtenemos las capacidades del servidor
        logger.info("\n--- CAPACIDADES ---")
        capabilities = client.get_capabilities()
        print(f"Servidor: {capabilities['name']}")
        print(f"Descripción: {capabilities['description']}")
        print(f"Acciones soportadas: {capabilities['supported_actions']}")
        print(f"Recursos soportados: {capabilities['supported_resources']}")
        
        # 3. Obtenemos un recurso específico
        logger.info("\n--- GET ---")
        get_response = client.get_resource("test", "/test1")
        if get_response.success:
            print(f"Recurso obtenido: {get_response.data}")
        else:
            print(f"Error: {get_response.error.message}")
            
        # 4. Listamos recursos
        logger.info("\n--- LIST ---")
        list_response = client.list_resources("test", "/")
        if list_response.success:
            print(f"Recursos listados: {list_response.data}")
        else:
            print(f"Error: {list_response.error.message}")
            
        # 5. Buscamos recursos
        logger.info("\n--- SEARCH ---")
        search_response = client.search_resources("test", "Hello")
        if search_response.success:
            print(f"Resultados de búsqueda: {search_response.data}")
        else:
            print(f"Error: {search_response.error.message}")
            
        # 6. Enviamos un mensaje de eco personalizado
        logger.info("\n--- ECHO PERSONALIZADO ---")
        echo_response = client.send_echo(
            {"message": "Hola, servidor!", "timestamp": "2023-01-01"}
        )
        if echo_response.success:
            print(f"Eco recibido: {echo_response.data}")
        else:
            print(f"Error: {echo_response.error.message}")
            
        # 7. Intentamos una operación no soportada
        logger.info("\n--- OPERACIÓN NO SOPORTADA ---")
        unsupported_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="test",
            resource_path="/new",
            data={"value": "New item"}
        )
        unsupported_response = client.send_message(unsupported_message)
        if not unsupported_response.success:
            print(f"Error esperado: {unsupported_response.error.message}")
            
    except Exception as e:
        logger.error(f"Error en la demo: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Desconectamos el cliente
        client.disconnect()
        logger.info("Demo finalizada")

if __name__ == "__main__":
    run_demo()
