# MainAssistant - Agente Central Coordinador

El `MainAssistant` es el componente central del sistema de agentes, actuando como punto único de interacción con el usuario y coordinador inteligente del resto de agentes especializados.

## Descripción

`MainAssistant` implementa una arquitectura centralizada donde todas las consultas del usuario pasan primero por este agente, que analiza la naturaleza de la consulta y decide:

1. Responder directamente para consultas generales o conversacionales
2. Delegar a un agente especializado para tareas específicas
3. Coordinar múltiples agentes para tareas complejas

Esta arquitectura centralizada proporciona una experiencia coherente y unificada para el usuario, manteniendo la especialización y modularidad del sistema.

## Características principales

- **Punto único de interacción**: Interfaz unificada para todas las consultas
- **Delegación inteligente**: Análisis y redirección a agentes especializados
- **Integración con TTS**: Generación de respuestas por voz con personalización
- **Memoria contextual**: Mantenimiento del contexto entre consultas
- **Formato de respuesta coherente**: Estilo consistente independiente del agente que procese
- **Gestión de errores**: Manejo centralizado de excepciones y fallos
- **Capacidades conversacionales**: Habilidades de chat natural para consultas generales

## Arquitectura

```
MainAssistant
│
├── Análisis de consultas
│   ├── Categorización semántica
│   ├── Detección de intención
│   └── Identificación de agente adecuado
│
├── Gestión de comunicación
│   ├── Comunicador central (AgentCommunicator)
│   ├── Sistema de mensajería
│   └── Gestión de respuestas
│
├── Capacidades TTS
│   ├── AgentTTSInterface
│   ├── Personalización de voz
│   └── Reproducción automática
│
└── Gestión de agentes
    ├── Registro y descubrimiento
    ├── Monitoreo de estado
    └── Coordinación con orquestador
```

## Implementación

El `MainAssistant` está implementado como una extensión de la clase `BaseAgent` con capacidades adicionales:

```python
class MainAssistant(BaseAgent):
    """Agente principal centralizado que coordina todos los demás agentes."""
    
    def __init__(self, agent_id, **kwargs):
        """
        Inicializa el MainAssistant.
        
        Args:
            agent_id (str): Identificador único del agente
            kwargs: Argumentos adicionales
                - name (str): Nombre amigable del asistente
                - description (str): Descripción del asistente
                - use_tts (bool): Habilitar Text-to-Speech
                - default_voice (str): Voz predeterminada para TTS
                - agent_voices (dict): Mapa de voces específicas por agente
        """
        # Inicialización
    
    async def process(self, query, context=None):
        """
        Procesa una consulta del usuario, delegando si es necesario.
        
        Args:
            query (str): Consulta del usuario
            context (dict): Contexto adicional
        
        Returns:
            AgentResponse: Respuesta procesada
        """
        # Implementación
    
    def _analyze_query_type(self, query):
        """
        Analiza la consulta para determinar qué agente debe manejarla.
        
        Args:
            query (str): Consulta a analizar
        
        Returns:
            tuple: (tipo_consulta, agente_recomendado, confianza)
        """
        # Implementación
    
    async def _delegate_to_agent(self, agent_id, query, context=None):
        """
        Delega una consulta a un agente especializado.
        
        Args:
            agent_id (str): ID del agente especializado
            query (str): Consulta original del usuario
            context (dict): Contexto adicional
        
        Returns:
            AgentResponse: Respuesta del agente especializado
        """
        # Implementación
```

## Delegación basada en contenido

El `MainAssistant` analiza la naturaleza de cada consulta para determinar el agente más adecuado:

| Tipo de consulta | Agente recomendado | Ejemplo de consulta |
|------------------|--------------------|--------------------|
| Programación | `code_agent` | "Escribe una función que calcule el factorial" |
| Sistema operativo | `system_agent` | "Muestra los archivos en el directorio actual" |
| Conversacional | (maneja directamente) | "¿Cómo estás hoy?" |
| Eco/Test | `echo_agent` | "Eco de: hola mundo" |
| Compleja | `orchestrator_agent` | "Crea un programa y guárdalo en un archivo" |

## Integración con TTS

