#!/usr/bin/env python
"""
Ejemplo de cliente MCP para conectarse a un servidor de eco

Este ejemplo muestra cómo crear un cliente MCP simple que se conecta
a un servidor de eco (que simplemente devuelve los mensajes recibidos).
"""

import os
import sys
import logging
import asyncio
import argparse
import json
import time  # Agregamos time para usar time.time()

# Agregar el directorio raíz del proyecto al path para poder importar los módulos
# Ajustamos para manejar la nueva estructura de ejemplos
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/mcp
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

try:
    # Intentar importar los módulos desde el paquete completo
    from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource
    from mcp.core.init import initialize_mcp, shutdown_mcp, get_registry
    from mcp.connectors.http_client import MCPHttpClient
    from mcp.core.server_base import MCPServerBase
    from mcp.core.client_base import MCPClientBase
    
    # Alias para compatibilidad
    async def async_initialize_mcp():
        """Inicializa el MCP de forma asíncrona."""
        return initialize_mcp()
    
    print("Módulos MCP importados correctamente desde paquete instalado")
except ImportError as e:
    print(f"Error al importar módulos MCP desde paquete instalado: {e}")
    print("Intentando importación alternativa...")
    
    try:
        # Importación alternativa creando un sistema de módulos mock para el ejemplo
        # Esto permite ejecutar el ejemplo sin necesidad de tener el paquete instalado
        class MockMCP:
            class Protocol:
                class MCPMessage:
                    def __init__(self, action=None, resource_type=None, resource_path=None, data=None):
                        self.action = action
                        self.resource_type = resource_type
                        self.resource_path = resource_path
                        self.data = data
                
                class MCPResponse:
                    def __init__(self, success=True, data=None, error=None):
                        self.success = success
                        self.data = data or {}
                        self.error = error
                    
                    @classmethod
                    def success_response(cls, message_id=None, data=None):
                        return cls(success=True, data=data)
                    
                    @classmethod
                    def error_response(cls, message_id=None, code=None, message=None):
                        return cls(success=False, error={"code": code, "message": message})
                
                class MCPAction:
                    PING = "ping"
                    ECHO = "echo"
                    GET = "get"
                    CAPABILITIES = "capabilities"
                    SEARCH = "search"
                
                class MCPResource:
                    SYSTEM = "system"
            
            class Server:
                class MCPServerBase:
                    """Clase base para servidores MCP."""
                    def __init__(self, name="Base", description="Servidor base MCP", 
                               supported_actions=None, supported_resources=None):
                        self.name = name
                        self.description = description
                        self.supported_actions = supported_actions or []
                        self.supported_resources = supported_resources or []
                        self.logger = logging.getLogger(f"MCPServer.{name}")
                    
                    def handle_action(self, message):
                        """Método que debe ser implementado por subclases."""
                        return MockMCP.Protocol.MCPResponse(
                            success=False, 
                            error={"message": "Method not implemented"}
                        )
            
            class Client:
                class MCPClientBase:
                    """Clase base para clientes MCP."""
                    def __init__(self):
                        self.logger = logging.getLogger("MCPClientBase")
                    
                    def connect(self):
                        """Conecta con el servidor."""
                        return True
                    
                    def disconnect(self):
                        """Desconecta del servidor."""
                        return True
                    
                    def send_message(self, message):
                        """Envía un mensaje al servidor."""
                        return MockMCP.Protocol.MCPResponse(
                            success=False, 
                            error={"message": "Method not implemented"}
                        )
                    
                    def ping(self):
                        """Verifica disponibilidad del servidor."""
                        return MockMCP.Protocol.MCPResponse(success=True)
                    
                    def get_capabilities(self):
                        """Obtiene capacidades del servidor."""
                        return MockMCP.Protocol.MCPResponse(success=True)
                
                class MCPHttpClient:
                    def __init__(self, base_url, headers=None):
                        self.base_url = base_url
                        self.headers = headers or {}
                    
                    def connect(self):
                        # En un ejemplo real, esto conectaría con el servidor
                        print(f"Conectando a {self.base_url}...")
                        return True
                    
                    def disconnect(self):
                        # En un ejemplo real, esto desconectaría del servidor
                        print("Desconectando...")
                    
                    def ping(self):
                        # Simulación de ping
                        return MockMCP.Protocol.MCPResponse(success=True)
                    
                    def get_capabilities(self):
                        # Simulación de capabilities
                        return MockMCP.Protocol.MCPResponse(success=True, data={
                            "actions": ["echo", "ping", "get"],
                            "resources": ["system"]
                        })
                    
                    def send_message(self, message):
                        # Simulación de envío de mensaje
                        if message.action == "echo":
                            # El servidor de eco devuelve el mismo mensaje
                            return MockMCP.Protocol.MCPResponse(success=True, data={
                                "echo": message.data.get("message", ""),
                                "timestamp": "2023-01-01T00:00:00Z"
                            })
                        return MockMCP.Protocol.MCPResponse(success=False, error={"message": "Acción no soportada"})
        
        # Usar la implementación mock para el ejemplo
        MCPMessage = MockMCP.Protocol.MCPMessage
        MCPResponse = MockMCP.Protocol.MCPResponse
        MCPAction = MockMCP.Protocol.MCPAction
        MCPResource = MockMCP.Protocol.MCPResource
        MCPHttpClient = MockMCP.Client.MCPHttpClient
        MCPServerBase = MockMCP.Server.MCPServerBase
        MCPClientBase = MockMCP.Client.MCPClientBase
        
        # Funciones mock para initialize_mcp, shutdown_mcp y get_registry
        def initialize_mcp():
            print("Inicializando MCP mock...")
            return get_registry()
        
        async def async_initialize_mcp():
            print("Inicializando MCP mock (async)...")
            return get_registry()
        
        async def shutdown_mcp():
            print("Cerrando MCP mock...")
            return True
        
        def get_registry():
            class Registry:
                def register_client(self, name, client):
                    pass
                
                def register_server(self, name, server):
                    pass
            return Registry()
            
        print("Usando implementación mock para demostración")
    except Exception as mock_error:
        print(f"Error al crear mock: {mock_error}")
        print("No se pueden importar los módulos necesarios. Asegúrate de que el proyecto esté configurado correctamente.")
        sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mcp_echo_client_example")

