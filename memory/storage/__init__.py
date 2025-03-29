"""
Memory Storage Package

This package provides storage backends for the memory system,
allowing for persistent storage of memory items using different
storage technologies.
"""

from .base_storage import BaseStorage
from .in_memory_storage import InMemoryStorage

__all__ = ["BaseStorage", "InMemoryStorage"] 