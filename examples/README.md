# Ejemplos y Pruebas del Sistema de Agentes IA

Este directorio contiene ejemplos y pruebas para los diferentes componentes del Sistema de Agentes IA basado en Model Context Protocol (MCP), incluyendo implementaciones de MCP, agentes inteligentes, sistemas de memoria y modelos de IA.

## Estructura del Directorio

Los ejemplos están organizados en las siguientes carpetas:

- **[`mcp/`](./mcp/)**: Ejemplos del Model Context Protocol y sus implementaciones
- **[`agents/`](./agents/)**: Ejemplos de agentes especializados (Echo, Code, System)
- **[`models/`](./models/)**: Ejemplos de gestión de modelos de IA locales y en la nube
- **[`memory/`](./memory/)**: Ejemplos del sistema de memoria para agentes
- **[`integration/`](./integration/)**: Pruebas de integración y herramientas generales

## Ejecutando Pruebas

Para facilitar la ejecución de pruebas, hemos desarrollado un script ejecutor mejorado en `integration/run_tests.py`, que permite ejecutar ejemplos individualmente o por categorías.

### Ver las pruebas disponibles

Para ver todas las pruebas disponibles:

```bash
cd examples/integration
python run_tests.py --list
```

### Ejecutar una prueba específica

Para ejecutar una prueba específica, use el formato `categoria:prueba`:

```bash
python run_tests.py --run mcp:core
python run_tests.py --run agents:echo
```

### Ejecutar todas las pruebas de una categoría

Para ejecutar todas las pruebas de una categoría:

```bash
python run_tests.py --run-category mcp
python run_tests.py --run-category agents
```

### Ejecutar todas las pruebas

Para ejecutar todas las pruebas disponibles:

```bash
python run_tests.py --run-all
```

### Opciones adicionales

- `--verbose` o `-v`: Muestra información detallada durante la ejecución de las pruebas
- `--save-report`: Guarda un informe detallado de los resultados en formato JSON
- `--report-file`: Especifica el nombre del archivo para el informe (por defecto: `test_report.json`)

## Ejemplos por Categoría

### MCP (Model Context Protocol)

- **mcp_echo_client_example.py**: Cliente MCP simple que envía mensajes a un servidor de eco
- **sqlite_mcp_example.py**: Servidor MCP para bases de datos SQLite
- **brave_search_client_example.py**: Cliente MCP para Brave Search
- **brave_search_server_example.py**: Servidor MCP para Brave Search

### Agentes

- **echo_agent_example.py**: Agente básico que simplemente repite mensajes (útil para pruebas)
- **code_agent_example.py**: Agente especializado en tareas de programación
- **system_agent_example.py**: Agente para interactuar con el sistema operativo
- **agent_communication_example.py**: Demostración de comunicación entre agentes

### Modelos de IA

- **model_manager_example.py**: Gestión de modelos de IA locales y en la nube

### Sistema de Memoria

- **memory_example.py**: Demostración del sistema de memoria para agentes

## Configuración Requerida

Algunos ejemplos pueden requerir configuración adicional:

1. **API Keys**: Los ejemplos relacionados con servicios en la nube (como Brave Search) requieren API keys. Configúrelas en un archivo `.env` siguiendo el formato del archivo `.env.example`.

2. **Modelos locales**: Los ejemplos de modelos locales requieren archivos GGUF. Asegúrese de descargarlos y configurar correctamente sus rutas.

## Reportes de Pruebas

El nuevo sistema de ejecución de pruebas genera reportes detallados que incluyen:

- Resumen de pruebas pasadas, fallidas y omitidas
- Tiempos de ejecución para cada prueba
- Mensajes de error detallados
- Estadísticas de rendimiento global

Para generar un reporte:

```bash
python run_tests.py --run-all --save-report
```

## Solución de Problemas

### Errores Comunes

- **ModuleNotFoundError**: Asegúrese de ejecutar los scripts desde el directorio raíz del proyecto
- **API key not found**: Verifique la configuración en el archivo `.env`
- **Model not found**: Verifique que los modelos GGUF estén correctamente instalados
- **Connection Error**: Para servidores HTTP, verifique que los puertos no estén siendo utilizados

### Logs

Active el modo verbose para obtener más información durante la ejecución:

```bash
python run_tests.py --run-category mcp --verbose
``` 