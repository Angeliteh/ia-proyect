# Sistema de Memoria Semántica

Este componente proporciona capacidades de búsqueda semántica (vectorial) para el sistema de agentes IA, permitiendo recuperar información basada en significado y no solo en coincidencias exactas de texto.

## Componentes Principales

### 1. MemoryEmbedder
Convierte textos en vectores numéricos (embeddings) que capturan el significado semántico del contenido.

```python
from memory.processors.embedder import MemoryEmbedder

# Crear un embedder con configuración personalizada
embedder = MemoryEmbedder(
    embedding_function=my_custom_function,  # Opcional
    embedding_dim=768  # Por defecto
)

# Generar embedding para una memoria
embedding = embedder.generate_embedding(memory_item)
```

#### Modelo de Embeddings
El sistema usa **sentence-transformers/all-mpnet-base-v2** como modelo predeterminado para generar embeddings de alta calidad.

### 2. MCP Vector Resource
El protocolo MCP incluye soporte para búsquedas vectoriales a través del tipo de recurso `vector`:

```python
from mcp.core import MCPMessage, MCPAction, MCPResource

# Búsqueda semántica
search_msg = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type=MCPResource.VECTOR,
    resource_path="/",
    data={
        "query": "mi consulta de búsqueda",
        "threshold": 0.25  # Umbral de similitud
    }
)
```

### 3. MemoryAgent
Agente especializado para gestionar búsquedas semánticas y operaciones de memoria.

```python
from agents.specialized.memory_agent import MemoryAgent

# Crear agente de memoria
memory_agent = MemoryAgent(
    agent_id="memory",
    config={
        "memory_config": {...},
        "semantic_threshold": 0.25,  # Umbral para búsquedas semánticas
        "keyword_fallback_threshold": 0.2  # Umbral para búsqueda por palabras clave
    }
)
```

## Integración con Agentes

El sistema permite la delegación desde el `MainAssistant` al `MemoryAgent` para consultas de memoria:

```python
# Desde MainAssistant
response = await main_assistant.process(
    query="Busca en tu memoria información sobre transformers",
    context={"target_agent": "memory"}  # ID del MemoryAgent
)
```

## Configuración Recomendada

Para un rendimiento óptimo:

1. **Modelo de embeddings**: `sentence-transformers/all-mpnet-base-v2`
2. **Umbral semántico**: Entre 0.25 y 0.3
3. **Volumen de datos**: Mínimo 20-30 memorias diversas para resultados fiables

## Ejemplo de Uso

Ver `examples/agents/memory_semantic_agent.py` para un ejemplo completo que demuestra:
- Configuración del servidor de memoria MCP
- Creación de agentes (MainAssistant y MemoryAgent)
- Almacenamiento de memorias con embeddings
- Búsquedas semánticas
- Delegación entre agentes

## Rendimiento y Limitaciones

- **Hardware**: El rendimiento depende del hardware disponible (CPU/RAM)
- **Escalabilidad**: Con el modelo actual, funciona bien hasta ~1000 memorias
- **Precisión**: La calidad de resultados mejora con mayor volumen de datos
- **Modelos**: El rendimiento varía según el modelo de embeddings utilizado
  - **MiniLM**: Más rápido pero menos preciso
  - **MPNet**: Mejor calidad pero más recursos
  - **OpenAI/API**: Mayor calidad pero requiere conexión y costos

## Mejoras Futuras

- Implementación de índices vectoriales (HNSW/Annoy) para mejor rendimiento
- Soporte para embeddings de OpenAI/Cohere para mayor precisión
- Clustering automático de memorias similares
- Filtros avanzados por metadatos combinados con búsqueda semántica 