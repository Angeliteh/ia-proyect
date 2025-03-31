# Servidor MCP de Memoria

Este módulo implementa un servidor MCP para gestionar un sistema de memoria persistente 
con capacidades avanzadas de búsqueda.

## Características

- Operaciones CRUD completas para memorias
- Persistencia en SQLite
- Búsqueda por palabras clave y metadatos
- **Búsqueda semántica vectorial**
- Generación de embeddings para memorias
- Compatibilidad con diversos tipos de memoria (episódica, semántica, etc.)

## Recursos y Acciones Soportadas

| Recurso | Acción | Descripción |
|---------|--------|-------------|
| `MEMORY` | `GET` | Recuperar una memoria por ID |
| `MEMORY` | `LIST` | Listar todas las memorias o filtrar por criterios |
| `MEMORY` | `SEARCH` | Buscar memorias por contenido o metadatos |
| `MEMORY` | `CREATE` | Crear una nueva memoria |
| `MEMORY` | `UPDATE` | Actualizar una memoria existente |
| `MEMORY` | `DELETE` | Eliminar una memoria por ID |
| `vector` | `GET` | Generar un embedding para un texto |
| `vector` | `SEARCH` | Realizar búsqueda semántica directa |

## Ejemplos de Uso

### Búsqueda Estándar

```python
search_message = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type=MCPResource.MEMORY,
    resource_path="/",
    data={
        "query": "python programming",
        "limit": 5
    }
)
```

### Búsqueda Semántica

```python
semantic_search_message = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type=MCPResource.MEMORY,
    resource_path="/",
    data={
        "query": "lenguajes de desarrollo web",
        "limit": 5,
        "semantic": True,
        "threshold": 0.2  # Umbral de similitud
    }
)
```

### Búsqueda Vectorial Directa

```python
vector_search_message = MCPMessage(
    action=MCPAction.SEARCH,
    resource_type="vector",
    resource_path="/",
    data={
        "query": "Cómo funcionan las redes neuronales",
        "limit": 5,
        "threshold": 0.15
    }
)
```

### Generar Embedding para un Texto

```python
embedding_message = MCPMessage(
    action=MCPAction.GET,
    resource_type="vector",
    resource_path="/",
    data={"text": "Texto para convertir en vector"}
)
```

## Integración con Sentence Transformers

El servidor de memoria puede utilizar modelos de Sentence Transformers para generar embeddings de alta calidad. Si la biblioteca está disponible, se utilizará automáticamente; de lo contrario, se utilizará una función de embedding simple basada en hash.

Para instalar sentence-transformers:
```
pip install sentence-transformers
```

## Ejemplo Completo

Ver `examples/mcp/memory_semantic_example.py` para un ejemplo que demuestra todas las capacidades del servidor de memoria, incluyendo:

- Creación de memorias con embeddings
- Comparación entre búsqueda estándar y semántica
- Implementación de un agente que utiliza memoria semántica
- Estrategia combinada de búsqueda (semántica con fallback a palabras clave) 