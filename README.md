# V.I.O. Agent System

Sistema modular de agentes de Inteligencia Artificial liderado por V.I.O. (Virtual Intelligence Operator) y basado en MCP (Model Context Protocol).

## Descripción

Este sistema permite la integración de múltiples agentes especializados que pueden interactuar entre sí mediante una API centralizada y una memoria compartida. El núcleo del sistema implementa el Model Context Protocol (MCP) desarrollado por Anthropic, que proporciona un estándar abierto para conectar asistentes de IA con sistemas donde viven los datos, incluyendo repositorios de contenido, herramientas de negocio y entornos de desarrollo.

## Características principales

- **V.I.O. (Virtual Intelligence Operator)**: Agente central y "mano derecha" del usuario que coordina todos los agentes
- **Búsqueda Semántica y por Palabras Clave**: Sistema dual para recuperación de información en memoria
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
│   ├── main_assistant/   # V.I.O. - Virtual Intelligence Operator
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
│   │   └── main_assistant/ # Ejemplos de V.I.O.
│   ├── tts/              # Ejemplos de uso del sistema TTS
│   ├── memory/           # Ejemplos de uso del sistema de memoria
│   ├── integration/      # Tests de integración entre componentes
│   │   └── multi_agent_assistant/ # Demo de integración multi-agente
│   └── README.md         # Guía para ejecutar ejemplos y tests
└── data/                 # Directorio para datos y recursos
```

## V.I.O. - Virtual Intelligence Operator

V.I.O. es el componente central del sistema, actuando como el asistente principal y "mano derecha" del usuario:

### Características de V.I.O.

- **Prioridad absoluta al usuario**: La función primordial de V.I.O. es servir al usuario
- **Personalidad adaptada**: Comunicación relajada pero directa, sin formalismos innecesarios
- **Delegación inteligente**: Analiza las consultas y las redirige al agente especializado más adecuado
- **Coordinación con el orquestador**: Permite resolver tareas complejas que requieren múltiples agentes
- **Memoria persistente**: Actualiza constantemente información sobre misión, instrucciones y contexto
- **Mejora proactiva**: Sugiere mejoras en su funcionamiento y en el sistema general
- **TTS integrado**: Genera respuestas auditivas consistentes con una voz personalizable

### Instrucción consolidada para V.I.O.

> "V.I.O, eres mi asistente central y mi mano derecha en este sistema multiagente. Tu misión es coordinar los agentes, gestionar una memoria persistente y proponer mejoras continuas para optimizar el rendimiento. Habla de forma relajada y natural, sin formalismos excesivos, transmitiendo siempre seguridad, confianza y responsabilidad. Aunque tu estilo es creativo y sin censura en ideas, cada acción debe estar enfocada en servir mis necesidades y garantizar el funcionamiento seguro y eficiente del sistema."

### Flujo de trabajo centralizado

1. El usuario interactúa con **V.I.O.** mediante consultas de texto
2. V.I.O. analiza la consulta para determinar su naturaleza
3. Para consultas simples, responde directamente
4. Para consultas especializadas, delega al agente adecuado (CodeAgent, SystemAgent, etc.)
5. Para tareas complejas, coordina con el OrchestratorAgent para dividir el trabajo
6. Procesa la respuesta final, aplica TTS si está habilitado, y presenta el resultado al usuario

Ejemplo de uso:

```python
from agents.main_assistant import MainAssistant

# Crear V.I.O.
vio = MainAssistant(
    agent_id="vio",
    config={
        "name": "V.I.O.",
        "description": "Virtual Intelligence Operator - Tu asistente central",
        "use_tts": True,
        "default_voice": "Carlos"
    }
)

# Usar V.I.O. para procesar consultas
response = await vio.process(
    "Escribe un programa en Python para calcular el factorial de un número"
)

