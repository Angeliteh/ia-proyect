# AI Agent System

Sistema modular de agentes de Inteligencia Artificial basado en MCP (Model Context Protocol).

## Descripción

Este sistema permite la integración de múltiples agentes especializados que pueden interactuar entre sí mediante una API centralizada y una memoria compartida. El núcleo del sistema implementa el Model Context Protocol (MCP) desarrollado por Anthropic, que proporciona un estándar abierto para conectar asistentes de IA con sistemas donde viven los datos, incluyendo repositorios de contenido, herramientas de negocio y entornos de desarrollo.

## Características principales

- **MCP (Model Context Protocol)**: Implementación del estándar abierto de Anthropic para conectar modelos de IA con datos
- **Arquitectura Cliente-Servidor**: Permite a los modelos acceder a datos a través de servidores MCP
- **Arquitectura modular**: Cada agente es independiente y con capacidades específicas
- **Modelo híbrido local/nube**: Capacidad de ejecutar modelos localmente o en la nube según recursos disponibles
- **Detección automática de recursos**: Sistema inteligente para determinar el dispositivo óptimo (CPU/GPU)
- **Memoria compartida**: Sistema de memoria vectorial y documental para persistencia de datos
- **API centralizada**: Para interacción unificada con todos los agentes
- **Monitoreo de recursos**: Gestión inteligente de recursos de hardware
- **Arquitectura Event-Driven**: Comunicación basada en eventos para reducir acoplamiento

## Estructura del proyecto

```
ai-agent-system/
├── mcp/                  # Implementación del Model Context Protocol
│   ├── core/             # Núcleo del protocolo y clases base
│   ├── protocol/         # Definiciones del protocolo MCP
│   ├── connectors/       # Conectores para sistemas externos
│   ├── transport/        # Componentes para comunicación (HTTP, WebSockets)
│   ├── utils/            # Utilidades para MCP
│   └── README.md         # Documentación detallada del MCP
├── mcp_servers/          # Implementaciones de servidores MCP
│   ├── brave_search/     # Servidor MCP para Brave Search
│   ├── sqlite/           # Servidor MCP para bases de datos SQLite
│   └── README.md         # Documentación de servidores MCP
├── mcp_clients/          # Implementaciones de clientes MCP
│   ├── brave_search/     # Cliente específico para Brave Search
│   ├── http/             # Cliente genérico HTTP para MCP
│   └── README.md         # Documentación de clientes MCP
├── agents/               # Implementaciones de agentes
│   ├── base.py           # Clase base para todos los agentes
│   ├── agent_communication.py  # Sistema de comunicación entre agentes
│   ├── echo_agent.py     # Agente de eco simple (para pruebas)
│   ├── code_agent.py     # Agente especializado en tareas de código
│   └── system_agent.py   # Agente para interacción con el sistema
├── memory/               # Sistema de memoria compartida
│   ├── core/             # Núcleo del sistema de memoria
│   ├── storage/          # Backends de almacenamiento
│   └── types/            # Tipos especializados de memoria
├── models/               # Gestores de modelos de IA
│   ├── core/             # Componentes core como ResourceDetector
│   ├── cloud/            # Modelos de IA en la nube (OpenAI, Anthropic)
│   ├── local/            # Modelos locales (archivos .gguf)
│   └── README.md         # Documentación específica de modelos
├── api/                  # API central y endpoints
├── config/               # Archivos de configuración
│   └── models.json       # Configuración de modelos disponibles
├── utils/                # Utilidades generales
├── tests/                # Pruebas unitarias y de integración
├── logs/                 # Archivos de log del sistema
├── examples/             # Scripts de ejemplo
│   ├── mcp/              # Ejemplos de uso del MCP
│   ├── models/           # Ejemplos de uso de modelos
│   ├── agents/           # Ejemplos de uso de agentes
│   ├── memory/           # Ejemplos de uso del sistema de memoria
│   ├── integration/      # Tests de integración entre componentes
│   └── README.md         # Guía para ejecutar ejemplos y tests
└── data/                 # Directorio para datos y recursos
```

## Acerca del Model Context Protocol (MCP)

El Model Context Protocol (MCP) es un estándar abierto desarrollado por Anthropic que funciona como un "USB-C para integraciones de IA", permitiendo una conexión uno-a-muchos entre aplicaciones de IA y diversas fuentes de datos. MCP proporciona:

- **Conexiones bidireccionales seguras**: Entre fuentes de datos y herramientas de IA
- **Arquitectura cliente-servidor**: Servidores MCP que exponen datos y clientes MCP que los consumen
- **Estandarización**: Un protocolo universal para todas las integraciones

