#!/usr/bin/env python
"""
Orchestrator-Planner Integration Example

Este ejemplo demuestra la integración entre el OrchestratorAgent y el PlannerAgent,
donde el orquestador delega la planificación de tareas al planificador y ejecuta el plan resultante.
"""

import os
import sys
import argparse
import logging
import asyncio
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger("orchestrator_planner_integration")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Intentar importar los módulos reales
try:
    import agents
    from agents import (
        OrchestratorAgent, 
        PlannerAgent,
        EchoAgent,
        CodeAgent,
        SystemAgent,
        setup_communication_system,
        shutdown_communication_system
    )
    from agents.base import AgentResponse
    
    USING_REAL_MODULES = True
    logger.info("Módulos de agentes importados correctamente")
        
except ImportError as e:
    logger.warning(f"Error al importar módulos reales de agentes: {e}")
    logger.info("Usando implementaciones mínimas para demostración")
    USING_REAL_MODULES = False
    
    # Si no podemos importar los módulos reales, crear versiones mínimas para demostración
    setup_communication_system = lambda: None
    shutdown_communication_system = lambda: None
    
    class AgentResponse:
        def __init__(self, content, status="success", metadata=None):
            self.content = content
            self.status = status
            self.metadata = metadata or {}
    
    class MockAgent:
        def __init__(self, agent_id, config=None):
            self.agent_id = agent_id
            self.config = config or {}
            self.logger = logging.getLogger(f"agent.{agent_id}")
        
        async def process(self, query, context=None):
            return AgentResponse(
                content=f"Respuesta simulada del agente {self.agent_id}: {query}",
                status="success",
                metadata={}
            )
        
        def get_capabilities(self):
            return []
    
    class OrchestratorAgent(MockAgent):
        def __init__(self, agent_id, config=None):
            super().__init__(agent_id, config)
            self.available_agents = {}
        
        async def register_available_agent(self, agent_id, capabilities):
            self.available_agents[agent_id] = {
                "capabilities": capabilities,
                "status": "idle"
            }
            logger.info(f"Agente {agent_id} registrado con capacidades: {capabilities}")
    
    class PlannerAgent(MockAgent):
        def __init__(self, agent_id, config=None):
            super().__init__(agent_id, config)
            self.plans = {}
            
        async def process(self, query, context=None):
            return AgentResponse(
                content=f"Plan creado para: {query}",
                metadata={
                    "plan_id": "sample_plan_id",
                    "plan": {
                        "execution_order": ["task1", "task2"],
                        "tasks": {
                            "task1": {
                                "description": "Tarea de análisis",
                                "required_capabilities": ["analysis"]
                            },
                            "task2": {
                                "description": "Tarea de implementación",
                                "required_capabilities": ["code_generation"]
                            }
                        }
                    }
                }
            )
    
    class EchoAgent(MockAgent):
        def get_capabilities(self):
            return ["echo", "test"]
    
    class CodeAgent(MockAgent):
        def get_capabilities(self):
            return ["code_generation", "analysis", "testing"]
    
    class SystemAgent(MockAgent):
        def get_capabilities(self):
            return ["system_operations", "file_management"]

