"""
Servidor MCP para Brave Search API.

Este servidor implementa un endpoint MCP que se conecta directamente con la API
de Brave Search para proporcionar capacidades de búsqueda web y local.
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, Any, Optional, List, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import uuid

# Ajustar la ruta para importar los módulos MCP
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.core.protocol import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPError,
    MCPErrorCode
)

from mcp.core.server_base import MCPServerBase

# Configurar logging
logger = logging.getLogger("brave_search_server")

class BraveSearchMCPServer:
    """Servidor MCP para Brave Search API."""
    
    def __init__(self, api_key, base_url="https://api.search.brave.com/res/v1/web", timeout=30):
        """
        Inicializa el servidor MCP para Brave Search.
        
        Args:
            api_key: API key para Brave Search
            base_url: URL base para la API de Brave Search
            timeout: Timeout para solicitudes HTTP en segundos
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        
        # Configurar sesión HTTP
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
            "User-Agent": "BraveSearchMCP/1.0"
        })
        
        logging.info(f"Servidor MCP de Brave Search inicializado con base_url: {base_url}")
    
    def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Procesa un mensaje MCP y devuelve una respuesta.
        
        Args:
            message: El mensaje MCP recibido
            
        Returns:
            La respuesta MCP
        """
        try:
            # Verificar que tenemos una API key válida
            if not self.api_key:
                return MCPResponse(
                    message_id=message.id,
                    status="error",
                    error="No se ha proporcionado una API key para Brave Search",
                    data=None
                )

            # Procesar según la acción
            if message.action == "ping":
                return self._handle_ping(message)
            elif message.action == "capabilities":
                return self._handle_capabilities(message)
            elif message.action == "search":
                return self._handle_search(message)
            else:
                return MCPResponse(
                    message_id=message.id,
                    status="error",
                    error=f"Acción no soportada: {message.action}",
                    data=None
                )
        except Exception as e:
            logging.error(f"Error al procesar mensaje: {e}", exc_info=True)
            return MCPResponse(
                message_id=message.id,
                status="error",
                error=f"Error interno del servidor: {str(e)}",
                data=None
            )
    
    def _handle_ping(self, message: MCPMessage) -> MCPResponse:
        """Maneja la acción PING."""
        return MCPResponse(
            message_id=message.id,
            status="success",
            data={"status": "ok"},
            error=None
        )
    
    def _handle_capabilities(self, message: MCPMessage) -> MCPResponse:
        """Maneja la acción CAPABILITIES."""
        capabilities = {
            "actions": ["ping", "capabilities", "search"],
            "resources": ["web_search", "local_search"],
            "version": "1.0",
            "name": "Brave Search MCP Server",
            "description": "Servidor MCP para Brave Search API"
        }
        
        return MCPResponse(
            message_id=message.id,
            status="success",
            data=capabilities,
            error=None
        )
    
    def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción SEARCH.
        
        Args:
            message: Mensaje MCP con la acción SEARCH
            
        Returns:
            MCPResponse con los resultados de la búsqueda
        """
        # Obtener datos de la búsqueda
        data = message.data or {}
        
        if not data or not isinstance(data, dict):
            return MCPResponse(
                message_id=message.id,
                status="error",
                error="Datos de búsqueda no válidos",
                data=None
            )
        
        # Obtener parámetros de búsqueda
        resource_type = data.get("resource_type", "web_search")
        query = data.get("query", "")
        
        if not query:
            return MCPResponse(
                message_id=message.id,
                status="error",
                error="No se ha proporcionado una consulta de búsqueda",
                data=None
            )
        
        # Realizar búsqueda según el tipo de recurso
        if resource_type == "web_search":
            count = int(data.get("count", 10))
            offset = int(data.get("offset", 0))
            search_lang = data.get("search_lang", "es")
            country = data.get("country", "ES")
            
            results = self._perform_web_search(
                query=query,
                count=count,
                search_lang=search_lang,
                country=country,
                offset=offset
            )
            
            # Verificar si hay error
            if "error" in results:
                return MCPResponse(
                    message_id=message.id,
                    status="error",
                    error=results["error"],
                    data=None
                )
            
            return MCPResponse(
                message_id=message.id,
                status="success",
                data=results,
                error=None
            )
            
        elif resource_type == "local_search":
            count = int(data.get("count", 5))
            country = data.get("country", "ES")
            search_lang = data.get("search_lang", "es")
            
            # Verificar si se debe usar fallback
            use_fallback = data.get("use_fallback", True)
            
            results = self._perform_local_search(
                query=query,
                count=count,
                country=country,
                search_lang=search_lang
            )
            
            # Verificar si hay error
            if "error" in results:
                return MCPResponse(
                    message_id=message.id,
                    status="error",
                    error=results["error"],
                    data=None
                )
            
            # Si no hay resultados y se permite fallback, usar web_search
            if use_fallback and results.get("count", 0) == 0:
                logging.info("No se encontraron resultados locales, usando fallback a web_search")
                
                fallback_results = self._perform_web_search(
                    query=query,
                    count=count,
                    search_lang=search_lang,
                    country=country
                )
                
                # Verificar si hay error en fallback
                if "error" in fallback_results:
                    return MCPResponse(
                        message_id=message.id,
                        status="error",
                        error=fallback_results["error"],
                        data=None
                    )
                
                # Añadir información de fallback
                fallback_results["is_fallback"] = True
                fallback_results["original_type"] = "local_search"
                
                return MCPResponse(
                    message_id=message.id,
                    status="success",
                    data=fallback_results,
                    error=None
                )
            
            return MCPResponse(
                message_id=message.id,
                status="success",
                data=results,
                error=None
            )
        
        else:
            return MCPResponse(
                message_id=message.id,
                status="error",
                error=f"Tipo de recurso no soportado: {resource_type}",
                data=None
            )
    
    def _perform_web_search(self, query, count=10, search_lang="es", country="ES", offset=0):
        """
        Realiza una búsqueda web en Brave Search.
        
        Args:
            query: Término de búsqueda
            count: Número de resultados (predeterminado: 10)
            search_lang: Idioma de búsqueda (predeterminado: es)
            country: País para resultados (predeterminado: ES)
            offset: Desplazamiento para paginación (predeterminado: 0)
            
        Returns:
            Resultados de la búsqueda o error
        """
        params = {
            "q": query,
            "count": count,
            "offset": offset,
            "search_lang": search_lang,
            "country": country
        }
        
        try:
            url = f"{self.base_url}/search"
            logging.info(f"Realizando búsqueda web en {url} con params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            # Registrar respuesta para depuración
            logging.info(f"Código de estado de la respuesta: {response.status_code}")
            logging.info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Verificar si tenemos un error
            if response.status_code != 200:
                error_message = f"Error en la API: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("detail", "Sin detalles")
                        error_code = error_data["error"].get("code", "UNKNOWN")
                        error_message = f"Error en la API: {error_code} - {error_detail}"
                except:
                    error_message = f"Error en la API: {response.status_code} - {response.text[:200]}"
                    
                logging.error(error_message)
                return {"error": error_message}
            
            # Intentar procesar respuesta JSON
            try:
                data = response.json()
                
                if "web" in data and "results" in data["web"]:
                    # Procesar resultados web
                    results = data["web"]["results"]
                    processed_results = []
                    
                    for item in results:
                        processed_results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("description", ""),
                            "age": item.get("age", ""),
                            "is_family_friendly": item.get("is_family_friendly", True)
                        })
                    
                    return {
                        "count": len(processed_results),
                        "results": processed_results,
                        "query": query
                    }
                else:
                    logging.warning(f"No se encontraron resultados web. Estructura recibida: {list(data.keys())}")
                    return {"count": 0, "results": [], "query": query}
            except Exception as e:
                logging.error(f"Error al procesar respuesta JSON: {e}")
                logging.error(f"Contenido de la respuesta: {response.text[:500]}")
                return {"error": f"Error al procesar respuesta: {str(e)}"}
                
        except Exception as e:
            logging.error(f"Error al realizar la búsqueda web: {e}")
            return {"error": f"Error en la comunicación con Brave Search: {str(e)}"}
    
    def _perform_local_search(self, query, count=5, country="ES", search_lang="es"):
        """
        Realiza una búsqueda local en Brave Search.
        
        Args:
            query: Término de búsqueda
            count: Número de resultados (predeterminado: 5)
            country: País para resultados (predeterminado: ES)
            search_lang: Idioma de búsqueda (predeterminado: es)
            
        Returns:
            Resultados de la búsqueda o error
        """
        # Para la búsqueda local, usamos la misma API que para web search
        # pero intentamos extraer información de lugares si existe
        params = {
            "q": query,
            "count": count,
            "search_lang": search_lang,
            "country": country
        }
        
        try:
            url = f"{self.base_url}/search"
            logging.info(f"Realizando búsqueda local en {url} con params: {params}")
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            # Registrar respuesta para depuración
            logging.info(f"Código de estado de la respuesta: {response.status_code}")
            logging.info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Verificar si tenemos un error
            if response.status_code != 200:
                error_message = f"Error en la API: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"].get("detail", "Sin detalles")
                        error_code = error_data["error"].get("code", "UNKNOWN")
                        error_message = f"Error en la API: {error_code} - {error_detail}"
                except:
                    error_message = f"Error en la API: {response.status_code} - {response.text[:200]}"
                    
                logging.error(error_message)
                return {"error": error_message}
            
            # Intentar procesar respuesta JSON
            try:
                data = response.json()
                
                # Buscar resultados de lugares
                if "places" in data and "results" in data["places"]:
                    # Procesar resultados de lugares
                    results = data["places"]["results"]
                    processed_results = []
                    
                    for item in results:
                        processed_results.append({
                            "name": item.get("name", ""),
                            "address": item.get("addr", ""),
                            "type": item.get("type", ""),
                            "rating": item.get("rating", 0),
                            "distance": item.get("distance", 0)
                        })
                    
                    return {
                        "count": len(processed_results),
                        "results": processed_results,
                        "query": query
                    }
                else:
                    logging.warning("No se encontraron resultados de lugares. Se usará fallback si está habilitado.")
                    return {"count": 0, "results": [], "query": query}
            except Exception as e:
                logging.error(f"Error al procesar respuesta JSON: {e}")
                logging.error(f"Contenido de la respuesta: {response.text[:500]}")
                return {"error": f"Error al procesar respuesta: {str(e)}"}
                
        except Exception as e:
            logging.error(f"Error al realizar la búsqueda local: {e}")
            return {"error": f"Error en la comunicación con Brave Search: {str(e)}"}

