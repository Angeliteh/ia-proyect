# Servidor MCP para SQLite

Este módulo implementa un servidor MCP (Model Context Protocol) que permite a los modelos de IA interactuar con bases de datos SQLite a través de operaciones estándar y consultas SQL personalizadas.

## Características

- **Operaciones CRUD completas** para bases de datos y tablas SQLite
- **Consultas SQL personalizadas** con soporte para parámetros
- **Paginación** para listar grandes conjuntos de datos
- **Validación y sanitización** de consultas SQL y nombres de archivos
- **Exposición vía HTTP** para acceso remoto
- **CLI** para iniciar el servidor desde línea de comandos

## Estructura del módulo

```
mcp_servers/sqlite/
├── __init__.py            # Exporta las clases y funciones principales
├── sqlite_server.py       # Implementación principal del servidor SQLite MCP
├── cli.py                 # Herramienta de línea de comandos
└── README.md              # Esta documentación
```

## Acciones soportadas

El servidor SQLite MCP soporta las siguientes acciones MCP:

- **GET**: Obtener información sobre bases de datos, tablas y ejecutar consultas de tipo SELECT
- **LIST**: Listar bases de datos, tablas y registros con soporte para paginación
- **SEARCH**: Buscar registros con criterios específicos y consultas personalizadas
- **CREATE**: Crear bases de datos, tablas y registros
- **UPDATE**: Actualizar registros existentes
- **DELETE**: Eliminar bases de datos, tablas y registros

## Recursos soportados

- **database**: Representa una base de datos SQLite
- **table**: Representa una tabla dentro de una base de datos
- **query**: Permite ejecutar consultas SQL personalizadas

## Instalación

El servidor SQLite MCP es parte del sistema MCP y no requiere instalación adicional más allá de las dependencias estándar de Python.

Dependencias:
- Python 3.8+
- SQLite3 (incluido en Python estándar)
- Módulos MCP core

## Ejemplos de uso

### Uso como servidor independiente

```python
import asyncio
from mcp_servers.sqlite import SQLiteMCPServer, run_http_server

# Ruta donde se almacenarán las bases de datos
db_path = "./sqlite_databases"

# Iniciar servidor HTTP en localhost:8080
http_server, port = run_http_server(host="localhost", port=8080, db_path=db_path)

print(f"Servidor SQLite MCP iniciado en http://localhost:{port}")

# Mantener el servidor en ejecución
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print("Deteniendo servidor...")
    http_server.shutdown()
```

### Uso desde línea de comandos

```bash
# Iniciar servidor con opciones por defecto
python -m mcp_servers.sqlite.cli

# Especificar host, puerto y directorio de bases de datos
python -m mcp_servers.sqlite.cli --host 0.0.0.0 --port 8888 --db-path /ruta/a/mis/dbs

# Ver opciones disponibles
python -m mcp_servers.sqlite.cli --help
```

### Uso con un cliente MCP

```python
from mcp.connectors.http_client import MCPHttpClient
from mcp.core.protocol import MCPMessage, MCPAction

# Conectar con el servidor SQLite MCP
client = MCPHttpClient(base_url="http://localhost:8080")
client.connect()

# Crear una base de datos
create_db_msg = MCPMessage(
    action=MCPAction.CREATE,
    resource_type="database",
    resource_path="/my_database.db",
    data={"db_name": "my_database.db"}
)
response = client.send_message(create_db_msg)

# Crear una tabla
create_table_msg = MCPMessage(
    action=MCPAction.CREATE,
    resource_type="table",
    resource_path="/my_database.db/users",
    data={
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
            {"name": "name", "type": "TEXT", "not_null": True},
            {"name": "email", "type": "TEXT"},
            {"name": "age", "type": "INTEGER"}
        ]
    }
)
response = client.send_message(create_table_msg)

# Insertar datos
insert_msg = MCPMessage(
    action=MCPAction.CREATE,
    resource_type="query",
    resource_path="/query",
    data={
        "db_name": "my_database.db",
        "query": "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        "params": ["John Doe", "john@example.com", 30]
    }
)
response = client.send_message(insert_msg)

# Consultar datos
query_msg = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type="query",
    resource_path="/query",
    data={
        "db_name": "my_database.db",
        "query": "SELECT * FROM users WHERE age > ?",
        "params": [25]
    }
)
response = client.send_message(query_msg)

# Procesar resultados
if response.success:
    results = response.data.get("results", [])
    for user in results:
        print(f"Usuario: {user['name']}, Email: {user['email']}, Edad: {user['age']}")
```

## Estructura de rutas (paths)

El servidor utiliza un sistema de rutas similar a URLs para identificar recursos:

- `/` - Raíz (lista de bases de datos)
- `/{db_name}` - Una base de datos específica
- `/{db_name}/{table_name}` - Una tabla específica
- `/query` - Endpoint para consultas SQL personalizadas

## Mejores prácticas

1. **Seguridad**: El servidor implementa sanitización básica, pero en producción considere implementar autenticación y restricciones adicionales.

2. **Rendimiento**: Para operaciones con grandes conjuntos de datos, use paginación a través de los parámetros `page` y `page_size`.

3. **Respaldo**: Implemente una estrategia de respaldo regular para las bases de datos SQLite.

4. **Concurrencia**: SQLite tiene limitaciones en operaciones concurrentes de escritura. Para cargas altas, considere otras alternativas como PostgreSQL.

## Detalles de implementación

### Clase SQLiteMCPServer

La clase principal `SQLiteMCPServer` extiende `MCPServerBase` e implementa:

- Manejo de solicitudes MCP a través de métodos específicos por acción
- Gestión de conexiones SQLite
- Validación y sanitización de entradas
- Conversión entre tipos de datos SQLite y Python

### Función run_http_server

Esta función facilita la exposición del servidor a través de HTTP, iniciando un servidor web que:

- Convierte solicitudes HTTP en mensajes MCP
- Pasa los mensajes al servidor SQLite MCP
- Convierte las respuestas MCP en respuestas HTTP

## Solución de problemas

### Errores comunes

- **"Database not found"**: Verifique que la base de datos exista en el directorio configurado.
- **"Table not found"**: Asegúrese de que la tabla mencionada exista en la base de datos.
- **"SQL error"**: Revise la sintaxis de la consulta SQL y que los parámetros sean del tipo correcto.

### Logging

El servidor registra eventos importantes. Para aumentar el nivel de detalle, configure el nivel de logging:

```python
import logging
logging.getLogger("mcp_servers.sqlite").setLevel(logging.DEBUG)
```

## Contribuir

Las contribuciones son bienvenidas. Áreas de mejora potenciales:

- Soporte para índices y constraints
- Implementación de transacciones
- Mejoras en el rendimiento para grandes conjuntos de datos
- Más opciones de autenticación y seguridad 