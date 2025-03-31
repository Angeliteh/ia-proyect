# Sistema de Gestión de Modelos

Este directorio contiene la implementación del sistema de gestión de modelos de IA, tanto locales como en la nube, con detección de recursos y sistema de fallback.

## Estructura del Directorio

```
models/
├── core/                   # Componentes centrales del sistema
│   ├── model_manager.py    # Gestor de modelos
│   └── resource_detector.py# Detector de recursos
├── cloud/                  # Modelos de IA en la nube
│   ├── gemini_model.py     # Implementación de Google Gemini
│   └── ...                 # Otros modelos en la nube (OpenAI, etc.)
├── local/                  # Modelos de IA locales
│   ├── llama_cpp_model.py  # Implementación de modelos con llama.cpp
│   └── ...                 # Otros modelos locales
└── README.md               # Este archivo
```

## Arquitectura

El sistema de modelos utiliza las siguientes clases principales:

- `ModelInterface`: Interfaz base que deben implementar todos los modelos.
- `ModelInfo`: Contiene información sobre un modelo (nombre, tipo, ruta, etc.).
- `ModelOutput`: Clase estandarizada para las salidas de los modelos.
- `ModelManager`: Gestor central que carga, usa y descarga modelos.
- `ResourceDetector`: Detecta recursos del sistema (CPU, RAM, GPU).

### Diagrama de Flujo

```
+-------------+      +-----------------+      +----------------+
| Usuario/API |----->| ModelManager    |----->| ModelInterface |
+-------------+      | - load_model()  |      | - generate()   |
                     | - unload_model()|      | - generate_stream() |
                     +-----------------+      +----------------+
                            |                     ^
                            v                     |
                     +-----------------+    +----------------+
                     | ResourceDetector|    | Implementaciones |
                     | - detect_gpu()  |    | - GeminiModel   |
                     | - detect_cpu()  |    | - LlamaCppModel |
                     +-----------------+    +----------------+
```

## Características Principales

- **Carga dinámica de modelos**: Los modelos se cargan según necesidad y se liberan cuando no se usan.
- **Detección de recursos**: Selecciona automáticamente CPU o GPU según disponibilidad.
- **Streaming de texto**: Permite generación en tiempo real con ambos tipos de modelos.
- **Sistema de fallback**: Si un modelo falla, puede intentar con otro.
- **Mínimas restricciones de contenido**: Configuración permisiva para evitar censura.

## Cómo Usar

### Ejemplo Básico

```python
import asyncio
from models.core import ModelManager

async def main():
    # Crear el gestor de modelos
    model_manager = ModelManager()
    
    # Cargar un modelo
    model, info = await model_manager.load_model("gemini-2.0-flash")
    
    # Generar texto
    response = await model.generate(
        prompt="Escribe un poema sobre la tecnología",
        max_tokens=500,
        temperature=0.7
    )
    
    print(response.text)
    
    # Descargar el modelo
    await model_manager.unload_model("gemini-2.0-flash")

if __name__ == "__main__":
    asyncio.run(main())
```

### Ejemplo con Streaming

```python
import asyncio
from models.core import ModelManager

async def main():
    model_manager = ModelManager()
    model, _ = await model_manager.load_model("mistral-7b-instruct")
    
    # Usar generación en streaming
    async for chunk in model.generate_stream(
        prompt="Escribe un cuento de misterio",
        max_tokens=500
    ):
        print(chunk, end="", flush=True)
    
    await model_manager.unload_model("mistral-7b-instruct")

if __name__ == "__main__":
    asyncio.run(main())
```

## Añadir un Nuevo Modelo

Para añadir un nuevo modelo al sistema, sigue estos pasos:

### 1. Crear la Implementación del Modelo

Crea un nuevo archivo en `models/cloud/` o `models/local/` según corresponda:

```python
# models/cloud/nuevo_modelo.py
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from ..core.model_manager import ModelInterface, ModelInfo, ModelOutput

class NuevoModelo(ModelInterface):
    def __init__(self, model_info: ModelInfo):
        self.model_info = model_info
        # Inicialización específica del modelo
    
    async def generate(self, prompt: str, max_tokens: int = 1024, 
                      temperature: float = 0.7) -> ModelOutput:
        # Implementación de generación de texto
        return ModelOutput(text="Texto generado", tokens=10)
    
    async def generate_stream(self, prompt: str, max_tokens: int = 1024,
                             temperature: float = 0.7) -> AsyncGenerator[str, None]:
        # Implementación de streaming
        yield "Texto "
        yield "generado "
        yield "en chunks"
```

### 2. Registrar el Nuevo Modelo en ModelManager

En `models/core/model_manager.py`, añade la referencia al nuevo modelo:

```python
self.model_implementations = {
    ModelType.MISTRAL.value: "models.local.llama_cpp_model.LlamaCppModel",
    ModelType.GEMINI.value: "models.cloud.gemini_model.GeminiModel",
    ModelType.NUEVO.value: "models.cloud.nuevo_modelo.NuevoModelo" # Nuevo modelo
}
```

### 3. Añadir el Tipo de Modelo

En `models/core/model_manager.py`, agrega el nuevo tipo de modelo:

```python
class ModelType(str, Enum):
    """Tipos de modelos disponibles."""
    LLAMA = "llama"
    MISTRAL = "mistral"
    GEMINI = "gemini"
    NUEVO = "nuevo"  # Nuevo tipo de modelo
```

### 4. Configuración del Modelo

Añade la configuración en `config/models.json`:

```json
{
  "models": [
    {
      "name": "nuevo-modelo",
      "model_type": "nuevo",
      "local": false,
      "api_key_env": "NUEVO_API_KEY",
      "context_length": 16384
    }
  ]
}
```

## Mejores Prácticas

1. **Manejo de errores**: Implementa un buen manejo de excepciones en los modelos.
2. **Streaming eficiente**: Utiliza chunks pequeños para una experiencia fluida.
3. **Liberación de recursos**: Siempre llama a `unload_model()` cuando termines.
4. **Configuración modular**: Usa el archivo JSON para configurar los modelos.
5. **Extensibilidad**: Sigue los patrones existentes al añadir funcionalidades.

## Pruebas y Ejemplos

Consulta los ejemplos en el directorio `examples/models/` para ver implementaciones completas y casos de uso.

- `model_manager_example.py`: Muestra el uso básico del ModelManager.
- `streaming_example.py`: Ejemplo de generación en tiempo real.
- `fallback_example.py`: Demostración del sistema de fallback entre modelos. 