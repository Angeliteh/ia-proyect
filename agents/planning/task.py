"""
Task module for planning.

This module defines the data structures for representing tasks, dependencies,
and related concepts in the planning system.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


class TaskStatus(Enum):
    """Status of a task in the execution pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class DependencyType(Enum):
    """Types of dependencies between tasks."""
    FINISH_TO_START = "finish_to_start"  # Task B can start only after Task A finishes
    START_TO_START = "start_to_start"    # Task B can start only after Task A starts
    FINISH_TO_FINISH = "finish_to_finish"  # Task B can finish only after Task A finishes
    START_TO_FINISH = "start_to_finish"  # Task B can finish only after Task A starts


class Task:
    """
    Represents a task in a plan.
    
    A task is an atomic unit of work that can be assigned to an agent
    for execution. Tasks can have dependencies on other tasks.
    """
    
    def __init__(
        self,
        task_id: Optional[str] = None,
        description: str = "",
        estimated_complexity: float = 1.0,
        required_capabilities: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new task.
        
        Args:
            task_id: Unique identifier for the task (auto-generated if None)
            description: Human-readable description of the task
            estimated_complexity: Estimated complexity (1.0 = average)
            required_capabilities: List of capabilities required to execute the task
            context: Additional context information for the task
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.description = description
        self.estimated_complexity = estimated_complexity
        self.required_capabilities = required_capabilities or []
        self.context = context or {}
        
        # Execution state
        self.status = TaskStatus.PENDING
        self.assigned_agent = None
        self.result = None
        self.error = None
        
        # Timing information
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "estimated_complexity": self.estimated_complexity,
            "required_capabilities": self.required_capabilities,
            "context": self.context,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a task from a dictionary."""
        task = cls(
            task_id=data.get("task_id"),
            description=data.get("description", ""),
            estimated_complexity=data.get("estimated_complexity", 1.0),
            required_capabilities=data.get("required_capabilities", []),
            context=data.get("context", {})
        )
        
        # Set status
        status_str = data.get("status")
        if status_str:
            task.status = TaskStatus(status_str)
        
        # Set other fields
        task.assigned_agent = data.get("assigned_agent")
        task.result = data.get("result")
        task.error = data.get("error")
        
        # Set timing information
        created_at = data.get("created_at")
        if created_at:
            task.created_at = datetime.fromisoformat(created_at)
        
        started_at = data.get("started_at")
        if started_at:
            task.started_at = datetime.fromisoformat(started_at)
        
        completed_at = data.get("completed_at")
        if completed_at:
            task.completed_at = datetime.fromisoformat(completed_at)
        
        return task
    
    def start_execution(self, agent_id: str) -> None:
        """
        Mark this task as started by the specified agent.
        
        Args:
            agent_id: ID of the agent executing the task
        """
        self.status = TaskStatus.IN_PROGRESS
        self.assigned_agent = agent_id
        self.started_at = datetime.now()
    
    def complete(self, result: Any = None) -> None:
        """
        Mark this task as completed with the given result.
        
        Args:
            result: Result data from the task execution
        """
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()
    
    def fail(self, error: str) -> None:
        """
        Mark this task as failed with the given error.
        
        Args:
            error: Error message or information
        """
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()


class TaskDependency:
    """
    Represents a dependency between two tasks.
    
    A dependency defines a relationship where one task depends
    on another task in some way.
    """
    
    def __init__(
        self,
        source_task_id: str,
        target_task_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START
    ):
        """
        Initialize a new task dependency.
        
        Args:
            source_task_id: ID of the source task (the one being depended on)
            target_task_id: ID of the target task (the one that depends on the source)
            dependency_type: Type of dependency relationship
        """
        self.source_task_id = source_task_id
        self.target_task_id = target_task_id
        self.dependency_type = dependency_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dependency to a dictionary for serialization."""
        return {
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "dependency_type": self.dependency_type.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskDependency':
        """Create a dependency from a dictionary."""
        return cls(
            source_task_id=data["source_task_id"],
            target_task_id=data["target_task_id"],
            dependency_type=DependencyType(data.get("dependency_type", 
                                                  DependencyType.FINISH_TO_START.value))
        ) 