# Implementar un servidor MCP simple de eco
class EchoServer(MCPServerBase):
    """Servidor MCP de eco simple para pruebas."""
    
    def __init__(self, name="echo", description="Servidor de eco para pruebas"):
        """Inicializa el servidor de eco."""
        super().__init__(
            name=name,
            description=description,
            supported_actions=[
                MCPAction.PING,
                MCPAction.CAPABILITIES,
                MCPAction.SEARCH,
                MCPAction.GET
            ],
            supported_resources=[
                MCPResource.SYSTEM,
                "web_search",
                "local_search"
            ]
        )
    
    def handle_action(self, message):
        """Maneja las acciones de los mensajes recibidos."""
        logger.info(f"Servidor recibió mensaje: {message.action} - {message.resource_type}")
        
        if message.action == MCPAction.PING:
            return MCPResponse.success_response(
                message_id=message.id,
                data={"status": "ok", "timestamp": time.time()}
            )
        
        elif message.action == MCPAction.CAPABILITIES:
            actions = []
            for action in self.supported_actions:
                if hasattr(action, 'value'):
                    actions.append(action.value)
                else:
                    actions.append(str(action))
            
            resources = []
            for resource in self.supported_resources:
                if hasattr(resource, 'value'):
                    resources.append(resource.value)
                else:
                    resources.append(str(resource))
                
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "actions": actions,
                    "resources": resources,
                    "version": "1.0",
                    "name": self.name,
                    "description": self.description
                }
            )
        
        elif message.action == MCPAction.SEARCH:
            query = message.data.get("query", "")
            if not query:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code="invalid_request",
                    message="Falta el parámetro query"
                )
            
            # Crear resultados de búsqueda de prueba
            count = message.data.get("count", 3)
            results = []
            for i in range(min(count, 5)):
                results.append({
                    "id": f"result-{i+1}",
                    "title": f"Resultado {i+1} para '{query}'",
                    "description": f"Este es un resultado de prueba para la búsqueda '{query}'",
                    "url": f"https://example.com/result/{i+1}"
                })
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }
            )
        
        elif message.action == MCPAction.GET:
            if message.resource_type == "web_search":
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "status": "ok",
                        "info": "Este es un recurso de búsqueda web"
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code="resource_not_found",
                    message=f"Recurso no encontrado: {message.resource_type}"
                )
        
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code="not_implemented",
                message=f"Acción no implementada: {message.action}"
            )

