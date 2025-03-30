#!/usr/bin/env python
"""
Ejemplo de uso del cliente MCP para Brave Search API.

Este script utiliza un cliente MCP para conectarse a un servidor MCP de Brave Search
y realizar búsquedas web y locales.

Para ejecutar este ejemplo:
1. Primero asegúrate de tener el servidor MCP de Brave Search en ejecución
2. Ejecuta el script con: python brave_search_client_example.py

Ejemplos:
    python brave_search_client_example.py --query "inteligencia artificial" --count 3
    python brave_search_client_example.py --search-type local --query "restaurantes en Madrid"
"""

import os
import sys
import logging
import asyncio
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Agregar el directorio raíz del proyecto al path para poder importar los módulos
# Ajustamos para manejar la nueva estructura de ejemplos
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/mcp
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

# Importar los módulos MCP reales
try:
    from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
    from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
    from mcp.connectors.http_client import MCPHttpClient
    
    print("Módulos MCP importados correctamente desde paquete instalado")
except ImportError as e:
    print(f"Error al importar módulos MCP: {e}")
    print("\nPara solucionar este problema:")
    print("1. Asegúrate de que los módulos MCP estén instalados o en tu PYTHONPATH")
    print("2. Verifica que la estructura del proyecto sea correcta")
    print("3. Instala las dependencias necesarias con 'pip install -r requirements.txt'")
    print("\nEl ejemplo requiere la implementación real de MCP. No se utilizan mocks para el protocolo.")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("brave_search_client_example")

