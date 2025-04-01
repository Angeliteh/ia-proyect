"""
Planner Agent module.

This module implements a specialized agent for task planning and decomposition.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime

from .base import BaseAgent, AgentResponse
from .planning.task import Task, TaskStatus
from .planning.execution_plan import ExecutionPlan, PlanStatus
from .planning.algorithms import PlanningAlgorithms


class PlanStep:
    """
    Represents a step in an execution plan.
    
    This class is used to track individual steps in a plan, including their
    status, dependencies, and results.
    """
    
    def __init__(
        self,
        task_id: str,
        action: str,
        capability_requirements: List[str] = None,
        dependencies: List[str] = None
    ):
        """
        Initialize a new plan step.
        
        Args:
            task_id: Unique identifier for the task
            action: Description of the action to be performed
            capability_requirements: Capabilities required for this step
            dependencies: IDs of other tasks this step depends on
        """
        self.task_id = task_id
        self.action = action
        self.capability_requirements = capability_requirements or []
        self.dependencies = dependencies or []
        
        # Execution state
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        
        # Timing information
        self.created_at = datetime.now().isoformat()
        self.completed_at = None


class PlannerAgent(BaseAgent):
    """
    Agent specialized in planning task execution.
    
    This agent can:
    1. Decompose complex tasks into simpler subtasks
    2. Establish dependencies between subtasks
    3. Select appropriate agents for each subtask
    4. Create optimized execution plans
    
    Attributes:
        plans: Dictionary of active plans
        plan_history: Dictionary of completed plans
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the planner agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary
        """
        super().__init__(agent_id, config)
        
        # Active plans
        self.plans: Dict[str, ExecutionPlan] = {}
        
        # Completed plan history
        self.plan_history: Dict[str, ExecutionPlan] = {}
        
        # Maximum plan history size
        self.max_history_size = config.get("max_history_size", 10)
        
        self.logger.info(f"Planner agent initialized with {self.max_history_size} max history size")
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a planning request.
        
        This method:
        1. Analyzes the request to determine the type of planning needed
        2. Creates an execution plan with tasks, dependencies, and assignments
        3. Returns the plan for execution by the orchestrator
        
        Args:
            query: Planning request or task description
            context: Optional context information
            
        Returns:
            AgentResponse with the execution plan
        """
        self.set_state("processing")
        context = context or {}
        
        # Verificar si es una solicitud de actualización de tarea
        if query.startswith("update_task:") and context.get("update_type") == "task_status":
            try:
                return await self._handle_task_update(query, context)
            except Exception as e:
                self.logger.error(f"Error handling task update: {str(e)}")
                return AgentResponse(
                    content=f"Error updating task: {str(e)}",
                    status="error",
                    metadata={"error": str(e)}
                )
        
        try:
            # Analyze the request
            self.logger.info(f"Creating execution plan for: {query[:50]}...")
            
            # Create the execution plan
            plan = PlanningAlgorithms.create_execution_plan(query, context)
            
            # Store the plan
            self.plans[plan.plan_id] = plan
            
            # Format response
            task_descriptions = []
            for i, task_id in enumerate(plan.execution_order):
                task = plan.tasks[task_id]
                agent_type = ", ".join(task.required_capabilities)
                task_descriptions.append(f"- Step {i+1}: {task.description} (Agent type: {agent_type})")
            
            plan_description = (
                f"Plan {plan.plan_id} created with {len(plan.tasks)} tasks:\n\n" +
                "\n".join(task_descriptions)
            )
            
            self.set_state("idle")
            return AgentResponse(
                content=plan_description,
                metadata={
                    "plan_id": plan.plan_id,
                    "plan": plan.to_dict(),
                    "planner_id": self.agent_id
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error in planning: {str(e)}")
            self.set_state("error")
            return AgentResponse(
                content=f"Error creating plan: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
            
    async def _handle_task_update(self, query: str, context: Dict) -> AgentResponse:
        """
        Handle a task update notification from another agent.
        
        The query should be in the format: update_task:<task_id>:<status>
        
        Args:
            query: The task update query
            context: Request context with optional result data
            
        Returns:
            AgentResponse with the result
        """
        # Parse task update query
        parts = query.split(":", 2)
        if len(parts) < 3 or parts[0] != "update_task":
            return AgentResponse(
                content="Error: Invalid task update format. Expected 'update_task:<task_id>:<status>'",
                status="error",
                metadata={"error": "invalid_format"}
            )
        
        task_id = parts[1]
        try:
            status = TaskStatus(parts[2])
        except ValueError:
            return AgentResponse(
                content=f"Error: Invalid task status '{parts[2]}'. Expected one of {[s.value for s in TaskStatus]}",
                status="error",
                metadata={"error": "invalid_status"}
            )
            
        # Get result data and error if provided
        result = context.get("result", None)
        error = context.get("error", None)
        
        # Find plan containing this task
        target_plan_id = None
        target_plan = None
        
        # Manejar caso donde el plan_id viene directamente en el contexto
        if context and "plan_id" in context:
            plan_id = context["plan_id"]
            target_plan = self.plans.get(plan_id)
            if target_plan:
                target_plan_id = plan_id
        
        # Si no se encontró el plan, buscar en todos los planes
        if not target_plan:
            for plan_id, plan in self.plans.items():
                for step in plan.steps:
                    if step.task_id == task_id:
                        target_plan_id = plan_id
                        target_plan = plan
                        break
                if target_plan_id:
                    break
        
        # Si todavía no se encontró el plan, crear uno temporal para esta tarea
        if not target_plan_id:
            self.logger.warning(f"No plan found for task {task_id}. Creating a placeholder entry.")
            
            # Crear un plan provisional para la tarea
            new_plan_id = str(uuid.uuid4())
            placeholder_plan = ExecutionPlan(
                plan_id=new_plan_id,
                original_request=f"Placeholder for task {task_id}",
                steps=[
                    PlanStep(
                        task_id=task_id,
                        action=f"Unknown action for task {task_id}",
                        capability_requirements=["unknown"],
                        dependencies=[]
                    )
                ]
            )
            self.plans[new_plan_id] = placeholder_plan
            target_plan_id = new_plan_id
            target_plan = placeholder_plan
            
        # Update the task status
        try:
            success = await self.update_plan(target_plan_id, task_id, status, result, error)
            if success:
                self.logger.info(f"Updated task {task_id} in plan {target_plan_id} to {status.value}")
                return AgentResponse(
                    content=f"Task {task_id} in plan {target_plan_id} updated to {status.value}",
                    status="success",
                    metadata={"task_id": task_id, "plan_id": target_plan_id, "status": status.value}
                )
            else:
                return AgentResponse(
                    content=f"Error: Failed to update task {task_id} in plan {target_plan_id}",
                    status="error", 
                    metadata={"error": "update_failed", "task_id": task_id, "plan_id": target_plan_id}
                )
        except Exception as e:
            self.logger.error(f"Error handling task update: {str(e)}")
            return AgentResponse(
                content=f"Error updating task: {str(e)}",
                status="error",
                metadata={"error": "exception", "message": str(e)}
            )
    
    async def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """
        Get a plan by ID.
        
        Args:
            plan_id: ID of the plan to retrieve
            
        Returns:
            ExecutionPlan if found, None otherwise
        """
        return self.plans.get(plan_id) or self.plan_history.get(plan_id)
    
    async def update_plan(self, plan_id: str, 
                         task_id: str, 
                         status: TaskStatus,
                         result: Any = None,
                         error: str = None) -> Optional[ExecutionPlan]:
        """
        Update a task status within a plan.
        
        Args:
            plan_id: ID of the plan
            task_id: ID of the task to update
            status: New status for the task
            result: Optional result if the task was completed
            error: Optional error message if the task failed
            
        Returns:
            Updated plan or None if not found
        """
        try:
            # Verify the plan exists
            if plan_id not in self.plans:
                self.logger.warning(f"Plan {plan_id} not found. Using placeholder.")
                # Crear un plan provisional si no existe
                placeholder_plan = ExecutionPlan(
                    plan_id=plan_id,
                    original_request=f"Placeholder for task {task_id}",
                    steps=[
                        PlanStep(
                            task_id=task_id,
                            action=f"Unknown action for task {task_id}",
                            capability_requirements=["unknown"],
                            dependencies=[]
                        )
                    ]
                )
                self.plans[plan_id] = placeholder_plan
            
            plan = self.plans[plan_id]
            
            # Find the task in the plan
            task_found = False
            for step in plan.steps:
                if step.task_id == task_id:
                    # Verify valid state transition (with tolerance for repeated states)
                    if step.status != status:
                        self.logger.info(f"Updating task {task_id} status from {step.status.value} to {status.value}")
                    else:
                        self.logger.info(f"Task {task_id} status already set to {status.value}, no change needed")
                    
                    # Update status
                    step.status = status
                    
                    # Update result/error if provided
                    if status == TaskStatus.COMPLETED and result is not None:
                        step.result = result
                        step.completed_at = datetime.now().isoformat()
                    elif status == TaskStatus.FAILED and error is not None:
                        step.error = error
                        step.completed_at = datetime.now().isoformat()
                    
                    task_found = True
                    break
            
            # Create the task if not found
            if not task_found:
                self.logger.warning(f"Task {task_id} not found in plan {plan_id}. Adding as a new step.")
                new_step = PlanStep(
                    task_id=task_id,
                    action=f"Auto-added task {task_id}",
                    capability_requirements=["unknown"],
                    dependencies=[]
                )
                new_step.status = status
                
                if status == TaskStatus.COMPLETED and result is not None:
                    new_step.result = result
                    new_step.completed_at = datetime.now().isoformat()
                elif status == TaskStatus.FAILED and error is not None:
                    new_step.error = error
                    new_step.completed_at = datetime.now().isoformat()
                
                plan.steps.append(new_step)
            
            # Check if the entire plan should be updated
            self._update_plan_status(plan)
            
            return plan
        except Exception as e:
            self.logger.error(f"Error updating plan {plan_id}, task {task_id}: {str(e)}")
            return None
            
    def _update_plan_status(self, plan: ExecutionPlan) -> None:
        """
        Update a plan's status based on its tasks.
        
        Args:
            plan: The plan to update
        """
        # No tasks, can't determine status
        if not plan.steps:
            plan.status = PlanStatus.PENDING
            return
            
        # Count tasks by status
        pending = sum(1 for step in plan.steps if step.status == TaskStatus.PENDING)
        in_progress = sum(1 for step in plan.steps if step.status == TaskStatus.IN_PROGRESS)
        completed = sum(1 for step in plan.steps if step.status == TaskStatus.COMPLETED)
        failed = sum(1 for step in plan.steps if step.status == TaskStatus.FAILED)
        blocked = sum(1 for step in plan.steps if step.status == TaskStatus.BLOCKED)
        
        total = len(plan.steps)
        
        # Determine plan status
        if failed > 0:
            plan.status = PlanStatus.FAILED
        elif total == completed:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now().isoformat()
        elif in_progress > 0:
            plan.status = PlanStatus.IN_PROGRESS
        elif blocked > 0:
            plan.status = PlanStatus.BLOCKED
        else:
            plan.status = PlanStatus.PENDING
    
    def _archive_plan(self, plan_id: str) -> None:
        """
        Move a plan from active plans to history.
        
        Args:
            plan_id: ID of the plan to archive
        """
        if plan_id not in self.plans:
            return
            
        # Move plan to history
        self.plan_history[plan_id] = self.plans[plan_id]
        del self.plans[plan_id]
        
        # Limit history size
        if len(self.plan_history) > self.max_history_size:
            # Remove oldest plan (based on creation time)
            oldest_plan_id = min(
                self.plan_history.keys(),
                key=lambda pid: self.plan_history[pid].created_at
            )
            del self.plan_history[oldest_plan_id]
    
    async def replan(self, plan_id: str, reason: str) -> Optional[ExecutionPlan]:
        """
        Create a new plan based on an existing one, adjusting for failures or changes.
        
        Args:
            plan_id: ID of the original plan
            reason: Reason for replanning
            
        Returns:
            New ExecutionPlan if successful, None otherwise
        """
        original_plan = await self.get_plan(plan_id)
        if not original_plan:
            self.logger.warning(f"Attempt to replan nonexistent plan: {plan_id}")
            return None
            
        try:
            # Create a new plan with the same original request
            new_plan = PlanningAlgorithms.create_execution_plan(
                original_plan.original_request,
                context={"original_plan_id": plan_id, "replan_reason": reason}
            )
            
            # Store the new plan
            self.plans[new_plan.plan_id] = new_plan
            
            self.logger.info(f"Replanned {plan_id} -> {new_plan.plan_id} due to {reason}")
            return new_plan
            
        except Exception as e:
            self.logger.error(f"Error replanning {plan_id}: {str(e)}")
            return None
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        return [
            "task_planning",
            "task_decomposition",
            "dependency_management",
            "agent_selection",
            "execution_scheduling"
        ] 