Nuestra implementación incluye los componentes fundamentales del MCP:
- **Protocolo base**: Define mensajes, acciones y tipos de recursos
- **Servidores MCP**: Implementaciones que exponen diversos tipos de datos
- **Clientes MCP**: Componentes que permiten a los modelos consumir datos de los servidores
- **Registro central**: Gestiona las conexiones entre clientes y servidores

Para más información sobre MCP, visite [la documentación oficial](https://www.anthropic.com/news/model-context-protocol).

## Sistema de Gestión de Modelos

El sistema incluye un avanzado gestor de modelos con:

- **Soporte para modelos locales**: GGUF (Llama, Mistral, Phi) mediante llama.cpp
- **Soporte para modelos en la nube**: OpenAI (GPT), Anthropic (Claude), Google (Gemini)
- **ResourceDetector**: Detección automática de CPU, RAM, GPU y VRAM disponible
- **Selección inteligente de dispositivo**: Determina si usar CPU o GPU según el modelo y hardware
- **Optimización de parámetros**: Ajusta temperatura, tokens máximos y otros parámetros

Para más detalles, consulte [la documentación de modelos](./models/README.md).

## Requisitos

- Python 3.9+
- MongoDB (para persistencia de memoria documental)
- Para modelos locales:
  - llama-cpp-python
  - (Opcional) NVIDIA GPU con drivers CUDA para aceleración
  - (Opcional) PyTorch para detección y uso avanzado de GPU

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/tu-usuario/ai-agent-system.git
cd ai-agent-system
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:

Copia el archivo `.env.example` a `.env` y configura las variables según tu entorno:

```bash
cp .env.example .env
# Edita el archivo .env con tus claves API y configuraciones
```

4. (Opcional) Descarga modelos locales:

Para usar modelos locales, descarga los archivos GGUF en el directorio `models/local/`.

## Uso

### Ejemplos de modelos

Para probar el sistema de modelos:

```bash
# Usar modelo en la nube (necesita API key en .env)
python examples/model_manager_example.py --model gpt-3.5-turbo-16k

# Usar modelo local con selección automática de dispositivo
python examples/model_manager_example.py --model mistral-7b-instruct --device auto

# Forzar uso de GPU (si está disponible)
python examples/model_manager_example.py --model phi-2 --device gpu --temperature 0.3
```

### Modo interactivo

Para iniciar el sistema en modo interactivo:

```bash
python main.py --mode interactive
```

### Modo API

Para iniciar el servidor API:

```bash
python main.py --mode api
```

## Servidores MCP disponibles

El sistema incluye implementaciones de servidores MCP para conectar con:

- **SQLite**: Acceso completo a bases de datos SQLite con operaciones CRUD y consultas personalizadas
- **Brave Search**: Acceso a la API de búsqueda web y local de Brave (planificado)
- **Sistema de archivos local**: Acceso a archivos y directorios locales (planificado)
- **Base de datos MongoDB**: Conexión con bases de datos MongoDB (planificado)

### Servidor SQLite MCP

El servidor de SQLite permite a los modelos de IA interactuar con bases de datos SQLite a través del protocolo MCP. Características principales:

- **Operaciones CRUD completas** para bases de datos y tablas
- **Consultas SQL personalizadas** con soporte para parámetros
- **Paginación** para listar grandes conjuntos de datos
- **Validación y sanitización** de consultas SQL para prevenir inyecciones
- **Exposición vía HTTP** para acceso remoto
- **CLI** para iniciar el servidor desde línea de comandos

Ejemplo de uso:
```python
from mcp.connectors.http_client import MCPHttpClient
from mcp.core.protocol import MCPMessage, MCPAction

# Conectar con el servidor SQLite MCP
client = MCPHttpClient(base_url="http://localhost:8080")
client.connect()

# Crear una consulta
query_msg = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type="query",
    resource_path="/query",
    data={
        "db_name": "mi_base_datos.db",
        "query": "SELECT * FROM usuarios WHERE edad > ?",
        "params": [25]
    }
)

# Enviar la consulta y procesar resultados
response = client.send_message(query_msg)
if response.success:
    for usuario in response.data.get("results", []):
        print(f"Usuario: {usuario['nombre']}, Edad: {usuario['edad']}")
```

Para más detalles, consulte la [documentación del servidor SQLite MCP](./mcp_servers/sqlite/README.md).

### Brave Search MCP Server

El servidor de Brave Search permite a los modelos de IA realizar búsquedas web y locales a través de la API oficial de Brave. Características:

- **Búsqueda web**: Obtención de resultados web para consultas
- **Búsqueda local**: Búsqueda de lugares/negocios con coordenadas geográficas
- **Fallback automático**: Si no hay resultados locales, puede usar búsqueda web como respaldo
- **Autenticación**: Uso de API key para acceder a los servicios de Brave

Ejemplo de uso:
```python
from mcp.core import MCPMessage
from mcp_servers import BraveSearchMCPServer

# Crear servidor (requiere API key)
server = BraveSearchMCPServer(api_key="tu_api_key_brave")

# Crear mensaje para búsqueda web
message = MCPMessage.create_search_request(
    resource_type="web_search", 
    query="inteligencia artificial", 
    params={"count": 5}
)

# Enviar mensaje y obtener respuesta
response = server.handle_action(message)

# Procesar resultados
if response.status == "success":
    results = response.data.get("results", [])
    for item in results:
        print(f"Título: {item['title']}")
        print(f"URL: {item['url']}")
        print(f"Descripción: {item['description'][:100]}...")
```

## Agentes disponibles

- **Echo Agent**: Agente simple para pruebas que repite el input (actualmente implementado)
- **PC Control Agent**: Agente para control del sistema operativo (planificado)
- **Programming Agent**: Agente para generación y análisis de código (planificado)
- **Science Agent**: Agente para discusiones científicas y filosóficas (planificado)

## Licencia

MIT

## Contacto

[Tu nombre/email]

## Organización del código

El proyecto sigue una estructura modular con los siguientes componentes principales:

### Core MCP (`mcp/`)

Este módulo implementa el Model Context Protocol. Su documentación detallada está disponible en [la documentación de MCP](./mcp/README.md).

- **Protocolo**: Definiciones de mensajes, acciones y respuestas
- **Conectores**: Comunicación con servidores MCP (HTTP, etc.)
- **Transporte**: Implementación de servidores HTTP y WebSocket

### Servidores MCP (`mcp_servers/`)

Implementaciones específicas de servidores MCP:

- **SQLite**: [Servidor para bases de datos SQLite](./mcp_servers/sqlite/README.md)
- (Planificado) Brave Search, sistema de archivos, MongoDB

### Clientes MCP

La mayoría de las funcionalidades de cliente MCP se manejan a través de los conectores genéricos en `mcp/connectors/`, con algunas definiciones base en `mcp_clients/`. En el uso típico, los conectores genéricos son suficientes para interactuar con los servidores MCP.

### Sistema de Modelos (`models/`)

Gestión de modelos de IA locales y en la nube:

- **Detección de recursos**: Analiza CPU, GPU y memoria disponible
- **Gestión de modelos**: Carga/descarga y optimización
- **Inferencia**: Comunicación con modelos de distintos proveedores

## Sistema de Memoria

El sistema de memoria proporciona a los agentes capacidad para almacenar y recuperar información de manera eficiente y contextual. Características principales:

- **Diferentes tipos de memoria**: Memoria a corto plazo, largo plazo, episódica y semántica
- **Búsqueda inteligente**: Soporta búsqueda por palabras clave, similitud semántica y temporal
- **Fallback automático**: Si la búsqueda exacta falla, intenta con palabras clave individuales
- **Persistencia**: Almacenamiento en SQLite para mantener las memorias entre sesiones
- **Metadata flexible**: Permite almacenar metadatos personalizados para cada agente
- **Importancia gradual**: Las memorias tienen niveles de importancia para priorizar
- **Sistema compartido**: Los agentes pueden compartir sus memorias y acceder a memorias de otros agentes

Cada agente incluye capacidades de memoria que le permiten:

1. **Recordar interacciones previas**: Guardar consultas y respuestas anteriores
2. **Mejorar respuestas**: Utilizar contexto de conversaciones pasadas
3. **Inferir parámetros**: Recuperar información de operaciones similares
4. **Compartir conocimiento**: Acceder a información que otros agentes han almacenado

Ejemplo de uso de memoria:

```python
from memory import MemoryManager
from agents import CodeAgent

# Crear una instancia de memoria
memory_manager = MemoryManager()

# Configurar un agente con memoria
code_agent = CodeAgent("code_helper")
code_agent.setup_memory(memory_manager)

# El agente guarda automáticamente sus interacciones
response = await code_agent.process("Escribe una función para calcular factorial")

# Más tarde, el agente puede recordar esta interacción
response = await code_agent.process(
    "¿Puedes recordarme la función factorial que escribiste antes?",
    context={"use_memory": True}  # Forzar uso de memoria
)

# Verificar qué tiene el agente en memoria
memories = code_agent.recall(query="factorial", limit=5)
for mem in memories:
    print(f"Memoria: {mem.content}")
```

Para más detalles, consulte los [ejemplos de memoria](./examples/memory/) y las pruebas de integración.

## License

This project is licensed under the MIT License - see the LICENSE file for details.