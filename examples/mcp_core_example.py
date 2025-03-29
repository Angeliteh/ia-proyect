"""
Ejemplo básico del núcleo MCP.

Este script muestra cómo usar las clases base del núcleo MCP para
crear servidores y clientes personalizados.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, Union

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Añadir la ruta del proyecto al PATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar componentes del núcleo MCP
from mcp.core.protocol import (
    MCPMessage, MCPResponse, MCPAction, MCPResource, MCPError, MCPErrorCode
)
from mcp.core.server_base import MCPServerBase
from mcp.core.client_base import MCPClientBase
from mcp.core.registry import MCPRegistry
from mcp import initialize_mcp, shutdown_mcp, get_registry

# Implementar un servidor MCP simple para demostración
class SimpleEchoServer(MCPServerBase):
    """
    Servidor MCP de ejemplo que simplemente hace eco de los mensajes.
    """
    
    def __init__(self, name: str = "echo", description: str = "Servidor de eco simple"):
        """
        Inicializa el servidor de eco.
        
        Args:
            name: Nombre del servidor
            description: Descripción del servidor
        """
        supported_actions = [
            MCPAction.PING,
            MCPAction.CAPABILITIES,
            MCPAction.GET,
            MCPAction.SEARCH
        ]
        
        supported_resources = [
            MCPResource.SYSTEM,
            "echo"  # Tipo de recurso personalizado
        ]
        
        super().__init__(
            name=name,
            description=description,
            supported_actions=supported_actions,
            supported_resources=supported_resources
        )
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja un mensaje MCP.
        
        Args:
            message: Mensaje a procesar
            
        Returns:
            Respuesta al mensaje
        """
        self.logger.info(f"Procesando mensaje: {message.action} {message.resource_path}")
        
        if message.action == MCPAction.GET.value:
            if message.resource_type == "echo":
                # Para recursos de tipo "echo", devolver la ruta como mensaje
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "echo": f"Eco de la ruta: {message.resource_path}",
                        "original_data": message.data
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message=f"Tipo de recurso no soportado para GET: {message.resource_type}"
                )
                
        elif message.action == MCPAction.SEARCH.value:
            if message.resource_type == "echo":
                # Para búsquedas, hacer eco de la consulta
                query = message.data.get("query", "")
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "echo": f"Eco de la búsqueda: {query}",
                        "results": [
                            {"id": 1, "text": f"Resultado 1 para '{query}'"},
                            {"id": 2, "text": f"Resultado 2 para '{query}'"}
                        ]
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message=f"Tipo de recurso no soportado para SEARCH: {message.resource_type}"
                )
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Acción no implementada: {message.action}"
            )

