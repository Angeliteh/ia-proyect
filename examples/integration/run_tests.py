#!/usr/bin/env python
"""
Test runner for the MCP system

This script provides an integrated way to run tests across different components
of the MCP system. It supports running individual tests, tests by category, 
or all tests, with detailed reporting options.
"""

import os
import sys
import time
import glob
import json
import argparse
import subprocess
import logging
import importlib
import shutil
import colorama
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import shlex

# Intentar importar dotenv para cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # Cargar variables de entorno del archivo .env
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("Advertencia: python-dotenv no está instalado. Las variables de entorno no se cargarán desde .env")
    print("Para instalar: pip install python-dotenv")

# Initialize colorama for cross-platform colored terminal output
colorama.init()

# Color codes for output
class Colors:
    HEADER = colorama.Fore.MAGENTA
    PASSED = colorama.Fore.GREEN
    WARNING = colorama.Fore.YELLOW
    FAILED = colorama.Fore.RED
    INFO = colorama.Fore.CYAN
    FALLBACK = colorama.Fore.BLUE
    RESET = colorama.Style.RESET_ALL

# Updated test configuration with new directory structure and dependencies
TEST_CONFIG = {
    "mcp": {
        "core": {
            "module": "mcp_core_example.py",
            "dir": "../mcp",
            "args": "",
            "expected_result": 0,
            "description": "Basic MCP core functionality test",
            "dependencies": {
                "packages": ["json", "asyncio"],
                "files": [],
                "env_vars": []
            }
        },
        "echo_client": {
            "module": "mcp_echo_client_example.py",
            "dir": "../mcp",
            "args": "",
            "expected_result": 0,
            "description": "Echo client MCP example test",
            "dependencies": {
                "packages": ["json", "asyncio"],
                "files": [],
                "env_vars": []
            }
        },
        "sqlite": {
            "module": "sqlite_mcp_example.py",
            "dir": "../mcp",
            "args": "",
            "expected_result": 0,
            "description": "SQLite MCP integration test",
            "dependencies": {
                "packages": ["sqlite3", "json"],
                "files": [],
                "env_vars": ["SQLITE_PATH"]
            }
        }
    },
    "brave": {
        "server": {
            "module": "brave_search_server_example.py",
            "dir": "../mcp",
            "args": "--auto-exit",
            "expected_result": 0,
            "description": "Brave Search MCP server test",
            "dependencies": {
                "packages": ["requests", "json"],
                "files": [],
                "env_vars": ["BRAVE_API_KEY"]
            }
        },
        "client": {
            "module": "brave_search_client_example.py",
            "dir": "../mcp",
            "args": "--query 'test query' --count 2 --mock-server",
            "expected_result": 0,
            "description": "Brave Search MCP client test",
            "dependencies": {
                "packages": ["requests", "json"],
                "files": [],
                "env_vars": []
            }
        },
        "api": {
            "module": "test_brave_api.py",
            "dir": ".",
            "args": "",
            "expected_result": 0,
            "description": "Brave API direct test",
            "dependencies": {
                "packages": ["requests", "dotenv"],
                "files": [],
                "env_vars": ["BRAVE_API_KEY"]
            }
        },
        "mcp_test": {
            "module": "brave_api_mcp_test.py",
            "dir": ".",
            "args": "",
            "expected_result": 0,
            "description": "Brave API MCP integration test",
            "dependencies": {
                "packages": ["requests", "json"],
                "files": [],
                "env_vars": ["BRAVE_API_KEY"]
            }
        }
    },
    "agents": {
        "echo": {
            "module": "echo_agent_example.py",
            "dir": "../agents",
            "args": "",
            "expected_result": 0,
            "description": "Echo agent basic test",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        },
        "code": {
            "module": "code_agent_example.py",
            "dir": "../agents",
            "args": "--task generate --model gemini-2.0-flash",
            "expected_result": 0,
            "description": "Code agent test with Gemini model",
            "dependencies": {
                "packages": ["google.generativeai"],
                "files": [],
                "env_vars": ["GOOGLE_API_KEY"]
            }
        },
        "system": {
            "module": "system_agent_example.py",
            "dir": "../agents",
            "args": "--task info",
            "expected_result": 0,
            "description": "System agent info task test",
            "dependencies": {
                "packages": ["psutil"],
                "files": [],
                "env_vars": []
            }
        },
        "system_files": {
            "module": "system_agent_example.py",
            "dir": "../agents",
            "args": "--task files",
            "expected_result": 0,
            "description": "System agent file listing test",
            "dependencies": {
                "packages": ["psutil"],
                "files": [],
                "env_vars": []
            }
        },
        "communication": {
            "module": "agent_communication_example.py",
            "dir": "../agents",
            "args": "--test echo",
            "expected_result": 0,
            "description": "Basic agent communication test",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        },
        "communication_chain": {
            "module": "agent_communication_example.py",
            "dir": "../agents",
            "args": "--test chain",
            "expected_result": 0,
            "description": "Agent communication chain test",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        },
        "orchestrator": {
            "module": "orchestrator_example.py",
            "dir": "../agents",
            "args": "",
            "expected_result": 0,
            "description": "Test del Agente Orquestador para coordinar agentes especializados",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        }
    },
    # Nuevas pruebas para MainAssistant
    "main_assistant": {
        "basic": {
            "module": "main_assistant_example.py",
            "dir": "../agents/main_assistant",
            "args": "--test direct",
            "expected_result": 0,
            "description": "Prueba básica del MainAssistant respondiendo directamente",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        },
        "delegation": {
            "module": "main_assistant_example.py",
            "dir": "../agents/main_assistant",
            "args": "--test all",
            "expected_result": 0,
            "description": "Prueba completa de delegación del MainAssistant a agentes especializados",
            "dependencies": {
                "packages": ["google.generativeai"],
                "files": [],
                "env_vars": ["GOOGLE_API_KEY"]
            }
        }
    },
    # Nuevas pruebas para TTS
    "tts": {
        "basic": {
            "module": "tts_echo_test.py",
            "dir": "../tts",
            "args": "--query 'Prueba de texto a voz' --no-play",
            "expected_result": 0,
            "description": "Prueba básica del sistema TTS con EchoAgent",
            "dependencies": {
                "packages": ["gtts", "pygame"],
                "files": [],
                "env_vars": []
            }
        },
        "voice_list": {
            "module": "tts_echo_test.py",
            "dir": "../tts",
            "args": "--list-voices --no-play",
            "expected_result": 0,
            "description": "Listar voces disponibles en el sistema TTS",
            "dependencies": {
                "packages": ["gtts"],
                "files": [],
                "env_vars": []
            }
        },
        "cache": {
            "module": "tts_echo_test.py",
            "dir": "../tts",
            "args": "--query 'Prueba de caché de TTS' --check-cache --no-play",
            "expected_result": 0,
            "description": "Prueba del sistema de caché de TTS",
            "dependencies": {
                "packages": ["gtts", "pygame"],
                "files": [],
                "env_vars": []
            }
        }
    },
    # Pruebas de manejo de errores
    "error_handling": {
        "agent_unavailable": {
            "module": "error_tests.py",
            "dir": "../error_handling",
            "args": "--test agent_unavailable",
            "expected_result": 0,
            "description": "Test de manejo de error cuando un agente no está disponible",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        },
        "invalid_request": {
            "module": "error_tests.py",
            "dir": "../error_handling",
            "args": "--test invalid_request",
            "expected_result": 0,
            "description": "Test de manejo de solicitudes inválidas",
            "dependencies": {
                "packages": [],
                "files": [],
                "env_vars": []
            }
        }
    },
    "models": {
        "manager": {
            "module": "model_manager_example.py",
            "dir": "../models",
            "args": "--model gemini-2.0-flash --max-tokens 32",
            "expected_result": 0,
            "description": "Model manager test with Gemini model",
            "dependencies": {
                "packages": ["google.generativeai"],
                "files": ["../models/model_config.json"],
                "env_vars": ["GOOGLE_API_KEY"]
            }
        },
        "local_model": {
            "module": "model_manager_example.py",
            "dir": "../models",
            "args": "--model mistral-7b-instruct --max-tokens 32 --device cpu",
            "expected_result": 0,
            "description": "Model manager test with local model",
            "dependencies": {
                "packages": ["ctransformers"],
                "files": ["../models/model_config.json"],
                "env_vars": ["LOCAL_MODELS_DIR"]
            }
        }
    },
    "memory": {
        "basic": {
            "module": "memory_example.py",
            "dir": "../memory",
            "args": "--demo basic",
            "expected_result": 0,
            "description": "Basic memory system test",
            "dependencies": {
                "packages": ["sqlite3"],
                "files": [],
                "env_vars": []
            }
        },
        "episodic": {
            "module": "memory_example.py",
            "dir": "../memory",
            "args": "--demo episodic",
            "expected_result": 0,
            "description": "Episodic memory system test",
            "dependencies": {
                "packages": ["sqlite3"],
                "files": [],
                "env_vars": []
            }
        }
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize test results storage
test_results = {
    "passed": [],
    "failed": [],
    "skipped": [],
    "total_duration": 0
}

# Test workflows for interdependent tests
TEST_WORKFLOWS = {
    "basic_validation": {
        "description": "Basic system validation workflow that checks core components",
        "steps": [
            {"test": "models:manager", "id": "model_check"},
            {"test": "mcp:core", "depends_on": "model_check"},
            {"test": "agents:echo", "depends_on": "model_check"}
        ]
    },
    "brave_search": {
        "description": "End-to-end workflow for Brave Search functionality",
        "steps": [
            {"test": "brave:api", "id": "api_test"},
            {"test": "brave:server", "depends_on": "api_test", "id": "server_test"},
            {"test": "brave:client", "depends_on": "server_test"},
            {"test": "brave:mcp_test", "depends_on": ["api_test", "server_test"]}
        ]
    },
    "full_system": {
        "description": "Comprehensive system validation testing all components",
        "steps": [
            {"test": "models:manager", "id": "models_ready"},
            {"test": "mcp:sqlite", "depends_on": "models_ready", "id": "mcp_ready"},
            {"test": "brave:api", "id": "brave_ready"},
            {"test": "agents:system", "depends_on": "mcp_ready"},
            {"test": "agents:code", "depends_on": "models_ready"},
            {"test": "memory:basic", "depends_on": "models_ready"},
            {"test": "agents:communication", "depends_on": ["models_ready", "mcp_ready"]}
        ]
    },
    "orchestration_workflow": {
        "name": "Workflow de Orquestación",
        "description": "Prueba de orquestación de múltiples agentes",
        "steps": [
            "models:manager",  # Verificar que el gestor de modelos funciona
            "agents:echo",     # Probar agente echo básico
            "agents:code",     # Probar agente de código
            "agents:system",   # Probar agente de sistema
            "agents:orchestrator"  # Probar el orquestador
        ]
    },
    # Nuevo workflow para MainAssistant con TTS
    "vio_basic_workflow": {
        "description": "Flujo de trabajo básico de V.I.O. (antes MainAssistant) con TTS",
        "steps": [
            {"test": "tts:basic", "id": "tts_ready"},
            {"test": "main_assistant:basic", "depends_on": "tts_ready", "id": "main_assistant_basic"},
            {"test": "tts:voice_list", "depends_on": "tts_ready"}
        ]
    },
    # Workflow completo para V.I.O.
    "vio_full_workflow": {
        "description": "Flujo de trabajo completo de V.I.O. con todos los componentes",
        "steps": [
            {"test": "models:manager", "id": "model_ready"},
            {"test": "tts:basic", "id": "tts_ready"},
            {"test": "agents:echo", "id": "echo_ready"},
            {"test": "agents:code", "depends_on": "model_ready", "id": "code_ready"},
            {"test": "agents:system", "id": "system_ready"},
            {"test": "agents:orchestrator", "depends_on": ["echo_ready", "code_ready", "system_ready"], "id": "orchestrator_ready"},
            {"test": "main_assistant:delegation", "depends_on": ["tts_ready", "orchestrator_ready"]}
        ]
    },
    # Workflow para probar el manejo de errores
    "error_handling_workflow": {
        "description": "Flujo de trabajo que prueba el manejo de errores y la robustez del sistema",
        "steps": [
            {"test": "tts:basic", "id": "tts_ready"},
            {"test": "agents:echo", "id": "echo_ready"},
            {"test": "error_handling:agent_unavailable", "depends_on": ["tts_ready", "echo_ready"], "id": "agent_unavailable_test"},
            {"test": "error_handling:invalid_request", "depends_on": ["tts_ready", "echo_ready"], "id": "invalid_request_test"},
            {"test": "main_assistant:basic", "depends_on": ["agent_unavailable_test", "invalid_request_test"], "id": "main_assistant_after_errors"}
        ]
    }
}

# Define parametrized test variants
TEST_VARIANTS = {
    "models:variable_tokens": {
        "base_test": "models:manager",
        "description": "Test model manager with various token limits",
        "vary_param": "--max-tokens",
        "values": ["16", "32", "64", "128"]
    },
    "sqlite:modes": {
        "base_test": "mcp:sqlite",
        "description": "Test SQLite MCP in different modes",
        "vary_param": "--mode",
        "values": ["direct", "http", "both"]
    }
}

class TestResult:
    """Class to store results of a test run"""
    def __init__(self, category: str, name: str, status: str, duration: float,
                 returncode: int, stdout: str, stderr: str, description: str = "", using_fallback=None):
        self.category = category
        self.name = name
        self.status = status  # "passed", "failed", "skipped"
        self.duration = duration
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.description = description
        self.timestamp = datetime.now().isoformat()
        self.using_fallback = using_fallback

def find_python_executable() -> str:
    """Find the Python executable to use for tests."""
    # Use sys.executable if available
    if sys.executable:
        return sys.executable
    
    # Try some common Python executable names
    for cmd in ["python", "python3", "py"]:
        try:
            result = subprocess.run([cmd, "--version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    
    # Default to "python" if nothing else found
    return "python"

def check_package_dependency(package_name: str) -> bool:
    """Check if a Python package is installed and can be imported."""
    try:
        # Handle special case for packages with submodules
        if "." in package_name:
            main_package = package_name.split(".")[0]
            importlib.import_module(main_package)
        else:
            importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def check_command_dependency(command: str) -> bool:
    """Check if a command is available in the system PATH."""
    return shutil.which(command) is not None

def check_file_dependency(file_path: str) -> bool:
    """Check if a required file exists."""
    # Handle both absolute and relative paths
    if os.path.isabs(file_path):
        return os.path.exists(file_path)
    else:
        # For relative paths, check relative to the script directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, file_path)
        return os.path.exists(full_path)

def check_env_var_dependency(var_name: str) -> bool:
    """Check if an environment variable is set."""
    return var_name in os.environ and os.environ[var_name]

def verify_dependencies(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verify all dependencies for a test.
    
    Returns:
        Tuple[bool, List[str]]: A tuple where the first element is a boolean indicating if all 
        dependencies are met, and the second element is a list of missing dependency descriptions.
    """
    # Default empty dependencies if not specified
    dependencies = config.get("dependencies", {
        "packages": [],
        "files": [],
        "env_vars": []
    })
    
    all_satisfied = True
    missing_deps = []
    
    # Check package dependencies
    for package in dependencies.get("packages", []):
        if not check_package_dependency(package):
            all_satisfied = False
            missing_deps.append(f"Python package: {package}")
    
    # Check file dependencies
    for file_path in dependencies.get("files", []):
        if not check_file_dependency(file_path):
            all_satisfied = False
            missing_deps.append(f"File: {file_path}")
    
    # Check environment variable dependencies
    for env_var in dependencies.get("env_vars", []):
        if not check_env_var_dependency(env_var):
            all_satisfied = False
            missing_deps.append(f"Environment variable: {env_var}")
    
    return all_satisfied, missing_deps

def discover_tests() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Dynamically discover available tests in the examples directory structure."""
    # This is a placeholder for future auto-discovery functionality
    # For now, we'll use the static TEST_CONFIG
    return TEST_CONFIG

def run_test(category: str, test_name: str, config: Dict[str, Any], verbose: bool = False, check_real_modules: bool = False) -> TestResult:
    """Run a single test and return a TestResult object."""
    module = config["module"]
    directory = config["dir"]
    args = config["args"]
    expected_result = config.get("expected_result", 0)
    description = config.get("description", "")
    
    # Check dependencies first
    deps_satisfied, missing_deps = verify_dependencies(config)
    if not deps_satisfied:
        deps_str = "\n    - ".join([""] + missing_deps)
        print(f"{Colors.WARNING}⚠ Test {category}:{test_name} skipped due to missing dependencies:{deps_str}{Colors.RESET}")
        return TestResult(
            category=category,
            name=test_name,
            status="skipped",
            duration=0,
            returncode=-1,
            stdout="",
            stderr=f"Missing dependencies: {', '.join(missing_deps)}",
            description=description
        )
    
    # Get the full path to the test module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, directory)
    test_path = os.path.join(test_dir, module)
    
    if not os.path.exists(test_path):
        logger.error(f"Test module not found: {test_path}")
        return TestResult(
            category=category,
            name=test_name,
            status="skipped",
            duration=0,
            returncode=-1,
            stdout="",
            stderr=f"Test module not found: {test_path}",
            description=description
        )
    
    # Command to run the test
    python_exe = find_python_executable()
    cmd = [python_exe, test_path]
    
    # Add check_real_modules flag if requested
    if check_real_modules:
        cmd.append("--check-real-modules")
    
    # Add arguments if provided, using shlex to preserve quoted strings
    if args:
        try:
            cmd.extend(shlex.split(args))
        except ValueError as e:
            logger.error(f"Error parsing arguments '{args}': {e}")
            return TestResult(
                category=category,
                name=test_name,
                status="failed",
                duration=0,
                returncode=-1,
                stdout="",
                stderr=f"Error parsing arguments: {e}",
                description=description
            )
    
    # Run the test
    print(f"{Colors.INFO}Running test: {category}:{test_name}{Colors.RESET}")
    if description:
        print(f"  Description: {description}")
    print(f"  Command: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=test_dir
        )
        stdout, stderr = process.communicate(timeout=120)  # Extended timeout to 120 seconds
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check if using real modules or fallback
        using_fallback = False
        if check_real_modules:
            # Buscar indicadores de uso de fallback en la salida
            if "USING_REAL_MODULES = False" in stdout or "Usando implementaciones simuladas" in stdout:
                using_fallback = True
                print(f"{Colors.FALLBACK}ℹ Test {category}:{test_name} using FALLBACK implementation{Colors.RESET}")
            elif "USING_REAL_MODULES = True" in stdout or "Módulos importados correctamente" in stdout:
                print(f"{Colors.INFO}ℹ Test {category}:{test_name} using REAL modules{Colors.RESET}")
        
        if process.returncode == expected_result:
            status = "passed"
            status_msg = f"{Colors.PASSED}✓ Test {category}:{test_name} completed successfully in {duration:.2f}s"
            if using_fallback:
                status_msg += f" {Colors.FALLBACK}(using fallback implementation){Colors.RESET}"
            else:
                status_msg += f"{Colors.RESET}"
            print(status_msg)
        else:
            status = "failed"
            print(f"{Colors.FAILED}✗ Test {category}:{test_name} failed with code {process.returncode} in {duration:.2f}s{Colors.RESET}")
            if verbose:
                print(f"\nSTDOUT:\n{stdout[:500]}..." if len(stdout) > 500 else f"\nSTDOUT:\n{stdout}")
                print(f"\nSTDERR:\n{stderr[:500]}..." if len(stderr) > 500 else f"\nSTDERR:\n{stderr}")
                
        return TestResult(
            category=category,
            name=test_name,
            status=status,
            duration=duration,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            description=description,
            using_fallback=using_fallback if check_real_modules else None
        )
            
    except subprocess.TimeoutExpired:
        process.kill()
        end_time = time.time()
        duration = end_time - start_time
        print(f"{Colors.FAILED}✗ Test {category}:{test_name} timed out after 120s{Colors.RESET}")
        
        return TestResult(
            category=category,
            name=test_name,
            status="failed",
            duration=duration,
            returncode=-1,
            stdout="",
            stderr="Timeout expired",
            description=description,
            using_fallback=None
        )
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"{Colors.FAILED}✗ Error running test {category}:{test_name}: {str(e)}{Colors.RESET}")
        
        return TestResult(
            category=category,
            name=test_name,
            status="failed", 
            duration=duration,
            returncode=-1,
            stdout="",
            stderr=str(e),
            description=description,
            using_fallback=None
        )

def run_category(category: str, verbose: bool = False, check_real_modules: bool = False) -> List[TestResult]:
    """Run all tests in a category and return results."""
    if category not in TEST_CONFIG:
        logger.error(f"Unknown test category: {category}")
        return []
    
    print(f"\n{Colors.HEADER}Running all tests in category: {category}{Colors.RESET}")
    tests = TEST_CONFIG[category]
    results = []
    
    for test_name, test_config in tests.items():
        result = run_test(category, test_name, test_config, verbose, check_real_modules)
        results.append(result)
        
        # Store for reporting
        if result.status == "passed":
            test_results["passed"].append(result)
        elif result.status == "failed":
            test_results["failed"].append(result)
        else:
            test_results["skipped"].append(result)
        
        test_results["total_duration"] += result.duration
    
    return results

def run_all_tests(verbose: bool = False, check_real_modules: bool = False) -> Dict[str, List[TestResult]]:
    """Run all tests in all categories and return results."""
    print(f"\n{Colors.HEADER}Running all tests{Colors.RESET}")
    results = {}
    
    for category in TEST_CONFIG:
        results[category] = run_category(category, verbose, check_real_modules)
    
    return results

def run_specified_test(test_id: str, verbose: bool = False, check_real_modules: bool = False) -> TestResult:
    """Run a single test specified by its ID in the format 'category:name'."""
    parts = test_id.split(":")
    if len(parts) != 2:
        logger.error(f"Invalid test ID format: {test_id}. Expected format: 'category:name'")
        return None
    
    category, test_name = parts
    
    if category not in TEST_CONFIG:
        logger.error(f"Unknown test category: {category}")
        return None
    
    if test_name not in TEST_CONFIG[category]:
        logger.error(f"Unknown test name: {test_name} in category {category}")
        return None
    
    print(f"\n{Colors.HEADER}Running specified test: {test_id}{Colors.RESET}")
    result = run_test(category, test_name, TEST_CONFIG[category][test_name], verbose, check_real_modules)
    
    # Store for reporting
    if result.status == "passed":
        test_results["passed"].append(result)
    elif result.status == "failed":
        test_results["failed"].append(result)
    else:
        test_results["skipped"].append(result)
    
    test_results["total_duration"] += result.duration
    
    return result

def run_workflow(workflow_id: str, verbose: bool = False, check_real_modules: bool = False) -> Dict[str, TestResult]:
    """Run a predefined workflow and return the results of each step."""
    if workflow_id not in TEST_WORKFLOWS:
        logger.error(f"Unknown workflow ID: {workflow_id}")
        return {}
    
    workflow = TEST_WORKFLOWS[workflow_id]
    workflow_steps = workflow["steps"]
    workflow_description = workflow.get("description", "")
    
    print(f"\n{Colors.HEADER}Running workflow: {workflow_id}{Colors.RESET}")
    print(f"  Description: {workflow_description}")
    print(f"  Steps: {len(workflow_steps)}")
    
    # Store results by ID for dependency resolution
    step_results = {}
    
    # Track overall workflow status
    workflow_status = {
        "passed": True,
        "total": len(workflow_steps),
        "completed": 0,
        "skipped": 0,
        "real_modules": 0,
        "fallback_modules": 0
    }
    
    # Run each step in order
    for step_idx, step in enumerate(workflow_steps):
        test_spec = step["test"]
        step_id = step.get("id", test_spec)
        dependencies = step.get("depends_on", [])
        
        # Convert single dependency to list for uniform handling
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        
        # Check if all dependencies have passed
        deps_passed = True
        missing_deps = []
        
        for dep_id in dependencies:
            if dep_id not in step_results:
                logger.error(f"Step {step_id} depends on unknown step ID: {dep_id}")
                deps_passed = False
                missing_deps.append(f"Unknown step: {dep_id}")
            elif step_results[dep_id].status != "passed":
                deps_passed = False
                missing_deps.append(f"Failed dependency: {dep_id}")
        
        # Skip this step if dependencies failed
        if not deps_passed:
            print(f"{Colors.WARNING}⚠ Step {step_idx+1}/{len(workflow_steps)}: {test_spec} (ID: {step_id}) skipped due to failed dependencies:{Colors.RESET}")
            for missing in missing_deps:
                print(f"    - {missing}")
            
            # Create a skipped result
            result = TestResult(
                category="workflow",
                name=step_id,
                status="skipped",
                duration=0,
                returncode=-1,
                stdout="",
                stderr=f"Skipped due to failed dependencies: {', '.join(missing_deps)}",
                description=f"Workflow step {step_idx+1}/{len(workflow_steps)}: {test_spec}",
                using_fallback=None
            )
            
            step_results[step_id] = result
            test_results["skipped"].append(result)
            workflow_status["skipped"] += 1
            continue
        
        # Run the test
        print(f"\n{Colors.INFO}Step {step_idx+1}/{len(workflow_steps)}: {test_spec} (ID: {step_id}){Colors.RESET}")
        if dependencies:
            print(f"  Dependencies: {', '.join(dependencies)}")
        
        # Parse and run the test
        parts = test_spec.split(":")
        if len(parts) != 2:
            logger.error(f"Invalid test specification: {test_spec}")
            result = TestResult(
                category="workflow",
                name=step_id,
                status="failed",
                duration=0,
                returncode=-1,
                stdout="",
                stderr=f"Invalid test specification: {test_spec}",
                description=f"Workflow step {step_idx+1}/{len(workflow_steps)}",
                using_fallback=None
            )
        else:
            category, test_name = parts
            
            # Check if this is a test variant
            variant_id = f"{category}:{test_name}"
            if variant_id in TEST_VARIANTS:
                # For variants, run all parameter combinations and succeed if any pass
                print(f"  Running parameterized test variant: {variant_id}")
                variants = resolve_variant(variant_id)
                
                if not variants:
                    result = TestResult(
                        category=category,
                        name=test_name,
                        status="failed",
                        duration=0,
                        returncode=-1,
                        stdout="",
                        stderr=f"Could not resolve test variant: {variant_id}",
                        description=f"Workflow step {step_idx+1}/{len(workflow_steps)}",
                        using_fallback=None
                    )
                else:
                    # Run all variants and collect results
                    variant_results = []
                    variant_duration = 0
                    for variant in variants:
                        v_category = variant["category"]
                        v_test_name = variant["test_name"]
                        v_config = variant["config"]
                        display_name = variant["display_name"]
                        
                        print(f"    Running variant: {display_name}")
                        v_result = run_test(v_category, v_test_name, v_config, verbose, check_real_modules)
                        variant_results.append(v_result)
                        variant_duration += v_result.duration
                    
                    # If any variant passed, the overall result is a pass
                    any_passed = any(r.status == "passed" for r in variant_results)
                    
                    if any_passed:
                        result = TestResult(
                            category=category,
                            name=step_id,
                            status="passed",
                            duration=variant_duration,
                            returncode=0,
                            stdout="Parameterized test: at least one variant passed",
                            stderr="",
                            description=f"Workflow step {step_idx+1}/{len(workflow_steps)}: {test_spec}",
                            using_fallback=any(r.using_fallback for r in variant_results if r.using_fallback is not None)
                        )
                    else:
                        # All variants failed
                        result = TestResult(
                            category=category,
                            name=step_id,
                            status="failed",
                            duration=variant_duration,
                            returncode=-1,
                            stdout="",
                            stderr="All parameterized variants failed",
                            description=f"Workflow step {step_idx+1}/{len(workflow_steps)}: {test_spec}",
                            using_fallback=any(r.using_fallback for r in variant_results if r.using_fallback is not None)
                        )
            else:
                # Regular (non-variant) test
                if category not in TEST_CONFIG or test_name not in TEST_CONFIG[category]:
                    logger.error(f"Unknown test: {test_spec}")
                    result = TestResult(
                        category=category,
                        name=test_name,
                        status="failed",
                        duration=0,
                        returncode=-1,
                        stdout="",
                        stderr=f"Unknown test: {test_spec}",
                        description=f"Workflow step {step_idx+1}/{len(workflow_steps)}",
                        using_fallback=None
                    )
                else:
                    result = run_test(category, test_name, TEST_CONFIG[category][test_name], verbose, check_real_modules)
        
        # Store the result and update workflow status
        step_results[step_id] = result
        workflow_status["completed"] += 1
        
        # Track implementation type (real or fallback)
        if hasattr(result, 'using_fallback') and result.using_fallback is not None:
            if result.using_fallback:
                workflow_status["fallback_modules"] += 1
            else:
                workflow_status["real_modules"] += 1
        
        if result.status == "passed":
            test_results["passed"].append(result)
        elif result.status == "failed":
            test_results["failed"].append(result)
            workflow_status["passed"] = False
        else:  # skipped
            test_results["skipped"].append(result)
        
        test_results["total_duration"] += result.duration
    
    # Print workflow summary
    print(f"\n{Colors.HEADER}Workflow {workflow_id} completed{Colors.RESET}")
    print(f"  Total steps: {workflow_status['total']}")
    print(f"  Completed: {workflow_status['completed']}")
    print(f"  Skipped: {workflow_status['skipped']}")
    
    if check_real_modules:
        real_count = workflow_status["real_modules"]
        fallback_count = workflow_status["fallback_modules"]
        total_with_info = real_count + fallback_count
        
        if total_with_info > 0:
            print(f"  Module implementations:")
            print(f"    - {Colors.INFO}Real modules: {real_count}/{total_with_info} ({real_count/total_with_info*100:.1f}%){Colors.RESET}")
            print(f"    - {Colors.FALLBACK}Fallback implementations: {fallback_count}/{total_with_info} ({fallback_count/total_with_info*100:.1f}%){Colors.RESET}")
    
    print(f"  Overall status: {Colors.PASSED if workflow_status['passed'] else Colors.FAILED}" +
          f"{'PASSED' if workflow_status['passed'] else 'FAILED'}{Colors.RESET}")
    
    return step_results

def run_variant(variant_id: str, verbose: bool = False) -> List[TestResult]:
    """
    Run a parametrized test variant with multiple parameter values.
    
    Args:
        variant_id: The ID of the variant to run
        verbose: Whether to show verbose output
        
    Returns:
        A list of test results, one for each parameter value
    """
    print(f"\n{Colors.HEADER}Running parametrized test variant: {variant_id}{Colors.RESET}")
    variants = resolve_variant(variant_id)
    
    if not variants:
        print(f"{Colors.FAILED}Failed to resolve variant: {variant_id}{Colors.RESET}")
        return []
    
    results = []
    
    for variant in variants:
        category = variant["category"]
        test_name = variant["test_name"]
        config = variant["config"]
        display_name = variant["display_name"]
        
        print(f"\n{Colors.INFO}Running variant: {display_name}{Colors.RESET}")
        result = run_test(category, test_name, config, verbose)
        results.append(result)
        
        # Store for reporting
        if result.status == "passed":
            test_results["passed"].append(result)
        elif result.status == "failed":
            test_results["failed"].append(result)
        else:
            test_results["skipped"].append(result)
        
        test_results["total_duration"] += result.duration
    
    return results

def main():
    """Main function to handle command-line arguments and run tests."""
    parser = argparse.ArgumentParser(description="Test runner for MCP system")
    
    # Test selection options
    test_group = parser.add_argument_group("Test Selection")
    test_group.add_argument("--run", metavar="CATEGORY:TEST", help="Run a specific test")
    test_group.add_argument("--run-category", metavar="CATEGORY", help="Run all tests in a category")
    test_group.add_argument("--run-all", action="store_true", help="Run all tests")
    test_group.add_argument("--run-workflow", metavar="WORKFLOW_ID", help="Run a predefined workflow")
    test_group.add_argument("--run-variant", metavar="VARIANT_ID", help="Run a test variant with multiple parameters")
    
    # Test discovery options
    discover_group = parser.add_argument_group("Test Discovery")
    discover_group.add_argument("--list", action="store_true", help="List available tests")
    discover_group.add_argument("--list-workflows", action="store_true", help="List available workflows")
    discover_group.add_argument("--list-variants", action="store_true", help="List available test variants")
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    output_group.add_argument("--report", metavar="REPORT_FILE", help="Generate a JSON report")
    output_group.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                            default="INFO", help="Set the logging level")
    
    # Implementation verification
    impl_group = parser.add_argument_group("Implementation Options")
    impl_group.add_argument("--check-real-modules", action="store_true", 
                         help="Check if tests are using real modules or fallback implementations")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    global logger
    logger = logging.getLogger("test_runner")
    
    # Show program header
    print(f"{Colors.HEADER}MCP System Test Runner{Colors.RESET}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # List available tests if requested
    if args.list:
        list_tests()
        return
    
    # List available workflows if requested
    if args.list_workflows:
        list_workflows()
        return
    
    # List available test variants if requested
    if args.list_variants:
        list_variants()
        return
    
    # Execute requested test(s)
    if args.run:
        # Run a specific test
        run_specified_test(args.run, args.verbose, args.check_real_modules)
    elif args.run_category:
        # Run all tests in a category
        run_category(args.run_category, args.verbose, args.check_real_modules)
    elif args.run_all:
        # Run all tests
        run_all_tests(args.verbose, args.check_real_modules)
    elif args.run_workflow:
        # Run a predefined workflow
        run_workflow(args.run_workflow, args.verbose, args.check_real_modules)
    elif args.run_variant:
        # Run a test variant
        run_variant(args.run_variant, args.verbose)
    else:
        logger.warning("No test run command specified. Use --run, --run-category, --run-all, --run-workflow, or --run-variant")
        parser.print_help()
        return
    
    # Print summary
    print_summary()
    
    # Generate report if requested
    if args.report:
        generate_report(args.report)
    
    # Return appropriate exit code
    if test_results["failed"]:
        sys.exit(1)
    else:
        sys.exit(0)

def print_summary():
    """Generate and print a test report."""
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    skipped = len(test_results["skipped"])
    total = passed + failed + skipped
    
    if total == 0:
        print("\nNo tests were run.")
        return
    
    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"TEST SUMMARY")
    print(f"{'=' * 60}{Colors.RESET}")
    print(f"Total tests: {total}")
    print(f"{Colors.PASSED}Passed: {passed} ({passed/total*100:.1f}%){Colors.RESET}" if total > 0 else f"{Colors.PASSED}Passed: 0 (0.0%){Colors.RESET}")
    
    # Calculate percentages safely to avoid division by zero
    failed_pct = failed/total*100 if total > 0 else 0
    skipped_pct = skipped/total*100 if total > 0 else 0
    
    print(f"{Colors.FAILED}Failed: {failed} ({failed_pct:.1f}%){Colors.RESET}")
    print(f"{Colors.WARNING}Skipped: {skipped} ({skipped_pct:.1f}%){Colors.RESET}")
    print(f"Total duration: {test_results['total_duration']:.2f}s")
    
    # Count real vs fallback implementations
    real_modules = 0
    fallback_modules = 0
    unknown_impl = 0
    
    for result in test_results["passed"] + test_results["failed"]:
        if hasattr(result, 'using_fallback') and result.using_fallback is not None:
            if result.using_fallback:
                fallback_modules += 1
            else:
                real_modules += 1
        else:
            unknown_impl += 1
    
    total_with_impl = real_modules + fallback_modules
    if total_with_impl > 0:
        print(f"\n{Colors.HEADER}IMPLEMENTATION DETAILS:{Colors.RESET}")
        print(f"{Colors.INFO}Using real modules: {real_modules}/{total_with_impl} ({real_modules/total_with_impl*100:.1f}%){Colors.RESET}")
        print(f"{Colors.FALLBACK}Using fallback implementations: {fallback_modules}/{total_with_impl} ({fallback_modules/total_with_impl*100:.1f}%){Colors.RESET}")
        if unknown_impl > 0:
            print(f"{Colors.WARNING}Unknown implementation: {unknown_impl}{Colors.RESET}")
    
    if failed > 0:
        print(f"\n{Colors.HEADER}FAILED TESTS:{Colors.RESET}")
        for result in test_results["failed"]:
            impl_note = ""
            if hasattr(result, 'using_fallback') and result.using_fallback is not None:
                impl_note = f" {Colors.FALLBACK}(fallback){Colors.RESET}" if result.using_fallback else f" {Colors.INFO}(real){Colors.RESET}"
            
            print(f"{Colors.FAILED}• {result.category}:{result.name}{impl_note} - {result.description}{Colors.RESET}")
            print(f"  Error: {result.stderr[:100]}..." if len(result.stderr) > 100 else f"  Error: {result.stderr}")
    
    if skipped > 0:
        print(f"\n{Colors.HEADER}SKIPPED TESTS:{Colors.RESET}")
        for result in test_results["skipped"]:
            print(f"{Colors.WARNING}• {result.category}:{result.name} - {result.description}{Colors.RESET}")
    
    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"END OF REPORT")
    print(f"{'=' * 60}{Colors.RESET}")

def generate_report(filename: str = "test_report.json"):
    """Save the test report to a JSON file."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["skipped"]),
            "passed": len(test_results["passed"]),
            "failed": len(test_results["failed"]),
            "skipped": len(test_results["skipped"]),
            "total_duration": test_results["total_duration"],
            "implementations": {
                "real_modules": sum(1 for r in test_results["passed"] + test_results["failed"] 
                                 if hasattr(r, 'using_fallback') and r.using_fallback is False),
                "fallback_implementations": sum(1 for r in test_results["passed"] + test_results["failed"] 
                                            if hasattr(r, 'using_fallback') and r.using_fallback is True)
            }
        },
        "tests": {
            "passed": [
                {
                    "category": r.category,
                    "name": r.name,
                    "duration": r.duration,
                    "description": r.description,
                    "timestamp": r.timestamp,
                    "using_fallback": r.using_fallback if hasattr(r, 'using_fallback') else None
                } for r in test_results["passed"]
            ],
            "failed": [
                {
                    "category": r.category,
                    "name": r.name,
                    "duration": r.duration,
                    "description": r.description,
                    "returncode": r.returncode,
                    "stderr": r.stderr,
                    "timestamp": r.timestamp,
                    "using_fallback": r.using_fallback if hasattr(r, 'using_fallback') else None
                } for r in test_results["failed"]
            ],
            "skipped": [
                {
                    "category": r.category,
                    "name": r.name,
                    "description": r.description,
                    "reason": r.stderr,
                    "timestamp": r.timestamp
                } for r in test_results["skipped"]
            ]
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest report saved to {filename}")

def list_tests():
    """List all available tests organized by category."""
    print(f"{Colors.HEADER}Available tests:{Colors.RESET}")
    for category, tests in TEST_CONFIG.items():
        print(f"\n{Colors.INFO}{category}:{Colors.RESET}")
        for test_name, test_config in tests.items():
            description = test_config.get("description", "")
            print(f"  - {test_name}: {test_config['module']} {Colors.WARNING}({description}){Colors.RESET}")

def list_workflows():
    """List all available predefined workflows."""
    print(f"{Colors.HEADER}Available workflows:{Colors.RESET}")
    for workflow_id, workflow in TEST_WORKFLOWS.items():
        description = workflow.get("description", "")
        steps = len(workflow.get("steps", []))
        print(f"\n{Colors.INFO}{workflow_id}:{Colors.RESET}")
        print(f"  Description: {description}")
        print(f"  Steps: {steps}")
        
        # Show detailed steps
        for i, step in enumerate(workflow.get("steps", [])):
            test_spec = step["test"]
            step_id = step.get("id", test_spec)
            dependencies = step.get("depends_on", [])
            
            if isinstance(dependencies, str):
                dependencies = [dependencies]
            
            deps_str = f" (depends on: {', '.join(dependencies)})" if dependencies else ""
            print(f"    {i+1}. {test_spec}{Colors.WARNING}{deps_str}{Colors.RESET}")

def list_variants():
    """List all available parameterized test variants."""
    print(f"{Colors.HEADER}Available parameterized test variants:{Colors.RESET}")
    for variant_id, variant_config in TEST_VARIANTS.items():
        description = variant_config.get("description", "")
        base_test = variant_config.get("base_test", "")
        vary_param = variant_config.get("vary_param", "")
        values = variant_config.get("values", [])
        
        print(f"\n{Colors.INFO}{variant_id}:{Colors.RESET}")
        print(f"  Description: {description}")
        print(f"  Base test: {base_test}")
        print(f"  Parameter to vary: {vary_param}")
        print(f"  Values: {', '.join(map(str, values))}")

def resolve_variant(variant_id: str) -> List[Dict[str, Any]]:
    """
    Resolve a parameterized test variant into multiple test configurations.
    
    Args:
        variant_id: The identifier of the variant to resolve
        
    Returns:
        A list of test configurations with different parameter values
    """
    if variant_id not in TEST_VARIANTS:
        logger.error(f"Unknown test variant: {variant_id}")
        return []
    
    variant_config = TEST_VARIANTS[variant_id]
    base_test_id = variant_config["base_test"]
    vary_param = variant_config["vary_param"]
    values = variant_config["values"]
    
    # Get the base test configuration
    parts = base_test_id.split(":")
    if len(parts) != 2:
        logger.error(f"Invalid base test specification: {base_test_id}")
        return []
    
    category, test_name = parts
    if category not in TEST_CONFIG or test_name not in TEST_CONFIG[category]:
        logger.error(f"Base test {base_test_id} not found in test configuration")
        return []
    
    base_config = TEST_CONFIG[category][test_name].copy()
    result_configs = []
    
    # Create a variant for each value
    for value in values:
        variant_config = base_config.copy()
        
        # Update the args with the new parameter value
        current_args = variant_config.get("args", "")
        
        # If parameter already exists in args, replace its value
        if f"{vary_param} " in current_args:
            # Extract current parameter value and replace it
            import re
            pattern = f"({vary_param}\\s+[^\\s]+)"
            replacement = f"{vary_param} {value}"
            variant_config["args"] = re.sub(pattern, replacement, current_args)
        else:
            # Append parameter if it doesn't exist
            separator = " " if current_args else ""
            variant_config["args"] = f"{current_args}{separator}{vary_param} {value}"
        
        # Add the variant to the result
        result_configs.append({
            "category": category,
            "test_name": f"{test_name}_{value}",  # Create a unique test name
            "config": variant_config,
            "display_name": f"{category}:{test_name} (with {vary_param}={value})"
        })
    
    return result_configs

def run_variant(variant_id: str, verbose: bool = False) -> List[TestResult]:
    """
    Run a parameterized test variant with multiple parameter values.
    
    Args:
        variant_id: The ID of the variant to run
        verbose: Whether to show verbose output
        
    Returns:
        A list of test results, one for each parameter value
    """
    print(f"\n{Colors.HEADER}Running parameterized test variant: {variant_id}{Colors.RESET}")
    
    # Resolve the variant
    variants = resolve_variant(variant_id)
    if not variants:
        logger.error(f"Could not resolve variant: {variant_id}")
        return []
    
    results = []
    for variant in variants:
        category = variant["category"]
        test_name = variant["test_name"]
        config = variant["config"]
        display_name = variant["display_name"]
        
        print(f"  Running variant: {display_name}")
        result = run_test(category, test_name, config, verbose)
        results.append(result)
        
        # Store for reporting
        if result.status == "passed":
            test_results["passed"].append(result)
        elif result.status == "failed":
            test_results["failed"].append(result)
        else:
            test_results["skipped"].append(result)
        
        test_results["total_duration"] += result.duration
    
    # Print summary for the variant
    passed = sum(1 for r in results if r.status == "passed")
    total = len(results)
    pass_rate = passed / total * 100 if total > 0 else 0
    
    print(f"\n{Colors.INFO}Variant {variant_id} results: {passed}/{total} passed ({pass_rate:.1f}%){Colors.RESET}")
    return results

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test run interrupted by user{Colors.RESET}")
        sys.exit(130)  # 130 is the standard exit code for SIGINT
    except Exception as e:
        print(f"\n{Colors.FAILED}Unexpected error: {str(e)}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 