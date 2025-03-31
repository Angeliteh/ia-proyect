# AI Agent System

Sistema modular de agentes de Inteligencia Artificial basado en MCP (Model Context Protocol).

## Descripción

Este sistema permite la integración de múltiples agentes especializados que pueden interactuar entre sí mediante una API centralizada y una memoria compartida. El núcleo del sistema implementa el Model Context Protocol (MCP) desarrollado por Anthropic, que proporciona un estándar abierto para conectar asistentes de IA con sistemas donde viven los datos, incluyendo repositorios de contenido, herramientas de negocio y entornos de desarrollo.

## Características principales

- **MainAssistant**: Punto central de interacción con el usuario que coordina todos los agentes
- **TTS (Text-to-Speech)**: Capacidad de respuesta por voz usando múltiples proveedores
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
├── agents/                # Implementaciones de agentes
│   ├── base.py           # Clase base para todos los agentes
│   ├── agent_communication.py  # Sistema de comunicación entre agentes
│   ├── main_assistant/   # Agente principal para interacción centralizada
│   ├── echo_agent.py     # Agente de eco simple (para pruebas)
│   ├── code_agent.py     # Agente especializado en tareas de código
│   ├── system_agent.py   # Agente para interacción con el sistema
│   └── orchestrator_agent.py # Agente para coordinar tareas complejas
├── tts/                  # Sistema Text-to-Speech
│   ├── core/             # Componentes principales del sistema TTS
│   │   ├── simple_tts_manager.py  # Implementación con gTTS (Google)
│   │   ├── tts_manager.py # Implementación con MAYA/ElevenLabs
│   │   └── file_manager.py # Gestión de archivos temporales
│   └── temp/             # Archivos temporales de audio
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
│   │   └── main_assistant/ # Ejemplos del MainAssistant
│   ├── tts/              # Ejemplos de uso del sistema TTS
│   ├── memory/           # Ejemplos de uso del sistema de memoria
│   ├── integration/      # Tests de integración entre componentes
│   └── README.md         # Guía para ejecutar ejemplos y tests
└── data/                 # Directorio para datos y recursos
```

## Arquitectura centralizada con MainAssistant

El sistema implementa una arquitectura centralizada a través del componente `MainAssistant`, que actúa como punto único de interacción con el usuario y coordina todos los agentes especializados:

### Características del MainAssistant

- **Interacción unificada**: Presenta una interfaz consistente y coherente para el usuario
- **Delegación inteligente**: Analiza las consultas y las redirige al agente especializado más adecuado
- **Coordinación con el orquestador**: Permite resolver tareas complejas que requieren múltiples agentes
- **TTS integrado**: Genera respuestas auditivas consistentes con una voz personalizable
- **Gestión de contexto**: Mantiene el contexto de la conversación y registro histórico
- **Memoria persistente**: Almacena interacciones para referencias futuras

### Flujo de trabajo centralizado

1. El usuario interactúa con el **MainAssistant** mediante consultas de texto
2. MainAssistant analiza la consulta para determinar su naturaleza
3. Para consultas simples, responde directamente
4. Para consultas especializadas, delega al agente adecuado (CodeAgent, SystemAgent, etc.)
5. Para tareas complejas, coordina con el OrchestratorAgent para dividir el trabajo
6. Procesa la respuesta final, aplica TTS si está habilitado, y presenta el resultado al usuario

Ejemplo de uso:

```python
from agents import MainAssistant

# Crear el asistente principal
main_assistant = MainAssistant(
    agent_id="jarvis",
    config={
        "name": "Jarvis",
        "description": "Asistente principal centralizado",
        "use_tts": True,
        "default_voice": "Carlos"
    }
)

# Usar el asistente para procesar consultas
response = await main_assistant.process(
    "Escribe un programa en Python para calcular el factorial de un número"
)

