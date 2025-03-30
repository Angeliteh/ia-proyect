# Model Context Protocol (MCP)

Este módulo implementa el estándar Model Context Protocol (MCP) desarrollado por Anthropic, que permite a los modelos de IA conectarse con diversas fuentes de datos y herramientas.

## Arquitectura

El sistema MCP está diseñado con los siguientes componentes principales:

### Componentes Core (`mcp/core/`)

- **protocol.py**: Define las estructuras fundamentales como `MCPMessage`, `MCPResponse` y `MCPAction`.
- **server_base.py**: Proporciona la clase base `MCPServerBase` que todos los servidores MCP deben implementar.
- **client_base.py**: Define la interfaz `MCPClientBase` para los clientes MCP.
- **init.py**: Inicializa el entorno MCP, configurando el registro central y otros servicios.
- **registry.py**: Gestiona el registro de clientes y servidores MCP disponibles.

### Transporte (`mcp/transport/`)

- **http_server.py**: Implementa un servidor HTTP para exponer servidores MCP a través de REST.
- **websocket_server.py**: Soporte para comunicación MCP vía WebSockets.
- **base.py**: Define interfaces base para transportes MCP.

### Conectores (`mcp/connectors/`)

- **http_client.py**: Implementa un cliente HTTP genérico para comunicarse con servidores MCP.
- (Planificado) **websocket_client.py**: Cliente para comunicarse con servidores MCP vía WebSockets.

### Utilidades (`mcp/utils/`)

- **helpers.py**: Funciones de utilidad como configuración de logging y otras herramientas comunes.

## Flujo de Datos en MCP

1. Un **cliente MCP** construye un mensaje (`MCPMessage`) especificando:
   - Una acción (GET, SEARCH, CREATE, etc.)
   - Un tipo de recurso (DATABASE, FILE, WEB_SEARCH, etc.)
   - Una ruta de recurso (similar a una URL)
   - Datos adicionales (parámetros, filtros, etc.)

2. El mensaje se envía a un **servidor MCP** a través de un mecanismo de transporte (HTTP, WebSockets, etc.).

3. El **servidor MCP** procesa el mensaje, realiza la acción solicitada, y devuelve un `MCPResponse` con:
   - Indicador de éxito/error
   - Datos resultantes (si tiene éxito)
   - Información de error (si falla)

4. El **cliente MCP** recibe la respuesta y la procesa según sus necesidades.

## Ejemplo de Uso

### Crear un Cliente MCP

```python
from mcp.connectors.http_client import MCPHttpClient
from mcp.core.protocol import MCPMessage, MCPAction, MCPResource

# Crear un cliente HTTP
client = MCPHttpClient(base_url="http://localhost:8080")
client.connect()

# Crear un mensaje para buscar algo
message = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type=MCPResource.WEB_SEARCH,
    resource_path="/search",
    data={"query": "inteligencia artificial", "limit": 5}
)

# Enviar el mensaje y recibir respuesta
response = client.send_message(message)

# Procesar la respuesta
if response.success:
    results = response.data.get("results", [])
    for result in results:
        print(f"Título: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"---")
else:
    print(f"Error: {response.error.message}")
```

### Implementar un Servidor MCP

```python
from mcp.core.server_base import MCPServerBase
from mcp.core.protocol import MCPMessage, MCPResponse, MCPAction, MCPResource

class EchoMCPServer(MCPServerBase):
    """Servidor MCP simple que hace eco del mensaje recibido."""
    
    def __init__(self):
        super().__init__(
            name="echo_server",
            description="Un servidor MCP simple que hace eco del mensaje recibido",
            supported_actions=[MCPAction.GET, MCPAction.SEARCH],
            supported_resources=[MCPResource.SYSTEM]
        )
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """Procesa un mensaje MCP y devuelve una respuesta."""
        # Simplemente devuelve los datos del mensaje como respuesta
        return MCPResponse.success_response(
            message_id=message.id,
            data={"echo": message.data, "message": "Eco recibido"}
        )
```

## Implementaciones de Servidores MCP

Los servidores MCP implementados se encuentran en el directorio `mcp_servers/`. Cada implementación proporciona funcionalidades específicas:

- **SQLite**: Permite acceder y manipular bases de datos SQLite.
- (Planificado) **Brave Search**: Proporciona acceso a la API de búsqueda de Brave.
- (Planificado) **File System**: Acceso a archivos y directorios del sistema.

## Implementaciones de Clientes MCP

Los clientes MCP se implementan principalmente a través de los conectores genéricos en `mcp/connectors/`, con la clase base definida en `mcp_clients/base.py`. En la mayoría de los casos, no es necesario implementar clientes específicos, ya que los conectores genéricos son suficientes.

## Mejores Prácticas

1. **Servidores MCP**:
   - Implementar validación adecuada de mensajes entrantes
   - Manejar errores de forma robusta y devolver respuestas de error informativas
   - Documentar claramente qué acciones y recursos soporta el servidor

2. **Clientes MCP**:
   - Implementar reconexión automática en caso de fallos
   - Manejar correctamente los errores devueltos por el servidor
   - Validar los datos antes de enviarlos

3. **General**:
   - Usar tipos de datos adecuados para cada campo
   - Seguir el estándar MCP en cuanto a formato de mensajes y respuestas
   - Implementar logging adecuado para facilitar la depuración 