#!/usr/bin/env python
"""
Ejemplo de uso del cliente HTTP MCP para conectarse al servidor MCP de Brave Search.

Este script muestra cómo configurar y utilizar un cliente HTTP para acceder
al servidor Brave Search MCP, que proporciona capacidades de búsqueda web y local.

Para ejecutar este ejemplo:
1. Primero asegúrate de tener una API key de Brave Search (https://brave.com/search/api/)
2. Configura la API key usando la variable de entorno BRAVE_API_KEY o pásala con --api-key
3. Ejecuta el script con: python mcp_http_client_example.py --query "tu consulta"

Ejemplo:
    python mcp_http_client_example.py --query "restaurantes en Madrid" --search-type local
    python mcp_http_client_example.py --query "inteligencia artificial" --search-type web
"""

import os
import sys
import logging
import argparse
import json
import time
from dotenv import load_dotenv

# Agregar el directorio padre al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import MCPHttpClient, MCPResource, MCPAction, MCPMessage, MCPResponse, initialize_mcp, shutdown_mcp, get_registry

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mcp_http_example")

def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(description="Cliente HTTP MCP para Brave Search")
    parser.add_argument("--url", help="URL base del servidor MCP", default="https://bravesearch-mcp.brave.com")
    parser.add_argument("--api-key", help="API key para autenticación con Brave Search")
    parser.add_argument("--query", help="Consulta para búsqueda", default="inteligencia artificial")
    parser.add_argument("--search-type", choices=["web", "local"], default="web", 
                        help="Tipo de búsqueda (web o local)")
    parser.add_argument("--count", type=int, default=5, help="Número de resultados (máx. 20)")
    parser.add_argument("--offset", type=int, default=0, help="Desplazamiento para paginación (solo web)")
    args = parser.parse_args()
    
    # Inicializar el subsistema MCP
    initialize_mcp()
    
    # Cargar variables de entorno para API keys
    load_dotenv()
    
    # Usar API key de argumentos o de variables de entorno
    api_key = args.api_key or os.getenv("BRAVE_API_KEY")
    
    if not api_key:
        logger.error("No se ha proporcionado una API key de Brave Search. Use --api-key o defina BRAVE_API_KEY en .env")
        sys.exit(1)
    
    try:
        # Registrar el cliente HTTP para Brave Search
        registry = get_registry()
        http_client = MCPHttpClient(
            base_url=args.url,
            api_key=api_key,
            headers={"User-Agent": "MCP-BraveSearch-Client/1.0"}
        )
        registry.register_client("brave_search_client", http_client)
        
        logger.info(f"Conectando a servidor MCP de Brave Search en {args.url}")
        
        # Conectar al servidor
        if http_client.connect():
            logger.info("Conexión exitosa con el servidor de Brave Search")
            
            # Verificar disponibilidad con ping
            ping_response = http_client.ping()
            if ping_response.success:
                logger.info("Ping al servidor: Exitoso")
            else:
                logger.error(f"Ping al servidor: Fallido - {ping_response.error.message if ping_response.error else 'Error desconocido'}")
                return
            
            # Obtener capacidades del servidor
            try:
                capabilities = http_client.get_capabilities()
                logger.info(f"Capacidades del servidor: {capabilities.data}")
                
                # Verificar si el servidor soporta el tipo de búsqueda elegido
                capabilities_data = capabilities.data
                actions = capabilities_data.get("actions", [])
                resources = capabilities_data.get("resources", [])
                
                # Determinar el tipo de herramienta de búsqueda a usar basado en los argumentos
                search_tool = "brave_web_search" if args.search_type == "web" else "brave_local_search"
                
                # Verificar que soporta la búsqueda
                if "search" in actions:
                    logger.info(f"Realizando búsqueda {args.search_type}: {args.query}")
                    
                    # Construir parámetros específicos según el tipo de búsqueda
                    search_params = {
                        "query": args.query,
                        "count": min(args.count, 20)  # Máximo 20 resultados
                    }
                    
                    # Añadir parámetros específicos para búsqueda web
                    if args.search_type == "web" and args.offset > 0:
                        search_params["offset"] = min(args.offset, 9)  # Máximo offset 9
                    
                    # Realizar búsqueda utilizando el recurso apropiado
                    resource_type = "web_search" if args.search_type == "web" else "local_search"
                    
                    # Crear un mensaje MCP personalizado para la búsqueda
                    search_message = MCPMessage(
                        action=MCPAction.SEARCH,
                        resource_type=resource_type,
                        resource_path="/search",
                        data=search_params
                    )
                    
                    search_response = http_client.send_message(search_message)
                    
                    if search_response.success:
                        logger.info(f"Búsqueda {args.search_type} exitosa")
                        
                        # Imprimir resultados de forma legible
                        results = search_response.data.get("results", [])
                        total = search_response.data.get("total_results", 0)
                        
                        logger.info(f"Se encontraron {total} resultados. Mostrando {len(results)}:")
                        
                        for i, result in enumerate(results, 1):
                            # Formatear la salida según el tipo de búsqueda
                            if args.search_type == "web":
                                print(f"\n[{i}] {result.get('title', 'Sin título')}")
                                print(f"URL: {result.get('url', 'N/A')}")
                                print(f"Descripción: {result.get('description', 'Sin descripción')}")
                            else:  # local
                                print(f"\n[{i}] {result.get('name', 'Sin nombre')}")
                                print(f"Dirección: {result.get('address', 'N/A')}")
                                print(f"Tipo: {result.get('type', 'N/A')}")
                                if "rating" in result:
                                    print(f"Valoración: {result.get('rating', 'N/A')}")
                            
                            print("--------------------")
                        
                    else:
                        logger.error(f"Error en búsqueda: {search_response.error.message if search_response.error else 'Error desconocido'}")
                        
                        # Si la búsqueda local falló, podríamos intentar una búsqueda web como backup
                        if args.search_type == "local" and search_response.error:
                            logger.info("Intentando búsqueda web como fallback...")
                            # Implementar aquí el fallback a búsqueda web
                else:
                    logger.warning(f"El servidor no soporta búsquedas")
                
            except Exception as e:
                logger.error(f"Error obteniendo capacidades: {str(e)}")
        else:
            logger.error("No se pudo conectar al servidor MCP de Brave Search")
    
    except Exception as e:
        logger.exception(f"Error en la ejecución: {str(e)}")
    
    finally:
        # Asegurar la desconexión y limpieza
        if 'http_client' in locals():
            http_client.disconnect()
        
        # Cerrar el subsistema MCP
        shutdown_mcp()
        logger.info("Ejemplo finalizado")

if __name__ == "__main__":
    main() 