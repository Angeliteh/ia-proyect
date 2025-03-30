"""
Planning package for task decomposition and execution planning.

This package provides components for decomposing complex tasks into simpler subtasks,
establishing dependencies between tasks, and creating execution plans.
"""

from .task import Task, TaskStatus, TaskDependency, DependencyType 