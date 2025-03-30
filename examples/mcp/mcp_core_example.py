#!/usr/bin/env python
"""
MCP Core Example

Este ejemplo muestra el funcionamiento básico del Model Context Protocol (MCP),
incluyendo mensajes, respuestas y un sencillo servidor de eco.
"""

import os
import sys
import asyncio
import argparse
import logging
import uuid
import time
import json
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("mcp_core_example")

# Añadir el directorio raíz del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Intentar importar dotenv para cargar variables de entorno
try:
    from dotenv import load_dotenv
    # Cargar variables de entorno del archivo .env
    load_dotenv()
    logger.info("Variables de entorno cargadas desde .env")
except ImportError:
    logger.warning("python-dotenv no está instalado. Las variables de entorno no se cargarán desde .env")

# Intentar importar los módulos reales
try:
    # Importar desde el módulo adecuado
    import mcp.core
    from mcp.core import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPError
    from mcp.core import MCPServerBase, MCPClientBase, MCPRegistry
    # Importar de init.py funciones específicas
    from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
    
    logger.info("Módulos MCP core importados correctamente")
    USING_REAL_MODULES = True
except ImportError as e:
    logger.warning(f"Error al importar módulos reales de MCP core: {e}")
    logger.info("Usando implementaciones mínimas para demostración")
    USING_REAL_MODULES = False
    
    # Implementaciones mínimas para demostración
    class MCPAction:
        """Acciones definidas en el protocolo MCP."""
        PING = "ping"
        GET = "get"
        LIST = "list"
        SEARCH = "search"
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"
        CAPABILITIES = "capabilities"
    
    class MCPResource:
        """Tipos de recursos definidos en el protocolo MCP."""
        FILE = "file"
        DIRECTORY = "directory"
        SEARCH_RESULT = "search_result"
        SYSTEM_INFO = "system_info"
        DATABASE = "database"
        MEMORY = "memory"
    
    class MCPErrorCode:
        """Códigos de error definidos en el protocolo MCP."""
        INVALID_REQUEST = "invalid_request"
        RESOURCE_NOT_FOUND = "resource_not_found"
        UNAUTHORIZED = "unauthorized"
        FORBIDDEN = "forbidden"
        SERVER_ERROR = "server_error"
        NOT_IMPLEMENTED = "not_implemented"
    
    class MCPError:
        """Representación de un error MCP."""
        def __init__(self, code, message, details=None):
            self.code = code
            self.message = message
            self.details = details or {}
        
        def to_dict(self):
            return {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
    
    class MCPMessage:
        """Mensaje del protocolo MCP."""
        def __init__(self, action, resource_type=None, resource_id=None, params=None, data=None, headers=None):
            self.id = str(uuid.uuid4())
            self.action = action
            self.resource_type = resource_type
            self.resource_id = resource_id
            self.params = params or {}
            self.data = data or {}
            self.headers = headers or {}
            self.timestamp = int(time.time())
        
        def to_dict(self):
            return {
                "id": self.id,
                "action": self.action,
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
                "params": self.params,
                "data": self.data,
                "headers": self.headers,
                "timestamp": self.timestamp
            }
        
        @classmethod
        def from_dict(cls, data):
            msg = cls(
                action=data["action"],
                resource_type=data.get("resource_type"),
                resource_id=data.get("resource_id"),
                params=data.get("params", {}),
                data=data.get("data", {}),
                headers=data.get("headers", {})
            )
            msg.id = data.get("id", msg.id)
            msg.timestamp = data.get("timestamp", msg.timestamp)
            return msg
    
    class MCPResponse:
        """Respuesta del protocolo MCP."""
        def __init__(self, message_id, success=True, data=None, error=None, metadata=None):
            self.id = str(uuid.uuid4())
            self.message_id = message_id
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}
            self.timestamp = int(time.time())
        
        def to_dict(self):
            result = {
                "id": self.id,
                "message_id": self.message_id,
                "success": self.success,
                "data": self.data,
                "metadata": self.metadata,
                "timestamp": self.timestamp
            }
            
            if self.error:
                result["error"] = self.error.to_dict() if hasattr(self.error, "to_dict") else self.error
            
            return result
        
        @classmethod
        def from_dict(cls, data):
            error = None
            if "error" in data and data["error"]:
                error = MCPError(
                    code=data["error"]["code"],
                    message=data["error"]["message"],
                    details=data["error"].get("details", {})
                )
            
            resp = cls(
                message_id=data["message_id"],
                success=data["success"],
                data=data.get("data", {}),
                error=error,
                metadata=data.get("metadata", {})
            )
            resp.id = data.get("id", resp.id)
            resp.timestamp = data.get("timestamp", resp.timestamp)
            return resp
    
    class MCPServerBase:
        """Clase base para servidores MCP."""
        def __init__(self, name, description=None, version="1.0.0"):
            self.name = name
            self.description = description or f"MCP Server: {name}"
            self.version = version
            self.handlers = {}
            self.register_default_handlers()
        
        def register_default_handlers(self):
            """Registrar manejadores predeterminados."""
            self.register_handler(MCPAction.PING, self.handle_ping)
            self.register_handler(MCPAction.CAPABILITIES, self.handle_capabilities)
        
        def register_handler(self, action, handler):
            """Registrar un manejador para una acción específica."""
            self.handlers[action] = handler
        
        async def handle_message(self, message):
            """Procesar un mensaje MCP y generar una respuesta."""
            if not isinstance(message, MCPMessage):
                if isinstance(message, dict):
                    try:
                        message = MCPMessage.from_dict(message)
                    except (KeyError, ValueError) as e:
                        return MCPResponse(
                            message_id="unknown",
                            success=False,
                            error=MCPError(
                                code=MCPErrorCode.INVALID_REQUEST,
                                message=f"Invalid message format: {str(e)}"
                            )
                        )
                else:
                    return MCPResponse(
                        message_id="unknown",
                        success=False,
                        error=MCPError(
                            code=MCPErrorCode.INVALID_REQUEST,
                            message="Invalid message format"
                        )
                    )
            
            action = message.action
            if action in self.handlers:
                try:
                    return await self.handlers[action](message)
                except Exception as e:
                    logger.exception(f"Error handling action {action}")
                    return MCPResponse(
                        message_id=message.id,
                        success=False,
                        error=MCPError(
                            code=MCPErrorCode.SERVER_ERROR,
                            message=f"Error handling action {action}: {str(e)}"
                        )
                    )
            else:
                return MCPResponse(
                    message_id=message.id,
                    success=False,
                    error=MCPError(
                        code=MCPErrorCode.NOT_IMPLEMENTED,
                        message=f"Action {action} not implemented"
                    )
                )
        
        async def handle_ping(self, message):
            """Manejar un mensaje de ping."""
            return MCPResponse(
                message_id=message.id,
                success=True,
                data={"status": "ok", "timestamp": int(time.time())},
                metadata={"server_name": self.name, "version": self.version}
            )
        
        async def handle_capabilities(self, message):
            """Manejar un mensaje de solicitud de capacidades."""
            capabilities = {
                "actions": list(self.handlers.keys()),
                "version": self.version,
                "name": self.name,
                "description": self.description
            }
            return MCPResponse(
                message_id=message.id,
                success=True,
                data=capabilities
            )
    
    class MCPClientBase:
        """Clase base para clientes MCP."""
        def __init__(self, client_id=None):
            self.client_id = client_id or str(uuid.uuid4())
            self.server = None
        
        async def connect(self, server):
            """Conectar con un servidor."""
            self.server = server
            logger.info(f"Cliente {self.client_id} conectado al servidor {server.name}")
            return True
        
        async def disconnect(self):
            """Desconectar del servidor."""
            if self.server:
                logger.info(f"Cliente {self.client_id} desconectado del servidor {self.server.name}")
                self.server = None
                return True
            return False
        
        async def send_message(self, message):
            """Enviar un mensaje al servidor conectado."""
            if not self.server:
                logger.error("Cliente no conectado a ningún servidor")
                return None
            
            if isinstance(message, dict):
                message = MCPMessage.from_dict(message)
            
            # Añadir encabezados del cliente
            if "client_id" not in message.headers:
                message.headers["client_id"] = self.client_id
            
            logger.debug(f"Enviando mensaje: {message.to_dict()}")
            response = await self.server.handle_message(message)
            logger.debug(f"Respuesta recibida: {response.to_dict()}")
            
            return response
    
    class MCPRegistry:
        """Registro central de servidores MCP."""
        def __init__(self):
            self.servers = {}
        
        def register_server(self, server_id, server):
            """Registrar un servidor en el registro."""
            self.servers[server_id] = server
            logger.info(f"Servidor {server_id} registrado")
            return True
        
        def unregister_server(self, server_id):
            """Eliminar un servidor del registro."""
            if server_id in self.servers:
                del self.servers[server_id]
                logger.info(f"Servidor {server_id} eliminado")
                return True
            logger.warning(f"Servidor {server_id} no encontrado")
            return False
        
        def get_server(self, server_id):
            """Obtener un servidor del registro."""
            return self.servers.get(server_id)
        
        def list_servers(self):
            """Listar todos los servidores registrados."""
            return list(self.servers.keys())
    
    # Registro global y funciones de inicialización/finalización
    _global_registry = None
    
    def initialize_mcp():
        """Inicializar el sistema MCP."""
        global _global_registry
        _global_registry = MCPRegistry()
        logger.info("Sistema MCP inicializado")
        return _global_registry
    
    def shutdown_mcp():
        """Finalizar el sistema MCP."""
        global _global_registry
        _global_registry = None
        logger.info("Sistema MCP finalizado")
    
    def get_registry():
        """Obtener el registro global."""
        if _global_registry is None:
            initialize_mcp()
        return _global_registry

