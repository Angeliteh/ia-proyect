#!/usr/bin/env python
"""
Echo Agent Example

Este ejemplo demuestra un agente simple que repite los mensajes que recibe.
Es útil para probar y verificar la infraestructura de agentes.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("echo_agent_example")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Intentar importar los módulos reales
try:
    # Primero vamos a ver si tenemos la estructura esperada del proyecto
    # Creamos un puente para que 'agents.base.agent' sea accessible desde 'agents.base'
    import agents
    if hasattr(agents, 'base') and hasattr(agents, 'echo_agent'):
        # Podemos acceder a través de la estructura real
        from agents.base import BaseAgent as Agent
        from agents.echo_agent import EchoAgent
        USING_REAL_MODULES = True
        logger.info("Módulos de agentes importados correctamente")
    else:
        raise ImportError("Estructura de módulos no coincide con lo esperado")
        
except ImportError as e:
    logger.warning(f"Error al importar módulos reales de agentes: {e}")
    logger.info("Usando implementaciones mínimas para demostración")
    USING_REAL_MODULES = False
    
    # Implementaciones mínimas para demostración
    class Agent:
        """Clase base para agentes."""
        
        def __init__(self, name, description=None):
            self.name = name
            self.description = description or f"Agent: {name}"
            self.created_at = datetime.now()
            logger.info(f"Agente {name} creado")
        
        def process_message(self, message, **kwargs):
            """Procesar un mensaje (método abstracto)."""
            raise NotImplementedError("Los agentes deben implementar process_message")
        
        def get_info(self):
            """Obtener información sobre el agente."""
            return {
                "name": self.name,
                "description": self.description,
                "type": self.__class__.__name__,
                "created_at": self.created_at.isoformat()
            }
    
    class EchoAgent(Agent):
        """Agente simple que repite los mensajes que recibe."""
        
        def __init__(self, name="EchoAgent", description=None):
            super().__init__(name, description or "Agent that echoes back the messages it receives")
            self.message_count = 0
        
        def process_message(self, message, **kwargs):
            """Procesar un mensaje, devolviéndolo como eco."""
            self.message_count += 1
            response = f"Echo: [{self.message_count}] {message}"
            logger.info(f"{self.name} processando mensaje: '{message}' -> '{response}'")
            return response

def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(description="Ejemplo de EchoAgent")
    parser.add_argument("--message", default="¡Hola, mundo!", help="Mensaje a enviar al agente")
    parser.add_argument("--count", type=int, default=3, help="Número de veces a repetir el mensaje")
    parser.add_argument("--check-real-modules", action="store_true", 
                        help="Verificar si se están usando módulos reales o simulados")
    
    args = parser.parse_args()
    
    # Verificar si estamos usando módulos reales o simulados
    if args.check_real_modules:
        if USING_REAL_MODULES:
            print("USING_REAL_MODULES = True")
            sys.exit(0)
        else:
            print("USING_REAL_MODULES = False")
            # No consideramos un error que se esté usando una implementación de fallback
            # solo lo reportamos para fines informativos
            sys.exit(0)
    
    # Crear un agente de eco
    echo_agent = EchoAgent(name="EchoDemo")
    
    # Mostrar información del agente
    info = echo_agent.get_info()
    logger.info(f"Información del agente: {info}")
    
    # Procesar el mensaje varias veces
    message = args.message
    count = args.count
    
    logger.info(f"Enviando '{message}' al agente {count} veces...")
    
    for i in range(count):
        response = echo_agent.process_message(message)
        logger.info(f"Respuesta {i+1}: {response}")
    
    logger.info("Ejemplo completado")

if __name__ == "__main__":
    main() 