"""
Ejemplo de uso del gestor de modelos.

Este script muestra cómo utilizar el gestor de modelos para cargar
y utilizar diferentes tipos de modelos, tanto locales como en la nube.
"""

import os
import sys
import asyncio
import logging
import json
import argparse
from typing import Dict, Any, List, Optional
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Añadir la ruta del proyecto al PATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar componentes del sistema
from models import ModelManager, ModelInfo, ModelType, QuantizationLevel, ModelOutput
from models.core.resource_detector import ResourceDetector

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Variables de entorno cargadas desde .env")
except ImportError:
    print("python-dotenv no está instalado. No se cargarán variables desde .env")
    print("Instálalo con: pip install python-dotenv")

async def test_model(
    manager: ModelManager, 
    model_name: str, 
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
    device: Optional[str] = None
) -> None:
    """
    Prueba un modelo generando texto a partir de un prompt.
    
    Args:
        manager: Gestor de modelos a utilizar
        model_name: Nombre del modelo a probar
        prompt: Prompt para la generación
        max_tokens: Máximo de tokens a generar
        temperature: Temperatura de generación
        stream: Si se debe usar modo streaming
        device: Dispositivo a utilizar (cpu, gpu, auto)
    """
    logger = logging.getLogger("example")
    
    try:
        # Cargar el modelo
        logger.info(f"Cargando modelo '{model_name}'...")
        
        # Inicializar las variables de información del dispositivo
        device_used = 'No disponible'
        device_info = 'No disponible'
        
        # Si el dispositivo es 'auto', decidir automáticamente
        force_device = None
        if device and device != 'auto':
            force_device = device
            # Actualizar device_used según el dispositivo forzado
            device_used = device.upper() if device else 'No disponible'
            device_info = "Dispositivo seleccionado manualmente"
            logger.info(f"Dispositivo seleccionado manualmente: {device}")
        
        # Cargar el modelo con el dispositivo especificado
        model, model_info = await manager.load_model(model_name, force_device=force_device)
        
        # Decidir automáticamente CPU/GPU si se seleccionó 'auto' o no se especificó
        if device == 'auto' or device is None:
            # Intentar obtener información si es un modelo local
            if model_info.local:
                # Obtener el dispositivo real usado
                if hasattr(model, 'model') and hasattr(model.model, 'model'):
                    llama_model = model.model.model
                    if hasattr(llama_model, 'n_gpu_layers') and hasattr(llama_model, 'params'):
                        n_gpu_layers = llama_model.n_gpu_layers
                        if n_gpu_layers > 0:
                            device_used = 'GPU'
                            device_info = f"{n_gpu_layers} capas en GPU"
                        else:
                            device_used = 'CPU'
                            device_info = "Todas las capas en CPU"
            
            logger.info(f"Dispositivo seleccionado automáticamente: {device_used} ({device_info})")
        else:
            # Para dispositivos forzados, también intentar detectar uso real de GPU
            if model_info.local:
                if hasattr(model, 'model') and hasattr(model.model, 'model'):
                    llama_model = model.model.model
                    if hasattr(llama_model, 'n_gpu_layers') and hasattr(llama_model, 'params'):
                        n_gpu_layers = llama_model.n_gpu_layers
                        if n_gpu_layers > 0:
                            device_used = 'GPU'
                            device_info = f"{n_gpu_layers} capas en GPU forzadas"
                        else:
                            device_used = 'CPU'
                            device_info = "Todas las capas en CPU (forzado a GPU falló)"
        
        # Verificar el tipo de modelo y mostrar mensaje informativo
        if not model_info.local:
            api_key_env = model_info.api_key_env
            api_provider = "OpenAI" if model_info.model_type == "openai" else "Anthropic"
            logger.info(f"Modelo en la nube de {api_provider}. Utilizando variable de entorno: {api_key_env}")
            
            # Verificar si la API key existe
            api_key = os.environ.get(api_key_env)
            if not api_key:
                logger.warning(f"[AVISO] No se encontró la clave API en la variable {api_key_env}")
                print(f"\n[AVISO] La variable de entorno {api_key_env} no está configurada.")
                print(f"Por favor, asegúrate de tener un archivo .env con tu clave API de {api_provider}:")
                print(f"{api_key_env}=tu-clave-aqui")
                return
            elif len(api_key) < 20:  # Verificación básica de longitud
                logger.warning(f"[AVISO] La clave API en {api_key_env} parece ser demasiado corta")
        else:
            # Para modelos locales, mostrar información de recursos
            detector = ResourceDetector()
            resources = detector.detect_resources()
            
            # Mostrar información del modelo
            model_size_gb = model_info.size_gb if model_info.size_gb else "Desconocido"
            parameters_b = model_info.parameters if model_info.parameters else "Desconocido"
            
            print(f"\n--- Información del modelo local ---")
            print(f"Nombre: {model_info.name}")
            print(f"Tipo: {model_info.model_type}")
            print(f"Parámetros: {parameters_b} billones")
            print(f"Tamaño aproximado: {model_size_gb} GB")
            print(f"Cuantización: {model_info.quantization}")
            print(f"Ruta: {model_info.path}")
            
            # Mostrar recursos del sistema
            print(f"\n--- Recursos del sistema ---")
            print(f"CPU: {resources['cpu']['logical_cores']} núcleos lógicos")
            print(f"RAM: {resources['memory']['total_gb']:.1f} GB (Disponible: {resources['memory']['available_gb']:.1f} GB)")
            
            if resources['gpu']['available']:
                for device in resources['gpu']['devices']:
                    print(f"GPU: {device['name']} ({device.get('total_memory_gb', 'N/A')} GB)")
            else:
                print("GPU: No detectada")
        
        logger.info(f"Modelo cargado: {model_info.name} ({model_info.model_type})")
        logger.info(f"Generando respuesta para prompt: {prompt[:50]}...")
        
        start_time = asyncio.get_event_loop().time()
        
        # Generar texto
        if stream:
            logger.info("Generando en modo streaming:")
            print("\n--- Respuesta en streaming ---")
            
            # Contadores para estadísticas
            total_tokens = 0
            
            async for chunk in await model.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            ):
                # Imprimir texto generado
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    total_tokens += chunk.tokens
                
                # Si es el último chunk, mostrar metadatos
                if chunk.metadata.get("is_complete", False):
                    duration = asyncio.get_event_loop().time() - start_time
                    tokens_per_second = total_tokens / duration if duration > 0 else 0
                    print(f"\n\n--- Generación completada ---")
                    print(f"Tokens generados: {total_tokens}")
                    print(f"Tiempo: {duration:.2f} segundos")
                    print(f"Velocidad: {tokens_per_second:.2f} tokens/segundo")
                    
                    if model_info.local:
                        hardware_info = "GPU parcial" if device_used == 'GPU' else "Solo CPU"
                        print(f"Hardware: {hardware_info} ({device_info})")
        else:
            # Generación completa (no streaming)
            result: ModelOutput = await model.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            tokens_per_second = result.tokens / duration if duration > 0 else 0
            
            print("\n--- Respuesta completa ---")
            print(result.text)
            print("\n--- Estadísticas ---")
            print(f"Tokens generados: {result.tokens}")
            print(f"Tiempo: {duration:.2f} segundos")
            print(f"Velocidad: {tokens_per_second:.2f} tokens/segundo")
            
            if model_info.local:
                hardware_info = "GPU parcial" if device_used == 'GPU' else "Solo CPU"
                print(f"Hardware: {hardware_info} ({device_info})")
            
            # Mostrar metadatos si hay
            if result.metadata:
                print("\n--- Metadatos ---")
                for key, value in result.metadata.items():
                    print(f"{key}: {value}")
        
        # Descargar modelo
        logger.info(f"Descargando modelo '{model_name}'...")
        await manager.unload_model(model_name)
        
    except Exception as e:
        logger.error(f"Error probando modelo '{model_name}': {e}")
        traceback.print_exc()
        
        # Manejo específico para errores comunes
        error_str = str(e).lower()
        error_msg = str(e)
        
        # Error 400: Bad Request con saldo insuficiente para Anthropic
        if "400" in error_str and "credit balance is too low" in error_str and "anthropic" in error_str:
            print("\n[AVISO] ERROR: Saldo insuficiente en Anthropic")
            print("Tu cuenta de Anthropic no tiene suficientes créditos para usar la API.")
            print("\nPasos para obtener créditos gratuitos:")
            print("1. Visita https://console.anthropic.com/settings/billing")
            print("2. Inicia sesión o crea una cuenta nueva")
            print("3. Busca la opción 'Claim Free Credits' o similar")
            print("4. Sigue las instrucciones para reclamar tus créditos gratuitos")
            print("5. Una vez confirmados los créditos (espera unos minutos), intenta nuevamente")
            
            # Si el usuario está utilizando la API por primera vez
            if "access the anthropic api" in error_str:
                print("\nNota: Si es la primera vez que utilizas la API de Anthropic, necesitas:")
                print("1. Crear una cuenta en https://console.anthropic.com/")
                print("2. Verificar tu correo electrónico")
                print("3. Reclamar los créditos gratuitos iniciales")
                print("4. Crear una clave API nueva en https://console.anthropic.com/settings/keys")
            return
        
        # Error 429: Too Many Requests
        elif "429" in error_str or "too many requests" in error_str:
            print("\n[AVISO] ERROR 429: Demasiadas solicitudes")
            print("Has excedido el límite de solicitudes para este modelo.")
            print("\nPosibles soluciones:")
            print("1. Espera unos minutos e intenta nuevamente")
            print("2. Prueba con un modelo diferente que tenga límites más altos:")
            print("   - gpt-3.5-turbo-16k suele tener límites más altos que gpt-4")
            print("   - claude-3-haiku-20240307 suele tener límites más altos que claude-3-opus-20240229")
            
            if "openai" in error_str:
                print("\nPara OpenAI:")
                print("3. Verifica tu saldo y límites en: https://platform.openai.com/account/billing")
                print("4. Si el error menciona 'quota exceeded', añade fondos a tu cuenta:")
                print("   a. Ve a https://platform.openai.com/account/billing")
                print("   b. Haz clic en 'Add to credit balance'")
                print("   c. Espera 3-5 minutos después de agregar fondos")
                print("   d. Si el problema persiste, crea una nueva API key")
            
            elif "anthropic" in error_str:
                print("\nPara Anthropic:")
                print("3. Verifica tu plan y límites en: https://console.anthropic.com/settings/billing")
                print("4. Considera actualizar tu plan si necesitas más cuota")
        
        # Error 401: Unauthorized
        elif "401" in error_str or "unauthorized" in error_str or "api key" in error_str:
            print("\n[AVISO] ERROR: Problema con la API Key")
            
            if "openai" in error_str:
                print("Error de autenticación con OpenAI:")
                print("1. Verifica que tu API key de OpenAI sea correcta")
                print("2. Asegúrate de que la API key comience con 'sk-'")
                print("3. Si acabas de agregar fondos, puede que necesites generar una nueva API key")
                print("4. Configura la clave en el archivo .env con el formato:")
                print("   OPENAI_API_KEY=sk-tu-clave-aqui")
                print("5. Si el problema persiste, visita: https://platform.openai.com/api-keys")
            
            elif "anthropic" in error_str:
                print("Error de autenticación con Anthropic:")
                print("1. Verifica que tu API key de Anthropic sea correcta")
                print("2. Asegúrate de que la API key comience con 'sk-ant'")
                print("3. Configura la clave en el archivo .env con el formato:")
                print("   ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui")
                print("4. Si el problema persiste, visita: https://console.anthropic.com/settings/keys")
            
            else:
                print("Problema de autenticación con el proveedor de API:")
                print("1. Asegúrate de haber configurado correctamente la clave API en el archivo .env")
                print("2. Verifica que la clave sea válida y esté activa")
                print("3. Si acabas de crear la clave, espera unos minutos para que se active")
        
        # Error 400: Bad Request (otros casos)
        elif "400" in error_str or "bad request" in error_str:
            print("\n[AVISO] ERROR 400: Bad Request")
            print("Hay un problema con el formato o contenido de la solicitud.")
            
            # Intentar extraer el mensaje de error más detallado
            if "detalle:" in error_msg:
                detail_start = error_msg.find("Detalle:") + 9
                detail = error_msg[detail_start:].strip()
                print(f"\nDetalles del error: {detail}")
            
            print("\nPosibles soluciones:")
            print("1. Verifica que el nombre del modelo sea correcto")
            print("2. Asegúrate de que el prompt no esté vacío")
            print("3. Comprueba que no estés excediendo los límites de tokens del modelo")
            print("4. Si el error persiste, contacta al soporte del proveedor de API")
        
        # Error de conexión
        elif "connect" in error_str or "timeout" in error_str or "connection" in error_str:
            print("\n[AVISO] ERROR: Problema de conexión")
            print("No se pudo conectar con el servidor de la API.")
            print("\nPosibles soluciones:")
            print("1. Verifica tu conexión a Internet")
            print("2. Comprueba si hay un firewall o proxy bloqueando la conexión")
            print("3. El servicio podría estar experimentando problemas. Intenta más tarde")
        
        else:
            # Para otros errores, mostrar el traceback completo
            print("\n[AVISO] Error inesperado:")
            traceback.print_exc()

