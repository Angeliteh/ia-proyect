#!/usr/bin/env python
"""
Script para ejecutar pruebas organizadas de los ejemplos disponibles.

Este script permite ejecutar ejemplos específicos o grupos de ejemplos
para facilitar la verificación de la funcionalidad del sistema.
"""

import os
import sys
import argparse
import subprocess
import logging
from typing import Dict, List, Tuple, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("test_runner")

# Directorio actual donde se encuentra el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = SCRIPT_DIR  # Los ejemplos están en el mismo directorio que este script

# Organización de pruebas por categorías
TESTS: Dict[str, Dict[str, Dict[str, str]]] = {
    "mcp": {
        "description": "Pruebas relacionadas con el Model Context Protocol (MCP)",
        "tests": {
            "core": {
                "description": "Pruebas del núcleo MCP",
                "script": "mcp_core_example.py",
                "args": ""
            },
            "echo": {
                "description": "Cliente MCP Echo simple",
                "script": "mcp_echo_client_example.py",
                "args": ""
            },
            "http": {
                "description": "Cliente MCP sobre HTTP",
                "script": "mcp_http_client_example.py",
                "args": ""
            }
        }
    },
    "brave": {
        "description": "Pruebas relacionadas con la integración de Brave Search",
        "tests": {
            "api": {
                "description": "Prueba directa de la API de Brave",
                "script": "test_brave_api.py",
                "args": ""
            },
            "client": {
                "description": "Cliente MCP para Brave Search",
                "script": "brave_search_client_example.py",
                "args": ""
            },
            "server": {
                "description": "Servidor MCP para Brave Search",
                "script": "brave_search_server_example.py",
                "args": "--auto-exit"
            },
            "mcp_test": {
                "description": "Prueba de integración MCP con Brave API",
                "script": "brave_api_mcp_test.py",
                "args": ""
            }
        }
    },
    "sqlite": {
        "description": "Pruebas relacionadas con el servidor SQLite MCP",
        "tests": {
            "direct": {
                "description": "Prueba directa del servidor SQLite MCP",
                "script": "sqlite_mcp_example.py",
                "args": "--mode direct"
            },
            "http": {
                "description": "Prueba del servidor SQLite MCP sobre HTTP",
                "script": "sqlite_mcp_example.py",
                "args": "--mode http"
            },
            "both": {
                "description": "Prueba completa del servidor SQLite MCP (directo y HTTP)",
                "script": "sqlite_mcp_example.py",
                "args": "--mode both"
            }
        }
    },
    "models": {
        "description": "Pruebas relacionadas con el gestor de modelos de IA",
        "tests": {
            "manager": {
                "description": "Prueba del gestor de modelos",
                "script": "model_manager_example.py",
                "args": ""
            }
        }
    }
}