# Implementación de un servidor simple de eco
class SimpleEchoServer(MCPServerBase):
    """Un servidor simple que repite los mensajes."""
    
    def __init__(self):
        super().__init__(name="SimpleEchoServer", description="A simple echo server for MCP")
        self.register_handler(MCPAction.GET, self.handle_get)
        self.register_handler(MCPAction.LIST, self.handle_list)
        self.register_handler(MCPAction.SEARCH, self.handle_search)
    
    async def handle_get(self, message):
        """Manejar una solicitud GET."""
        logger.info(f"GET recibido: {message.to_dict()}")
        return MCPResponse(
            message_id=message.id,
            success=True,
            data={"echo": message.data, "message": "Echo of your GET request"},
            metadata={"resource_type": message.resource_type, "resource_id": message.resource_id}
        )
    
    async def handle_list(self, message):
        """Manejar una solicitud LIST."""
        logger.info(f"LIST recibido: {message.to_dict()}")
        # Generar algunos elementos de ejemplo
        items = [
            {"id": f"item-{i}", "name": f"Item {i}", "value": i * 10}
            for i in range(1, 6)
        ]
        return MCPResponse(
            message_id=message.id,
            success=True,
            data={"items": items, "count": len(items)},
            metadata={"resource_type": message.resource_type}
        )
    
    async def handle_search(self, message):
        """Manejar una solicitud SEARCH."""
        logger.info(f"SEARCH recibido: {message.to_dict()}")
        query = message.params.get("query", "")
        
        # Generar resultados simulados
        results = [
            {"id": f"result-{i}", "name": f"Result {i} for '{query}'", "relevance": 1.0 - i * 0.1}
            for i in range(5)
        ]
        
        return MCPResponse(
            message_id=message.id,
            success=True,
            data={"results": results, "count": len(results), "query": query},
            metadata={"resource_type": MCPResource.SEARCH_RESULT}
        )

