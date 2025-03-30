"""
Execution Plan module.

This module defines structures for representing execution plans,
which are collections of tasks with dependencies.
"""

import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from .task import Task, TaskStatus, TaskDependency, DependencyType


class PlanStatus(Enum):
    """Status of an execution plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionPlan:
    """
    Represents a plan for executing a set of tasks with dependencies.
    
    An execution plan is a directed acyclic graph (DAG) of tasks with
    dependencies between them, along with metadata about execution order
    and status.
    """
    
    def __init__(
        self,
        plan_id: Optional[str] = None,
        original_request: str = "",
        tasks: Optional[Dict[str, Task]] = None,
        dependencies: Optional[List[TaskDependency]] = None
    ):
        """
        Initialize a new execution plan.
        
        Args:
            plan_id: Unique identifier for the plan (auto-generated if None)
            original_request: The original request that led to this plan
            tasks: Dictionary of tasks in the plan, keyed by task_id
            dependencies: List of dependencies between tasks
        """
        self.plan_id = plan_id or str(uuid.uuid4())
        self.original_request = original_request
        self.tasks = tasks or {}
        self.dependencies = dependencies or []
        
        # Execution state
        self.status = PlanStatus.PENDING
        self.execution_order: List[str] = []  # Task IDs in execution order
        
        # Timing information
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the plan to a dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "original_request": self.original_request,
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "status": self.status.value,
            "execution_order": self.execution_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionPlan':
        """Create a plan from a dictionary."""
        plan = cls(
            plan_id=data.get("plan_id"),
            original_request=data.get("original_request", ""),
        )
        
        # Set tasks
        tasks_data = data.get("tasks", {})
        plan.tasks = {tid: Task.from_dict(task_data) 
                     for tid, task_data in tasks_data.items()}
        
        # Set dependencies
        deps_data = data.get("dependencies", [])
        plan.dependencies = [TaskDependency.from_dict(dep_data) 
                           for dep_data in deps_data]
        
        # Set status
        status_str = data.get("status")
        if status_str:
            plan.status = PlanStatus(status_str)
        
        # Set execution order
        plan.execution_order = data.get("execution_order", [])
        
        # Set timing information
        created_at = data.get("created_at")
        if created_at:
            plan.created_at = datetime.fromisoformat(created_at)
        
        started_at = data.get("started_at")
        if started_at:
            plan.started_at = datetime.fromisoformat(started_at)
        
        completed_at = data.get("completed_at")
        if completed_at:
            plan.completed_at = datetime.fromisoformat(completed_at)
        
        return plan
    
    def add_task(self, task: Task) -> None:
        """
        Add a task to the plan.
        
        Args:
            task: The task to add
        """
        self.tasks[task.task_id] = task
    
    def add_dependency(self, dependency: TaskDependency) -> None:
        """
        Add a dependency to the plan.
        
        Args:
            dependency: The dependency to add
        """
        self.dependencies.append(dependency)
    
    def compute_execution_order(self) -> List[str]:
        """
        Compute a valid execution order for the tasks in this plan.
        
        This implements a topological sort algorithm to ensure that
        tasks are executed only after their dependencies are met.
        
        Returns:
            List of task IDs in execution order
        """
        # Build dependency graph
        graph: Dict[str, List[str]] = {task_id: [] for task_id in self.tasks}
        in_degree: Dict[str, int] = {task_id: 0 for task_id in self.tasks}
        
        for dep in self.dependencies:
            if dep.dependency_type.value == "finish_to_start":
                source = dep.source_task_id
                target = dep.target_task_id
                graph[source].append(target)
                in_degree[target] += 1
        
        # Find all tasks with no dependencies
        queue: List[str] = [task_id for task_id, count in in_degree.items() if count == 0]
        
        # Process queue
        execution_order: List[str] = []
        while queue:
            current = queue.pop(0)
            execution_order.append(current)
            
            # Process all tasks that depend on the current task
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(execution_order) != len(self.tasks):
            raise ValueError("Dependency cycle detected in the plan")
        
        self.execution_order = execution_order
        return execution_order
    
    def get_ready_tasks(self) -> List[Task]:
        """
        Get tasks that are ready to be executed.
        
        A task is ready if:
        1. It's in PENDING status
        2. All its dependencies are satisfied
        
        Returns:
            List of ready tasks
        """
        ready_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING and self._are_dependencies_met(task_id):
                ready_tasks.append(task)
        
        return ready_tasks
    
    def _are_dependencies_met(self, task_id: str) -> bool:
        """
        Check if all dependencies for a task are met.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            True if all dependencies are met, False otherwise
        """
        for dep in self.dependencies:
            if dep.target_task_id != task_id:
                continue
                
            source_task = self.tasks.get(dep.source_task_id)
            if not source_task:
                continue
                
            # Check if dependency is satisfied based on type
            if dep.dependency_type == DependencyType.FINISH_TO_START:
                if source_task.status != TaskStatus.COMPLETED:
                    return False
            elif dep.dependency_type == DependencyType.START_TO_START:
                if source_task.status == TaskStatus.PENDING:
                    return False
        
        return True
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Any = None, error: str = None) -> None:
        """
        Update the status of a task in the plan.
        
        Args:
            task_id: ID of the task to update
            status: New status for the task
            result: Result data (if task completed)
            error: Error message (if task failed)
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found in plan")
            
        task = self.tasks[task_id]
        task.status = status
        
        if status == TaskStatus.COMPLETED:
            task.result = result
            task.completed_at = datetime.now()
        elif status == TaskStatus.FAILED:
            task.error = error
            task.completed_at = datetime.now()
        
        # Update plan status if necessary
        self._update_plan_status()
    
    def _update_plan_status(self) -> None:
        """Update the overall status of the plan based on task statuses."""
        # Count tasks by status
        status_counts = {status: 0 for status in TaskStatus}
        for task in self.tasks.values():
            status_counts[task.status] += 1
        
        # All tasks completed
        if status_counts[TaskStatus.COMPLETED] == len(self.tasks):
            self.status = PlanStatus.COMPLETED
            self.completed_at = datetime.now()
            return
            
        # Any task failed (and not all tasks are completed)
        if status_counts[TaskStatus.FAILED] > 0:
            self.status = PlanStatus.FAILED
            self.completed_at = datetime.now()
            return
            
        # Any task in progress
        if status_counts[TaskStatus.IN_PROGRESS] > 0:
            self.status = PlanStatus.IN_PROGRESS
            if not self.started_at:
                self.started_at = datetime.now()
            return
            
        # Otherwise, plan is still pending
        self.status = PlanStatus.PENDING 