#!/usr/bin/env python
"""
Ejemplo simplificado de MCP que utiliza un cliente y servidor en memoria.

Este script demuestra el uso básico del protocolo MCP con un cliente
y servidor que se comunican directamente en memoria, sin necesidad
de HTTP, sockets u otras comunicaciones de red.
"""

import os
import sys
import logging
import time

# Agregar el directorio padre al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import (
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPServerBase, 
    MCPClientBase,
    initialize_mcp, 
    shutdown_mcp, 
    get_registry
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mcp_echo_example")

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
            return MCPResponse(
                success=True,
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
                
            return MCPResponse(
                success=True,
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
                return MCPResponse(
                    success=False,
                    message_id=message.id,
                    error={
                        "code": "invalid_request",
                        "message": "Falta el parámetro query"
                    }
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
            
            return MCPResponse(
                success=True,
                message_id=message.id,
                data={
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }
            )
        
        elif message.action == MCPAction.GET:
            if message.resource_type == "web_search":
                return MCPResponse(
                    success=True,
                    message_id=message.id,
                    data={
                        "status": "ok",
                        "info": "Este es un recurso de búsqueda web"
                    }
                )
            else:
                return MCPResponse(
                    success=False,
                    message_id=message.id,
                    error={
                        "code": "resource_not_found",
                        "message": f"Recurso no encontrado: {message.resource_type}"
                    }
                )
        
        else:
            return MCPResponse(
                success=False,
                message_id=message.id,
                error={
                    "code": "not_implemented",
                    "message": f"Acción no implementada: {message.action}"
                }
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
            return MCPResponse(
                success=False,
                message_id=message.id,
                error={
                    "code": "not_connected",
                    "message": "Cliente no conectado al servidor"
                }
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

def main():
    """Función principal del ejemplo."""
    # Inicializar el subsistema MCP
    initialize_mcp()
    
    try:
        # Crear y registrar un servidor de eco
        echo_server = EchoServer()
        registry = get_registry()
        registry.register_server("echo", EchoServer)
        
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
        else:
            logger.error("No se pudo conectar al servidor")
    
    except Exception as e:
        logger.exception(f"Error en la ejecución: {str(e)}")
    
    finally:
        # Desconectar el cliente
        if 'client' in locals():
            client.disconnect()
        
        # Cerrar el subsistema MCP
        shutdown_mcp()
        logger.info("Ejemplo finalizado")

if __name__ == "__main__":
    main() 