async def main():
    """Función principal del ejemplo."""
    # Parsear argumentos
    parser = argparse.ArgumentParser(description="Ejemplo del gestor de modelos")
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo-16k", 
                      help="Nombre del modelo a usar (ej: gpt-3.5-turbo-16k, claude-3-haiku-20240307)")
    parser.add_argument("--prompt", type=str, 
                      default="Explica de manera sencilla cómo funciona un modelo de lenguaje grande.",
                      help="Prompt para generar texto")
    parser.add_argument("--max-tokens", type=int, default=256,
                      help="Máximo de tokens a generar (reducido para evitar límites)")
    parser.add_argument("--temperature", type=float, default=0.7,
                      help="Temperatura para la generación")
    parser.add_argument("--stream", action="store_true",
                      help="Usar modo streaming")
    parser.add_argument("--config", type=str, default="config/models.json",
                      help="Ruta al archivo de configuración de modelos")
    parser.add_argument("--device", type=str, choices=["cpu", "gpu", "auto"], default="auto",
                      help="Dispositivo a utilizar para modelos locales (cpu, gpu, auto)")
    
    args = parser.parse_args()
    
    # Comprobar si existe el archivo de configuración
    if args.config and not os.path.exists(args.config):
        print(f"[AVISO] El archivo de configuración '{args.config}' no existe.")
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), args.config)
        if os.path.exists(config_path):
            print(f"[INFO] Usando ruta alternativa: {config_path}")
            args.config = config_path
        else:
            print("[INFO] Se usará la configuración predeterminada.")
            args.config = None
    
    # Verificar si existe el archivo .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        print(f"[AVISO] No se encontró el archivo .env en {env_path}")
        print("Si deseas usar modelos en la nube, crea un archivo .env con tus claves API:")
        print("OPENAI_API_KEY=sk-tu-clave-aqui")
        print("ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui")
    
    # Verificar recursos disponibles
    print(f"\n--- Analizando recursos del sistema ---")
    detector = ResourceDetector()
    resources = detector.detect_resources()
    
    # Imprimir recursos principales
    gpu_available = resources['gpu']['available']
    if gpu_available:
        gpu_count = resources['gpu'].get('count', 0)
        print(f"- GPU: {gpu_count} dispositivo(s) encontrado(s)")
        for i, device in enumerate(resources['gpu']['devices']):
            print(f"  → GPU {i+1}: {device['name']} - "
                  f"{device.get('total_memory_gb', 'N/A')} GB")
    else:
        print("- GPU: No se detectaron dispositivos compatibles")
        
    print(f"- CPU: {resources['cpu']['logical_cores']} núcleos lógicos")
    print(f"- RAM: {resources['memory']['total_gb']:.2f} GB total, "
          f"{resources['memory']['available_gb']:.2f} GB disponible")
    
    if args.device == "gpu" and not gpu_available:
        print(f"\n[AVISO] Has seleccionado GPU, pero no se detectaron dispositivos GPU compatibles.")
        print(f"Se utilizará CPU en su lugar.")
        args.device = "cpu"
    
    if args.device == "auto":
        print(f"\nDispositivo: AUTO (selección automática basada en recursos)")
    else:
        print(f"\nDispositivo: {args.device.upper()} (seleccionado manualmente)")
    
    # Crear gestor de modelos
    model_manager = ModelManager(config_path=args.config)
    
    # Mostrar modelos disponibles
    available_models = model_manager.list_available_models()
    print(f"Modelos disponibles ({len(available_models)}):")
    for i, model in enumerate(available_models, 1):
        local_str = "LOCAL" if model["local"] else "NUBE"
        path_str = f" - {model['path']}" if model.get("path") else ""
        desc_str = f" - {model.get('description', '')}" if model.get("description") else ""
        print(f"{i}. {model['name']} ({model['model_type']}) - {local_str}{path_str}{desc_str}")
    
    # Comprobar si el modelo existe
    model_exists = args.model in [m["name"] for m in available_models]
    if not model_exists:
        print(f"[ERROR] El modelo '{args.model}' no está disponible")
        print("Modelos disponibles:", ", ".join([m["name"] for m in available_models]))
        return
    
    # Mostrar información del modelo seleccionado
    selected_model = next((m for m in available_models if m["name"] == args.model), None)
    if selected_model:
        print(f"\nModelo seleccionado: {args.model}")
        print(f"Tipo: {selected_model['model_type']}")
        print(f"Local: {'Sí' if selected_model['local'] else 'No'}")
        
        # Si es un modelo local, mostrar información adicional
        if selected_model['local']:
            model_size_gb = selected_model.get('size_gb', "Desconocido")
            parameters_b = selected_model.get('parameters', "Desconocido")
            quantization = selected_model.get('quantization', "Ninguna")
            
            print(f"Parámetros: {parameters_b} billones")
            print(f"Tamaño: {model_size_gb} GB")
            print(f"Cuantización: {quantization}")
            
            # Si es auto, estimar el dispositivo óptimo
            if args.device == "auto" and model_size_gb and model_size_gb != "Desconocido":
                optimal_device = detector.estimate_optimal_device(
                    model_size_gb=float(model_size_gb),
                    context_length=selected_model.get('context_length', 4096)
                )
                
                print(f"Dispositivo recomendado: {optimal_device['device'].upper()}")
                if 'warning' in optimal_device:
                    print(f"[AVISO] {optimal_device['warning']}")
        
        if not selected_model['local']:
            api_key_env = selected_model.get('api_key_env', 'Desconocido')
            print(f"Variable de entorno para API key: {api_key_env}")
            
            if api_key_env not in os.environ:
                print(f"[AVISO] No se encontró la variable {api_key_env} en el entorno")
        
        if 'description' in selected_model and selected_model['description']:
            print(f"Descripción: {selected_model['description']}")
    
    print(f"\nPrompt: {args.prompt[:50]}...")
    print(f"Configuración: max_tokens={args.max_tokens}, temperature={args.temperature}, stream={args.stream}")
    
    # Probar el modelo
    await test_model(
        manager=model_manager,
        model_name=args.model,
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        stream=args.stream,
        device=args.device
    )

if __name__ == "__main__":
    # Ejecutar función principal
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario")
    except Exception as e:
        print(f"Error en la aplicación: {e}")
        traceback.print_exc() 