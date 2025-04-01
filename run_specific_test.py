#!/usr/bin/env python
"""
Script para ejecutar pruebas de integración específicas.

Este script permite ejecutar pruebas de integración individuales del sistema V.I.O.,
lo que facilita depurar problemas específicos sin tener que ejecutar todas las pruebas.
También permite deshabilitar el TTS para reducir la verbosidad de los logs.
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List, Optional

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
sys.path.insert(0, project_root)

# Importar el tester de integración
from test_integration import IntegrationTester

# Lista de pruebas disponibles
AVAILABLE_TESTS = [
    "direct_communication",      # Prueba de comunicación directa entre agentes
    "vio_delegation",           # Prueba de delegación de V.I.O. a agentes especializados
    "orchestrator_coordination", # Prueba de coordinación multi-agente vía OrchestratorAgent
    "planner_execution",        # Prueba de planificación y ejecución de tareas complejas
    "memory_queries",           # Prueba de consultas de memoria semántica y por palabras clave
    "end_to_end_flow"           # Prueba de flujo completo de principio a fin
]

def configure_logging(verbose: bool, log_file: Optional[str] = None):
    """Configura el sistema de logging según los parámetros."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configuración básica para consola
    handlers = [logging.StreamHandler()]
    
    # Agregar manejador para archivo si se especifica
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    # Configurar formato básico o detallado según verbosidad
    if verbose:
        log_format = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    else:
        log_format = '%(levelname)-8s | %(message)s'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )
    
    # Silenciar logs no esenciales si no es modo verbose
    if not verbose:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('mcp').setLevel(logging.WARNING)

def disable_tts():
    """Deshabilita el TTS para reducir la verbosidad."""
    # Modificar temporalmente el módulo de TTS para que no genere audio
    try:
        from tts.core.agent_tts_interface import AgentTTSInterface
        
        # Guardar método original
        original_process = AgentTTSInterface.process_response
        
        # Reemplazar con versión que no hace nada
        def dummy_process(self, *args, **kwargs):
            return {"success": True, "audio_file": None, "voice": "dummy"}
        
        AgentTTSInterface.process_response = dummy_process
        print("TTS deshabilitado correctamente.")
        
        # Devolver función para restaurar
        def restore_tts():
            AgentTTSInterface.process_response = original_process
            print("TTS restaurado.")
        
        return restore_tts
    except ImportError:
        print("Módulo TTS no encontrado, no se requiere deshabilitar.")
        return lambda: None

async def run_specific_tests(test_names: List[str], no_tts: bool, verbose: bool):
    """Ejecuta las pruebas especificadas."""
    # Deshabilitar TTS si se solicita
    restore_tts = None
    if no_tts:
        restore_tts = disable_tts()
    
    try:
        # Inicializar el tester
        tester = IntegrationTester()
        
        # Configurar el entorno de prueba
        if not await tester.setup():
            print("❌ Error al configurar el entorno de prueba")
            return False
        
        # Añadir memorias de prueba
        if not await tester.add_test_memories():
            print("⚠️ Error al añadir memorias de prueba")
        
        results = {}
        
        try:
            # Ejecutar las pruebas seleccionadas
            for test_name in test_names:
                test_method = getattr(tester, f"test_{test_name}", None)
                if test_method:
                    print(f"\n{'='*80}\n🔍 Ejecutando prueba: {test_name}\n{'='*80}")
                    try:
                        result = await test_method()
                        results[test_name] = result
                        print(f"Resultado: {'✅ ÉXITO' if result else '❌ FALLO'}")
                    except Exception as e:
                        print(f"❌ Error durante la prueba: {str(e)}")
                        if verbose:
                            import traceback
                            traceback.print_exc()
                        results[test_name] = False
                else:
                    print(f"❌ Prueba '{test_name}' no encontrada")
                    results[test_name] = False
                
                # Pequeña pausa entre pruebas
                await asyncio.sleep(0.5)
                
            # Mostrar resumen
            print(f"\n{'='*80}\nRESUMEN DE RESULTADOS\n{'='*80}")
            all_passed = True
            for test_name, result in results.items():
                status = "✅ ÉXITO" if result else "❌ FALLO"
                print(f"{status} - {test_name}")
                all_passed = all_passed and result
                
            print(f"{'='*80}")
            print(f"RESULTADO GENERAL: {'✅ TODAS LAS PRUEBAS EXITOSAS' if all_passed else '❌ HAY PRUEBAS FALLIDAS'}")
            print(f"{'='*80}")
            
            return all_passed
            
        finally:
            # Limpiar recursos
            await tester.cleanup()
            print("🧹 Recursos liberados")
    
    finally:
        # Restaurar TTS si fue deshabilitado
        if restore_tts:
            restore_tts()

def parse_args():
    """Procesa los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Ejecuta pruebas específicas del sistema de integración.")
    
    # Argumentos para seleccionar pruebas
    parser.add_argument(
        "tests", 
        nargs="*",
        choices=AVAILABLE_TESTS + ["all"],
        default=["all"],
        help="Pruebas a ejecutar. Usar 'all' para todas las pruebas."
    )
    
    # Opciones de configuración
    parser.add_argument("--no-tts", action="store_true", help="Deshabilita el TTS para reducir logs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Muestra logs detallados")
    parser.add_argument("--log-file", help="Guarda los logs en un archivo")
    
    return parser.parse_args()

def main():
    """Función principal."""
    args = parse_args()
    
    # Configurar logging
    configure_logging(args.verbose, args.log_file)
    
    # Determinar pruebas a ejecutar
    tests_to_run = args.tests
    if "all" in tests_to_run:
        tests_to_run = AVAILABLE_TESTS
    
    print(f"🧪 Ejecutando pruebas: {', '.join(tests_to_run)}")
    if args.no_tts:
        print("🔇 TTS deshabilitado")
    
    # Ejecutar pruebas
    result = asyncio.run(run_specific_tests(tests_to_run, args.no_tts, args.verbose))
    
    # Retornar código de salida adecuado
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main()) 