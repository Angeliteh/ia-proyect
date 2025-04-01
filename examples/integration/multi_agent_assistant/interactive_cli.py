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

# Importar sistema TTS para poder desactivarlo globalmente
from tts.core import agent_tts_interface

# Variables globales para estado
main_assistant = None
memory_client = None
should_exit = False
tts_enabled = True  # Por defecto habilitado

# Configuración de ejemplos de consultas realistas para pruebas
REALISTIC_TEST_QUERIES = [
    # Consultas de conocimiento general
    "¿Cuáles son los principios SOLID en programación?",
    "Explícame qué es el patrón de diseño Observer y dame un ejemplo práctico",
    "¿Qué diferencias hay entre SQLite, MySQL y PostgreSQL?",
    
    # Consultas de programación específicas
    "Necesito una función en Python que conecte a una API REST y maneje errores",
    "¿Cómo implemento autenticación JWT en una aplicación web?",
    "Escribe un script que busque archivos duplicados en un directorio",
    
    # Consultas de debugging
    "Mi código Python da error 'TypeError: cannot unpack non-iterable NoneType object', ¿qué significa?",
    "¿Por qué mi consulta SQL con JOIN devuelve filas duplicadas?",
    "Mi aplicación JavaScript tiene una fuga de memoria, ¿cómo puedo detectarla?",
    
    # Consultas de aprendizaje
    "Recomiéndame recursos para aprender desarrollo web fullstack",
    "¿Cuál es la mejor manera de aprender machine learning desde cero?",
    "Explícame cómo funciona un transformer en procesamiento de lenguaje natural",
    
    # Consultas técnicas complejas
    "Explícame paso a paso cómo implementar un sistema de caché distribuido",
    "¿Cómo funciona internamente la recolección de basura en Python?",
    "¿Qué consideraciones de seguridad debería tener para una API pública?",
    
    # Consultas con requisitos específicos
    "Necesito un sistema para clasificar documentos PDF por contenido",
    "Quiero crear un chatbot que responda preguntas sobre mi base de datos de productos",
    "Necesito optimizar el rendimiento de consultas a mi base de datos de 5 millones de registros",
    
    # Consultas contextuales encadenadas
    "Estoy desarrollando una aplicación de gestión de inventario",
    "¿Qué base de datos me recomiendas para este tipo de aplicación?",
    "¿Cómo debería estructurar los modelos para gestionar productos, proveedores y movimientos?",
    
    # Consultas de integración
    "¿Cómo puedo integrar un sistema de pagos como Stripe en mi aplicación?",
    "Necesito sincronizar datos entre mi CRM y mi aplicación web",
    "¿Cómo implemento un sistema de notificaciones en tiempo real?"
]

def signal_handler(sig, frame):
    """Maneja la señal de interrupción (Ctrl+C)."""
    global should_exit
    print("\nSaliendo del programa...")
    should_exit = True

def print_divider():
    """Imprime un divisor para mejorar la legibilidad"""
    terminal_width = os.get_terminal_size().columns
    print("-" * terminal_width)

def print_header(text):
    """Imprime un encabezado formateado"""
    terminal_width = os.get_terminal_size().columns
    padding = (terminal_width - len(text) - 4) // 2
    padding = max(0, padding)
    print()
    print("=" * terminal_width)
    print(" " * padding + f"[ {text} ]")
    print("=" * terminal_width)

def toggle_tts():
    """Toggle Text-to-Speech functionality on or off"""
    from tts.core.agent_tts_interface import disable_tts, enable_tts, is_tts_enabled
    
    if is_tts_enabled():
        disable_tts()
        print("TTS desactivado. Las respuestas serán solo texto.")
    else:
        enable_tts()
        print("TTS activado. Las respuestas incluirán audio cuando sea posible.")
    
    return True  # Continuar ejecutando

