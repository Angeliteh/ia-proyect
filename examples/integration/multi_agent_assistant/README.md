# Sistema Multi-Agente Integrado

Este ejemplo demuestra la integración completa de los componentes principales del sistema de agentes IA:

1. **MainAssistant** - Punto central de interacción
2. **Sistema de Memoria** con búsqueda semántica
3. **Agentes Especializados** conectados entre sí
4. **Sistema MCP** para comunicación entre componentes

## Componentes involucrados

Este ejemplo integra:

- **MemoryAgent**: Gestión de memoria semántica
- **CodeAgent**: Generación y análisis de código
- **SystemAgent**: Operaciones del sistema
- **EchoAgent**: Agente simple para testing
- **OrchestratorAgent**: Coordinación entre agentes
- **MainAssistant**: Hub central de interacción

## Cómo ejecutar

Hay dos formas de ejecutar este ejemplo:

### 1. Ejecución automática (demo)

Este script ejecuta una serie de consultas predefinidas para demostrar el sistema:

```bash
# Desde el directorio raíz del proyecto
python examples/integration/multi_agent_assistant/multi_agent_demo.py
```

### 2. Interfaz interactiva de línea de comandos

Para interactuar directamente con el sistema mediante línea de comandos:

```bash
# Versión básica
python examples/integration/multi_agent_assistant/interactive_cli.py

# Sin cargar memorias de ejemplo
python examples/integration/multi_agent_assistant/interactive_cli.py --no-examples

# Mostrar logs de depuración
python examples/integration/multi_agent_assistant/interactive_cli.py --debug
```

#### Comandos disponibles en la CLI interactiva

- `help`, `ayuda` - Muestra ayuda sobre los comandos disponibles
- `exit`, `salir`, `quit` - Sale del programa
- `agents`, `agentes` - Lista los agentes disponibles y sus capacidades
- `memory [texto]`, `memoria [texto]` - Crea una nueva memoria con el texto proporcionado
- `search [consulta]`, `buscar [consulta]` - Busca en la memoria con la consulta proporcionada

Para cualquier otra entrada, el sistema tratará el texto como una consulta y la procesará a través del MainAssistant.

## Ejemplos de consultas

El demo prueba automáticamente las siguientes consultas:

1. "Hola, ¿cómo estás?" - Respuesta directa del MainAssistant
2. "¿Qué sabes sobre Python?" - Búsqueda en memoria
3. "Genera un código simple en Python que calcule el factorial de un número" - Delegación al CodeAgent
4. "¿Qué es la inteligencia artificial?" - Búsqueda en memoria
5. "Muéstrame información sobre patrones de diseño" - Búsqueda en memoria y procesamiento

## Arquitectura

```
Usuario
  ↓
MainAssistant ← → MemoryAgent
  ↓     ↑           ↑
  ↓     ↑           ↑
  ↓  OrchestratorAgent
  ↓     ↑    ↑    ↑ 
  ↓     ↑    ↑    ↑
  ↓   CodeAgent SystemAgent EchoAgent
```

## Extensión del ejemplo

Este ejemplo puede extenderse:

1. Añadiendo nuevos agentes especializados
2. Implementando flujos de trabajo más complejos
3. Conectando con fuentes de datos externas vía MCP
4. Creando una interfaz de usuario web o GUI para interacción directa

## Conexiones MCP

```
               +---------------+
               | MemoryServer  |
               +-------+-------+
                       ↑
                       | MCP
                       ↓
+------------+  +------+-------+  +------------+
| MainAsst.  |→→| MemoryAgent  |←←| OtherAgents|
+------------+  +--------------+  +------------+
```

Este ejemplo muestra la arquitectura recomendada donde los servidores MCP exponen recursos que son consumidos por los agentes a través de clientes MCP. 