"""
Servidor HTTP para el protocolo MCP.

Este módulo implementa un servidor HTTP que permite exponer
servidores MCP a través del protocolo HTTP.
"""

import logging
import asyncio
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Tuple, Optional

from ..utils.helpers import create_logger
from ..core.server_base import MCPServerBase
from ..core.protocol import MCPMessage

# Configurar logging
logger = create_logger("mcp.transport.http")

class MCPHTTPHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para servidores MCP."""
    
    server_instance = None  # Instancia del servidor MCP
    
    def _serialize_response(self, response):
        """Serializa una respuesta a JSON."""
        return json.dumps(response.to_dict()).encode('utf-8')
    
    def _parse_request(self):
        """Parsea una solicitud HTTP a un mensaje MCP."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        if not body:
            return None
            
        try:
            data = json.loads(body)
            return MCPMessage.from_dict(data)
        except Exception as e:
            logger.error(f"Error al parsear solicitud: {e}")
            return None
    
    def _return_json(self, status_code, data):
        """Envía una respuesta JSON."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        response = json.dumps(data).encode('utf-8')
        self.wfile.write(response)
    
    def _return_error(self, status_code, message):
        """Envía una respuesta de error."""
        error_data = {
            "error": {
                "code": status_code,
                "message": message
            }
        }
        self._return_json(status_code, error_data)
    
    def do_OPTIONS(self):
        """Maneja solicitudes OPTIONS para CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_POST(self):
        """Maneja solicitudes POST."""
        # Verificar si hay una instancia de servidor
        if not self.server_instance:
            self._return_error(500, "Servidor MCP no inicializado")
            return
            
        # Parsear la solicitud
        message = self._parse_request()
        if not message:
            self._return_error(400, "Solicitud inválida o mal formada")
            return
            
        try:
            # Procesar el mensaje con el servidor MCP
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process():
                return await self.server_instance.process_message(message)
                
            response = loop.run_until_complete(process())
            loop.close()
            
            # Enviar la respuesta
            self._return_json(200, response.to_dict())
            
        except Exception as e:
            logger.error(f"Error procesando solicitud: {e}", exc_info=True)
            self._return_error(500, f"Error interno del servidor: {str(e)}")
    
    def do_GET(self):
        """Maneja solicitudes GET."""
        # Ruta para verificar estado del servidor
        if self.path == '/ping':
            self._return_json(200, {"status": "ok", "server": self.server_instance.name if self.server_instance else "unknown"})
        else:
            self._return_error(404, "Ruta no encontrada")

def start_http_server(
    host: str = "localhost", 
    port: int = 8080, 
    mcp_server: Optional[MCPServerBase] = None
) -> Tuple[HTTPServer, int]:
    """
    Inicia un servidor HTTP para exponer un servidor MCP.
    
    Args:
        host: Host en el que escuchar
        port: Puerto en el que escuchar
        mcp_server: Instancia del servidor MCP a exponer
        
    Returns:
        Tupla con el servidor HTTP y el puerto real usado
    """
    # Asignar servidor MCP al manejador HTTP
    MCPHTTPHandler.server_instance = mcp_server
    
    # Intentar iniciar el servidor en el puerto indicado
    # Si está ocupado, incrementar el puerto
    max_port = port + 100
    current_port = port
    
    while current_port < max_port:
        try:
            http_server = HTTPServer((host, current_port), MCPHTTPHandler)
            logger.info(f"Servidor HTTP MCP iniciado en http://{host}:{current_port}")
            
            # Iniciar el servidor en un hilo separado
            server_thread = threading.Thread(target=http_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            return http_server, current_port
            
        except OSError:
            logger.warning(f"Puerto {current_port} ocupado, intentando el siguiente")
            current_port += 1
    
    raise RuntimeError(f"No se pudo iniciar el servidor HTTP en ningún puerto entre {port} y {max_port-1}")

def stop_http_server(http_server: HTTPServer) -> None:
    """
    Detiene un servidor HTTP.
    
    Args:
        http_server: Servidor HTTP a detener
    """
    if http_server:
        logger.info("Deteniendo servidor HTTP MCP")
        http_server.shutdown()
        http_server.server_close() 