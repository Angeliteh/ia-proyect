#!/usr/bin/env python
"""
Ejemplo de uso del servidor MCP para Brave Search API.

Este script inicia el servidor MCP para Brave Search y prueba realizar búsquedas web y locales
utilizando la API real de Brave Search.

Para ejecutar este ejemplo:
1. Primero asegúrate de tener una API key de Brave Search (https://brave.com/search/api/)
2. Configura la API key usando la variable de entorno BRAVE_API_KEY o pásala con --api-key
3. Ejecuta el script con: python brave_search_server_example.py

Ejemplos:
    python brave_search_server_example.py --test-search web --query "inteligencia artificial"
    python brave_search_server_example.py --test-search local --query "restaurantes en Madrid"
"""

import os
import sys
import logging
import argparse
import time
import asyncio
from dotenv import load_dotenv

# Agregar el directorio raíz del proyecto al path para poder importar los módulos
# Ajustamos para manejar la nueva estructura de ejemplos
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/mcp
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

# Importar los módulos desde el paquete completo
try:
    from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
    from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
    from mcp.connectors.http_client import MCPHttpClient
    from mcp_servers.brave_search_server import BraveSearchMCPServer, run_http_server
    
    print("Módulos MCP importados correctamente desde paquete instalado")
except ImportError as e:
    print(f"Error al importar módulos MCP: {e}")
    print("\nPara solucionar este problema:")
    print("1. Asegúrate de que los módulos MCP estén instalados o en tu PYTHONPATH")
    print("2. Verifica que la estructura del proyecto sea correcta")
    print("3. Instala las dependencias necesarias con 'pip install -r requirements.txt'")
    print("\nEl ejemplo requiere la implementación real de MCP. No se utilizan mocks.")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("brave_search_server_example")

async def test_server_with_client(url, query, search_type, count=5, offset=0):
    """
    Prueba el servidor MCP para Brave Search utilizando un cliente HTTP.
    
    Args:
        url: URL del servidor MCP
        query: Consulta de búsqueda
        search_type: Tipo de búsqueda (web o local)
        count: Número de resultados a mostrar
        offset: Offset para paginación (solo web)
    """
    # Inicializar el subsistema MCP
    initialize_mcp()
    
    try:
        # Crear y registrar un cliente HTTP para conectar con el servidor
        registry = get_registry()
        client = MCPHttpClient(
            base_url=url,
            headers={"User-Agent": "MCP-BraveSearch-Test/1.0"}
        )
        registry.register_client("test_client", client)
        
        logger.info(f"Conectando a servidor MCP de Brave Search en {url}")
        
        # Conectar al servidor
        if client.connect():
            logger.info("Conexión exitosa al servidor MCP")
            
            # Verificar disponibilidad con ping
            ping_response = client.ping()
            if ping_response.success:
                logger.info("Ping al servidor: Exitoso")
            else:
                logger.error(f"Ping al servidor: Fallido - {ping_response.error.message if ping_response.error else 'Error desconocido'}")
                return
            
            # Obtener capacidades del servidor
            try:
                capabilities = client.get_capabilities()
                if capabilities.success:
                    logger.info("Capacidades del servidor obtenidas correctamente")
                    logger.info(f"Acciones soportadas: {capabilities.data.get('actions', [])}")
                    logger.info(f"Recursos soportados: {capabilities.data.get('resources', [])}")
                else:
                    logger.error(f"Error obteniendo capacidades: {capabilities.error.message if capabilities.error else 'Error desconocido'}")
                    return
                
                # Determinar el tipo de recurso según el tipo de búsqueda
                resource_type = "web_search" if search_type == "web" else "local_search"
                
                # Realizar búsqueda
                logger.info(f"Realizando búsqueda {search_type}: '{query}'")
                
                # Construir parámetros específicos según el tipo de búsqueda
                search_params = {
                    "query": query,
                    "count": count,
                    "resource_type": resource_type
                }
                
                # Añadir parámetros específicos para búsqueda web
                if search_type == "web" and offset > 0:
                    search_params["offset"] = offset
                
                # Crear mensaje para búsqueda
                search_message = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type=MCPResource.SYSTEM,
                    resource_path=f"/search/{resource_type}",
                    data=search_params
                )
                
                # Enviar solicitud de búsqueda
                search_response = client.send_message(search_message)
                
                if search_response.success:
                    logger.info(f"Búsqueda {search_type} exitosa")
                    
                    # Procesar y mostrar resultados
                    results = search_response.data.get("results", [])
                    total = search_response.data.get("total_results", 0)
                    
                    logger.info(f"Se encontraron {total} resultados. Mostrando {len(results)}:")
                    
                    for i, result in enumerate(results, 1):
                        # Formatear la salida según el tipo de búsqueda
                        if "title" in result:  # Resultado web
                            print(f"\n[{i}] {result.get('title', 'Sin título')}")
                            print(f"URL: {result.get('url', 'N/A')}")
                            print(f"Descripción: {result.get('description', 'Sin descripción')}")
                        elif "name" in result:  # Resultado local
                            if result.get("type") == "fallback_notice":
                                print(f"\n--- {result.get('name')} ---")
                            else:
                                print(f"\n[{i}] {result.get('name', 'Sin nombre')}")
                                print(f"Dirección: {result.get('address', 'N/A')}")
                                print(f"Tipo: {result.get('type', 'N/A')}")
                                if "rating" in result:
                                    print(f"Valoración: {result.get('rating', 'N/A')}")
                                if "distance" in result:
                                    print(f"Distancia: {result.get('distance', 'N/A')}")
                        
                        print("-" * 50)
                else:
                    logger.error(f"Error en búsqueda: {search_response.error.message if search_response.error else 'Error desconocido'}")
            
            except Exception as e:
                logger.error(f"Error inesperado: {str(e)}")
        else:
            logger.error("No se pudo conectar al servidor MCP")
    
    except Exception as e:
        logger.exception(f"Error en la ejecución: {str(e)}")
    
    finally:
        # Asegurar la desconexión y limpieza
        if 'client' in locals():
            client.disconnect()
        
        # Cerrar el subsistema MCP
        await shutdown_mcp()
        logger.info("Prueba finalizada")