El `MainAssistant` integra capacidades de Text-to-Speech, permitiendo:

1. Generar respuestas por voz para consultas del usuario
2. Personalizar voces según el agente que responde
3. Mantener coherencia en la respuesta auditiva
4. Activar/desactivar TTS según el contexto

```python
# Ejemplo de uso con TTS habilitado
response = await main_assistant.process(
    "¿Cuál es la capital de Francia?",
    context={"use_tts": True}
)
```

## Gestión de contexto

El `MainAssistant` mantiene contexto entre consultas para proporcionar respuestas más coherentes:

```python
# Primera consulta
response1 = await main_assistant.process("¿Qué es Python?")

# Segunda consulta (referencia implícita a la primera)
response2 = await main_assistant.process("¿Cuáles son sus principales características?")
```

El sistema utiliza:
- Memoria a corto plazo para el contexto inmediato
- Referencias a consultas previas
- Mantenimiento de estado conversacional

## Ejemplos de uso

### Uso básico

```python
from agents.main_assistant import MainAssistant

# Crear instancia del asistente principal
assistant = MainAssistant(
    agent_id="jarvis",
    name="Jarvis",
    description="Asistente personal inteligente",
    use_tts=True,
    default_voice="Carlos"
)

# Procesar consultas
response = await assistant.process("Escribe un programa que calcule el factorial de un número")
print(response.content)
```

### Personalización de voces por agente

```python
# Configurar voces específicas por agente
agent_voices = {
    "main_assistant": "Carlos",
    "code_agent": "Jorge",
    "system_agent": "Diego",
    "echo_agent": "Enrique"
}

# Crear asistente con voces personalizadas
assistant = MainAssistant(
    agent_id="jarvis",
    use_tts=True,
    agent_voices=agent_voices
)
```

### Modo de depuración

```python
# Habilitar modo de depuración para ver el proceso de delegación
response = await assistant.process(
    "Escribe una función que calcule la secuencia Fibonacci",
    context={"debug": True}
)
```

## Delegación a agentes especializados

El proceso de delegación sigue estos pasos:

1. El usuario envía una consulta al `MainAssistant`
2. `MainAssistant` analiza la naturaleza de la consulta
3. Determina si debe manejarla directamente o delegarla
4. Si delega, selecciona el agente más adecuado
5. Envía la consulta al agente seleccionado a través del comunicador
6. Recibe la respuesta del agente especializado
7. Formatea y procesa la respuesta para mantener coherencia
8. Si TTS está habilitado, genera respuesta auditiva
9. Retorna la respuesta final al usuario

## Comunicación entre agentes

El `MainAssistant` utiliza el sistema `AgentCommunicator` para la comunicación con otros agentes:

```python
from agents.agent_communication import AgentCommunicator, AgentMessage

# Obtener la instancia única del comunicador
communicator = AgentCommunicator.get_instance()

# Crear mensaje para un agente específico
message = AgentMessage(
    sender_id="main_assistant",
    recipient_id="code_agent",
    message_type="request",
    content="Escribe una función para calcular el factorial",
    correlation_id="query_123"
)

# Enviar mensaje y esperar respuesta
response = await communicator.send_and_receive(message)
```

## Configuración y personalización

El `MainAssistant` puede configurarse mediante varios parámetros:

```python
# Configuración avanzada
assistant = MainAssistant(
    agent_id="custom_assistant",
    config={
        "name": "Asistente Personalizado",
        "description": "Mi asistente virtual personal",
        "use_tts": True,
        "default_voice": "Carlos",
        "agent_voices": {
            "code_agent": "Jorge",
            "system_agent": "Diego"
        },
        "default_timeout": 30,  # Tiempo máximo de espera para respuestas (segundos)
        "auto_delegation": True,  # Delegación automática sin confirmación
        "debug_mode": False,  # Modo de depuración
    }
)
```

## Requisitos

- Python 3.9+
- Sistema de agentes base
- (Opcional) Sistema TTS para respuestas por voz

## Implementación futura

- Modos de personalidad configurables
- Integración con memoria a largo plazo
- Delegación basada en modelos avanzados
- Interfaz web para interacción
- Soporte para consultas multimodales (texto + imágenes)

## Licencia

MIT 