def run_test(category: str, test_name: str) -> Tuple[int, str]:
    """
    Ejecuta un test específico.
    
    Args:
        category: Categoría del test
        test_name: Nombre del test
        
    Returns:
        Tupla con el código de salida y la salida del proceso
    """
    if category not in TESTS or test_name not in TESTS[category]["tests"]:
        return 1, f"Test {category}/{test_name} no encontrado"
    
    test_info = TESTS[category]["tests"][test_name]
    script_path = os.path.join(EXAMPLES_DIR, test_info["script"])
    
    if not os.path.exists(script_path):
        return 1, f"Script {script_path} no encontrado"
    
    args = test_info["args"].split() if test_info["args"] else []
    cmd = [sys.executable, script_path] + args
    
    logger.info(f"Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, f"Error ejecutando prueba: {e}"

def list_tests() -> None:
    """Muestra una lista de las pruebas disponibles."""
    print("\n=== Pruebas disponibles ===\n")
    
    for category, info in TESTS.items():
        print(f"\n== {category.upper()} - {info['description']} ==")
        
        for test_name, test_info in info["tests"].items():
            print(f"  {category}:{test_name} - {test_info['description']}")
            
            # Mostrar script y argumentos
            script = test_info["script"]
            args = test_info["args"]
            print(f"    Script: {script}")
            if args:
                print(f"    Args: {args}")
    
    print("\nEjemplos de uso:")
    print("  python run_tests.py --list")
    print("  python run_tests.py --run mcp:core")
    print("  python run_tests.py --run sqlite:direct")
    print("  python run_tests.py --run-category sqlite")

def run_category(category: str) -> bool:
    """
    Ejecuta todas las pruebas en una categoría.
    
    Args:
        category: Nombre de la categoría
        
    Returns:
        True si todas las pruebas tuvieron éxito, False en caso contrario
    """
    if category not in TESTS:
        logger.error(f"Categoría '{category}' no encontrada")
        return False
    
    logger.info(f"Ejecutando todas las pruebas de la categoría '{category}'")
    
    success = True
    for test_name in TESTS[category]["tests"]:
        logger.info(f"=== Prueba: {category}:{test_name} ===")
        
        exit_code, output = run_test(category, test_name)
        
        if exit_code == 0:
            logger.info(f"Prueba {category}:{test_name} completada con éxito")
        else:
            logger.error(f"Prueba {category}:{test_name} falló (código: {exit_code})")
            success = False
        
        # Mostrar primeras y últimas líneas de la salida para no abrumar
        output_lines = output.splitlines()
        if len(output_lines) > 20:
            logger.info("Primeras 10 líneas de la salida:")
            for line in output_lines[:10]:
                print(f"  {line}")
            print("  ...")
            logger.info("Últimas 10 líneas de la salida:")
            for line in output_lines[-10:]:
                print(f"  {line}")
        else:
            logger.info("Salida completa:")
            for line in output_lines:
                print(f"  {line}")
        
        print("\n")  # Separador entre pruebas
    
    return success

def run_all_tests() -> bool:
    """
    Ejecuta todas las pruebas de todas las categorías.
    
    Returns:
        True si todas las pruebas tuvieron éxito, False en caso contrario
    """
    logger.info("Ejecutando todas las pruebas disponibles")
    
    success = True
    for category in TESTS.keys():
        logger.info(f"\n=== EJECUTANDO PRUEBAS DE CATEGORÍA: {category.upper()} ===\n")
        category_success = run_category(category)
        if not category_success:
            success = False
    
    return success

def main() -> None:
    """Función principal que procesa los argumentos y ejecuta las pruebas."""
    parser = argparse.ArgumentParser(description="Ejecutor de pruebas para ejemplos IA Project")
    
    # Grupo mutuamente excluyente para las acciones
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--list", action="store_true", help="Listar todas las pruebas disponibles")
    action_group.add_argument("--run", help="Ejecutar una prueba específica (formato: categoria:prueba)")
    action_group.add_argument("--run-category", help="Ejecutar todas las pruebas de una categoría")
    action_group.add_argument("--run-all", action="store_true", help="Ejecutar todas las pruebas disponibles")
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar salida detallada")
    
    args = parser.parse_args()
    
    # Configurar nivel de logging según verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Listar pruebas disponibles
    if args.list:
        list_tests()
        return
    
    # Ejecutar prueba específica
    if args.run:
        try:
            category, test_name = args.run.split(":")
        except ValueError:
            logger.error("Formato incorrecto. Debe ser 'categoria:prueba'")
            return
        
        logger.info(f"Ejecutando prueba {category}:{test_name}")
        exit_code, output = run_test(category, test_name)
        
        if exit_code == 0:
            logger.info(f"Prueba {category}:{test_name} completada con éxito")
        else:
            logger.error(f"Prueba {category}:{test_name} falló (código: {exit_code})")
        
        print("\n--- Salida de la prueba ---")
        print(output)
    
    # Ejecutar todas las pruebas de una categoría
    if args.run_category:
        success = run_category(args.run_category)
        
        if success:
            logger.info(f"Todas las pruebas de la categoría '{args.run_category}' completadas con éxito")
        else:
            logger.error(f"Una o más pruebas de la categoría '{args.run_category}' fallaron")
    
    # Ejecutar todas las pruebas
    if args.run_all:
        success = run_all_tests()
        
        if success:
            logger.info("Todas las pruebas completadas con éxito")
        else:
            logger.error("Una o más pruebas fallaron")

if __name__ == "__main__":
    main() 