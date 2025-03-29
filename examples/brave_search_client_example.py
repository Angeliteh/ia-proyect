#!/usr/bin/env python
"""
Ejemplo simplificado de cliente MCP para Brave Search (usando un servidor de prueba)

Este script demuestra cómo conectarse a un servidor MCP con capacidades de
búsqueda web y local, similar a lo que Brave Search MCP ofrece, pero usando
un servidor local de prueba para fines de simulación.

Este ejemplo muestra:
1. Cómo configurar un cliente HTTP MCP
2. Cómo obtener capacidades del servidor
3. Cómo realizar búsquedas web y locales
4. Cómo manejar los resultados de búsqueda
"""

import os
import sys
import logging
import argparse
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Agregar el directorio padre al path para poder importar los módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Importación directa de los módulos locales
from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
from mcp.connectors.http_client import MCPHttpClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("brave_search_example")

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
            if action == MCPAction.PING.value:
                self._set_headers()
                response = self._create_response(success=True, data={"status": "ok"})
                self.wfile.write(response)
                
            elif action == MCPAction.CAPABILITIES.value:
                self._set_headers()
                response = self._create_response(
                    success=True, 
                    data={
                        "actions": [
                            MCPAction.PING.value, 
                            MCPAction.CAPABILITIES.value,
                            MCPAction.SEARCH.value
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
                
            elif action == MCPAction.SEARCH.value:
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
                            "url": f"https://example.com/result/{idx}",
                            "source": "Brave Search (simulado)"
                        })
                
                # Para búsquedas locales
                elif resource_type == "local_search":
                    for i in range(min(count, 3)):  # Menos resultados locales para simular realismo
                        idx = i + 1
                        results.append({
                            "id": f"local-{idx}",
                            "name": f"Negocio {idx} para '{query}'",
                            "address": f"Calle Principal {idx * 100}, Ciudad Ejemplo",
                            "type": ["restaurante", "café", "tienda"][i % 3],
                            "rating": round(3.5 + (i * 0.5), 1),
                            "phone": f"+1-555-{idx}00-{idx}000",
                            "distance": f"{i * 0.5 + 0.5} km"
                        })
                    
                    # Si no hay suficientes resultados locales, simulamos la capacidad de fallback
                    if len(results) < count and "fallback" in data and data["fallback"]:
                        fallback_note = {
                            "id": "fallback-note",
                            "name": "Resultados web como fallback",
                            "type": "fallback_notice"
                        }
                        results.append(fallback_note)
                        
                        # Añadimos algunos resultados web como fallback
                        for i in range(len(results), count):
                            idx = i - len(results) + 1
                            results.append({
                                "id": f"web-fallback-{idx}",
                                "title": f"Resultado web {idx} para '{query}'",
                                "description": f"Este es un resultado web de fallback para '{query}'",
                                "url": f"https://example.com/fallback/{idx}",
                                "source": "Brave Search (fallback)"
                            })
                
                self._set_headers()
                response = self._create_response(
                    success=True, 
                    data={
                        "query": query,
                        "results": results,
                        "total_results": len(results) + (10 if resource_type == "web_search" else 3),
                        "search_type": resource_type
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

# Función para iniciar el servidor de prueba
def start_test_server(port=8080):
    """Inicia un servidor HTTP simple para pruebas."""
    server = HTTPServer(('localhost', port), BraveSearchMockHandler)
    logger.info(f"Iniciando servidor de simulación de Brave Search MCP en http://localhost:{port}")
    
    # Iniciar el servidor en un hilo separado
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True  # El hilo se cerrará cuando termine el programa
    server_thread.start()
    
    # Dar tiempo al servidor para iniciar
    time.sleep(1)
    
    return server

def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(description="Cliente HTTP MCP para Brave Search (simulado)")
    parser.add_argument("--url", help="URL base del servidor MCP", default="http://localhost:8080")
    parser.add_argument("--query", help="Consulta para búsqueda", default="inteligencia artificial")
    parser.add_argument("--search-type", choices=["web", "local"], default="web", 
                        help="Tipo de búsqueda (web o local)")
    parser.add_argument("--count", type=int, default=5, help="Número de resultados (máx. 20)")
    parser.add_argument("--offset", type=int, default=0, help="Desplazamiento para paginación (solo web)")
    parser.add_argument("--disable-fallback", action="store_true", help="Desactivar fallback para búsquedas locales")
    args = parser.parse_args()
    
    # Inicializar el subsistema MCP
    initialize_mcp()
    
    # Iniciar servidor de prueba
    server = start_test_server()
    
    try:
        # Registrar el cliente HTTP para Brave Search
        registry = get_registry()
        http_client = MCPHttpClient(
            base_url=args.url,
            headers={"User-Agent": "Brave-Search-MCP-Client/1.0"}
        )
        registry.register_client("brave_search_client", http_client)
        
        logger.info(f"Conectando a servidor MCP de Brave Search (simulado) en {args.url}")
        
        # Conectar al servidor
        if http_client.connect():
            logger.info("Conexión exitosa")
            
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
                
                # Determinar el tipo de recurso basado en el tipo de búsqueda
                resource_type = "web_search" if args.search_type == "web" else "local_search"
                
                # Realizar búsqueda
                logger.info(f"Realizando búsqueda {args.search_type}: {args.query}")
                
                # Construir parámetros específicos según el tipo de búsqueda
                search_params = {
                    "query": args.query,
                    "count": min(args.count, 20),  # Máximo 20 resultados
                    "resource_type": resource_type  # Incluir el tipo de recurso en los datos
                }
                
                # Añadir parámetros específicos para búsqueda web
                if args.search_type == "web" and args.offset > 0:
                    search_params["offset"] = min(args.offset, 9)  # Máximo offset 9
                
                # Añadir parámetro de fallback para búsqueda local
                if args.search_type == "local" and not args.disable_fallback:
                    search_params["fallback"] = True
                
                # Crear mensaje para búsqueda usando SYSTEM como tipo de recurso
                search_message = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type=MCPResource.SYSTEM,  # Usar SYSTEM en lugar del tipo personalizado
                    resource_path="/search/" + resource_type,  # Incluir el tipo en el path
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
                        
                        print("--------------------")
                    
                else:
                    logger.error(f"Error en búsqueda: {search_response.error.message if search_response.error else 'Error desconocido'}")
                
            except Exception as e:
                logger.error(f"Error: {str(e)}")
        else:
            logger.error("No se pudo conectar al servidor MCP")
    
    except Exception as e:
        logger.exception(f"Error en la ejecución: {str(e)}")
    
    finally:
        # Asegurar la desconexión y limpieza
        if 'http_client' in locals():
            http_client.disconnect()
        
        # Detener el servidor de prueba
        if server:
            server.shutdown()
            server.server_close()
            logger.info("Servidor de prueba detenido")
        
        # Cerrar el subsistema MCP
        shutdown_mcp()
        logger.info("Ejemplo finalizado")

if __name__ == "__main__":
    main() 