async def process_command(command, agents):
    """
    Procesa un comando del usuario.
    
    Args:
        command: El comando introducido
        agents: Diccionario de agentes disponibles
        
    Returns:
        Resultado del procesamiento
    """
    global tts_enabled
    
    # Comandos especiales
    if command.lower() == "exit" or command.lower() == "salir" or command.lower() == "quit":
        global should_exit
        should_exit = True
        return "Saliendo del sistema..."
    
    elif command.lower() == "help" or command.lower() == "ayuda":
        return """
Comandos disponibles:
--------------------
help, ayuda           - Mostrar esta ayuda
exit, salir           - Salir del programa
agents, agentes       - Listar agentes disponibles
memory, memoria       - Añadir una memoria (ej: memory Este es un recuerdo importante)
profile, perfil       - Añadir perfil de usuario estructurado (ej: profile Ángel es programador...)
search, buscar        - Buscar en memoria (ej: search Python)
tts [on|off]          - Activar/desactivar Text-to-Speech o alternar sin argumento
status                - Mostrar estado del sistema

Para interactuar con el asistente, simplemente escribe tu consulta.
"""
    
    elif command.lower() in ["agents", "agentes"]:
        result = "Agentes disponibles:\n"
        for agent_id, agent in agents.items():
            capabilities = ", ".join(agent.get_capabilities())
            result += f"- {agent_id}: {agent.name} [{capabilities}]\n"
        return result
    
    elif command.lower() == "status":
        # Mostrar estado del sistema
        status = f"""
Estado del Sistema:
------------------
TTS: {'ACTIVADO' if tts_enabled else 'DESACTIVADO'}
Agentes activos: {len(agents)}
"""
        return status
    
    elif command.lower().startswith("tts"):
        # Comando para controlar TTS
        parts = command.lower().split()
        if len(parts) > 1:
            if parts[1] == "on":
                tts_enabled = True
            elif parts[1] == "off":
                tts_enabled = False
        else:
            # Sin argumento, alternar estado
            tts_enabled = not tts_enabled
        
        # Desactivar TTS globalmente
        try:
            if hasattr(agent_tts_interface, 'disable_tts'):
                if not tts_enabled:
                    agent_tts_interface.disable_tts()
                else:
                    agent_tts_interface.enable_tts()
        except Exception as e:
            logger.warning(f"Error configurando TTS global: {str(e)}")
            
        # Aplicar cambio al asistente principal
        if "main_assistant" in agents and hasattr(agents["main_assistant"], "use_tts"):
            agents["main_assistant"].use_tts = tts_enabled
            
        # Informar sobre cambios a todos los agentes que soporten TTS
        for agent_id, agent in agents.items():
            if hasattr(agent, "use_tts"):
                try:
                    agent.use_tts = tts_enabled
                except:
                    pass
            
        status = "ACTIVADO" if tts_enabled else "DESACTIVADO"
        return f"Text-to-Speech {status}"
    
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
    
    elif command.lower().startswith("profile ") or command.lower().startswith("perfil "):
        # Comando para añadir perfil de usuario estructurado
        content = command[8:] if command.lower().startswith("profile ") else command[7:]
        if not content.strip():
            return "Error: Debes proporcionar contenido para el perfil"
        
        try:
            # Procesar el perfil usando el método especializado del MemoryAgent
            # que organiza automáticamente la información en secciones semánticas
            print("\nEstructurando y procesando el perfil de usuario...")
            
            # Metadatos para el perfil
            metadata = {
                "source": "cli_user", 
                "category": "user_profile",
                "context": "personal_information",
                "importance": "high",
                "user_provided": True
            }
            
            # Usar el método especializado si está disponible
            if hasattr(agents["memory"], "process_profile_data"):
                memory_ids = await agents["memory"].process_profile_data(content.strip(), metadata)
                
                # Verificar éxito
                if "error" in memory_ids:
                    return f"Error procesando perfil: {memory_ids['error']}\nID parcial: {memory_ids.get('main_profile', 'ninguno')}"
                
                # Mostrar información sobre las secciones creadas
                sections_info = "\n".join([f"- {section}: {id[:8]}..." for section, id in memory_ids.get("sections", {}).items() if id])
                
                return f"""Perfil de usuario procesado y estructurado con éxito.
ID principal: {memory_ids.get('main_profile', 'error')}
Secciones creadas:
{sections_info}

La información se ha organizado semánticamente y vectorizado para búsquedas avanzadas.
Ahora V.I.O. podrá responder consultas específicas sobre el perfil."""
            
            # Fallback al método anterior si el especializado no está disponible
            else:
                # Añadir un perfil estructurado en memoria con más relevancia
                profile_data = {
                    "content": content.strip(),
                    "memory_type": "user_profile",
                    "importance": 0.9,  # Alta importancia para darle prioridad
                    "metadata": metadata
                }
                
                # Crear memoria principal del perfil
                profile_id = await agents["memory"].create_memory(profile_data)
                
                # También crear una versión resumida con alta relevancia para consultas rápidas
                summary = f"Perfil de usuario: {content.strip()[:100]}..."
                summary_data = {
                    "content": summary,
                    "memory_type": "user_profile_summary",
                    "importance": 0.95,
                    "metadata": {
                        **metadata,
                        "parent_id": profile_id,
                        "context": "personal_information_summary"
                    }
                }
                
                summary_id = await agents["memory"].create_memory(summary_data)
                
                return f"Perfil de usuario añadido con éxito. ID: {profile_id}, Resumen ID: {summary_id}\nLa información se ordenará y vectorizará automáticamente para búsquedas semánticas."
        except Exception as e:
            return f"Error creando perfil: {str(e)}"
    
    # Comando normal: consulta al asistente principal
    try:
        # Asegurar que el TTS esté configurado correctamente
        if "main_assistant" in agents and hasattr(agents["main_assistant"], "use_tts"):
            agents["main_assistant"].use_tts = tts_enabled
            
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
    global should_exit, tts_enabled
    
    print_header("Sistema Multi-Agente Interactivo V.I.O.")
    print(f"TTS está {'ACTIVADO' if tts_enabled else 'DESACTIVADO'} inicialmente.")
    print("Escribe 'help' para ver los comandos disponibles o 'exit' para salir.")
    print_divider()
    
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
                print("\nProcesando...", end="", flush=True)
                result = await process_command(command, agents)
                print("\r" + " " * 12 + "\r")  # Limpiar "Procesando..."
                print_divider()
                print(f"\n{result}")
                print_divider()
                
                # Guardar comando en historial
                try:
                    readline.write_history_file(histfile)
                except:
                    pass
        except KeyboardInterrupt:
            print("\nOperación cancelada.")
        except Exception as e:
            print(f"\nError: {str(e)}")
    
    print("\nSesión finalizada.")