# Crear un servidor HTTP simple para simular Brave Search MCP
class BraveSearchMockHandler(BaseHTTPRequestHandler):
    """Manejador HTTP simple para simular el servidor MCP de Brave Search."""
    
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
    
    def _create_response(self, success=True, data=None, error=None):
        response = {
            "success": success,
            "message_id": "test-message-id"
        }
        
        if data:
            response["data"] = data
        
        if error:
            response["error"] = error
            
        return json.dumps(response).encode('utf-8')
    
    def do_GET(self):
        """Maneja solicitudes GET."""
        if self.path == '/ping':
            self._set_headers()
            response = self._create_response(success=True, data={"status": "ok"})
            self.wfile.write(response)
        else:
            self._set_headers(404)
            response = self._create_response(
                success=False, 
                error={"code": "not_found", "message": "Ruta no encontrada"}
            )
            self.wfile.write(response)
    
    def do_POST(self):
        """Maneja solicitudes POST."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request = json.loads(post_data.decode('utf-8'))
        
        if self.path == '/api':
            # Extraer información del mensaje
            action = request.get("action", "")
            resource = request.get("resource", {})
            resource_type = resource.get("type", "")
            resource_path = resource.get("path", "")
            data = request.get("data", {})
            
            # Procesar diferentes tipos de mensajes
            if action == "ping":
                self._set_headers()
                response = self._create_response(success=True, data={"status": "ok"})
                self.wfile.write(response)
                
            elif action == "capabilities":
                self._set_headers()
                response = self._create_response(
                    success=True, 
                    data={
                        "actions": [
                            "ping", 
                            "capabilities",
                            "search"
                        ],
                        "resources": [
                            "web_search", 
                            "local_search"
                        ],
                        "version": "1.0",
                        "name": "Brave Search MCP (Simulado)",
                        "description": "Servidor simulado de Brave Search MCP"
                    }
                )
                self.wfile.write(response)
                
            elif action == "search":
                query = data.get("query", "")
                count = data.get("count", 5)
                offset = data.get("offset", 0)
                resource_type = data.get("resource_type", "web_search")  # Obtener tipo de recurso de los datos
                
                if not query:
                    self._set_headers(400)
                    response = self._create_response(
                        success=False, 
                        error={"code": "invalid_request", "message": "Falta el parámetro query"}
                    )
                    self.wfile.write(response)
                    return
                
                # Crear resultados dependiendo del tipo de búsqueda
                results = []
                
                # Para búsquedas web
                if resource_type == "web_search":
                    for i in range(count):
                        idx = i + 1 + offset
                        results.append({
                            "id": f"web-{idx}",
                            "title": f"Resultado web {idx} para '{query}'",
                            "description": f"Este es un resultado web simulado para la búsqueda '{query}'",
                            "url": f"https://example.com/result/{idx}?q={query}"
                        })
                # Para búsquedas locales
                elif resource_type == "local_search":
                    for i in range(count):
                        idx = i + 1 + offset
                        results.append({
                            "id": f"local-{idx}",
                            "name": f"Local {idx} cerca de '{query}'",
                            "address": f"Calle Ejemplo {idx}, Ciudad",
                            "rating": round(4.0 + (i * 0.2), 1),  # Valoraciones entre 4.0 y 5.0
                            "distance": round(0.5 + (i * 0.3), 1),  # Distancias entre 0.5km y 2.0km
                            "type": "restaurant"
                        })
                
                self._set_headers()
                response = self._create_response(
                    success=True, 
                    data={
                        "results": results,
                        "count": len(results),
                        "query": query,
                        "resource_type": resource_type
                    }
                )
                self.wfile.write(response)
            else:
                self._set_headers(400)
                response = self._create_response(
                    success=False, 
                    error={"code": "invalid_action", "message": f"Acción no soportada: {action}"}
                )
                self.wfile.write(response)
        else:
            self._set_headers(404)
            response = self._create_response(
                success=False, 
                error={"code": "not_found", "message": "Ruta no encontrada"}
            )
            self.wfile.write(response)

def start_test_server(port=8080):
    """
    Inicia un servidor HTTP de prueba para simular un servidor MCP.
    
    Args:
        port: Puerto en el que ejecutar el servidor
        
    Returns:
        El servidor iniciado
    """
    server = HTTPServer(('localhost', port), BraveSearchMockHandler)
    
    def run_server():
        logger.info(f"Iniciando servidor MCP simulado en http://localhost:{port}")
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"Error en el servidor simulado: {e}")
    
    thread = threading.Thread(target=run_server)
    thread.daemon = True  # El hilo se cerrará cuando el programa principal termine
    thread.start()
    
    return thread

async def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(description="Cliente MCP para Brave Search API")
    parser.add_argument("--query", default="inteligencia artificial", help="Consulta de búsqueda")
    parser.add_argument("--count", type=int, default=5, help="Número de resultados")
    parser.add_argument("--search-type", choices=["web", "local"], default="web", 
                        help="Tipo de búsqueda: web o local")
    parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor MCP")
    parser.add_argument("--mock-server", action="store_true", help="Usar servidor simulado")
    parser.add_argument("--timeout", type=int, default=15, help="Tiempo máximo para esperar")
    args = parser.parse_args()
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Inicializar MCP (no es necesario para este ejemplo básico)
    if not args.mock_server:
        try:
            await initialize_mcp()
            registry = get_registry()
            logger.info("MCP inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar MCP: {e}")
            logger.info("Continuando sin inicialización MCP...")
    
    if args.mock_server:
        # Iniciar servidor de simulación
        logger.info("Iniciando servidor simulado...")
        server_thread = start_test_server(port=args.port)
    
    try:
        # Crear y configurar cliente HTTP
        client_url = f"http://localhost:{args.port}"
        client = MCPHttpClient(base_url=client_url)
        
        # Registrar cliente si se inicializó MCP
        if 'registry' in locals():
            registry.register_client("brave_search", client)
        
        # Conectar al servidor
        logger.info(f"Conectando al servidor MCP en {client_url}...")
        connect_success = client.connect()
        
        if not connect_success:
            logger.error("No se pudo conectar al servidor MCP")
            return
        
        logger.info("Conexión establecida con el servidor MCP")
        
        # Verificar disponibilidad del servidor
        logger.info("Verificando disponibilidad del servidor (ping)...")
        ping_response = client.ping()
        if not ping_response.success:
            logger.error(f"Error al hacer ping al servidor: {ping_response.error}")
            return
        
        logger.info("Servidor responde correctamente")
        
        # Obtener capacidades del servidor
        logger.info("Solicitando capacidades del servidor...")
        capabilities_response = client.get_capabilities()
        if not capabilities_response.success:
            logger.error(f"Error al obtener capacidades: {capabilities_response.error}")
            return
        
        actions = capabilities_response.data.get("actions", [])
        resources = capabilities_response.data.get("resources", [])
        
        logger.info(f"Acciones soportadas: {', '.join(actions)}")
        logger.info(f"Recursos disponibles: {', '.join(resources)}")
        
        # Verificar si el servidor soporta búsquedas
        if "search" not in actions:
            logger.error("El servidor no soporta la acción de búsqueda")
            return
        
        # Verificar tipo de búsqueda solicitada
        resource_type = "web_search" if args.search_type == "web" else "local_search"
        if resource_type not in resources:
            logger.error(f"El servidor no soporta el tipo de recurso: {resource_type}")
            return
        
        # Crear mensaje de búsqueda
        logger.info(f"Realizando búsqueda {args.search_type}: '{args.query}', {args.count} resultados...")
        message = MCPMessage(
            action="search",
            resource_type=resource_type,
            resource_path=f"/{args.search_type}",
            data={
                "query": args.query,
                "count": args.count,
                "offset": 0,
                "resource_type": resource_type,
                "country": "ES",
                "search_lang": "es"
            }
        )
        
        # Enviar mensaje y recibir respuesta
        search_response = client.send_message(message)
        
        if not search_response.success:
            logger.error(f"Error en la búsqueda: {search_response.error}")
            return
        
        # Procesar resultados
        results = search_response.data.get("results", [])
        total_count = len(results)
        
        logger.info(f"Búsqueda completada. Resultados obtenidos: {total_count}")
        
        # Mostrar resultados
        if args.search_type == "web":
            for i, result in enumerate(results, 1):
                logger.info(f"\nResultado {i}:")
                logger.info(f"  Título: {result.get('title', 'N/A')}")
                logger.info(f"  URL: {result.get('url', 'N/A')}")
                logger.info(f"  Descripción: {result.get('description', 'N/A')[:150]}...")
        else:
            for i, result in enumerate(results, 1):
                logger.info(f"\nResultado local {i}:")
                logger.info(f"  Nombre: {result.get('name', 'N/A')}")
                logger.info(f"  Dirección: {result.get('address', 'N/A')}")
                if "rating" in result:
                    logger.info(f"  Valoración: {result['rating']}")
                if "distance" in result:
                    logger.info(f"  Distancia: {result['distance']} km")
        
        logger.info("\nBúsqueda completada exitosamente")
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Desconectar cliente
        if 'client' in locals():
            logger.info("Desconectando del servidor...")
            client.disconnect()
        
        # Cerrar servidor simulado si está activo
        if args.mock_server and 'server_thread' in locals():
            logger.info("Deteniendo servidor simulado...")
            # Aquí normalmente habría código para detener el servidor
        
        # Cerrar MCP si se inicializó
        if not args.mock_server:
            try:
                await shutdown_mcp()
                logger.info("MCP cerrado correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar MCP: {e}")

if __name__ == "__main__":
    """Punto de entrada principal."""
    # En Windows, necesitamos esto para que asyncio funcione correctamente
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main()) 