async def main():
    """Función principal asíncrona del ejemplo."""
    parser = argparse.ArgumentParser(description="Ejemplo de servidor MCP para Brave Search API")
    parser.add_argument("--host", default="localhost", help="Host en el que escuchar")
    parser.add_argument("--port", type=int, default=8080, help="Puerto en el que escuchar")
    parser.add_argument("--api-key", help="Clave API para Brave Search")
    parser.add_argument("--test-search", choices=["web", "local"], help="Realizar una búsqueda de prueba")
    parser.add_argument("--query", default="inteligencia artificial", help="Consulta para la búsqueda de prueba")
    parser.add_argument("--count", type=int, default=5, help="Número de resultados a mostrar")
    parser.add_argument("--offset", type=int, default=0, help="Offset para paginación (solo web)")
    parser.add_argument("--auto-exit", action="store_true", help="Salir automáticamente después de un tiempo")
    args = parser.parse_args()
    
    # Cargar variables de entorno para API keys
    load_dotenv()
    
    # Obtener API key de argumentos o variables de entorno
    api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    
    if not api_key:
        logger.error("No se ha proporcionado una API key para Brave Search. Use --api-key o defina BRAVE_API_KEY en .env")
        sys.exit(1)
    
    # Iniciar el servidor MCP
    logger.info("Iniciando servidor MCP para Brave Search...")
    http_server, brave_server = run_http_server(args.host, args.port, api_key)
    logger.info(f"Servidor iniciado en http://{args.host}:{args.port}")
    
    try:
        # Si se solicita una búsqueda de prueba, ejecutarla
        if args.test_search:
            logger.info(f"Ejecutando búsqueda de prueba: {args.test_search}")
            # Dar tiempo al servidor para inicializarse completamente
            time.sleep(1)
            await test_server_with_client(
                url=f"http://{args.host}:{args.port}",
                query=args.query,
                search_type=args.test_search,
                count=args.count,
                offset=args.offset
            )
            # Terminar después de la prueba
            return
        
        # Detectar si estamos en un entorno de prueba
        is_test_environment = args.auto_exit or "PYTEST_CURRENT_TEST" in os.environ or "TEST_ENV" in os.environ
        
        if is_test_environment:
            # En entorno de prueba, ejecutar por tiempo limitado
            logger.info("Ejecutando en modo prueba. El servidor se detendrá automáticamente en 5 segundos.")
            timeout = 5
            
            # Esperar un tiempo corto
            for i in range(timeout):
                time.sleep(1)
                remaining = timeout - i - 1
                if remaining > 0:
                    logger.info(f"Cerrando en {remaining} segundos...")
                
            logger.info("Tiempo de prueba completado. Cerrando servidor...")
            return
        else:
            # Si no hay búsqueda de prueba ni estamos en modo prueba, mantener el servidor en ejecución
            logger.info("Servidor MCP de Brave Search en ejecución. Presiona Ctrl+C para detener.")
            while True:
                time.sleep(1)
    
    except KeyboardInterrupt:
        # Manejar Ctrl+C para detener el servidor
        logger.info("Deteniendo servidor...")
    
    finally:
        # Asegurar que el servidor se detenga correctamente
        if 'http_server' in locals():
            http_server.shutdown()
            http_server.server_close()
            logger.info("Servidor detenido")

if __name__ == "__main__":
    # Ejecutar función asíncrona principal
    asyncio.run(main()) 