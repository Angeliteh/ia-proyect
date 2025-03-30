#!/usr/bin/env python
"""
Model Manager Example

Este script muestra cómo usar el sistema de gestión de modelos para cargar y utilizar
diferentes modelos de IA tanto locales como en la nube.
"""

import os
import sys
import argparse
import time
import logging
import json
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("model_manager_example")

# Añadir la ruta del proyecto al PATH de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_dir, ".env"))
    logger.info("Variables de entorno cargadas desde .env")
except ImportError:
    logger.warning("No se pudo importar python-dotenv. Las variables de entorno no se cargarán desde .env")

# Intentar importar los módulos reales
try:
    # Importar directamente desde models.core
    from models.core import ModelInfo, ModelManager, ResourceDetector
    
    logger.info("Módulos de gestión de modelos importados correctamente")
    USING_REAL_MODULES = True
except ImportError as e:
    logger.warning(f"Error al importar módulos reales de gestión de modelos: {e}")
    USING_REAL_MODULES = False
    logger.info("Usando implementaciones mínimas para demostración")
    
    # Implementaciones mínimas para demostración
    class ModelInfo:
        def __init__(self, name, provider, model_type, context_size=8192, max_tokens=None):
            self.name = name
            self.provider = provider  # 'openai', 'anthropic', 'google', 'local'
            self.model_type = model_type  # 'chat', 'completion', 'embedding'
            self.context_size = context_size
            self.max_tokens = max_tokens or context_size
            self.capabilities = []
        
        def __str__(self):
            return f"{self.name} ({self.provider}, {self.model_type})"
    
    class ResourceDetector:
        def __init__(self):
            self.available_ram = 16  # GB
            self.available_vram = 4  # GB
            
        def check_system_resources(self):
            # Esta es una implementación simulada
            return {
                "ram": {"total": 32, "available": self.available_ram, "unit": "GB"},
                "vram": {"total": 8, "available": self.available_vram, "unit": "GB"},
                "cpu": {"name": "Simulado CPU", "cores": 8, "threads": 16},
                "gpu": {"name": "Simulado GPU", "memory": 8, "unit": "GB"}
            }
        
        def can_run_model(self, model_info):
            # Siempre permitimos ejecutar modelos de nube
            if model_info.provider in ['openai', 'anthropic', 'google']:
                return True
            
            # Para modelos locales, comprobamos RAM/VRAM
            if model_info.provider == 'local':
                # Esto es una simulación muy básica
                model_size = {'q4_k_m': 2, 'q5_k_m': 3, 'q8_0': 6}.get('q4_k_m', 2)  # GB
                return self.available_vram >= model_size
            
            return False
    
    class ModelManager:
        CLOUD_PROVIDERS = {
            'openai': ['gpt-3.5-turbo', 'gpt-4o', 'gpt-4-turbo', 'gpt-4'],
            'anthropic': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku', 'claude-instant-1'],
            'google': ['gemini-2.0-flash', 'gemini-2.0-pro', 'gemini-1.5-pro', 'gemini-1.5-flash'],
        }
        
        LOCAL_MODELS = ['phi-3-mini', 'llama-3-8b', 'mistral-7b', 'phi-2']
        
        def __init__(self):
            self.resource_detector = ResourceDetector()
            self.loaded_models = {}
            self.available_models = self._discover_available_models()
        
        def _discover_available_models(self):
            """Descubrir modelos disponibles en el sistema."""
            available_models = {}
            
            # Añadir modelos de nube si hay claves API configuradas
            if os.environ.get('OPENAI_API_KEY'):
                for model in self.CLOUD_PROVIDERS['openai']:
                    available_models[model] = ModelInfo(
                        name=model,
                        provider='openai',
                        model_type='chat',
                        context_size=128 * 1024 if 'gpt-4' in model else 16 * 1024
                    )
            
            if os.environ.get('ANTHROPIC_API_KEY'):
                for model in self.CLOUD_PROVIDERS['anthropic']:
                    context_size = 200 * 1024 if 'opus' in model else 100 * 1024
                    available_models[model] = ModelInfo(
                        name=model,
                        provider='anthropic',
                        model_type='chat',
                        context_size=context_size
                    )
            
            if os.environ.get('GOOGLE_API_KEY'):
                for model in self.CLOUD_PROVIDERS['google']:
                    context_size = 1 * 1024 * 1024 if 'gemini-1.5' in model else 128 * 1024
                    available_models[model] = ModelInfo(
                        name=model,
                        provider='google',
                        model_type='chat',
                        context_size=context_size
                    )
            
            # Añadir modelos locales simulados
            for model in self.LOCAL_MODELS:
                available_models[model] = ModelInfo(
                    name=model,
                    provider='local',
                    model_type='chat',
                    context_size=8 * 1024  # Contextual window simulada
                )
            
            return available_models
        
        def get_available_models(self):
            """Obtener la lista de modelos disponibles."""
            return list(self.available_models.keys())
        
        def load_model(self, model_name):
            """Cargar un modelo para su uso."""
            if model_name not in self.available_models:
                return None
            
            model_info = self.available_models[model_name]
            
            # Verificar si el modelo ya está cargado
            if model_name in self.loaded_models:
                return self.loaded_models[model_name]
            
            # Verificar si tenemos recursos para ejecutar el modelo
            if not self.resource_detector.can_run_model(model_info):
                return None
            
            # Simulamos la carga del modelo
            logger.info(f"Cargando modelo: {model_name} (proveedor: {model_info.provider})")
            time.sleep(0.5)  # Simular tiempo de carga
            
            self.loaded_models[model_name] = {
                "info": model_info,
                "instance": f"MODELO_SIMULADO:{model_name}"
            }
            
            return self.loaded_models[model_name]
        
        def generate_text(self, model_name, prompt, max_tokens=100):
            """Generar texto usando el modelo especificado."""
            # Primero cargamos el modelo si no está cargado
            if model_name not in self.loaded_models:
                if not self.load_model(model_name):
                    return f"No se pudo cargar el modelo: {model_name}"
            
            model_info = self.available_models[model_name]
            
            # Simulamos la generación de texto según el proveedor
            logger.info(f"Generando texto con el modelo {model_name}...")
            
            # Ajustar max_tokens si es necesario
            if max_tokens > model_info.max_tokens:
                max_tokens = model_info.max_tokens
                logger.warning(f"max_tokens ajustado a {max_tokens} para el modelo {model_name}")
            
            # Simular retraso según complejidad del modelo
            delay = 0.5
            if model_info.provider == 'openai':
                delay = 0.8 if 'gpt-4' in model_name else 0.4
            elif model_info.provider == 'anthropic':
                delay = 1.0 if 'opus' in model_name else 0.5
            elif model_info.provider == 'google':
                delay = 0.6
            elif model_info.provider == 'local':
                delay = 1.2  # Los modelos locales suelen ser más lentos
            
            time.sleep(delay)
            
            # Generar respuesta simulada
            if "suma" in prompt.lower() or "calcula" in prompt.lower():
                return "El resultado de la operación es 42."
            elif "lista" in prompt.lower():
                return "1. Primer elemento\n2. Segundo elemento\n3. Tercer elemento"
            elif "ejemplo" in prompt.lower() or "código" in prompt.lower():
                if "python" in prompt.lower():
                    return "```python\ndef hello_world():\n    print('¡Hola, mundo!')\n\nhello_world()\n```"
                else:
                    return "```javascript\nfunction helloWorld() {\n    console.log('¡Hola, mundo!');\n}\n\nhelloWorld();\n```"
        else:
                return f"Esta es una respuesta simulada de {model_name}. El modelo ha procesado tu solicitud: '{prompt}' y ha generado esta respuesta. Esto es solo una demostración."

