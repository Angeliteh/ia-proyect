# Sistema de Gestión de Modelos de IA

Este módulo proporciona un sistema completo para gestionar modelos de lenguaje de IA, tanto locales como en la nube, optimizando el uso de recursos del sistema.

## Características principales

- **Gestión unificada** de modelos locales y en la nube con una interfaz común
- **Detección automática de recursos** (CPU, RAM, GPU, VRAM) para optimizar la carga de modelos
- **Selección inteligente de dispositivo** (CPU/GPU) según el tamaño del modelo y recursos disponibles
- **Interfaz asíncrona** para todas las operaciones de modelo, incluyendo streaming de respuestas
- **Soporte para múltiples tipos de modelos**:
  - Locales: Llama, Mistral, Phi (usando llama.cpp)
  - Nube: OpenAI, Anthropic, Google Gemini
- **Configuración flexible** de modelos mediante archivos JSON

## Estructura del módulo

```
models/
├── core/                  # Componentes core
│   ├── model_manager.py   # Gestor principal de modelos
│   └── resource_detector.py # Detector de recursos del sistema
├── local/                 # Implementaciones de modelos locales
│   └── llama_cpp_model.py # Modelo usando llama.cpp
├── cloud/                 # Implementaciones de modelos en la nube
│   └── openai_model.py    # Cliente para la API de OpenAI
└── examples/              # Scripts de ejemplo
    ├── model_manager_example.py # Demo del gestor de modelos
    └── model_config.json  # Configuración de ejemplo
```

## Clases principales

### ModelManager

Clase central que gestiona la carga, uso y liberación de modelos. Proporciona métodos para:

- Cargar modelos automáticamente seleccionando el dispositivo óptimo
- Listar modelos disponibles y cargados
- Guardar y cargar configuraciones de modelos

### ModelInfo

Almacena información sobre un modelo específico:

- Nombre y tipo
- Ubicación (local o nube)
- Propiedades como longitud de contexto y nivel de cuantización
- API keys para modelos en la nube

### ModelInterface

Interfaz abstracta que todos los modelos implementan:

- Generación de texto (con o sin streaming)
- Tokenización y conteo de tokens
- Generación de embeddings

### ResourceDetector

Detecta los recursos disponibles en el sistema:

- Información de CPU (núcleos, hilos)
- Memoria RAM disponible
- GPUs y VRAM disponible
- Capacidad para estimar el dispositivo óptimo para cada modelo

## Uso básico

```python
import asyncio
from models import ModelManager

async def main():
    # Crear gestor de modelos 
    model_manager = ModelManager()
    
    # Listar modelos disponibles
    models = model_manager.list_available_models()
    print(f"Modelos disponibles: {len(models)}")
    
    # Cargar un modelo
    model, model_info = await model_manager.load_model("gpt-4o")
    
    # Generar texto
    result = await model.generate(
        prompt="Explica de manera sencilla cómo funciona un modelo de lenguaje grande.",
        max_tokens=1024
    )
    
    print(result.text)
    
    # Descargar modelo
    await model_manager.unload_model("gpt-4o")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuración

### Modelo local

```json
{
  "name": "mistral-7b-instruct",
  "model_type": "mistral",
  "local": true,
  "path": "models/local/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
  "context_length": 8192,
  "quantization": "q4_k_m",
  "parameters": 7.0
}
```

### Modelo en la nube

```json
{
  "name": "gpt-4o",
  "model_type": "openai",
  "local": false,
  "api_key_env": "OPENAI_API_KEY",
  "context_length": 128000
}
```

## Requisitos

### Generales
- Python 3.8+
- asyncio

### Para modelos locales
- llama-cpp-python
- (Opcional) PyTorch para detección de GPU

### Para modelos en la nube
- httpx

## Próximas mejoras

- Implementación de clientes para Anthropic y Google Gemini
- Caché de resultados de generación
- Balanceo de carga entre múltiples modelos
- Más opciones de cuantización y optimización 