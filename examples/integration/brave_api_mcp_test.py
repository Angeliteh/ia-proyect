#!/usr/bin/env python
"""
Script simplificado para probar el servidor MCP de Brave Search.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Añadir directorio raíz al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))  # integration/
example_dir = os.path.dirname(current_dir)  # examples/
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

# Intentar importar componentes MCP
try:
    from mcp.core.protocol import MCPMessage
    from mcp_servers.brave_search_server import BraveSearchMCPServer
    
    logging.info("Módulos MCP importados correctamente")
except ImportError as e:
    logging.error(f"Error al importar módulos MCP: {e}")
    logging.info("Intentando importación alternativa...")
    
    try:
        # Implementación mínima para pruebas
        class MCPMessage:
            def __init__(self, message_id=None, action=None, resource_type=None, resource_path=None, data=None):
                self.message_id = message_id
                self.action = action
                self.resource_type = resource_type
                self.resource_path = resource_path
                self.data = data or {}
        
        class MCPResponse:
            def __init__(self, success=True, data=None, error=None):
                self.success = success
                self.data = data or {}
                self.error = error
        
        # Intentar importar el servidor de Brave Search
        try:
            # Usamos la ruta correcta para importar desde mcp_servers
            from mcp_servers.brave_search_server import BraveSearchMCPServer
            logging.info("Servidor Brave Search importado correctamente")
        except ImportError:
            # Implementación mock del servidor para demostración
            class BraveSearchMCPServer:
                def __init__(self, api_key=None):
                    self.api_key = api_key
                    self.logger = logging.getLogger("brave_search_mock")
                
                def handle_action(self, message):
                    """Maneja las acciones del protocolo MCP."""
                    if message.action == "ping":
                        return MCPResponse(success=True, data={"status": "ok"})
                    elif message.action == "capabilities":
                        return MCPResponse(success=True, data={
                            "actions": ["ping", "capabilities", "search"],
                            "resources": ["web_search", "local_search"]
                        })
                    elif message.action == "search":
                        resource_type = message.resource_type
                        query = message.data.get("query", "")
                        count = message.data.get("count", 3)
                        
                        if resource_type == "web_search":
                            return MCPResponse(success=True, data={
                                "results": [
                                    {"title": f"Resultado web 1 para '{query}'", "url": "https://example.com/1", "description": "Descripción de ejemplo 1"},
                                    {"title": f"Resultado web 2 para '{query}'", "url": "https://example.com/2", "description": "Descripción de ejemplo 2"},
                                ],
                                "count": 2
                            })
                        elif resource_type == "local_search":
                            return MCPResponse(success=True, data={
                                "results": [
                                    {"name": f"Local 1 cerca de '{query}'", "address": "Dirección 1", "rating": 4.5},
                                    {"name": f"Local 2 cerca de '{query}'", "address": "Dirección 2", "rating": 4.0},
                                ],
                                "count": 2
                            })
                        
                        return MCPResponse(success=False, error={"message": f"Tipo de recurso no soportado: {resource_type}"})
            
            logging.warning("Usando implementación MOCK del servidor Brave Search para demostración")
        
        logging.info("Usando implementación mínima para pruebas")
    except Exception as mock_error:
        logging.error(f"Error al crear mock: {mock_error}")
        logging.error("No se pueden importar los módulos necesarios. Asegúrate de que el proyecto esté configurado correctamente.")
        sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('brave_mcp_test.log'),
        logging.StreamHandler()
    ]
)

def test_ping(server):
    """Prueba la acción PING."""
    logging.info("=== Prueba PING ===")
    
    message = MCPMessage(
        message_id="test-ping-1",
        action="ping",
        resource_type="system",
        resource_path="/",
        data={}
    )
    
    response = server.handle_action(message)
    
    logging.info(f"Respuesta: success={response.success}, error={response.error}")
    if response.data:
        logging.info(f"Datos: {response.data}")
    
    return response

def test_capabilities(server):
    """Prueba la acción CAPABILITIES."""
    logging.info("\n=== Prueba CAPABILITIES ===")
    
    message = MCPMessage(
        message_id="test-capabilities-1",
        action="capabilities",
        resource_type="system",
        resource_path="/",
        data={}
    )
    
    response = server.handle_action(message)
    
    logging.info(f"Respuesta: success={response.success}, error={response.error}")
    if response.data:
        logging.info(f"Capacidades: {response.data}")
    
    return response

def test_web_search(server, query="inteligencia artificial", count=5):
    """Prueba la acción SEARCH para búsqueda web."""
    logging.info(f"\n=== Prueba WEB SEARCH: '{query}' ===")
    
    message = MCPMessage(
        message_id="test-web-search-1",
        action="search",
        resource_type="web_search",
        resource_path="/web",
        data={
            "resource_type": "web_search",
            "query": query,
            "count": count,
            "search_lang": "es",
            "country": "ES"
        }
    )
    
    response = server.handle_action(message)
    
    logging.info(f"Respuesta: success={response.success}, error={response.error}")
    if not response.success:
        logging.error(f"Error en búsqueda web: {response.error}")
    elif response.data:
        count = response.data.get("count", 0)
        logging.info(f"Resultados encontrados: {count}")
        
        # Mostrar primeros resultados
        results = response.data.get("results", [])
        for i, item in enumerate(results[:3], 1):
            logging.info(f"Resultado {i}:")
            logging.info(f"  Título: {item.get('title', 'N/A')}")
            logging.info(f"  URL: {item.get('url', 'N/A')}")
            logging.info(f"  Descripción: {item.get('description', 'N/A')[:100]}...")
    
    return response

def test_local_search(server, query="restaurantes en Madrid", count=5):
    """Prueba la acción SEARCH para búsqueda local."""
    logging.info(f"\n=== Prueba LOCAL SEARCH: '{query}' ===")
    
    message = MCPMessage(
        message_id="test-local-search-1",
        action="search",
        resource_type="local_search",
        resource_path="/local",
        data={
            "resource_type": "local_search",
            "query": query,
            "count": count,
            "search_lang": "es",
            "country": "ES",
            "use_fallback": True
        }
    )
    
    response = server.handle_action(message)
    
    logging.info(f"Respuesta: success={response.success}, error={response.error}")
    if not response.success:
        logging.error(f"Error en búsqueda local: {response.error}")
    elif response.data:
        count = response.data.get("count", 0)
        is_fallback = response.data.get("is_fallback", False)
        
        if is_fallback:
            logging.info(f"Se usó fallback a búsqueda web. Resultados: {count}")
        else:
            logging.info(f"Resultados locales encontrados: {count}")
        
        # Mostrar primeros resultados
        results = response.data.get("results", [])
        for i, item in enumerate(results[:3], 1):
            if is_fallback:
                logging.info(f"Resultado web {i}:")
                logging.info(f"  Título: {item.get('title', 'N/A')}")
                logging.info(f"  URL: {item.get('url', 'N/A')}")
            else:
                logging.info(f"Resultado local {i}:")
                logging.info(f"  Nombre: {item.get('name', 'N/A')}")
                logging.info(f"  Dirección: {item.get('address', 'N/A')}")
                if "rating" in item:
                    logging.info(f"  Valoración: {item['rating']}")
                if "distance" in item:
                    logging.info(f"  Distancia: {item['distance']} km")
    
    return response

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Prueba del servidor MCP de Brave Search")
    parser.add_argument("--api-key", help="API key para Brave Search")
    parser.add_argument("--test", choices=["ping", "capabilities", "web", "local", "all"], 
                      default="all", help="Tipo de prueba a realizar")
    parser.add_argument("--query-web", default="inteligencia artificial",
                      help="Consulta para búsqueda web")
    parser.add_argument("--query-local", default="restaurantes en Madrid",
                      help="Consulta para búsqueda local")
    parser.add_argument("--check-real-modules", action="store_true",
                       help="Verificar si se están usando módulos reales")
    args = parser.parse_args()
    
    # Verificar si estamos usando módulos reales
    if args.check_real_modules:
        try:
            # Intentar una importación específica del paquete mcp_servers
            # que nos diga si estamos usando los módulos reales o no
            from mcp.core.protocol import MCPMessage
            from mcp_servers.brave_search_server import BraveSearchMCPServer
            print("USING_REAL_MODULES = True")
            return
        except ImportError:
            print("USING_REAL_MODULES = False")
            return
    
    # Cargar variables de entorno para API keys
    load_dotenv()
    
    # Obtener API key de argumentos o variables de entorno
    api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    
    if not api_key:
        logging.error("No se ha proporcionado una API key para Brave Search. Use --api-key o defina BRAVE_API_KEY")
        sys.exit(1)
    
    logging.info("=== INICIANDO PRUEBA DE MCP BRAVE SEARCH ===")
    logging.info(f"API Key (primeros 4 caracteres): {api_key[:4]}...")
    
    # Crear servidor MCP
    server = BraveSearchMCPServer(api_key=api_key)
    
    # Ejecutar pruebas según lo solicitado
    if args.test in ["ping", "all"]:
        test_ping(server)
    
    if args.test in ["capabilities", "all"]:
        test_capabilities(server)
    
    if args.test in ["web", "all"]:
        test_web_search(server, args.query_web)
    
    if args.test in ["local", "all"]:
        test_local_search(server, args.query_local)
    
    logging.info("\n=== PRUEBA FINALIZADA ===")

if __name__ == "__main__":
    main() 