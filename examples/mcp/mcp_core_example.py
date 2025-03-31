"""
Ejemplo simplificado del protocolo MCP (Model Context Protocol).

Este ejemplo demuestra:
1. Cómo implementar un servidor MCP simple (EchoServer)
2. Cómo implementar un cliente MCP simple (SimpleDirectClient)
3. Cómo establecer comunicación cliente-servidor
4. Cómo realizar operaciones básicas del protocolo
"""

import asyncio
import logging
import sys
import os
import uuid
from typing import Dict, Any, Optional

# Aseguramos que el directorio raíz del proyecto esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Importamos los componentes básicos de MCP
try:
    from mcp import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPError, MCPErrorCode
    from mcp import MCPServerBase, MCPClientBase
except ImportError as e:
    print(f"Error al importar módulos MCP: {e}")
    print(f"Ruta de búsqueda actual: {sys.path}")
    sys.exit(1)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("mcp_example")

# --------------------- IMPLEMENTACIÓN DEL SERVIDOR -----------------------

class EchoServer(MCPServerBase):
    """
    Un servidor MCP sencillo que simplemente devuelve (eco) los datos que recibe.
    """
    
    def __init__(self):
        """Inicializa el servidor de eco."""
        super().__init__(
            name="echo_server",
            description="Servidor MCP de eco para pruebas",
            auth_required=False,
            supported_actions=[
                MCPAction.PING,
                MCPAction.CAPABILITIES, 
                MCPAction.GET,
                MCPAction.LIST,
                MCPAction.SEARCH,
                "echo"  # Acción personalizada como cadena
            ],
            supported_resources=[
                MCPResource.SYSTEM,
                "test"  # Recurso personalizado
            ]
        )
        # Datos simulados para demostración
        self.test_data = {
            "/test1": {"id": "1", "name": "Test Item 1", "value": "Hello, world!"},
            "/test2": {"id": "2", "name": "Test Item 2", "value": "Hello again!"},
            "/test/nested": {"id": "3", "name": "Nested Item", "value": "I'm nested!"}
        }
        
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja las acciones recibidas por el servidor.
        """
        # Simular un pequeño retraso para hacer la demo más realista
        await asyncio.sleep(0.1)
        
        logger.info(f"EchoServer recibió: {message.action} - {message.resource_path}")
        
        # Acción personalizada de eco
        if message.action == "echo":
            # Simplemente devolvemos los datos recibidos
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "echo": message.data,
                    "message": "¡Eco del servidor!",
                    "path": message.resource_path
                }
            )
            
        # Acción estándar GET
        elif message.action == MCPAction.GET.value:
            # Verificamos si el recurso existe
            if message.resource_path in self.test_data:
                return MCPResponse.success_response(
                    message_id=message.id,
                    data=self.test_data[message.resource_path]
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Recurso no encontrado: {message.resource_path}"
                )
                
        # Acción estándar LIST
        elif message.action == MCPAction.LIST.value:
            # Listamos recursos que comienzan con el path proporcionado
            result = {}
            for path, data in self.test_data.items():
                if path.startswith(message.resource_path):
                    result[path] = data
                    
            return MCPResponse.success_response(
                message_id=message.id,
                data={"items": result}
            )
            
        # Acción estándar SEARCH
        elif message.action == MCPAction.SEARCH.value:
            # Simulamos una búsqueda simple por valor
            query = message.data.get("query", "")
            result = {}
            
            for path, data in self.test_data.items():
                if query.lower() in str(data).lower():
                    result[path] = data
                    
            return MCPResponse.success_response(
                message_id=message.id,
                data={"results": result, "query": query}
            )
            
        # Acción no implementada
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Acción no implementada: {message.action}"
            )

# --------------------- IMPLEMENTACIÓN DEL CLIENTE -----------------------

class SimpleDirectClient(MCPClientBase):
    """
    Un cliente MCP simple para comunicarse con servidores MCP locales.
    """
    
    def __init__(self, server_instance: MCPServerBase, server_name: str = None):
        """
        Inicializa un cliente MCP simple.
        """
        super().__init__(server_name=server_name or server_instance.name)
        self.server = server_instance
        self.connected = False
        
    def connect(self) -> bool:
        """
        Establece conexión con el servidor MCP.
        """
        self.connected = True
        logger.info(f"Cliente conectado al servidor: {self.server_name}")
        return True
        
    def disconnect(self) -> bool:
        """
        Cierra la conexión con el servidor MCP.
        """
        self.connected = False
        logger.info(f"Cliente desconectado del servidor: {self.server_name}")
        return True
        
    def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Envía un mensaje al servidor MCP y espera la respuesta.
        """
        if not self.connected:
            raise MCPError(
                code=MCPErrorCode.CONNECTION_ERROR,
                message="No hay conexión con el servidor"
            )
        
        logger.info(f"Enviando mensaje: {message.action} - {message.resource_path}")
        
        # Procesamos el mensaje de forma sincrónica
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self.server.process_message(message))
            return response
        finally:
            loop.close()
            logger.info(f"Respuesta recibida: success={(response.success if 'response' in locals() else False)}")

    def send_echo(self, data: Dict[str, Any], path: str = "/echo") -> MCPResponse:
        """
        Envía un mensaje de eco personalizado utilizando un método alternativo.
        """
        # En lugar de crear un objeto MCPMessage, creamos manualmente un mensaje
        # personalizado que el servidor pueda manejar
        from mcp.core.protocol import MCPMessage as RawMCPMessage
        
        # Creamos una instancia directa de MCPMessage sin usar los constructores que validan
        message = RawMCPMessage.__new__(RawMCPMessage)
        message.id = str(uuid.uuid4())
        message.action = "echo"  # Asignamos directamente la acción como string
        message.resource_type = "test"
        message.resource_path = path
        message.data = data
        message.auth_token = None
        
        return self.send_message(message)

