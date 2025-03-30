#!/usr/bin/env python
"""
Planner Agent Example

Este ejemplo demuestra el uso del agente de planificación para descomponer tareas complejas
en subtareas y crear planes de ejecución estructurados.
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
logger = logging.getLogger("planner_agent_example")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

# Intentar importar los módulos reales
try:
    # Primero vamos a ver si tenemos la estructura esperada del proyecto
    import agents
    from agents.planner_agent import PlannerAgent
    from agents.base import AgentResponse
    from agents.planning.task import Task, TaskStatus
    from agents.planning.execution_plan import ExecutionPlan, PlanStatus
    from agents.planning.algorithms import PlanningAlgorithms

    USING_REAL_MODULES = True
    logger.info("Módulos de agentes importados correctamente")
        
except ImportError as e:
    logger.warning(f"Error al importar módulos reales de agentes: {e}")
    logger.info("Usando implementaciones mínimas para demostración")
    USING_REAL_MODULES = False
    
    # Implementaciones mínimas para demostración (no se usan pero son necesarias para la compatibilidad)
    from enum import Enum
    
    class TaskStatus(Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
    
    class PlanStatus(Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
    
    class Task:
        def __init__(self, description, required_capabilities=None):
            self.description = description
            self.required_capabilities = required_capabilities or []
            self.status = TaskStatus.PENDING
    
    class ExecutionPlan:
        def __init__(self, original_request):
            self.original_request = original_request
            self.tasks = {}
            self.execution_order = []
            self.status = PlanStatus.PENDING
    
    class PlanningAlgorithms:
        @staticmethod
        def create_execution_plan(task_description, context=None):
            plan = ExecutionPlan(task_description)
            return plan
        
    class AgentResponse:
        def __init__(self, content, status="success", metadata=None):
            self.content = content
            self.status = status
            self.metadata = metadata or {}
    
    class PlannerAgent:
        def __init__(self, agent_id, config=None):
            self.agent_id = agent_id
            self.config = config or {}
            self.plans = {}
        
        async def process(self, query, context=None):
            plan = PlanningAlgorithms.create_execution_plan(query, context)
            self.plans["sample_plan_id"] = plan
            return AgentResponse(
                content=f"Plan creado para: {query}",
                metadata={"plan_id": "sample_plan_id"}
            )

async def run_planner_example(task_description, additional_context=None):
    """Ejecutar un ejemplo del PlannerAgent."""
    # Inicializar el agente planificador
    planner_config = {
        "name": "PlannerDemo",
        "description": "Agente de planificación para demostración",
        "max_history_size": 5
    }
    
    planner = PlannerAgent("planner_demo", planner_config)
    
    logger.info(f"Iniciando planificación para: '{task_description}'")
    
    # Preparar contexto
    context = additional_context or {}
    context["example_run"] = True
    context["timestamp"] = datetime.now().isoformat()
    
    # Procesar la solicitud
    response = await planner.process(task_description, context)
    
    # Mostrar el resultado
    logger.info(f"Respuesta del planificador:")
    logger.info(response.content)
    
    # Si tenemos un plan real, mostrar más detalles
    if USING_REAL_MODULES:
        plan_id = response.metadata['plan_id']
        plan = planner.plans[plan_id]
        
        # Mostrar tareas en orden de ejecución
        logger.info("\nTareas en orden de ejecución:")
        for i, task_id in enumerate(plan.execution_order):
            task = plan.tasks[task_id]
            capabilities = ", ".join(task.required_capabilities)
            logger.info(f"  {i+1}. {task.description} (Capacidades: {capabilities})")
        
        # Verificar si hay dependencias
        if plan.dependencies:
            logger.info("\nDependencias entre tareas:")
            for dep in plan.dependencies:
                source_task = plan.tasks[dep.source_task_id]
                target_task = plan.tasks[dep.target_task_id]
                logger.info(f"  '{source_task.description}' -> '{target_task.description}' ({dep.dependency_type.value})")
    
    return response

def main():
    """Función principal del ejemplo."""
    parser = argparse.ArgumentParser(description="Ejemplo de PlannerAgent")
    parser.add_argument("--task", default="Implementar un algoritmo de búsqueda binaria en Python", 
                        help="Descripción de la tarea a planificar")
    parser.add_argument("--context", default=None, 
                        help="Contexto adicional en formato JSON")
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
    asyncio.run(run_planner_example(args.task, context))
    
    logger.info("Ejemplo completado")

if __name__ == "__main__":
    main() 