# Función para simular la integración entre OrchestratorAgent y PlannerAgent
async def run_integration_example(task_description, additional_context=None):
    """Ejecutar un ejemplo de integración entre OrchestratorAgent y PlannerAgent."""
    try:
        # Inicializar sistema de comunicación entre agentes
        setup_communication_system()
        
        # Crear agentes especializados
        echo_agent = EchoAgent("echo_agent", {"name": "Echo"})
        code_agent = CodeAgent("code_agent", {"name": "Code"})
        system_agent = SystemAgent("system_agent", {"name": "System"})
        
        # Crear el agente planificador
        planner_agent = PlannerAgent("planner_agent", {
            "name": "Planner",
            "description": "Agente especializado en planificación de tareas",
            "max_history_size": 5
        })
        
        # Crear el agente orquestador
        orchestrator_agent = OrchestratorAgent("orchestrator_agent", {
            "name": "Orchestrator",
            "description": "Agente orquestador que coordina la ejecución de tareas",
            "max_concurrent_tasks": 3
        })
        
        # Registrar agentes con el orquestador
        await orchestrator_agent.register_available_agent(
            "echo_agent", echo_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "code_agent", code_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "system_agent", system_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "planner_agent", planner_agent.get_capabilities()
        )
        
        # Preparar el contexto
        context = additional_context or {}
        context["example_run"] = True
        context["timestamp"] = datetime.now().isoformat()
        
        # En un sistema real, el OrchestratorAgent detectaría que es una tarea compleja
        # y delegaría la planificación al PlannerAgent, pero en este ejemplo lo haremos explícitamente
        
        logger.info(f"Delegando planificación al PlannerAgent: '{task_description}'")
        
        # El orquestador solicita un plan al planificador
        plan_response = await planner_agent.process(task_description, context)
        
        logger.info(f"Plan recibido del planificador:")
        logger.info(plan_response.content)
        
        if USING_REAL_MODULES:
            # Obtener el plan generado
            plan_id = plan_response.metadata['plan_id']
            plan = plan_response.metadata['plan']
            
            logger.info("\nOrquestador ejecutando el plan...")
            
            # Simular la ejecución del plan por el orquestador
            # En un sistema real, el orquestador ejecutaría cada tarea del plan
            # asignando los agentes apropiados según las capacidades requeridas
            
            for i, task_id in enumerate(plan['execution_order']):
                task = plan['tasks'][task_id]
                logger.info(f"Ejecutando tarea {i+1}: {task['description']}")
                
                # Determinar qué agente asignar basado en las capacidades requeridas
                agent_id = None
                for aid, info in orchestrator_agent.available_agents.items():
                    caps = set(info['capabilities'])
                    req_caps = set(task['required_capabilities'])
                    if req_caps.intersection(caps):
                        agent_id = aid
                        break
                
                if agent_id:
                    agent = {
                        "echo_agent": echo_agent,
                        "code_agent": code_agent,
                        "system_agent": system_agent,
                        "planner_agent": planner_agent
                    }.get(agent_id)
                    
                    if agent:
                        logger.info(f"  Asignando agente: {agent_id}")
                        # Simular ejecución de tarea por el agente asignado
                        task_result = await agent.process(task['description'])
                        logger.info(f"  Resultado: {task_result.content[:50]}...")
                else:
                    logger.warning(f"  No se encontró un agente adecuado para esta tarea")
            
            logger.info("\nPlan ejecutado completamente")
        
        # En un sistema real, el orquestador devolvería el resultado consolidado
        return AgentResponse(
            content=f"Tarea completada: {task_description}",
            status="success"
        )
    
    finally:
        # Limpiar recursos
        shutdown_communication_system()

def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(
        description="Ejemplo de integración entre OrchestratorAgent y PlannerAgent"
    )
    parser.add_argument(
        "--task", 
        default="Desarrollar una aplicación de gestión de tareas con persistencia en archivos", 
        help="Descripción de la tarea a planificar y ejecutar"
    )
    parser.add_argument(
        "--context", 
        default=None, 
        help="Contexto adicional en formato JSON"
    )
    parser.add_argument(
        "--check-real-modules", 
        action="store_true", 
        help="Verificar si se están usando módulos reales o simulados"
    )
    
    args = parser.parse_args()
    
    # Verificar si estamos usando módulos reales o simulados
    if args.check_real_modules:
        if USING_REAL_MODULES:
            print("USING_REAL_MODULES = True")
            sys.exit(0)
        else:
            print("USING_REAL_MODULES = False")
            sys.exit(0)
    
    # Parsear contexto JSON si se proporciona
    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear contexto JSON: {e}")
            sys.exit(1)
    
    # Ejecutar el ejemplo de forma asíncrona
    asyncio.run(run_integration_example(args.task, context))
    
    logger.info("Ejemplo completado")

if __name__ == "__main__":
    main() 