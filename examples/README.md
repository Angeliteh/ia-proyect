# Ejemplos y Pruebas

Este directorio contiene ejemplos y pruebas para los diferentes componentes del sistema IA Project, incluyendo MCP (Model Context Protocol), servidores MCP específicos, modelos de IA y otros componentes.

## Estructura de los ejemplos

Los ejemplos están organizados por categorías:

- **MCP Core**: Ejemplos que demuestran las funcionalidades básicas del protocolo MCP
- **SQLite MCP**: Ejemplos del servidor MCP para bases de datos SQLite
- **Brave Search**: Ejemplos de la integración con la API de Brave Search
- **Modelos de IA**: Ejemplos del gestor de modelos y su uso

## Cómo ejecutar las pruebas

Para facilitar la ejecución y organización de las pruebas, hemos incluido el script `run_tests.py`, que permite ejecutar ejemplos individualmente o por categorías.

### Ver pruebas disponibles

Para ver todas las pruebas disponibles:

```bash
python run_tests.py --list
```

### Ejecutar una prueba específica

Para ejecutar una prueba específica, use el formato `categoria:prueba`:

```bash
python run_tests.py --run mcp:core
```

### Ejecutar todas las pruebas de una categoría

Para ejecutar todas las pruebas de una categoría:

```bash
python run_tests.py --run-category sqlite
```

### Opciones adicionales

- `--verbose` o `-v`: Muestra información detallada durante la ejecución de las pruebas

## Ejemplos disponibles

### MCP Core

- **mcp_core_example.py**: Demuestra las funcionalidades básicas del protocolo MCP
- **mcp_echo_client_example.py**: Cliente MCP simple que envía mensajes a un servidor de eco
- **mcp_http_client_example.py**: Cliente MCP que se comunica a través de HTTP

### SQLite MCP

- **sqlite_mcp_example.py**: Ejemplo completo del servidor SQLite MCP, con operaciones CRUD y consultas personalizadas
  - Modo directo: `--mode direct` - Prueba la comunicación directa con el servidor
  - Modo HTTP: `--mode http` - Prueba la comunicación a través de HTTP
  - Modo completo: `--mode both` - Ejecuta ambas pruebas secuencialmente

### Brave Search

- **test_brave_api.py**: Prueba directa de la API de Brave Search
- **brave_search_client_example.py**: Cliente MCP para Brave Search
- **brave_search_server_example.py**: Servidor MCP para Brave Search
- **brave_api_mcp_test.py**: Prueba de integración entre MCP y la API de Brave

### Modelos de IA

- **model_manager_example.py**: Demuestra el uso del gestor de modelos de IA para cargar y utilizar modelos locales y en la nube

## Configuración necesaria

Algunos ejemplos pueden requerir configuración adicional:

1. **API Keys**: Algunos ejemplos, como los relacionados con Brave Search, requieren una API key. Configúrela en un archivo `.env` siguiendo el formato del archivo `.env.example`.

2. **Modelos locales**: Los ejemplos de modelos locales requieren que los archivos de modelo correspondientes (GGUF) estén disponibles en el directorio adecuado.

## Añadir nuevos ejemplos

Si desea agregar un nuevo ejemplo, siga estas pautas:

1. Cree un nuevo archivo Python con un nombre descriptivo
2. Documente claramente el propósito y uso del ejemplo
3. Actualice el script `run_tests.py` para incluir su ejemplo en la categoría adecuada

## Solución de problemas

### Errores comunes

- **ModuleNotFoundError**: Asegúrese de que está ejecutando el script desde el directorio raíz del proyecto para que las importaciones funcionen correctamente.
- **API key not found**: Verifique que ha configurado correctamente las API keys en el archivo `.env`.
- **Connection Error**: Si prueba servidores HTTP, asegúrese de que no hay otros procesos usando los mismos puertos.

### Logs

Los ejemplos incluyen logging detallado. Use la opción `--verbose` para ver más información durante la ejecución:

```bash
python run_tests.py --run sqlite:http --verbose
``` 