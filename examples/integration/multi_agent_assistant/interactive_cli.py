#!/usr/bin/env python
"""
Interfaz de línea de comandos interactiva para el sistema Multi-Agente.

Este script permite interactuar directamente con el sistema de agentes a través
de una interfaz de consola simple.
"""

import os
import sys
import asyncio
import logging
import json
from pathlib import Path
import argparse
import signal
import readline  # Para historial de comandos y edición de línea

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("interactive_cli")

# Importar la función de configuración del script de demo
from examples.integration.multi_agent_assistant.multi_agent_demo import setup_memory_system, setup_agents, add_example_memories

# Variables globales para estado
main_assistant = None
memory_client = None
should_exit = False

def signal_handler(sig, frame):
    """Maneja la señal de interrupción (Ctrl+C)."""
    global should_exit
    print("\nSaliendo del programa...")
    should_exit = True

async def process_command(command, agents):
    """
    Procesa un comando del usuario.
    
    Args:
        command: El comando introducido
        agents: Diccionario de agentes disponibles
        
    Returns:
        Resultado del procesamiento
    """
    # Comandos especiales
    if command.lower() == "exit" or command.lower() == "salir" or command.lower() == "quit":
        global should_exit
        should_exit = True
        return "Saliendo del sistema..."
    
    elif command.lower() == "help" or command.lower() == "ayuda":
        return """
Comandos disponibles:
--------------------
help, ayuda     - Mostrar esta ayuda
exit, salir     - Salir del programa
agents, agentes - Listar agentes disponibles
memory, memoria - Añadir una memoria
search, buscar  - Buscar en memoria

Para interactuar con el asistente, simplemente escribe tu consulta.
"""
    
    elif command.lower() in ["agents", "agentes"]:
        result = "Agentes disponibles:\n"
        for agent_id, agent in agents.items():
            capabilities = ", ".join(agent.get_capabilities())
            result += f"- {agent_id}: {agent.name} [{capabilities}]\n"
        return result
    
    elif command.lower().startswith("memory ") or command.lower().startswith("memoria "):
        # Comando para añadir memoria
        content = command[7:] if command.lower().startswith("memory ") else command[8:]
        if not content.strip():
            return "Error: Debes proporcionar contenido para la memoria"
        
        try:
            memory_data = {
                "content": content.strip(),
                "memory_type": "general",
                "importance": 0.7,
                "metadata": {"source": "cli_user", "category": "user_input"}
            }
            
            memory_id = await agents["memory"].create_memory(memory_data)
            return f"Memoria creada con ID: {memory_id}"
        except Exception as e:
            return f"Error creando memoria: {str(e)}"
    
    elif command.lower().startswith("search ") or command.lower().startswith("buscar "):
        # Comando para buscar en memoria
        query = command[7:] if command.lower().startswith("search ") else command[7:]
        if not query.strip():
            return "Error: Debes proporcionar un término de búsqueda"
        
        try:
            # Búsqueda usando el MemoryAgent
            context = {"action": "recall", "semantic": True, "limit": 5}
            response = await agents["memory"].process(query.strip(), context)
            
            if response.status == "success":
                return f"Resultados de búsqueda:\n{response.content}"
            else:
                return f"Error en búsqueda: {response.metadata.get('error', 'desconocido')}"
        except Exception as e:
            return f"Error buscando en memoria: {str(e)}"
    
    # Comando normal: consulta al asistente principal
    try:
        # Procesar usando el MainAssistant
        response = await agents["main_assistant"].process(command)
        
        # Construir respuesta detallada
        result = f"{response.content}\n"
        
        # Añadir información del agente usado si está disponible
        if "agent_used" in response.metadata:
            agent_used = response.metadata["agent_used"]
            result += f"\n[Procesado por: {agent_used}]"
        
        # Añadir información de memoria usada si está disponible
        if "memory_used" in response.metadata and response.metadata["memory_used"]:
            result += f"\n[Memoria utilizada: {response.metadata.get('memories_found', '?')} recuerdos]"
            
        return result
    except Exception as e:
        return f"Error procesando consulta: {str(e)}"

async def cli_loop(agents):
    """
    Bucle principal de la interfaz de línea de comandos.
    
    Args:
        agents: Diccionario de agentes disponibles
    """
    global should_exit
    
    print("\n===== Sistema Multi-Agente Interactivo =====")
    print("Escribe 'help' para ver los comandos disponibles o 'exit' para salir.")
    print("----------------------------------------------")
    
    # Configurar historial de comandos
    histfile = os.path.join(os.path.expanduser("~"), ".multi_agent_history")
    try:
        readline.read_history_file(histfile)
        readline.set_history_length(1000)
    except FileNotFoundError:
        pass
    
    # Bucle principal
    while not should_exit:
        try:
            command = input("\n> ")
            if command.strip():
                print("Procesando...")
                result = await process_command(command, agents)
                print(f"\n{result}")
                
                # Guardar comando en historial
                try:
                    readline.write_history_file(histfile)
                except:
                    pass
        except KeyboardInterrupt:
            print("\nOperación cancelada.")
        except Exception as e:
            print(f"\nError: {str(e)}")
    
    print("Sesión finalizada.")

async def main():
    """Función principal que configura y ejecuta la CLI interactiva."""
    global memory_client, main_assistant
    
    # Configurar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="CLI Interactiva para Sistema Multi-Agente")
    parser.add_argument("--no-examples", action="store_true", help="No cargar memorias de ejemplo")
    parser.add_argument("--debug", action="store_true", help="Mostrar logs de debug")
    args = parser.parse_args()
    
    # Ajustar nivel de logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 1. Configurar directorio para datos
        data_dir = os.path.join(project_root, "examples/data/interactive_cli")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
        
        # Crear subdirectorios por agente
        agent_data_dirs = {
            "memory": os.path.join(data_dir, "memory_agent"),
            "main": os.path.join(data_dir, "main_assistant"),
            "code": os.path.join(data_dir, "code_agent"),
            "system": os.path.join(data_dir, "system_agent"),
            "echo": os.path.join(data_dir, "echo_agent"),
            "orchestrator": os.path.join(data_dir, "orchestrator_agent")
        }
        
        # Crear todos los subdirectorios
        for dir_path in agent_data_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Creado directorio: {dir_path}")
        
        # 2. Configurar sistema de memoria
        memory_server, memory_client = await setup_memory_system(agent_data_dirs["memory"])
        
        # 3. Configurar agentes
        agent_config = {
            "data_dir": data_dir,
            "data_dirs": agent_data_dirs
        }
        agents = await setup_agents(memory_client, agent_config)
        main_assistant = agents["main_assistant"]
        
        # 4. Añadir memorias de ejemplo (opcional)
        if not args.no_examples:
            await add_example_memories(agents["memory"])
            
        # 5. Iniciar bucle de CLI
        await cli_loop(agents)
        
        # 6. Limpiar y cerrar
        logger.info("Finalizando sesión...")
        memory_client.disconnect()
        from agents.agent_communication import shutdown_communication_system
        await shutdown_communication_system()
        
        return 0
    
    except Exception as e:
        logger.error(f"Error en la aplicación: {str(e)}")
        # Intentar limpiar recursos en caso de error
        try:
            if memory_client:
                memory_client.disconnect()
            from agents.agent_communication import shutdown_communication_system
            await shutdown_communication_system()
        except:
            pass
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
        sys.exit(130) 