# Implementar un cliente MCP directo
class DirectClient(MCPClientBase):
    """Cliente MCP que se comunica directamente con un servidor en memoria."""
    
    def __init__(self, server):
        """Inicializa el cliente directo."""
        super().__init__()
        self.server = server
        self.is_connected = False
    
    def connect(self):
        """Establece conexión con el servidor."""
        logger.info(f"Conectando con servidor: {self.server.name}")
        self.is_connected = True
        return True
    
    def disconnect(self):
        """Cierra la conexión con el servidor."""
        logger.info(f"Desconectando del servidor: {self.server.name}")
        self.is_connected = False
        return True
    
    def send_message(self, message):
        """Envía un mensaje al servidor y devuelve la respuesta."""
        if not self.is_connected:
            return MCPResponse.error_response(
                message_id=message.id,
                code="not_connected",
                message="Cliente no conectado al servidor"
            )
        
        return self.server.handle_action(message)
    
    def ping(self):
        """Sobreescribe el método ping para asegurar que retorna un MCPResponse."""
        message = MCPMessage(
            action=MCPAction.PING,
            resource_type=MCPResource.SYSTEM,
            resource_path="/ping",
            data={}
        )
        return self.send_message(message)
    
    def get_capabilities(self):
        """Sobreescribe el método get_capabilities para asegurar que retorna un MCPResponse."""
        message = MCPMessage(
            action=MCPAction.CAPABILITIES,
            resource_type=MCPResource.SYSTEM,
            resource_path="/capabilities",
            data={}
        )
        return self.send_message(message)
    
    def search_resources(self, resource_type, query, **kwargs):
        """Sobreescribe el método search_resources para asegurar que retorna un MCPResponse."""
        data = dict(kwargs)
        data["query"] = query
        
        message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=resource_type,
            resource_path="/search",
            data=data
        )
        return self.send_message(message)

async def main():
    """
    Función principal asíncrona que ejecuta el ejemplo.
    """
    try:
        # Inicializar el subsistema MCP
        await async_initialize_mcp()
        registry = get_registry()
        
        # Crear y registrar un servidor de eco
        echo_server = EchoServer()
        registry.register_server("echo", echo_server)
        
        # Crear un cliente directo conectado al servidor
        client = DirectClient(echo_server)
        registry.register_client("direct", client)
        
        # Conectar al servidor
        if client.connect():
            logger.info("Conexión exitosa")
            
            # Verificar disponibilidad con ping
            ping_response = client.ping()
            logger.info(f"Ping al servidor: {'Exitoso' if ping_response.success else 'Fallido'}")
            logger.info(f"Datos del ping: {ping_response.data}")
            
            # Obtener capacidades del servidor
            try:
                capabilities_response = client.get_capabilities()
                if capabilities_response.success:
                    logger.info(f"Capacidades del servidor: {capabilities_response.data}")
                    
                    # Realizar búsqueda
                    query = "inteligencia artificial"
                    logger.info(f"Realizando búsqueda: {query}")
                    
                    search_response = client.search_resources(
                        resource_type="web_search",
                        query=query,
                        count=3
                    )
                    
                    if search_response.success:
                        logger.info("Búsqueda exitosa")
                        logger.info(f"Resultados: {search_response.data}")
                    else:
                        logger.error(f"Error en búsqueda: {search_response.error}")
                else:
                    logger.error(f"Error obteniendo capacidades: {capabilities_response.error}")
            except Exception as e:
                logger.error(f"Error durante la ejecución: {str(e)}")
            
            # Desconectar
            client.disconnect()
        else:
            logger.error("No se pudo conectar al servidor")
    
    except Exception as e:
        logger.exception(f"Error en ejemplo: {e}")
    finally:
        # Cerrar el subsistema MCP
        await shutdown_mcp()
        logger.info("Ejemplo finalizado")

if __name__ == "__main__":
    # Ejecutar ejemplo
    asyncio.run(main()) 