async def main():
    """Función principal que configura y ejecuta la CLI interactiva."""
    global memory_client, main_assistant, tts_enabled
    
    # Configurar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="CLI Interactiva para Sistema Multi-Agente")
    parser.add_argument("--no-examples", action="store_true", help="No cargar memorias de ejemplo")
    parser.add_argument("--debug", action="store_true", help="Mostrar logs de debug")
    parser.add_argument("--no-tts", action="store_true", help="Iniciar con TTS desactivado")
    parser.add_argument("--data-dir", type=str, default="./data", help="Directorio de datos para memoria")
    args = parser.parse_args()
    
    # Ajustar nivel de logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Configurar TTS inicial ANTES de cualquier inicialización
    if args.no_tts:
        tts_enabled = False
        
        # Desactivar TTS globalmente (Importación directa para asegurar que se ejecuta)
        from tts.core.agent_tts_interface import disable_tts
        disable_tts()
        logger.info("TTS desactivado globalmente mediante configuración explícita")
    
    try:
        # 1. Configurar directorio para datos
        data_dir = args.data_dir
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
        
        # 3. Configurar agentes con opciones de TTS explícitas
        agent_config = {
            "data_dir": data_dir,
            "data_dirs": agent_data_dirs,
            "use_tts": tts_enabled,  # Pasar estado inicial de TTS a la configuración
            "tts_enabled": tts_enabled,  # Duplicado para asegurar compatibilidad
            "tts_active": tts_enabled  # Otra posible clave
        }
        
        # Para debugging
        logger.info(f"Configurando agentes con TTS: {tts_enabled}")
        
        agents = await setup_agents(memory_client, agent_config)
        main_assistant = agents["main_assistant"]
        
        # Asegurarse de que TTS esté configurado correctamente en TODOS los agentes
        for agent_id, agent in agents.items():
            if hasattr(agent, "use_tts"):
                agent.use_tts = tts_enabled
                logger.info(f"Configurando TTS para {agent_id}: {tts_enabled}")
        
        # Verificar y establecer TTS global una segunda vez (cinturón y tirantes)
        if not tts_enabled:
            # Verificación de seguridad para TTS
            from tts.core.agent_tts_interface import disable_tts, is_tts_enabled
            if is_tts_enabled():
                disable_tts()
                logger.warning("¡Desactivando TTS nuevamente porque seguía activo!")
        
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
        import traceback
        logger.error(traceback.format_exc())
        
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