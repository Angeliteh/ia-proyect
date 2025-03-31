# Ejemplos de MCP (Model Context Protocol)

Este directorio contiene ejemplos prácticos de uso del protocolo MCP (Model Context Protocol) con diferentes servidores y clientes.

## Ejemplos Disponibles

### Core MCP

- **mcp_core_example.py**: Ejemplo básico de la arquitectura cliente-servidor MCP con un servidor Echo
- **http_transport_example.py**: Demostración de comunicación MCP a través de HTTP

### Servidores MCP

- **filesystem_example.py**: Ejemplo de uso del servidor de sistema de archivos
- **sqlite_mcp_example.py**: Ejemplo de servidor SQLite para persistencia de datos
- **memory_example.py**: Ejemplo básico del servidor de memoria
- **memory_semantic_example.py**: Ejemplo avanzado de búsqueda semántica con el servidor de memoria

## Servidores Destacados

### Servidor SQLite

El ejemplo `sqlite_mcp_example.py` demuestra cómo el MCP puede interactuar con bases de datos SQLite:
- Conexión a base de datos
- Creación de tablas
- Operaciones CRUD
- Consultas SQL

### Servidor de Memoria Semántica

El ejemplo `memory_semantic_example.py` muestra las capacidades avanzadas de búsqueda semántica:
- Generación de embeddings para memorias
- Búsqueda por palabras clave vs. búsqueda semántica
- Implementación de un agente con memoria semántica
- Integración con sentence-transformers (si está disponible)

## Requisitos Adicionales

Algunos ejemplos pueden requerir bibliotecas adicionales:

```
pip install sentence-transformers  # Para memory_semantic_example.py
```

## Ejecución de Ejemplos

Para ejecutar un ejemplo específico:

```bash
# Desde la raíz del proyecto
python examples/mcp/memory_semantic_example.py
```

## Estructura de Directorio

```
examples/mcp/
├── data/                # Datos temporales generados por los ejemplos
├── mcp_core_example.py  # Ejemplo básico de MCP
├── http_transport_example.py  # Ejemplo de transporte HTTP
├── filesystem_example.py  # Ejemplo de sistema de archivos
├── sqlite_mcp_example.py  # Ejemplo de servidor SQLite
├── memory_example.py    # Ejemplo básico de memoria
├── memory_semantic_example.py  # Ejemplo de búsqueda semántica
└── README.md            # Este archivo
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