"""
Ejemplo simplificado de transporte HTTP para MCP.

Este ejemplo demuestra:
1. Cómo crear un servidor web para exponer un servidor MCP (EchoServer)
2. Cómo crear un cliente HTTP para conectarse al servidor
3. Cómo enviar y recibir mensajes a través de HTTP

Para ejecutar el ejemplo:
    python examples/mcp/http_transport_example.py
"""

import asyncio
import logging
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional, List
from aiohttp import web
import datetime

# Aseguramos que el directorio raíz del proyecto esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("http_transport_example")

# Importamos los componentes necesarios
try:
    from mcp.core import MCPServerBase, MCPMessage, MCPResponse, MCPRegistry, MCPAction
    from mcp.servers import EchoServer
    from mcp.clients import HttpClient
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    sys.exit(1)

# Puerto para el servidor HTTP
HTTP_PORT = 8080

# Crear una subclase de MCPMessage que permita acciones personalizadas
class CustomMessage(MCPMessage):
    """
    Subclase de MCPMessage que permite acciones personalizadas.
    
    Esta clase sobrescribe el constructor para permitir acciones que no están
    definidas en el enum MCPAction, como "echo" que usa el EchoServer.
    
    Restricciones importantes:
    1. EchoServer solo acepta los siguientes tipos de recursos:
       - MCPResource.SYSTEM (para acciones estándar)
       - "test" (tipo personalizado para acciones como "echo")
    2. EchoServer acepta estas acciones:
       - MCPAction.PING, MCPAction.CAPABILITIES, MCPAction.GET, MCPAction.LIST, MCPAction.SEARCH
       - "echo" (acción personalizada)
    
    Usar valores no soportados resultará en errores como:
    - "Tipo de recurso no soportado: xxx"
    - "Acción no implementada: xxx"
    """
    def __init__(
        self,
        action,
        resource_type,
        resource_path,
        data=None,
        auth_token=None,
        message_id=None,
        timestamp=None
    ):
        """
        Inicializa un mensaje con acción personalizada.
        
        Args:
            action: Acción a realizar (puede ser una cadena personalizada como "echo")
            resource_type: Tipo de recurso (use "test" para EchoServer con acciones personalizadas)
            resource_path: Ruta del recurso
            data: Datos adicionales para la acción
            auth_token: Token de autenticación (opcional)
            message_id: ID del mensaje (generado automáticamente si no se proporciona)
            timestamp: Marca de tiempo (generada automáticamente si no se proporciona)
        """
        self.id = message_id or str(uuid.uuid4())
        
        # Guardar la acción tal cual sin intentar convertirla a enum
        self.action = action
        
        # El resto es igual que en MCPMessage
        if hasattr(resource_type, 'value'):
            self.resource_type = resource_type
        else:
            try:
                from mcp.core import MCPResource
                self.resource_type = MCPResource(resource_type)
            except ValueError:
                # Si no es un valor válido de MCPResource, mantenerlo como cadena
                self.resource_type = resource_type
                
        self.resource_path = resource_path
        self.data = data or {}
        self.auth_token = auth_token
        self.timestamp = timestamp or datetime.datetime.now()

# Creamos un servidor web simple usando aiohttp
async def handle_mcp_message(request):
    """
    Maneja mensajes MCP recibidos vía HTTP.
    
    Este handler procesa los mensajes MCP que llegan al servidor web y los
    redirecciona al servidor MCP correspondiente (identificado por server_name).
    
    Flujo de procesamiento:
    1. Obtiene el nombre del servidor del URL (/api/mcp/{server_name})
    2. Verifica que el servidor existe en el registro
    3. Parsea el cuerpo JSON de la solicitud
    4. Crea un mensaje CustomMessage que permite acciones personalizadas
    5. Envía el mensaje al servidor MCP para procesamiento
    6. Devuelve la respuesta como JSON
    
    Restricciones importantes:
    - El servidor debe estar registrado en app['registry']._instances
    - El mensaje debe tener un formato válido (JSON con action, resource_type, etc.)
    - El tipo de recurso debe ser compatible con el servidor
      (EchoServer acepta "test" o MCPResource.SYSTEM)
    - La acción debe ser compatible con el servidor
      (EchoServer acepta acciones estándar y "echo")
    
    Args:
        request: Objeto Request de aiohttp que contiene la información de la solicitud HTTP
        
    Returns:
        Respuesta HTTP con el resultado del procesamiento del mensaje
    """
    server_name = request.match_info['server_name']
    
    # Verificar que el servidor existe
    if server_name not in app['registry']._instances:
        return web.json_response({
            "success": False,
            "message_id": str(uuid.uuid4()),
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Servidor no encontrado: {server_name}"
            }
        }, status=404)
    
    server = app['registry']._instances[server_name]
    
    # Leer el cuerpo de la solicitud como JSON
    try:
        message_data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({
            "success": False,
            "message_id": str(uuid.uuid4()),
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Cuerpo de solicitud JSON inválido"
            }
        }, status=400)
    
    # Crear objeto MCPMessage
    try:
        message = CustomMessage(
            message_id=message_data.get('id', str(uuid.uuid4())),
            action=message_data.get('action'),
            resource_type=message_data.get('resource_type'),
            resource_path=message_data.get('resource_path', '/'),
            data=message_data.get('data', {})
        )
    except Exception as e:
        return web.json_response({
            "success": False,
            "message_id": message_data.get('id', str(uuid.uuid4())),
            "error": {
                "code": "INVALID_REQUEST",
                "message": f"Error creando mensaje: {str(e)}"
            }
        }, status=400)
    
    # Procesar mensaje en el servidor MCP
    try:
        response = await server.process_message(message)
        return web.json_response(response.to_dict())
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")
        return web.json_response({
            "success": False,
            "message_id": message.id,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Error procesando mensaje: {str(e)}"
            }
        }, status=500)