# El MainAssistant delegará automáticamente al CodeAgent
print(response.content)
```

## Sistema Text-to-Speech (TTS)

El sistema incluye capacidades avanzadas de Text-to-Speech que permiten a los agentes comunicarse mediante voz:

### Características principales del TTS

- **Modular y extensible**: Arquitectura que permite múltiples implementaciones
- **Múltiples proveedores**: Soporte para Google TTS (gTTS) y MAYA/ElevenLabs
- **Gestión inteligente de archivos**: Sistema de limpieza automática y caché
- **Personalización de voces**: Asignación de voces específicas por agente
- **Selección de idioma**: Soporte para múltiples idiomas
- **Integración con agentes**: Todos los agentes pueden usar TTS con mínima configuración

### Componentes clave

- **AgentTTSInterface**: Interfaz unificada para todos los agentes
- **SimpleTTSManager**: Implementación basada en gTTS (gratuita, para desarrollo)
- **TTSManager**: Implementación basada en MAYA/ElevenLabs (mayor calidad)
- **TTSFileManager**: Gestión de archivos temporales con limpieza y caché

Ejemplo de uso directo del TTS:

```python
from tts.core import SimpleTTSManager

# Crear gestor TTS
tts_manager = SimpleTTSManager()

# Generar audio a partir de texto
audio_file = tts_manager.text_to_speech(
    text="Hola, soy un asistente virtual.",
    voice_name="Carlos"
)

# Reproducir el audio
tts_manager.play_audio(audio_file)
```

Para más información, consulte los [ejemplos de TTS](./examples/tts/).

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
- Para TTS:
  - pygame (reproducción de audio)
  - gTTS (Google Text-to-Speech)
  - (Opcional) API key MAYA/ElevenLabs para mayor calidad de voz

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

### MainAssistant (Interfaz centralizada)

Para interactuar con el sistema a través del asistente principal:

```bash
# Modo interactivo con el MainAssistant
python examples/agents/main_assistant/main_assistant_example.py --interactive

# Probar delegación a un agente específico
python examples/agents/main_assistant/main_assistant_example.py --test code

# Ejecutar todas las pruebas
python examples/agents/main_assistant/main_assistant_example.py --test all
```

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

### Ejemplos de TTS

Para probar el sistema de Text-to-Speech:

```bash
# Prueba básica con voces disponibles
python examples/tts/tts_echo_test.py --list-voices

# Generar y reproducir audio con una voz específica
python examples/tts/tts_echo_test.py --voice "Carlos" --query "Hola, esto es una prueba del sistema Text-to-Speech"

# Probar la caché y sistema de limpieza
python examples/tts/tts_echo_test.py --check-cache --cleanup
```

### Modo API

Para iniciar el servidor API:

```bash
python main.py --mode api
```

## Agentes disponibles

- **MainAssistant**: Agente centralizado que coordina todos los demás agentes (implementado)
- **Echo Agent**: Agente simple para pruebas que repite el input (implementado)
- **Code Agent**: Agente para generación y análisis de código (implementado)
- **System Agent**: Agente para control del sistema operativo (implementado)
- **Orchestrator Agent**: Agente que coordina tareas complejas (implementado)
- **Planner Agent**: Agente que planifica tareas complejas (implementado)
- **Science Agent**: Agente para discusiones científicas y filosóficas (planificado)

## Licencia

MIT

## Contacto

[Tu nombre/email]

## Organización del código

El proyecto sigue una estructura modular con los siguientes componentes principales:

### Agentes Centrales

- **MainAssistant**: Punto central de interacción que coordina todos los demás agentes
- **OrchestratorAgent**: Coordina la ejecución de tareas complejas entre múltiples agentes
- **Agentes especializados**: CodeAgent, SystemAgent, EchoAgent, etc.

### TTS (Text-to-Speech)

Este módulo implementa capacidades de voz para los agentes:

- **Interfaz común**: AgentTTSInterface que conecta agentes con sistemas TTS
- **Implementaciones**: SimpleTTSManager (gTTS) y TTSManager (MAYA/ElevenLabs)
- **Gestión de archivos**: Sistema de caché y limpieza automática

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