# Crear una clase de servidor HTTP para exponer el servidor MCP
class BraveSearchHTTPHandler(BaseHTTPRequestHandler):
    """
    Manejador HTTP para exponer el servidor MCP de Brave Search.
    """
    
    # Referencia al servidor MCP
    server_instance = None
    
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()
    
    def _return_error(self, status_code, message):
        self._set_headers(status_code)
        response = {
            "success": False,
            "error": {
                "code": status_code,
                "message": message
            }
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_GET(self):
        """Procesa solicitudes GET."""
        if self.path == '/ping':
            self._set_headers()
            # Crear un mensaje MCP para simular un ping
            ping_message = MCPMessage.create_ping()
            ping_response = self.server_instance._handle_ping(ping_message.id)
            self.wfile.write(json.dumps(ping_response.to_dict()).encode('utf-8'))
        else:
            self._return_error(404, "Ruta no encontrada")
    
    def do_POST(self):
        """Procesa solicitudes POST."""
        if self.path == '/api':
            # Leer y procesar el cuerpo de la solicitud
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Convertir a objeto MCPMessage
                message_dict = json.loads(post_data.decode('utf-8'))
                message = MCPMessage.from_dict(message_dict)
                
                # Procesar la solicitud con el servidor MCP
                response = self.server_instance.handle_action(message)
                
                # Devolver la respuesta
                self._set_headers()
                self.wfile.write(json.dumps(response.to_dict()).encode('utf-8'))
                
            except json.JSONDecodeError:
                self._return_error(400, "JSON inválido")
            except Exception as e:
                logger.error(f"Error procesando solicitud: {str(e)}")
                self._return_error(500, f"Error interno: {str(e)}")
        else:
            self._return_error(404, "Ruta no encontrada")

def run_http_server(host='localhost', port=8080, api_key=None):
    """
    Inicia un servidor HTTP que expone el servidor MCP de Brave Search.
    
    Args:
        host: Host en el que escuchar
        port: Puerto en el que escuchar
        api_key: Clave API para Brave Search
    
    Returns:
        tuple: El servidor HTTP y el servidor MCP
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Crear instancia del servidor MCP
    brave_server = BraveSearchMCPServer(api_key=api_key)
    
    # Asignar la instancia al manejador HTTP
    BraveSearchHTTPHandler.server_instance = brave_server
    
    # Crear y arrancar el servidor HTTP
    http_server = HTTPServer((host, port), BraveSearchHTTPHandler)
    
    logger.info(f"Iniciando servidor MCP de Brave Search en http://{host}:{port}")
    
    # Iniciar el servidor en un hilo separado
    server_thread = threading.Thread(target=http_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Dar tiempo al servidor para iniciar
    time.sleep(1)
    
    return http_server, brave_server

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Servidor MCP para Brave Search API")
    parser.add_argument("--host", default="localhost", help="Host en el que escuchar")
    parser.add_argument("--port", type=int, default=8080, help="Puerto en el que escuchar")
    parser.add_argument("--api-key", help="Clave API para Brave Search")
    args = parser.parse_args()
    
    # Obtener API key de argumentos o variables de entorno
    api_key = args.api_key or os.environ.get("BRAVE_API_KEY")
    
    if not api_key:
        logger.error("No se ha proporcionado una API key para Brave Search. Use --api-key o defina BRAVE_API_KEY")
        sys.exit(1)
    
    # Iniciar el servidor
    http_server, _ = run_http_server(args.host, args.port, api_key)
    
    try:
        # Mantener el proceso principal vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Manejar Ctrl+C
        logger.info("Deteniendo servidor...")
        http_server.shutdown()
        http_server.server_close()
        logger.info("Servidor detenido") 