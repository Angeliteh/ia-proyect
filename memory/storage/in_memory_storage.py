"""
In-Memory Storage Module

This module provides an in-memory implementation of the BaseStorage
interface for storing memory items in RAM.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_storage import BaseStorage

# This is a forward reference
MemoryItem = Any

logger = logging.getLogger(__name__)


class InMemoryStorage(BaseStorage):
    """
    In-memory storage backend for memory items.
    
    This storage backend keeps all memory items in RAM, which makes it
    fast but not persistent across restarts. It's suitable for short-lived
    applications or for testing purposes.
    """
    
    def __init__(self):
        """Initialize a new in-memory storage backend."""
        self._memories: Dict[str, MemoryItem] = {}
        logger.info("Initialized in-memory storage")
    
    def store(self, memory: MemoryItem) -> bool:
        """
        Store a memory item.
        
        Args:
            memory: The memory item to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        self._memories[memory.id] = memory
        logger.debug(f"Stored memory: {memory.id}")
        return True
    
    def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory item by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory item if found, None otherwise
        """
        memory = self._memories.get(memory_id)
        if memory:
            logger.debug(f"Retrieved memory: {memory_id}")
        else:
            logger.debug(f"Memory not found: {memory_id}")
        return memory
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory item.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if memory_id in self._memories:
            del self._memories[memory_id]
            logger.debug(f"Deleted memory: {memory_id}")
            return True
        else:
            logger.debug(f"Cannot delete non-existent memory: {memory_id}")
            return False
    
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
        results = []
        
        # Get all memories as a starting point
        all_memories = list(self._memories.values())
        
        # Apply filters
        filtered_memories = all_memories
        
        # Filter by memory type
        if "memory_type" in query:
            filtered_memories = [
                m for m in filtered_memories 
                if m.memory_type == query["memory_type"]
            ]
        
        # Filter by importance (min)
        if "min_importance" in query:
            filtered_memories = [
                m for m in filtered_memories 
                if m.importance >= query["min_importance"]
            ]
        
        # Filter by importance (max)
        if "max_importance" in query:
            filtered_memories = [
                m for m in filtered_memories 
                if m.importance <= query["max_importance"]
            ]
        
        # Filter by creation timestamp (before)
        if "before_timestamp" in query:
            before = query["before_timestamp"]
            filtered_memories = [
                m for m in filtered_memories 
                if m.created_at <= before
            ]
        
        # Filter by creation timestamp (after)
        if "after_timestamp" in query:
            after = query["after_timestamp"]
            filtered_memories = [
                m for m in filtered_memories 
                if m.created_at >= after
            ]
        
        # Filter by metadata
        if "metadata" in query:
            metadata_query = query["metadata"]
            filtered_memories = [
                m for m in filtered_memories 
                if all(
                    k in m.metadata and m.metadata[k] == v
                    for k, v in metadata_query.items()
                )
            ]
        
        # Sort by importance (highest first)
        filtered_memories.sort(key=lambda m: m.importance, reverse=True)
        
        # Apply pagination
        paginated_memories = filtered_memories[offset:offset + limit]
        
        logger.debug(f"Query returned {len(paginated_memories)} results")
        return paginated_memories
    
    def clear(self) -> bool:
        """
        Clear all memory items from storage.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        count = len(self._memories)
        self._memories.clear()
        logger.warning(f"Cleared {count} memories from in-memory storage")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the storage.
        
        Returns:
            A dictionary of statistics
        """
        memory_types = {}
        for memory in self._memories.values():
            if memory.memory_type in memory_types:
                memory_types[memory.memory_type] += 1
            else:
                memory_types[memory.memory_type] = 1
        
        return {
            "total": len(self._memories),
            "memory_types": memory_types
        } 