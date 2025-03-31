# Ejemplos de MCP

Este directorio contiene ejemplos de uso del protocolo MCP (Model Context Protocol).

## Ejemplos disponibles

### `mcp_core_example.py`

Ejemplo básico que muestra el funcionamiento del núcleo de MCP utilizando un cliente directo y un servidor de eco.

```bash
python examples/mcp/mcp_core_example.py
```

### `http_transport_example.py`

Ejemplo que demuestra cómo usar HTTP como transporte para MCP. Incluye:
- Implementación de un servidor web simple con aiohttp
- Exposición de un servidor MCP (EchoServer) a través de HTTP
- Uso de HttpClient para conectarse al servidor
- Envío de mensajes MCP a través de HTTP

```bash
python examples/mcp/http_transport_example.py
```

### `http_server_example.py`

Ejemplo más completo de un servidor HTTP para MCP, que incluye:
- Configuración avanzada de un servidor HTTP
- Registro de múltiples servidores MCP
- Cliente HTTP que interactúa con múltiples servidores MCP
- Operaciones sobre el sistema de archivos

```bash
python examples/mcp/http_server_example.py
```

### `sqlite_mcp_example.py`

Ejemplo de un servidor MCP basado en SQLite para almacenamiento persistente.

```bash
python examples/mcp/sqlite_mcp_example.py
```

### `nuevo/direct_usage_example.py`

Ejemplo simplificado que muestra cómo usar el cliente directo para conectarse a un servidor de eco.

```bash
python examples/mcp/nuevo/direct_usage_example.py
```

## Estructura de ejemplos

- **Clientes MCP**: Ejemplos de uso de diferentes tipos de clientes (directo, HTTP)
- **Servidores MCP**: Ejemplos de implementación de servidores MCP
- **Transporte**: Ejemplos de diferentes mecanismos de transporte (directo, HTTP)
- **Uso avanzado**: Ejemplos de funcionalidades adicionales

## Notas de uso

- Los ejemplos están diseñados para ser autocontenidos y fáciles de ejecutar
- Cada ejemplo incluye comentarios detallados para facilitar su comprensión
- La mayoría de los ejemplos utilizan servidores locales, por lo que no requieren configuración adicional
- Para los ejemplos que utilizan APIs externas, se requiere configurar credenciales

## Requisitos

Para ejecutar estos ejemplos, asegúrate de tener instaladas las dependencias necesarias:

```bash
pip install aiohttp aiohttp_cors
```

## Notas

- Los ejemplos están diseñados para ser educativos y demostrar conceptos clave
- Al ejecutar los ejemplos, verás la salida en la consola que explica cada paso
- Algunos ejemplos crean archivos temporales que son eliminados al finalizar 