"""
Main entry point for the AI Agent System.

This script initializes and runs the AI Agent System with the MCP.
"""

import os
import asyncio
import argparse
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración básica de logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("logs", "system.log"), mode="a")
    ]
)
logger = logging.getLogger("main")

# Asegurar que el directorio de logs existe
os.makedirs("logs", exist_ok=True)

async def interactive_mode():
    """Modo interactivo para interactuar con el sistema desde la línea de comandos."""
    from mcp.core import MCP
    from agents.echo_agent import EchoAgent
    
    # Inicializar MCP
    mcp = MCP()
    logger.info("Iniciando modo interactivo. Escribe 'salir' para terminar.")
    
    # Por ahora, usamos directamente el EchoAgent para pruebas
    agent = EchoAgent(
        agent_id="echo",
        config={
            "name": "Echo Agent",
            "description": "Simple agent that echoes back input"
        }
    )
    
    while True:
        try:
            query = input("\nTú > ")
            if query.lower() in ["salir", "exit", "quit"]:
                break
                
            # Procesar con el agente
            response = await agent.process(query)
            print(f"\nAgente > {response.content}")
            
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
        except Exception as e:
            logger.error(f"Error procesando consulta: {e}")
            print(f"\nError: {e}")

def start_api_server():
    """Inicia el servidor API."""
    import uvicorn
    import yaml
    
    # Cargar configuración
    with open(os.path.join("config", "config.yaml"), 'r') as f:
        config = yaml.safe_load(f)
        
    host = config["api"]["host"]
    port = config["api"]["port"]
    
    logger.info(f"Iniciando servidor API en {host}:{port}")
    uvicorn.run("api.main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema de Agentes IA")
    parser.add_argument(
        "--mode", 
        choices=["interactive", "api"], 
        default="interactive",
        help="Modo de ejecución (interactive o api)"
    )
    args = parser.parse_args()
    
    try:
        if args.mode == "interactive":
            asyncio.run(interactive_mode())
        else:
            start_api_server()
    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}")
        raise 