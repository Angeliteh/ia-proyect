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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar componentes MCP
from mcp.core.protocol import MCPMessage
from mcp_servers.brave_search_server import BraveSearchMCPServer

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
    
    logging.info(f"Respuesta: status={response.status}, error={response.error}")
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
    
    logging.info(f"Respuesta: status={response.status}, error={response.error}")
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
    
    logging.info(f"Respuesta: status={response.status}, error={response.error}")
    if response.status == "error":
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
    
    logging.info(f"Respuesta: status={response.status}, error={response.error}")
    if response.status == "error":
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
    args = parser.parse_args()
    
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