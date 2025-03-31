# Agentes Especializados

Este directorio contiene implementaciones de agentes especializados en tareas específicas.

## Agentes Disponibles

### CodeAgent
Agente especializado en tareas de programación como generación, explicación y depuración de código.

### SystemAgent
Agente para interactuar con el sistema operativo, realizar operaciones de archivos y ejecutar comandos.

### MemoryAgent
Agente especializado en gestión de memoria semántica con capacidades de búsqueda vectorial.

- **Funcionalidades clave**:
  - Búsqueda semántica en memorias
  - Recuperación por similitud de significado
  - Integración con MCP y sistema de embeddings vectoriales
  - Delegación desde MainAssistant

- **Documento de referencia**: Ver `examples/memory/README_memoria_semantica.md` para documentación detallada.

## Uso Común

Los agentes especializados se registran con el sistema de comunicación y pueden recibir solicitudes del MainAssistant:

```python
# Registrar un agente especializado
communicator.register_agent(memory_agent)
communicator.register_agent(main_assistant)

# Desde el código del MainAssistant
if "memoria" in query.lower():
    # Delegar a MemoryAgent
    return await self.delegate_to_agent("memory", query, context)
```

## Integración con MainAssistant

El asistente principal (MainAssistant) actúa como coordinador central y puede delegar tareas a los agentes especializados según sea necesario. 