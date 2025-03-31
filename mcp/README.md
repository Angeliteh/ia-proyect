# Model Context Protocol (MCP)

## Estructura

La implementación del Model Context Protocol (MCP) sigue la siguiente estructura:

```
mcp/
├── core/             # Núcleo del protocolo
│   ├── protocol.py   # Definiciones del protocolo (mensajes, acciones, etc.)
│   ├── server_base.py # Clase base para servidores
│   ├── client_base.py # Clase base para clientes
│   ├── registry.py   # Sistema de registro
│   ├── mcp_manager.py # Gestor principal de MCP
│   └── init.py       # Funciones de inicialización
├── protocol/         # Definiciones y extensiones del protocolo
├── connectors/       # Adaptadores y conectores genéricos
├── transport/        # Componentes de transporte
├── utils/            # Utilidades para MCP
├── servers/          # Implementaciones de servidores
│   ├── echo_server.py # Servidor de eco para pruebas
│   ├── brave_search_server.py # Servidor para Brave Search
│   └── filesystem/   # Servidor para sistema de archivos
└── clients/          # Implementaciones de clientes
    ├── direct_client.py # Cliente para conexión directa
    └── README.md     # Documentación de clientes
```

## Componentes Principales

### Core

El núcleo del MCP contiene las definiciones fundamentales del protocolo:

- `protocol.py`: Define `MCPMessage`, `MCPResponse`, `MCPAction`, etc.
- `server_base.py`: Clase base `MCPServerBase` para todos los servidores
- `client_base.py`: Clase base `MCPClientBase` para todos los clientes
- `registry.py`: Sistema de registro para servidores y clientes
- `mcp_manager.py`: Gestor principal que proporciona una interfaz unificada
- `init.py`: Funciones para inicializar y apagar el sistema MCP

### Servidores

Los servidores MCP implementan la interfaz definida por `MCPServerBase`:

- `EchoServer`: Servidor simple para pruebas que devuelve los datos recibidos
- `BraveSearchServer`: Servidor que proporciona búsqueda web a través de Brave Search API
- `FilesystemServer`: Servidor para acceder al sistema de archivos

### Clientes

Los clientes MCP implementan la interfaz definida por `MCPClientBase`:

- `SimpleDirectClient`: Cliente para conexión directa con servidores locales

## Uso Básico

```python
# Inicializar MCP
from mcp import initialize_mcp, MCPMessage
from mcp.servers import EchoServer
from mcp.clients import SimpleDirectClient

# Crear servidor y cliente
server = EchoServer()
client = SimpleDirectClient(server)

# Conectar
client.connect()

# Enviar mensaje
message = MCPMessage.create_ping()
response = client.send_message(message)
print(response.data)

# Desconectar
client.disconnect()
```

## Migración desde la versión anterior

Si estás utilizando las clases antiguas (`MCPServer` y `MCPClient`), puedes migrar gradualmente a la nueva estructura:

1. Primero, utiliza el módulo de compatibilidad:
   ```python
   from mcp.compat import MCPServer, MCPClient
   ```

2. Luego, migra a las nuevas clases base:
   ```python
   from mcp.core import MCPServerBase, MCPClientBase
   ```

Las clases antiguas están marcadas como obsoletas y serán eliminadas en versiones futuras.

## Ejemplos

Puedes encontrar ejemplos de uso en la carpeta `examples/mcp/`. 