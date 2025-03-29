"""
Base Storage Module

This module defines the BaseStorage abstract base class that all
storage backends must implement.
"""

import abc
from typing import List, Dict, Any, Optional
import logging

# This is a forward reference to avoid circular imports
# The actual type is defined in memory_item.py
MemoryItem = Any

logger = logging.getLogger(__name__)


class BaseStorage(abc.ABC):
    """
    Abstract base class for memory storage backends.
    
    All storage backends must implement these methods to provide
    a consistent interface for storing and retrieving memories.
    """
    
    @abc.abstractmethod
    def store(self, memory: MemoryItem) -> bool:
        """
        Store a memory item.
        
        Args:
            memory: The memory item to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory item by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory item if found, None otherwise
        """
        pass
    
    @abc.abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory item.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def query(
        self, 
        query: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        """
        Query for memory items matching the given criteria.
        
        Args:
            query: A dictionary of query parameters
            limit: Maximum number of results to return
            offset: Starting offset for pagination
            
        Returns:
            A list of memory items matching the query
        """
        pass
    
    @abc.abstractmethod
    def clear(self) -> bool:
        """
        Clear all memory items from storage.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        pass 