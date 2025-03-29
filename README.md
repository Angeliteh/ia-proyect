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
│   └── http/             # Componentes para comunicación HTTP
├── mcp_servers/          # Implementaciones de servidores MCP
│   ├── brave_search_server.py  # Servidor MCP para Brave Search
│   └── ...               # Otros servidores MCP
├── mcp_clients/          # Implementaciones de clientes MCP
│   ├── brave_search/     # Cliente específico para Brave Search
│   └── ...               # Otros clientes MCP
├── agents/               # Implementaciones de agentes
├── memory/               # Sistema de memoria compartida
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
└── examples/             # Scripts de ejemplo
    ├── mcp_echo_client_example.py     # Ejemplo de cliente MCP simple
    ├── brave_search_client_example.py # Ejemplo de cliente Brave Search
    └── ...               # Otros ejemplos
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

- **Brave Search**: Acceso a la API de búsqueda web y local de Brave
- **Sistema de archivos local**: Acceso a archivos y directorios locales (planificado)
- **Base de datos**: Conexión con bases de datos (SQLite, MongoDB, etc.) (planificado)

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