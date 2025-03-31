#!/usr/bin/env python
"""
Model Manager Example

Este script muestra cómo usar el sistema de gestión de modelos para cargar y utilizar
diferentes modelos de IA tanto locales como en la nube, con detección de recursos
y sistema de fallback.
"""

import os
import sys
import argparse
import asyncio
import logging
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

# Importar el ModelManager y ResourceDetector
from models.core import ModelManager
from models.core.resource_detector import ResourceDetector
from models.core.model_manager import ModelOutput

async def test_model(model_manager, model_name, prompt, max_tokens):
    """
    Prueba un modelo específico y retorna su respuesta.
    
    Args:
        model_manager: Instancia del ModelManager
        model_name: Nombre del modelo a probar
        prompt: Prompt a enviar
        max_tokens: Máximo número de tokens
        
    Returns:
        Respuesta del modelo o None si falla
    """
    try:
        logger.info(f"Probando modelo: {model_name}")
        model, model_info = await model_manager.load_model(model_name)
        
        logger.info(f"Generando texto con prompt: {prompt}")
        print(f"\nGenerando con {model_name}:")
        print("-" * 50)
        
        # Intentar usar streaming primero
        try:
            full_text = ""
            async for chunk in model.generate_stream(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7
            ):
                print(chunk, end="", flush=True)
                full_text += chunk
            print("\n" + "-" * 50)
            response = ModelOutput(text=full_text, tokens=len(full_text.split()))
        except (AttributeError, NotImplementedError):
            # Fallback a generación normal si no hay streaming
            response = await model.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7
            )
            print(response.text)
            print("-" * 50)
        
        logger.info(f"Respuesta generada ({response.tokens} tokens)")
        await model_manager.unload_model(model_name)
        return response.text
        
    except ImportError as e:
        logger.error(f"Error de importación con modelo {model_name}: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"Error de valor con modelo {model_name}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado con modelo {model_name}: {str(e)}")
        return None

async def main():
    parser = argparse.ArgumentParser(description="Ejemplo de uso del ModelManager con fallback")
    parser.add_argument("--cloud-model", default="gemini-2.0-flash", 
                        help="Modelo en la nube a utilizar (por defecto: gemini-2.0-flash)")
    parser.add_argument("--local-model", default="mistral-7b-instruct",
                        help="Modelo local a utilizar como fallback (por defecto: mistral-7b-instruct)")
    parser.add_argument("--prompt", default="Escribe un pequeño cuento que incluya: un gato, una biblioteca y un misterio. El cuento debe tener un final sorprendente.", 
                        help="Prompt a enviar al modelo")
    parser.add_argument("--max-tokens", type=int, default=500, 
                        help="Número máximo de tokens a generar")
    parser.add_argument("--list-models", action="store_true",
                        help="Listar modelos disponibles")
    parser.add_argument("--force-local", action="store_true",
                        help="Forzar el uso del modelo local")
    parser.add_argument("--no-stream", action="store_true",
                        help="Desactivar generación en tiempo real")
    
    args = parser.parse_args()
    
    # Crear gestor de modelos y detector de recursos
    config_path = os.path.join(project_dir, "config", "models.json")
    model_manager = ModelManager(config_path=config_path)
    resource_detector = ResourceDetector()
    
    # Listar modelos si se solicita
    if args.list_models:
        logger.info("Modelos disponibles:")
        for model in model_manager.list_available_models():
            logger.info(f"- {model['name']} ({model['model_type']})")
            if model.get('is_loaded'):
                logger.info("  [CARGADO]")
            if model.get('local'):
                logger.info(f"  Ruta: {model.get('path')}")
            else:
                logger.info(f"  API Key: {model.get('api_key_env')}")
        return
    
    # Detectar recursos disponibles
    resources = resource_detector.detect_resources()
    logger.info("Recursos del sistema detectados:")
    logger.info(f"CPU: {resources['cpu']['logical_cores']} cores")
    logger.info(f"Memoria disponible: {resources['memory']['available_gb']}GB")
    if resources['gpu']['available']:
        logger.info(f"GPU disponible: {resources['gpu']['devices'][0]['name']}")
        logger.info(f"VRAM disponible: {resources['gpu']['devices'][0]['free_memory_gb']}GB")
    else:
        logger.info("No se detectó GPU, usando CPU")
    
    try:
        # Probar modelo en la nube primero (a menos que se fuerce el local)
        cloud_response = None
        if not args.force_local:
            logger.info("Intentando usar modelo en la nube...")
            cloud_response = await test_model(
                model_manager,
                args.cloud_model,
                args.prompt,
                args.max_tokens
            )
        
        # Probar modelo local
        logger.info("Probando modelo local...")
        local_response = await test_model(
            model_manager,
            args.local_model,
            args.prompt,
            args.max_tokens
        )
        
        if not cloud_response and not local_response:
            logger.error("No se pudo obtener respuesta de ningún modelo")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 