async def handle_list_servers(request):
    """Maneja solicitudes para listar servidores disponibles."""
    servers = []
    
    for name, server in app['registry']._instances.items():
        servers.append({
            "name": name,
            "description": server.description,
            "auth_required": server.auth_required,
            "supported_actions": [
                action.value if hasattr(action, 'value') else action
                for action in server.supported_actions
            ],
            "supported_resources": [
                resource.value if hasattr(resource, 'value') else resource
                for resource in server.supported_resources
            ]
        })
    
    return web.json_response({
        "servers": servers,
        "count": len(servers)
    })

async def handle_health_check(request):
    """Maneja solicitudes de verificación de salud."""
    return web.json_response({
        "status": "ok",
        "servers": len(app['registry']._instances),
        "timestamp": asyncio.get_event_loop().time()
    })

async def init_app():
    """Inicializa la aplicación web."""
    global app
    app = web.Application()
    
    # Crear registro de servidores
    registry = MCPRegistry()
    app['registry'] = registry
    
    # Registrar servidores MCP
    echo_server = EchoServer()
    registry._instances[echo_server.name] = echo_server  # Registrar la instancia directamente
    
    # Configurar rutas
    app.router.add_post('/api/mcp/{server_name}', handle_mcp_message)
    app.router.add_get('/api/mcp/servers', handle_list_servers)
    app.router.add_get('/api/mcp/health', handle_health_check)
    
    return app

def print_section_header(title):
    """Imprime un encabezado de sección con formato tabulado."""
    separator = "=" * 80
    logger.info("\n" + separator)
    logger.info(f"  {title}")
    logger.info(separator)