# --------------------- FUNCIÓN PRINCIPAL DE DEMO -----------------------

def run_demo():
    """Ejecuta una demostración de las funcionalidades básicas de MCP."""
    
    logger.info("Iniciando demostración de MCP...")
    
    # Creamos el servidor
    server = EchoServer()
    logger.info(f"Servidor creado: {server.name}")
    
    # Creamos el cliente
    client = SimpleDirectClient(server)
    
    try:
        # Establecemos conexión
        client.connect()
        
        # 1. Enviamos un ping para verificar la conexión
        logger.info("\n--- PING ---")
        ping_message = MCPMessage.create_ping()
        ping_response = client.send_message(ping_message)
        print(f"Ping respuesta: {ping_response.success} - {ping_response.data}")
        
        # 2. Obtenemos las capacidades del servidor
        logger.info("\n--- CAPACIDADES ---")
        capabilities = client.get_capabilities()
        print(f"Servidor: {capabilities['name']}")
        print(f"Descripción: {capabilities['description']}")
        print(f"Acciones soportadas: {capabilities['supported_actions']}")
        print(f"Recursos soportados: {capabilities['supported_resources']}")
        
        # 3. Obtenemos un recurso específico
        logger.info("\n--- GET ---")
        get_response = client.get_resource("test", "/test1")
        if get_response.success:
            print(f"Recurso obtenido: {get_response.data}")
        else:
            print(f"Error: {get_response.error.message}")
            
        # 4. Listamos recursos
        logger.info("\n--- LIST ---")
        list_response = client.list_resources("test", "/")
        if list_response.success:
            print(f"Recursos listados: {list_response.data}")
        else:
            print(f"Error: {list_response.error.message}")
            
        # 5. Buscamos recursos
        logger.info("\n--- SEARCH ---")
        search_response = client.search_resources("test", "Hello")
        if search_response.success:
            print(f"Resultados de búsqueda: {search_response.data}")
        else:
            print(f"Error: {search_response.error.message}")
            
        # 6. Enviamos un mensaje de eco personalizado
        logger.info("\n--- ECHO PERSONALIZADO ---")
        echo_response = client.send_echo(
            {"message": "Hola, servidor!", "timestamp": "2023-01-01"}
        )
        if echo_response.success:
            print(f"Eco recibido: {echo_response.data}")
        else:
            print(f"Error: {echo_response.error.message}")
            
        # 7. Intentamos una operación no soportada
        logger.info("\n--- OPERACIÓN NO SOPORTADA ---")
        unsupported_message = MCPMessage(
            action=MCPAction.CREATE,
            resource_type="test",
            resource_path="/new",
            data={"value": "New item"}
        )
        unsupported_response = client.send_message(unsupported_message)
        if not unsupported_response.success:
            print(f"Error esperado: {unsupported_response.error.message}")
            
    except Exception as e:
        logger.error(f"Error en la demo: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Desconectamos el cliente
        client.disconnect()
        logger.info("Demo finalizada")

if __name__ == "__main__":
    run_demo()
