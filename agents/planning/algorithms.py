"""
Planning algorithms module.

This module provides algorithms for task decomposition, agent selection,
and other planning-related operations.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging

from .task import Task, TaskDependency, DependencyType
from .execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class PlanningAlgorithms:
    """
    Collection of algorithms for planning tasks.
    """
    
    @staticmethod
    def decompose_task(task_description: str, context: Optional[Dict] = None) -> List[Task]:
        """
        Decompose a complex task into simpler subtasks.
        
        This is a basic implementation of task decomposition that uses
        simple pattern matching to identify potential subtasks.
        
        Args:
            task_description: Description of the complex task
            context: Optional context information
            
        Returns:
            List of subtasks
        """
        # Esta es una implementación básica. En un escenario real,
        # podrías utilizar un LLM o algoritmos más sofisticados.
        
        subtasks = []
        
        # Detectar tareas relacionadas con programación
        if any(kw in task_description.lower() for kw in ["code", "program", "develop", "implement", 
                                                         "código", "programar", "desarrollar", "implementar"]):
            # Tarea de programación - desglosar en análisis, implementación, pruebas
            subtasks.append(Task(
                description="Analizar requerimientos y planificar implementación",
                required_capabilities=["analysis", "planning"],
                estimated_complexity=0.7
            ))
            
            subtasks.append(Task(
                description=f"Implementar solución para: {task_description}",
                required_capabilities=["code_generation", "problem_solving"],
                estimated_complexity=1.2
            ))
            
            subtasks.append(Task(
                description=f"Probar y verificar implementación para: {task_description}",
                required_capabilities=["testing", "verification"],
                estimated_complexity=0.8
            ))
        
        # Detectar tareas relacionadas con investigación
        elif any(kw in task_description.lower() for kw in ["research", "find", "search", "locate",
                                                          "investigar", "buscar", "encontrar", "localizar"]):
            # Tarea de investigación - desglosar en búsqueda y análisis
            subtasks.append(Task(
                description=f"Buscar información sobre: {task_description}",
                required_capabilities=["search", "information_retrieval"],
                estimated_complexity=0.9
            ))
            
            subtasks.append(Task(
                description=f"Analizar y resumir hallazgos para: {task_description}",
                required_capabilities=["analysis", "summarization"],
                estimated_complexity=0.8
            ))
        
        # Detectar tareas relacionadas con operaciones del sistema
        elif any(kw in task_description.lower() for kw in ["system", "file", "directory", "os", "process",
                                                         "sistema", "archivo", "directorio", "proceso"]):
            # Tarea de operación del sistema
            subtasks.append(Task(
                description=f"Ejecutar operaciones del sistema para: {task_description}",
                required_capabilities=["system_operations", "file_management"],
                estimated_complexity=0.7
            ))
        
        # Caso predeterminado - tarea única
        if not subtasks:
            subtasks.append(Task(
                description=task_description,
                required_capabilities=["general_processing"],
                estimated_complexity=1.0
            ))
        
        # Agregar contexto a todas las tareas
        for task in subtasks:
            if context:
                task.context.update(context)
        
        return subtasks
    
    @staticmethod
    def create_dependencies(tasks: List[Task]) -> List[TaskDependency]:
        """
        Crear dependencias entre tareas.
        
        En el caso más simple, esto crea una secuencia lineal de tareas
        donde cada tarea depende de la anterior.
        
        Args:
            tasks: Lista de tareas para crear dependencias
            
        Returns:
            Lista de dependencias de tareas
        """
        dependencies = []
        
        # Crear dependencias lineales simples
        for i in range(1, len(tasks)):
            dep = TaskDependency(
                source_task_id=tasks[i-1].task_id,
                target_task_id=tasks[i].task_id,
                dependency_type=DependencyType.FINISH_TO_START
            )
            dependencies.append(dep)
        
        return dependencies
    
    @staticmethod
    def select_agent_for_task(
        task: Task, 
        available_agents: Dict[str, Dict]
    ) -> Optional[str]:
        """
        Seleccionar el mejor agente para una tarea dada.
        
        Este algoritmo considera:
        1. Capacidades requeridas de la tarea
        2. Capacidades ofrecidas por cada agente
        3. Estado actual y carga de cada agente
        
        Args:
            task: La tarea a asignar
            available_agents: Diccionario de agentes disponibles con capacidades
            
        Returns:
            ID del agente seleccionado, o None si no se encuentra un agente adecuado
        """
        best_agent_id = None
        best_match_score = -1
        
        for agent_id, agent_info in available_agents.items():
            # Omitir agentes que no están inactivos
            if agent_info.get("status") != "idle":
                continue
            
            # Calcular puntuación de coincidencia de capacidades
            agent_capabilities = set(agent_info.get("capabilities", []))
            required_capabilities = set(task.required_capabilities)
            
            if not required_capabilities:
                # Si no se requieren capacidades específicas, cualquier agente puede hacerlo
                match_score = 1
            else:
                # Calcular coincidencia como proporción de capacidades requeridas que tiene el agente
                if not agent_capabilities:
                    match_score = 0
                else:
                    intersection = required_capabilities.intersection(agent_capabilities)
                    match_score = len(intersection) / len(required_capabilities)
            
            # Considerar uso reciente del agente (preferir agentes menos usados recientemente)
            last_used = agent_info.get("last_used")
            recency_bonus = 0.1 if last_used is None else 0
            
            # Puntuación final
            score = match_score + recency_bonus
            
            if score > best_match_score:
                best_match_score = score
                best_agent_id = agent_id
        
        # Solo devolver un agente si coincide al menos con algunas capacidades
        if best_match_score > 0:
            return best_agent_id
        else:
            return None
    
    @staticmethod
    def create_execution_plan(
        task_description: str, 
        context: Optional[Dict] = None
    ) -> ExecutionPlan:
        """
        Crear un plan de ejecución completo para una tarea.
        
        Esto combina la descomposición de tareas, la creación de dependencias
        y la programación inicial en una sola operación.
        
        Args:
            task_description: Descripción de la tarea compleja
            context: Información de contexto opcional
            
        Returns:
            Plan de ejecución para la tarea
        """
        # Crear plan
        plan = ExecutionPlan(
            original_request=task_description
        )
        
        # Descomponer tarea en subtareas
        subtasks = PlanningAlgorithms.decompose_task(task_description, context)
        
        # Agregar tareas al plan
        for task in subtasks:
            plan.add_task(task)
        
        # Crear dependencias
        dependencies = PlanningAlgorithms.create_dependencies(subtasks)
        
        # Agregar dependencias al plan
        for dep in dependencies:
            plan.add_dependency(dep)
        
        # Calcular orden de ejecución
        plan.compute_execution_order()
        
        return plan 