async def run_demo():
    """Ejecutar una demostración del sistema MCP."""
    
    # Inicializar el sistema MCP
    registry = initialize_mcp()
    logger.info("Sistema MCP inicializado")
    
    # Crear y registrar un servidor de eco
    echo_server = SimpleEchoServer()
    registry.register_server("echo", echo_server)
    
    # Crear un cliente
    client = MCPClientBase(client_id="demo-client")
    await client.connect(echo_server)
    
    # Enviar un mensaje PING
    ping_message = MCPMessage(action=MCPAction.PING)
    ping_response = await client.send_message(ping_message)
    logger.info(f"Respuesta PING: {ping_response.to_dict()}")
    
    # Enviar un mensaje CAPABILITIES
    cap_message = MCPMessage(action=MCPAction.CAPABILITIES)
    cap_response = await client.send_message(cap_message)
    logger.info(f"Respuesta CAPABILITIES: {json.dumps(cap_response.to_dict(), indent=2)}")
    
    # Enviar un mensaje GET
    get_message = MCPMessage(
        action=MCPAction.GET,
        resource_type=MCPResource.FILE,
        resource_id="example.txt",
        params={"encoding": "utf-8"}
    )
    get_response = await client.send_message(get_message)
    logger.info(f"Respuesta GET: {json.dumps(get_response.to_dict(), indent=2)}")
    
    # Enviar un mensaje LIST
    list_message = MCPMessage(
        action=MCPAction.LIST,
        resource_type=MCPResource.DIRECTORY,
        params={"path": "/examples"}
    )
    list_response = await client.send_message(list_message)
    logger.info(f"Respuesta LIST: {json.dumps(list_response.to_dict(), indent=2)}")
    
    # Enviar un mensaje SEARCH
    search_message = MCPMessage(
        action=MCPAction.SEARCH,
        resource_type=MCPResource.SEARCH_RESULT,
        params={"query": "ejemplo MCP"},
        data={"filters": {"type": "document"}}
    )
    search_response = await client.send_message(search_message)
    logger.info(f"Respuesta SEARCH: {json.dumps(search_response.to_dict(), indent=2)}")
    
    # Enviar un mensaje para una acción no implementada
    custom_message = MCPMessage(
        action="custom_action",
        data={"test": True}
    )
    custom_response = await client.send_message(custom_message)
    logger.info(f"Respuesta CUSTOM: {json.dumps(custom_response.to_dict(), indent=2)}")
    
    # Desconectar el cliente
    await client.disconnect()
    
    # Finalizar el sistema MCP
    shutdown_mcp()
    logger.info("Demostración completada")

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Ejemplo del núcleo MCP")
    parser.add_argument("--verbose", action="store_true", help="Mostrar mensajes de depuración")
    parser.add_argument("--check-real-modules", action="store_true", 
                        help="Verificar si se están usando módulos reales o simulados")
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Verificar si estamos usando módulos reales o simulados
    if args.check_real_modules:
        if USING_REAL_MODULES:
            print("USING_REAL_MODULES = True")
            sys.exit(0)
        else:
            print("USING_REAL_MODULES = False")
            # No consideramos un error que se esté usando una implementación de fallback
            # solo lo reportamos para fines informativos
            sys.exit(0)
    
    # Ejecutar la demostración
    asyncio.run(run_demo())

if __name__ == "__main__":
    main() 