# Implementar un cliente MCP simple para demostración
class DirectClient(MCPClientBase):
    """
    Cliente MCP que se comunica directamente con un servidor local.
    """
    
    def __init__(self, server_name: str, server: MCPServerBase):
        """
        Inicializa el cliente directo.
        
        Args:
            server_name: Nombre del servidor
            server: Instancia del servidor
        """
        super().__init__(server_name=server_name)
        self.server = server
        self.connected = False
    
    async def connect(self) -> bool:
        """
        Establece conexión con el servidor.
        
        Returns:
            True si la conexión se estableció correctamente
        """
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        """
        Cierra la conexión con el servidor.
        """
        self.connected = False
    
    async def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje al servidor.
        
        Args:
            message: Mensaje a enviar
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si no está conectado o hay un error
        """
        if not self.connected:
            raise MCPError(
                code=MCPErrorCode.SERVICE_UNAVAILABLE,
                message="Cliente no conectado"
            )
        
        # Enviar mensaje directamente al servidor
        return await self.server.process_message(message)
        
    async def ping(self) -> bool:
        """
        Verifica la disponibilidad del servidor. Versión asíncrona.
        
        Returns:
            True si el servidor está disponible, False en caso contrario
        """
        try:
            message = MCPMessage.create_ping()
            message.auth_token = self.auth_token
            
            response = await self.send_message(message)
            return response.success
        except Exception as e:
            self.logger.error(f"Error en ping: {str(e)}")
            return False
            
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Obtiene las capacidades del servidor. Versión asíncrona.
        
        Returns:
            Diccionario con las capacidades del servidor
            
        Raises:
            MCPError: Si ocurre un error al obtener las capacidades
        """
        message = MCPMessage.create_capabilities_request()
        message.auth_token = self.auth_token
        
        response = await self.send_message(message)
        
        if not response.success:
            raise MCPError(
                code=response.error.code if response.error else MCPErrorCode.SERVER_ERROR,
                message=f"Error obteniendo capacidades: {response.error.message if response.error else 'Error desconocido'}"
            )
        
        self._server_capabilities = response.data
        return self._server_capabilities
    
    async def get_resource(self, resource_type: Union[MCPResource, str], resource_path: str, **params) -> MCPResponse:
        """
        Obtiene un recurso del servidor. Versión asíncrona.
        
        Args:
            resource_type: Tipo de recurso
            resource_path: Ruta del recurso
            **params: Parámetros adicionales para la solicitud
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        message = MCPMessage.create_get_request(
            resource_type=resource_type,
            resource_path=resource_path,
            params=params
        )
        message.auth_token = self.auth_token
        
        return await self.send_message(message)
    
    async def search_resources(self, resource_type: Union[MCPResource, str], query: str, **params) -> MCPResponse:
        """
        Busca recursos en el servidor. Versión asíncrona.
        
        Args:
            resource_type: Tipo de recurso
            query: Consulta de búsqueda
            **params: Parámetros adicionales para la búsqueda
            
        Returns:
            Respuesta del servidor
            
        Raises:
            MCPError: Si ocurre un error en la comunicación
        """
        all_params = params.copy()
        all_params["query"] = query
        
        message = MCPMessage.create_search_request(
            resource_type=resource_type,
            query=query,
            params=params
        )
        message.auth_token = self.auth_token
        
        return await self.send_message(message)


async def run_example():
    """
    Ejecuta el ejemplo de demostración.
    """
    logger = logging.getLogger("example")
    logger.info("Iniciando ejemplo del núcleo MCP")
    
    try:
        # Crear y registrar un servidor de eco
        registry = get_registry()
        
        echo_server = SimpleEchoServer(name="echo_server")
        registry.register_server("echo", SimpleEchoServer)
        
        # Crear un cliente directo para el servidor
        client = DirectClient(server_name="echo", server=echo_server)
        
        # Conectar con el servidor
        logger.info("Conectando con el servidor...")
        await client.connect()
        
        # Verificar disponibilidad (ping)
        logger.info("Enviando ping al servidor...")
        ping_result = await client.ping()
        logger.info(f"Resultado del ping: {'Exitoso' if ping_result else 'Fallido'}")
        
        # Obtener capacidades del servidor
        logger.info("Obteniendo capacidades del servidor...")
        capabilities = await client.get_capabilities()
        logger.info(f"Capacidades del servidor: {capabilities}")
        
        # Enviar solicitud GET
        logger.info("Enviando solicitud GET...")
        response_get = await client.get_resource(
            resource_type="echo", 
            resource_path="/hello/world",
            param1="value1",
            param2=123
        )
        
        if response_get.success:
            logger.info(f"Respuesta GET: {response_get.data}")
        else:
            logger.error(f"Error en GET: {response_get.error.message}")
        
        # Enviar solicitud de búsqueda
        logger.info("Enviando solicitud de búsqueda...")
        response_search = await client.search_resources(
            resource_type="echo",
            query="Búsqueda de ejemplo",
            limit=10
        )
        
        if response_search.success:
            logger.info(f"Respuesta de búsqueda: {response_search.data}")
        else:
            logger.error(f"Error en búsqueda: {response_search.error.message}")
        
        # Probar un mensaje con acción no soportada
        logger.info("Enviando mensaje con acción no soportada...")
        unsupported_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="echo",
            resource_path="/test",
            data={"content": "Prueba"}
        )
        
        response_unsupported = await client.send_message(unsupported_message)
        if not response_unsupported.success:
            logger.info(f"Error esperado: {response_unsupported.error.message}")
        
        # Desconectar
        logger.info("Desconectando del servidor...")
        await client.disconnect()
        
        logger.info("Ejemplo completado con éxito")
    
    except Exception as e:
        logger.exception(f"Error en el ejemplo: {e}")
    finally:
        # Cerrar el subsistema MCP
        await async_shutdown_mcp()


async def async_shutdown_mcp():
    """Versión asíncrona de shutdown_mcp para usar con await."""
    shutdown_mcp()
    return None


if __name__ == "__main__":
    # Ejecutar ejemplo
    asyncio.run(run_example()) 