def main():
    parser = argparse.ArgumentParser(description="Ejemplo de uso del ModelManager")
    parser.add_argument("--model", default="gemini-2.0-flash", 
                        help="Modelo a utilizar (por defecto: gemini-2.0-flash)")
    parser.add_argument("--prompt", default="Dame un ejemplo de código en Python", 
                        help="Prompt a enviar al modelo")
    parser.add_argument("--max-tokens", type=int, default=100, 
                        help="Número máximo de tokens a generar")
    parser.add_argument("--list-models", action="store_true",
                        help="Listar modelos disponibles")
    parser.add_argument("--check-real-modules", action="store_true",
                        help="Verificar si se están usando módulos reales o simulados")
    
    args = parser.parse_args()
    
    # Reportar si estamos usando módulos reales o simulados
    if args.check_real_modules:
        if USING_REAL_MODULES:
            print("USING_REAL_MODULES = True")
            sys.exit(0)
        else:
            print("USING_REAL_MODULES = False")
            # No consideramos un error que se esté usando una implementación de fallback
            # solo lo reportamos para fines informativos
            sys.exit(0)
    
    # Crear gestor de modelos
    model_manager = ModelManager()
    
    # Listar modelos si se solicita
    if args.list_models:
        available_models = model_manager.get_available_models()
        print(f"Modelos disponibles ({len(available_models)}):")
        
        # Agrupar por proveedor para mejor visualización
        models_by_provider = {}
        for model_name in available_models:
            if model_name in model_manager.available_models:
                provider = model_manager.available_models[model_name].provider
                if provider not in models_by_provider:
                    models_by_provider[provider] = []
                models_by_provider[provider].append(model_name)
        
        for provider, models in models_by_provider.items():
            print(f"\n{provider.upper()}:")
            for model in models:
                print(f"  - {model}")
        
        return
    
    # Cargar el modelo seleccionado
    model_name = args.model
    if model_name not in model_manager.get_available_models():
        logger.error(f"Modelo '{model_name}' no disponible. Use --list-models para ver modelos disponibles.")
        return
    
    logger.info(f"Usando modelo: {model_name}")
    model = model_manager.load_model(model_name)
    
    if not model:
        logger.error(f"No se pudo cargar el modelo {model_name}")
        return
    
    # Mostrar información del modelo
    model_info = model["info"]
    print(f"\nInformación del modelo:")
    print(f"  Nombre: {model_info.name}")
    print(f"  Proveedor: {model_info.provider}")
    print(f"  Tipo: {model_info.model_type}")
    print(f"  Tamaño de contexto: {model_info.context_size} tokens")
    
    # Generar texto con el prompt proporcionado
    prompt = args.prompt
    max_tokens = args.max_tokens
    
    logger.info(f"Enviando prompt: {prompt}")
    logger.info(f"Tokens máximos: {max_tokens}")
    
    respuesta = model_manager.generate_text(model_name, prompt, max_tokens)
    
    print(f"\nRespuesta del modelo:")
    print(f"{respuesta}")

if __name__ == "__main__":
    main() 