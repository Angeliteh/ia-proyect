# Ejemplo de Búsqueda Semántica con MCP

Este ejemplo demuestra la potencia de las capacidades de búsqueda semántica implementadas en el servidor MCP de memoria.

## Características Demostradas

### 1. Embeddings Vectoriales
- Generación automática de embeddings para memorias
- Soporte para sentence-transformers (con fallback a función simple)
- Almacenamiento y recuperación de vectores de embedding

### 2. Tipos de Búsqueda
- **Búsqueda por palabras clave**: Encuentra coincidencias exactas
- **Búsqueda semántica**: Encuentra elementos relacionados por significado
- **Búsqueda vectorial directa**: Permite búsquedas en el espacio vectorial

### 3. Agente con Memoria Semántica
- Implementación de un `SemanticMemoryAgent` que puede:
  - Almacenar nuevos conocimientos con embeddings
  - Realizar búsquedas semánticas sobre su memoria
  - Responder preguntas basándose en búsquedas semánticas
  - Combinar estrategias de búsqueda (semántica + palabras clave)

## Cómo Funciona

### Embeddings

Los embeddings son representaciones numéricas (vectores) que capturan el significado semántico de un texto. Textos con significados similares tendrán vectores cercanos en el espacio vectorial.

Este ejemplo utiliza dos métodos para generar embeddings:
1. **SentenceTransformers**: Modelos neuronales optimizados para embeddings de texto
2. **Función simple de hash**: Fallback cuando no está disponible SentenceTransformers

### Búsqueda Semántica

La búsqueda semántica funciona calculando la similitud (producto punto normalizado o similitud coseno) entre el vector de la consulta y los vectores de las memorias almacenadas. Las memorias más similares se devuelven como resultados.

Parámetros clave:
- `threshold`: Umbral mínimo de similitud (0-1)
- `limit`: Número máximo de resultados

## Ejecución del Ejemplo

```bash
# Instalación de dependencias (recomendado)
pip install sentence-transformers

# Ejecución del ejemplo
python examples/mcp/memory_semantic_example.py
```

## Secciones del Ejemplo

1. **Configuración**: Inicialización del servidor y cliente
2. **Verificación de capacidades**: Comprobación de soporte vectorial
3. **Creación de memorias**: Almacenamiento de datos con embeddings
4. **Generación de embeddings**: Vectorización de textos de consulta
5. **Comparación de búsquedas**: Contraste entre búsqueda por palabras clave y semántica
6. **Ejemplo práctico**: Implementación de un agente con capacidades semánticas

## Resultados Esperados

El ejemplo mostrará:
- Comparativas entre búsquedas estándar y semánticas
- Resultados más relevantes al usar búsqueda semántica
- Capacidad del agente para responder preguntas basadas en búsqueda semántica

## Integración en Aplicaciones

Este componente puede integrarse para:
- Sistemas de memoria a largo plazo para agentes de IA
- Motores de búsqueda contextual
- Sistemas de recomendación
- Agentes conversacionales con memoria persistente

## Extensiones Posibles

- Implementación de clustering para organizar memorias semánticamente
- Uso de modelos de embedding más avanzados (ej. multilingual-e5)
- Añadir pesos a diferentes partes del contenido para búsquedas más precisas
- Implementar búsqueda híbrida (BM25 + vectorial) 