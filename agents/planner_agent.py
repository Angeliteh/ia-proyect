"""
Planner Agent module.

This module implements a specialized agent for task planning and decomposition.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any

from .base import BaseAgent, AgentResponse
from .planning.task import Task, TaskStatus
from .planning.execution_plan import ExecutionPlan, PlanStatus
from .planning.algorithms import PlanningAlgorithms


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
        Handle a task update request from the OrchestratorAgent.
        
        Args:
            query: Update message in format "update_task:task_id:status"
            context: Context containing update details
            
        Returns:
            AgentResponse acknowledging the update
        """
        # Extract task info from query
        parts = query.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid task update format: {query}")
            
        task_id = parts[1]
        status_str = parts[2]
        
        # Get plan info from context
        plan_id = context.get("plan_id")
        if not plan_id:
            raise ValueError("Missing plan_id in update context")
            
        # Map string status to TaskStatus enum
        status_map = {
            "PENDING": TaskStatus.PENDING,
            "IN_PROGRESS": TaskStatus.IN_PROGRESS,
            "COMPLETED": TaskStatus.COMPLETED,
            "FAILED": TaskStatus.FAILED,
            "BLOCKED": TaskStatus.BLOCKED
        }
        
        status = status_map.get(status_str)
        if not status:
            raise ValueError(f"Invalid task status: {status_str}")
            
        # Get additional info from context
        result = context.get("result")
        error = context.get("error")
        agent_id = context.get("assigned_agent")
        
        # Update the task
        updated_plan = await self.update_plan(plan_id, task_id, status, result, error)
        
        if not updated_plan:
            raise ValueError(f"Failed to update task {task_id} in plan {plan_id}")
            
        # Get the updated task
        task = updated_plan.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in plan {plan_id}")
            
        # Log detailed update
        if status == TaskStatus.IN_PROGRESS and agent_id:
            self.logger.info(f"Task {task_id} started by agent {agent_id}")
            response_content = f"Task {task_id} marked as in progress with agent {agent_id}"
        elif status == TaskStatus.COMPLETED:
            self.logger.info(f"Task {task_id} completed with result: {result[:50]}...")
            response_content = f"Task {task_id} marked as completed"
        elif status == TaskStatus.FAILED:
            self.logger.warning(f"Task {task_id} failed with error: {error}")
            response_content = f"Task {task_id} marked as failed: {error}"
        else:
            self.logger.info(f"Task {task_id} status updated to {status}")
            response_content = f"Task {task_id} status updated to {status}"
        
        # Check if the plan is completed
        plan_status = updated_plan.status
        if plan_status == PlanStatus.COMPLETED:
            self.logger.info(f"Plan {plan_id} is now complete")
            response_content += f". Plan {plan_id} is now complete."
        elif plan_status == PlanStatus.FAILED:
            self.logger.warning(f"Plan {plan_id} has failed")
            response_content += f". Plan {plan_id} has failed."
            
        # Return acknowledgment
        return AgentResponse(
            content=response_content,
            status="success",
            metadata={
                "plan_id": plan_id,
                "task_id": task_id,
                "task_status": status.value,
                "plan_status": plan_status.value
            }
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
        Update the status of a task in a plan.
        
        Args:
            plan_id: ID of the plan containing the task
            task_id: ID of the task to update
            status: New status for the task
            result: Result data (if task completed)
            error: Error message (if task failed)
            
        Returns:
            Updated ExecutionPlan if found, None otherwise
        """
        plan = self.plans.get(plan_id)
        if not plan:
            self.logger.warning(f"Attempt to update nonexistent plan: {plan_id}")
            return None
        
        # Update the task status
        try:
            plan.update_task_status(task_id, status, result, error)
            
            # If plan is completed or failed, move it to history
            if plan.status in [PlanStatus.COMPLETED, PlanStatus.FAILED]:
                self._archive_plan(plan_id)
            
            return plan
        except Exception as e:
            self.logger.error(f"Error updating plan {plan_id}: {str(e)}")
            return None
    
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