async def run_client():
    """Ejecuta el cliente HTTP MCP para probar el servidor."""
    # Crear variable para almacenar la URL
    server_url = f"http://localhost:{HTTP_PORT}/api/mcp/echo_server"
    
    # Crear una subclase personalizada de HttpClient que arregle los problemas
    class FixedHttpClient(HttpClient):
        """
        Versión mejorada de HttpClient que resuelve problemas de inconsistencia.
        
        Problemas que soluciona:
        1. HttpClient recibe server_url como parámetro, pero lo pasa como server_name 
           a la clase base MCPClientBase y no lo guarda como atributo.
        2. Los métodos de HttpClient intentan usar self.server_url pero ese atributo
           no existe, ya que solo existe self.server_name en la clase base.
        3. retry_attempts se pasa a la clase base pero no se almacena como atributo,
           aunque luego se usa en send_message.
        
        Esta subclase corrige estos problemas manteniendo la misma interfaz.
        """
        def __init__(self, server_url, timeout=30, retry_attempts=3, **kwargs):
            """
            Inicializa un cliente HTTP para MCP con las correcciones necesarias.
            
            Args:
                server_url: URL del servidor MCP (ej: 'http://localhost:8080/api/mcp')
                timeout: Tiempo de espera en segundos para operaciones HTTP
                retry_attempts: Número de intentos de reconexión
                **kwargs: Parámetros adicionales para HttpClient
            """
            super().__init__(server_url, timeout=timeout, retry_attempts=retry_attempts, **kwargs)
            # Guardar server_url como atributo de instancia
            self.server_url = server_url
            # Guardar retry_attempts como atributo de instancia
            self.retry_attempts = retry_attempts
        
        async def connect(self) -> bool:
            """
            Versión corregida de connect() que usa server_url en lugar de server_name.
            
            Returns:
                True si la conexión se estableció correctamente
            """
            try:
                if await self.transport.connect():
                    self.connected = True
                    self.logger.info(f"Cliente conectado a {self.server_url}")
                    return True
            except Exception as e:
                self.logger.error(f"Error conectando a {self.server_url}: {str(e)}")
            return False
        
        async def disconnect(self) -> bool:
            """
            Versión corregida de disconnect() que usa server_url en lugar de server_name.
            
            Returns:
                True si la desconexión fue exitosa
            """
            try:
                if await self.transport.disconnect():
                    self.connected = False
                    self.logger.info(f"Cliente desconectado de {self.server_url}")
                    return True
            except Exception as e:
                self.logger.error(f"Error desconectando de {self.server_url}: {str(e)}")
            self.connected = False
            return False
            
        async def get_capabilities(self) -> Dict[str, Any]:
            """
            Versión corregida de get_capabilities que usa el método correcto.
            
            La clase HttpClient usa MCPMessage.create_capabilities() que no existe,
            mientras que el método correcto es MCPMessage.create_capabilities_request().
            
            Returns:
                Diccionario con las capacidades del servidor
            """
            message = MCPMessage.create_capabilities_request()
            response = await self.send_message(message)
            
            if response.success:
                return response.data
            else:
                self.logger.error(f"Error obteniendo capacidades: {response.error.message}")
                return {}
    
    # Crear cliente HTTP con nuestra implementación corregida
    client = FixedHttpClient(
        server_url,
        timeout=30,
        retry_attempts=3
    )
    
    try:
        # Conectar al servidor
        await client.connect()
        
        # 1. Consultar servidores disponibles
        print_section_header("CONSULTANDO SERVIDORES DISPONIBLES")
        async with client.transport.session.get(
            f"http://localhost:{HTTP_PORT}/api/mcp/servers"
        ) as response:
            servers_data = await response.json()
            logger.info(f"Servidores disponibles: {len(servers_data['servers'])}")
            for server in servers_data['servers']:
                logger.info(f"  • {server['name']}: {server['description']}")
        
        # 2. Enviar un ping
        print_section_header("PING AL SERVIDOR ECHO")
        ping_result = await client.ping()
        logger.info(f"Ping resultado: {ping_result}")
        
        # 3. Obtener capacidades
        print_section_header("CAPACIDADES DEL SERVIDOR ECHO")
        capabilities = await client.get_capabilities()
        if capabilities:
            logger.info("Acciones soportadas:")
            for action in capabilities.get('supported_actions', []):
                logger.info(f"  • {action}")
            
            logger.info("Recursos soportados:")
            for resource in capabilities.get('supported_resources', []):
                logger.info(f"  • {resource}")
        else:
            logger.warning("No se pudieron obtener las capacidades del servidor")
        
        # 4. Enviar mensajes personalizados a través de HTTP
        print_section_header("MENSAJES PERSONALIZADOS")
        
        # Mensaje de eco simple
        echo_message = CustomMessage(
            action="echo",
            resource_type="test",
            resource_path="/echo",
            data={"message": "¡Hola desde el cliente HTTP!"}
        )
        response = await client.send_message(echo_message)
        if response.success:
            logger.info("✓ Respuesta eco simple:")
            logger.info(f"  • Mensaje: {response.data.get('echo', {}).get('message', '')}")
            if 'path' in response.data:
                logger.info(f"  • Ruta: {response.data.get('path', '')}")
        else:
            logger.error(f"✗ Error: {response.error.message}")
        
        # Mensaje con tiempo de procesamiento
        echo_delay = CustomMessage(
            action="echo",
            resource_type="test",
            resource_path="/echo_delay",
            data={"message": "Mensaje con retraso", "delay": 1.0}
        )
        response = await client.send_message(echo_delay)
        if response.success:
            logger.info("✓ Respuesta eco con retraso:")
            logger.info(f"  • Mensaje: {response.data.get('echo', {}).get('message', '')}")
            logger.info(f"  • Tiempo de procesamiento: {response.data.get('processing_time', 0)} segundos")
        else:
            logger.error(f"✗ Error: {response.error.message}")
        
        # Mensaje con transformación
        echo_transform = CustomMessage(
            action="echo",
            resource_type="test",
            resource_path="/echo_transform",
            data={"message": "transformar este texto", "transform": "uppercase"}
        )
        response = await client.send_message(echo_transform)
        if response.success:
            logger.info("✓ Respuesta eco con transformación:")
            logger.info(f"  • Mensaje original: {echo_transform.data.get('message', '')}")
            logger.info(f"  • Transformación: {echo_transform.data.get('transform', '')}")
            logger.info(f"  • Resultado: {response.data.get('echo', {}).get('message', '')}")
        else:
            logger.error(f"✗ Error: {response.error.message}")
        
    except Exception as e:
        logger.error(f"Error en el cliente: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Desconectar cliente
        await client.disconnect()
        logger.info("Cliente desconectado correctamente.")

async def main():
    """Función principal del ejemplo."""
    # Inicializar aplicación web
    app = await init_app()
    
    # Iniciar servidor HTTP
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', HTTP_PORT)
    await site.start()
    
    logger.info(f"Servidor HTTP iniciado en http://localhost:{HTTP_PORT}/api/mcp")
    
    try:
        # Ejecutar cliente
        await run_client()
    finally:
        # Detener servidor
        await runner.cleanup()
        logger.info("Servidor HTTP detenido.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Ejemplo interrumpido por el usuario.")
    except Exception as e:
        logger.error(f"Error en el ejemplo: {str(e)}")
        import traceback
        traceback.print_exc() 