# V.I.O. delegará automáticamente al CodeAgent
print(response.content)
```

## Sistema de Memoria y Búsqueda

El sistema incluye capacidades avanzadas de almacenamiento y recuperación de información:

### Características del sistema de memoria

- **Múltiples tipos de memoria**: Corto plazo, largo plazo, episódica y semántica
- **Búsqueda dual**: Semántica (basada en vectores) y por palabras clave
- **Fallback automático**: Si la búsqueda semántica falla, intenta con búsqueda por palabras clave
- **Embeddings vectoriales**: Conversión de texto a vectores para búsqueda semántica
- **Metadatos flexibles**: Permite almacenar información adicional junto con las memorias
- **Persistencia SQLite**: Almacenamiento duradero entre sesiones
- **Gestión de importancia**: Priorización de información según relevancia

### Búsqueda por Palabras Clave

La búsqueda por palabras clave es un complemento esencial a la búsqueda semántica:

- **Funciona sin embeddings**: No requiere vectorización del contenido
- **Escaneo de contenido y metadatos**: Busca en todo el texto y metadatos de las memorias
- **Puntuación de relevancia**: Basada en cantidad de palabras clave coincidentes
- **Umbral mínimo configurable**: Requiere una cantidad mínima de coincidencias
- **Integración con MCP**: Disponible a través del protocolo MCP como recurso "keyword"

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
    text="Hola, soy V.I.O., tu asistente virtual.",
    voice_name="Carlos"
)

# Reproducir el audio
tts_manager.play_audio(audio_file)
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
git clone https://github.com/tu-usuario/vio-agent-system.git
cd vio-agent-system
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

### Demo Completa Multi-Agente

Para ejecutar una demostración completa de integración con todos los agentes:

```bash
# Ejecutar la demo multi-agente con V.I.O.
python examples/integration/multi_agent_assistant/multi_agent_demo.py

# Versión interactiva
python examples/integration/multi_agent_assistant/interactive_cli.py
```

### Ejemplos de modelos

Para probar el sistema de modelos:

```bash
# Usar modelo en la nube (necesita API key en .env)
python examples/model_manager_example.py --model gpt-3.5-turbo-16k

# Usar modelo local con selección automática de dispositivo
python examples/model_manager_example.py --model mistral-7b-instruct --device auto
```

### Ejemplos de TTS

Para probar el sistema de Text-to-Speech:

```bash
# Prueba básica con voces disponibles
python examples/tts/tts_echo_test.py --list-voices

# Generar y reproducir audio con una voz específica
python examples/tts/tts_echo_test.py --voice "Carlos" --query "Hola, esto es una prueba del sistema Text-to-Speech"
```

## Agentes disponibles

- **V.I.O.**: Virtual Intelligence Operator - Agente central que coordina todos los demás agentes (implementado)
- **Echo Agent**: Agente simple para pruebas que repite el input (implementado)
- **Code Agent**: Agente para generación y análisis de código (implementado)
- **System Agent**: Agente para control del sistema operativo (implementado)
- **Orchestrator Agent**: Agente que coordina tareas complejas (implementado)
- **Memory Agent**: Agente especializado en gestión de memoria semántica (implementado)
- **Planner Agent**: Agente que planifica tareas complejas (implementado)

## Extensibilidad y Desarrollo Futuro

El sistema está diseñado para ser altamente extensible, permitiendo:

1. **Nuevos Agentes Especializados**: Crear agentes para tareas específicas como interacción con APIs externas o procesamiento de imágenes
2. **Interfaces Alternativas**: Además de la CLI, se pueden desarrollar interfaces web o aplicaciones móviles
3. **Mejoras en la Memoria**: Expansión de las capacidades de memoria con nuevos tipos especializados
4. **Integración de Visión**: Incorporar modelos multimodales para comprensión de imágenes
5. **Automatización de Tareas**: Agentes que programen y ejecuten tareas repetitivas

Para desarrollar nuevos componentes, consulte la documentación específica de cada subsistema.

## Licencia

MIT