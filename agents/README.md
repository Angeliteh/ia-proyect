# Sistema de Agentes IA

Este directorio contiene las implementaciones de los diferentes agentes inteligentes que forman parte del Sistema de Agentes IA basado en Model Context Protocol (MCP).

## Estructura y Componentes

El sistema de agentes está organizado de manera modular, con los siguientes componentes clave:

- **[`base.py`](./base.py)**: Define la clase base `BaseAgent` que todos los agentes deben implementar, junto con estructuras comunes para respuestas y mensajes de agentes.

- **[`agent_communication.py`](./agent_communication.py)**: Implementa el sistema de comunicación entre agentes, incluyendo un bus de mensajes, tipos de mensajes y un comunicador central.

- **[`echo_agent.py`](./echo_agent.py)**: Un agente simple que repite los mensajes que recibe. Útil para pruebas y depuración.

- **[`code_agent.py`](./code_agent.py)**: Un agente especializado en tareas de programación que puede generar, explicar y mejorar código.

- **[`system_agent.py`](./system_agent.py)**: Un agente para interactuar con el sistema operativo, permitiendo ejecutar comandos, administrar archivos y procesos.

- **[`orchestrator_agent.py`](./orchestrator_agent.py)**: Un agente orquestador que coordina múltiples agentes especializados para resolver tareas complejas mediante planificación y ejecución de workflows.

## Sistema de Comunicación entre Agentes

Los agentes pueden comunicarse entre sí a través del sistema implementado en `agent_communication.py`, que proporciona:

- **Bus de Mensajes**: Enrutamiento centralizado de mensajes entre agentes
- **Tipos de Mensajes**: Solicitudes, respuestas, notificaciones y errores
- **Comunicador**: Un singleton que gestiona la comunicación global
- **Comunicación Asíncrona**: Soporte para comunicación no bloqueante

Ejemplo básico de comunicación entre agentes:

```python
from agents import EchoAgent, communicator
from agents.agent_communication import Message, MessageType

# Crear agentes
echo_agent = EchoAgent("echo1", {"name": "Echo Agent 1"})

# Registrar con el comunicador
communicator.register_agent(echo_agent)

# Crear un mensaje
message = Message(
    msg_type=MessageType.REQUEST,
    sender_id="system",
    receiver_id="echo1",
    content="¡Hola, Echo Agent!",
    context={"priority": "high"}
)

# Enviar mensaje
response = await communicator.send_message(message)
print(f"Respuesta: {response.content}")
```

## Estados de los Agentes

Todos los agentes basados en `BaseAgent` implementan una máquina de estados simple con los siguientes estados:

- **idle**: El agente está inactivo y listo para procesar solicitudes
- **processing**: El agente está procesando activamente una solicitud
- **error**: El agente ha encontrado un error y necesita ser restablecido

Las transiciones válidas entre estados están definidas y aplicadas en el método `set_state()`.

## Agente Orquestador

El `OrchestratorAgent` es responsable de coordinar múltiples agentes especializados para resolver tareas complejas. Sus principales capacidades incluyen:

### Planificación de Tareas
- Divide tareas complejas en subtareas manejables
- Asigna tipos de agentes apropiados para cada subtarea
- Establece dependencias entre subtareas cuando es necesario

### Selección de Agentes
- Elige el mejor agente disponible para cada subtarea basándose en capacidades, estado y rendimiento
- Implementa mecanismos de fallback cuando los agentes ideales no están disponibles
- Mantiene un registro del estado de cada agente (idle/busy)

### Gestión de Workflows
- Ejecuta subtareas en secuencia, respetando dependencias
- Maneja errores y fallas en los pasos del workflow
- Proporciona resultados consolidados de la ejecución completa
- Mantiene un historial de workflows ejecutados

### Ejemplo de uso del Orquestador:

```python
from agents import EchoAgent, CodeAgent, SystemAgent, OrchestratorAgent, communicator

# Crear agentes especializados
echo_agent = EchoAgent("echo1", {"name": "Echo Agent"})
code_agent = CodeAgent("code1", {"name": "Code Agent"})
system_agent = SystemAgent("system1", {"name": "System Agent"})

# Crear orquestador
orchestrator = OrchestratorAgent("orchestrator", {"name": "Orchestrator"})

# Registrar agentes
communicator.register_agent(echo_agent)
communicator.register_agent(code_agent)
communicator.register_agent(system_agent)
communicator.register_agent(orchestrator)

# Registrar agentes con el orquestador
await orchestrator.register_available_agent("echo1", echo_agent.get_capabilities())
await orchestrator.register_available_agent("code1", code_agent.get_capabilities())
await orchestrator.register_available_agent("system1", system_agent.get_capabilities())

# Ejecutar una tarea compleja
response = await orchestrator.process(
    "Genera un script en Python que liste archivos en el directorio actual " +
    "y luego ejecútalo para ver el resultado"
)

print(f"Resultado: {response.content}")

# Ver workflows completados
workflows = await orchestrator.list_workflows(status="completed")
print(f"Workflows completados: {len(workflows)}")
```

## Implementando un Nuevo Agente

Para implementar un nuevo agente, extienda la clase `BaseAgent` e implemente los métodos requeridos:

```python
from agents.base import BaseAgent, AgentResponse
from typing import Dict, List, Optional

class MyNewAgent(BaseAgent):
    """Implementación de un nuevo agente."""
    
    def __init__(self, agent_id: str, config: Dict):
        super().__init__(agent_id, config)
        # Inicialización específica del agente
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Procesa una consulta y devuelve una respuesta."""
        self.set_state("processing")
        
        # Lógica específica del agente para procesar la consulta
        result = f"Procesado: {query}"
        
        self.set_state("idle")
        return AgentResponse(content=result, metadata={"source": self.agent_id})
    
    def get_capabilities(self) -> List[str]:
        """Devuelve las capacidades de este agente."""
        return ["capability1", "capability2"]
```

## Uso del Sistema de Agentes

Los agentes pueden utilizarse de manera individual o como parte de un sistema más amplio:

### Uso Individual

```python
from agents import CodeAgent

# Crear agente
code_agent = CodeAgent("code1", {"model": "gpt-3.5-turbo"})

# Procesar una consulta
response = await code_agent.process(
    "Escribe una función en Python para calcular el factorial de un número",
    context={"language": "python", "level": "beginner"}
)

print(response.content)
```

### Uso en Sistema

```python
from agents import SystemAgent, CodeAgent, communicator
from agents.agent_communication import send_agent_request

# Crear agentes
system_agent = SystemAgent("system1", {"os_access": True})
code_agent = CodeAgent("code1", {"model": "gpt-3.5-turbo"})

# Registrar con comunicador
communicator.register_agent(system_agent)
communicator.register_agent(code_agent)

# Enviar solicitud de un agente a otro
response = await send_agent_request(
    sender_id="system1",
    receiver_id="code1",
    content="Genera un script para listar archivos",
    context={"language": "python"}
)

# Usar la respuesta
script = response.content
print(f"Script generado: {script}")

# Ejecutar el script generado con el agente del sistema
execution_response = await system_agent.process(
    f"Ejecuta este script: {script}",
    context={"working_dir": "/tmp"}
)

print(f"Resultado de ejecución: {execution_response.content}")
```

## Extensiones Futuras

El próximo paso en el desarrollo del sistema de agentes es la implementación del **Agente Orquestador**, que coordinará múltiples agentes especializados y planificará flujos de trabajo complejos.

Para más detalles sobre los agentes específicos, consulte la documentación en cada archivo de implementación. 