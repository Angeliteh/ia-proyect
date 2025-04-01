#!/usr/bin/env python
"""
Script para probar agentes individuales del sistema V.I.O.

Este script permite probar un agente específico a la vez, con una configuración
mínima necesaria para su funcionamiento. Útil para verificar la implementación
de cada agente sin depender de la integración completa.

Uso:
    python test_agents.py echo      # Prueba EchoAgent
    python test_agents.py memory    # Prueba MemoryAgent
    python test_agents.py vio       # Prueba V.I.O. (MainAssistant)
    python test_agents.py system    # Prueba SystemAgent
    python test_agents.py code      # Prueba CodeAgent
    python test_agents.py sender    # Prueba TestSenderAgent
    python test_agents.py planner   # Prueba PlannerAgent
    python test_agents.py orchestrator  # Prueba OrchestratorAgent
    python test_agents.py all       # Prueba todos los agentes en secuencia
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("agent_tester")

# Importaciones comunes del sistema
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient
from agents.agent_communication import setup_communication_system, shutdown_communication_system

# Clases y constantes
AGENT_TYPES = {
    "echo": "EchoAgent",
    "memory": "MemoryAgent",
    "vio": "MainAssistant (V.I.O.)",
    "system": "SystemAgent",
    "code": "CodeAgent",
    "sender": "TestSenderAgent",
    "planner": "PlannerAgent",
    "orchestrator": "OrchestratorAgent"
}

AGENT_QUERIES = {
    "echo": [
        "Hola, soy un test para el EchoAgent", 
        "¿Puedes repetir este mensaje?"
    ],
    "memory": [
        "Recuerda que los tomates son rojos",
        "¿Qué sabes sobre los tomates?"
    ],
    "vio": [
        "Hola, ¿cómo estás?",
        "¿Cuál es tu función principal?"
    ],
    "system": [
        "¿Qué fecha es hoy?",
        "¿Cuánto espacio libre hay en el disco?"
    ],
    "code": [
        "Escribe una función en Python que calcule el factorial de un número",
        "Explica qué es un algoritmo de ordenamiento"
    ],
    "sender": [
        "Envía un mensaje al EchoAgent",
        "¿Cómo funciona el sistema de comunicación entre agentes?"
    ],
    "planner": [
        "Planifica los pasos para crear un sitio web simple",
        "¿Cómo planificarías un proyecto de análisis de datos?"
    ],
    "orchestrator": [
        "Coordina una tarea de búsqueda y resumen",
        "¿Cómo gestionas múltiples agentes simultáneamente?"
    ]
}

class AgentTester:
    """Clase para probar agentes individuales."""
    
    def __init__(self):
        """Inicializar el tester."""
        self.logger = logger
        self.agent = None
        self.agent_type = None
        self.memory_server = None
        self.memory_client = None
        self.data_dir = os.path.join(project_root, "test_data")
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def setup_memory(self):
        """Configurar servidor y cliente de memoria."""
        self.logger.info("Configurando sistema de memoria...")
        
        memory_dir = os.path.join(self.data_dir, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        self.memory_server = MemoryServer(
            name="test_memory_server",
            description="Servidor de memoria para pruebas de agentes",
            data_dir=memory_dir
        )
        
        self.memory_client = SimpleDirectClient(self.memory_server)
        self.memory_client.connect()
        
        from mcp.core import MCPMessage, MCPAction, MCPResource
        
        # Verificar que el servidor está activo
        info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.SYSTEM,
            resource_path="/info"
        )
        
        info_response = await self.memory_client.send_message_async(info_message)
        if info_response.success:
            self.logger.info("Servidor de memoria iniciado correctamente")
            return True
        else:
            self.logger.error("Error al iniciar servidor de memoria")
            return False
    
    async def cleanup(self):
        """Limpiar recursos."""
        self.logger.info("Limpiando recursos...")
        
        if self.memory_client:
            self.memory_client.disconnect()
        
        await shutdown_communication_system()
        self.logger.info("Recursos liberados")
    
    async def setup_agent(self, agent_type: str):
        """Configurar un agente específico."""
        self.agent_type = agent_type
        self.logger.info(f"Configurando agente: {AGENT_TYPES.get(agent_type, agent_type)}")
        
        # Inicializar sistema de comunicación entre agentes
        await setup_communication_system()
        
        # Crear directorio de datos para el agente
        agent_dir = os.path.join(self.data_dir, agent_type)
        os.makedirs(agent_dir, exist_ok=True)
        
        # Configuración de memoria común
        memory_config = {
            "data_dir": agent_dir,
            "mcp_client": self.memory_client
        }
        
        # Importar y configurar el agente específico
        try:
            if agent_type == "echo":
                from agents.echo_agent import EchoAgent
                
                config = {
                    "name": "TestEcho",
                    "description": "Agente de eco para pruebas",
                    "memory_config": memory_config
                }
                
                self.agent = EchoAgent(
                    agent_id="echo",
                    config=config
                )
                
            elif agent_type == "memory":
                from agents.specialized.memory_agent import MemoryAgent
                from models.core.model_manager import ModelManager
                
                # Configuración de modelos
                model_manager = ModelManager()
                model_config = {
                    "model_manager": model_manager,
                    "model": "gemini-pro"  # Ajustar según modelo disponible
                }
                
                config = {
                    "name": "TestMemory",
                    "description": "Agente de memoria para pruebas",
                    "model_config": model_config,
                    "memory_config": memory_config
                }
                
                self.agent = MemoryAgent(
                    agent_id="memory",
                    config=config
                )
                
            elif agent_type == "vio":
                from agents.main_assistant.main_assistant import MainAssistant
                
                config = {
                    "name": "V.I.O.",
                    "description": "Virtual Intelligence Operator - Para pruebas",
                    "memory_config": memory_config
                }
                
                self.agent = MainAssistant(
                    agent_id="vio",
                    config=config
                )
                
            elif agent_type == "system":
                from agents.system_agent import SystemAgent
                
                config = {
                    "name": "TestSystem",
                    "description": "Agente de sistema para pruebas",
                    "working_dir": os.getcwd(),
                    "memory_config": memory_config
                }
                
                self.agent = SystemAgent(
                    agent_id="system",
                    config=config
                )
                
            elif agent_type == "code":
                from agents.code_agent import CodeAgent
                from models.core.model_manager import ModelManager
                
                model_manager = ModelManager()
                
                config = {
                    "name": "TestCode",
                    "description": "Agente de código para pruebas",
                    "model_manager": model_manager,
                    "memory_config": memory_config
                }
                
                self.agent = CodeAgent(
                    agent_id="code",
                    config=config
                )
                
            elif agent_type == "sender":
                from agents.test_sender import TestSenderAgent
                
                config = {
                    "name": "TestSender",
                    "description": "Agente de prueba de comunicación",
                    "test_receiver": "echo"  # Por defecto envía al EchoAgent
                }
                
                self.agent = TestSenderAgent(
                    agent_id="sender",
                    config=config
                )
                
            elif agent_type == "planner":
                from agents.planner_agent import PlannerAgent
                
                config = {
                    "name": "TestPlanner",
                    "description": "Agente de planificación para pruebas",
                    "memory_config": memory_config
                }
                
                self.agent = PlannerAgent(
                    agent_id="planner", 
                    config=config
                )
                
            elif agent_type == "orchestrator":
                from agents.orchestrator_agent import OrchestratorAgent
                
                config = {
                    "name": "TestOrchestrator",
                    "description": "Agente orquestador para pruebas",
                    "memory_config": memory_config,
                    "max_concurrent_tasks": 2
                }
                
                self.agent = OrchestratorAgent(
                    agent_id="orchestrator",
                    config=config
                )
                
            else:
                self.logger.error(f"Tipo de agente desconocido: {agent_type}")
                return False
            
            # Registrar agente con el comunicador
            from agents.agent_communication import communicator
            communicator.register_agent(self.agent)
            
            self.logger.info(f"Agente {AGENT_TYPES.get(agent_type, agent_type)} configurado correctamente")
            return True
            
        except ImportError as e:
            self.logger.error(f"Error al importar agente: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error al configurar agente: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    async def test_agent(self):
        """Probar el agente con consultas predefinidas."""
        if not self.agent or not self.agent_type:
            self.logger.error("No hay agente configurado para probar")
            return False
        
        self.logger.info(f"=== PROBANDO AGENTE: {AGENT_TYPES.get(self.agent_type, self.agent_type)} ===")
        
        # Obtener consultas de prueba
        test_queries = AGENT_QUERIES.get(self.agent_type, ["Hola, esta es una prueba"])
        
        for i, query in enumerate(test_queries):
            self.logger.info(f"\n--- Consulta {i+1}: {query} ---")
            try:
                # Procesar consulta
                response = await self.agent.process(query)
                
                # Mostrar respuesta
                self.logger.info(f"Respuesta: {response.content[:200]}...")
                self.logger.info(f"Estado: {response.status}")
                
                # Mostrar metadatos importantes
                if response.metadata:
                    self.logger.info("Metadatos:")
                    for key, value in response.metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            self.logger.info(f"- {key}: {value}")
                
                # Esperar entre consultas
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error procesando consulta: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        self.logger.info(f"=== PRUEBA DE {AGENT_TYPES.get(self.agent_type, self.agent_type)} COMPLETADA ===\n")
        return True
    
    async def run_test(self, agent_type: str):
        """Ejecutar una prueba completa para un agente."""
        try:
            # Configurar memoria
            if not await self.setup_memory():
                self.logger.error("Error al configurar memoria, abortando prueba")
                return False
            
            # Configurar agente
            if not await self.setup_agent(agent_type):
                self.logger.error(f"Error al configurar agente {agent_type}, abortando prueba")
                await self.cleanup()
                return False
            
            # Probar agente
            await self.test_agent()
            
            # Limpiar recursos
            await self.cleanup()
            return True
            
        except Exception as e:
            self.logger.error(f"Error durante la prueba: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            await self.cleanup()
            return False

async def main():
    """Función principal."""
    # Parsear argumentos
    parser = argparse.ArgumentParser(description="Probar agentes individuales del sistema V.I.O.")
    parser.add_argument("agent", choices=list(AGENT_TYPES.keys()) + ["all"], 
                        help="Agente a probar (o 'all' para probar todos)")
    args = parser.parse_args()
    
    tester = AgentTester()
    
    if args.agent == "all":
        logger.info("Probando todos los agentes secuencialmente")
        for agent_type in AGENT_TYPES.keys():
            logger.info(f"\n{'='*50}")
            logger.info(f"INICIANDO PRUEBA DE: {AGENT_TYPES.get(agent_type, agent_type)}")
            logger.info(f"{'='*50}\n")
            
            success = await tester.run_test(agent_type)
            
            if success:
                logger.info(f"✅ Prueba de {AGENT_TYPES.get(agent_type, agent_type)} EXITOSA")
            else:
                logger.error(f"❌ Prueba de {AGENT_TYPES.get(agent_type, agent_type)} FALLIDA")
    else:
        logger.info(f"Probando agente: {AGENT_TYPES.get(args.agent, args.agent)}")
        success = await tester.run_test(args.agent)
        
        if success:
            logger.info(f"✅ Prueba EXITOSA")
        else:
            logger.error(f"❌ Prueba FALLIDA")

if __name__ == "__main__":
    asyncio.run(main()) 