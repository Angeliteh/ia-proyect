"""
Memory System Module

This module provides the core MemorySystem class that serves as the 
central component for managing and retrieving memories.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Set, Tuple, Union
from datetime import datetime
import uuid

from .memory_item import MemoryItem
from ..storage.base_storage import BaseStorage
from ..storage.in_memory_storage import InMemoryStorage

logger = logging.getLogger(__name__)


class MemorySystem:
    """
    Central memory management system for storing, retrieving, and querying memories.
    
    The MemorySystem serves as the core component of the memory architecture,
    providing a unified interface for working with memories regardless of
    their storage backend or memory type.
    """
    
    def __init__(self, storage: Optional[BaseStorage] = None):
        """
        Initialize a new memory system.
        
        Args:
            storage: The storage backend to use for storing memories.
                    If not provided, an InMemoryStorage is used.
        """
        self.storage = storage or InMemoryStorage()
        self._memory_links: Dict[str, Dict[str, Set[str]]] = {}
        logger.info(f"Initialized MemorySystem with storage: {type(self.storage).__name__}")
    
    def add_memory(
        self,
        content: Any,
        memory_type: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new memory item to the system.
        
        Args:
            content: The content of the memory. Can be text, a dictionary, or any JSON-serializable data.
            memory_type: The type of memory (e.g., "fact", "conversation", "task").
            importance: A value between 0 and 1 indicating the importance of the memory.
            metadata: Additional metadata about the memory.
            
        Returns:
            The ID of the newly created memory.
        """
        # Create a new memory item
        memory = MemoryItem(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        # Store the memory
        self.storage.store(memory)
        
        # Initialize link tracking for this memory
        self._memory_links[memory.id] = {}
        
        logger.debug(f"Added memory: {memory.id} (type: {memory_type}, importance: {importance})")
        return memory.id
    
    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve.
            
        Returns:
            The memory item if found, None otherwise.
        """
        memory = self.storage.retrieve(memory_id)
        if memory:
            memory.access()
            self.storage.store(memory)  # Update the access count
            logger.debug(f"Retrieved memory: {memory_id} (access count: {memory.access_count})")
        else:
            logger.debug(f"Memory not found: {memory_id}")
        
        return memory
    
    def update_memory(
        self,
        memory_id: str,
        content: Optional[Any] = None,
        memory_type: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing memory.
        
        Args:
            memory_id: The ID of the memory to update.
            content: The new content (if provided).
            memory_type: The new memory type (if provided).
            importance: The new importance value (if provided).
            metadata: New metadata to merge with existing metadata (if provided).
            
        Returns:
            True if the memory was updated, False if it couldn't be found.
        """
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"Cannot update non-existent memory: {memory_id}")
            return False
        
        # Update the memory fields
        if content is not None:
            memory.content = content
        
        if memory_type is not None:
            memory.memory_type = memory_type
        
        if importance is not None:
            memory.importance = importance
        
        if metadata is not None:
            memory.metadata.update(metadata)
        
        # Store the updated memory
        self.storage.store(memory)
        logger.debug(f"Updated memory: {memory_id}")
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from the system.
        
        Args:
            memory_id: The ID of the memory to delete.
            
        Returns:
            True if the memory was deleted, False if it couldn't be found.
        """
        # Remove any links to/from this memory
        if memory_id in self._memory_links:
            # Remove outgoing links
            outgoing_links = self._memory_links.pop(memory_id)
            
            # Remove incoming links
            for other_id in self._memory_links:
                for link_type in list(self._memory_links[other_id].keys()):
                    if memory_id in self._memory_links[other_id][link_type]:
                        self._memory_links[other_id][link_type].remove(memory_id)
                        
                        # Clean up empty link sets
                        if not self._memory_links[other_id][link_type]:
                            del self._memory_links[other_id][link_type]
        
        # Delete from storage
        result = self.storage.delete(memory_id)
        if result:
            logger.debug(f"Deleted memory: {memory_id}")
        else:
            logger.warning(f"Failed to delete memory: {memory_id}")
        
        return result
    
    def link_memories(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "related"
    ) -> bool:
        """
        Create a link between two memories.
        
        Args:
            source_id: The ID of the source memory.
            target_id: The ID of the target memory.
            link_type: The type of link (e.g., "related", "causes", "follows").
            
        Returns:
            True if the link was created, False if either memory couldn't be found.
        """
        # Verify both memories exist
        source = self.get_memory(source_id)
        target = self.get_memory(target_id)
        
        if not source or not target:
            logger.warning(f"Cannot link non-existent memories: {source_id} -> {target_id}")
            return False
        
        # Initialize link dicts if needed
        if source_id not in self._memory_links:
            self._memory_links[source_id] = {}
        
        if link_type not in self._memory_links[source_id]:
            self._memory_links[source_id][link_type] = set()
        
        # Add the link
        self._memory_links[source_id][link_type].add(target_id)
        logger.debug(f"Linked memories: {source_id} -[{link_type}]-> {target_id}")
        return True
    
    def unlink_memories(
        self,
        source_id: str,
        target_id: str,
        link_type: Optional[str] = None
    ) -> bool:
        """
        Remove a link between two memories.
        
        Args:
            source_id: The ID of the source memory.
            target_id: The ID of the target memory.
            link_type: The type of link to remove. If None, all links are removed.
            
        Returns:
            True if any links were removed, False otherwise.
        """
        if source_id not in self._memory_links:
            return False
        
        removed = False
        
        if link_type is None:
            # Remove all links
            for lt in list(self._memory_links[source_id].keys()):
                if target_id in self._memory_links[source_id][lt]:
                    self._memory_links[source_id][lt].remove(target_id)
                    removed = True
                    
                    # Clean up empty link sets
                    if not self._memory_links[source_id][lt]:
                        del self._memory_links[source_id][lt]
        elif link_type in self._memory_links[source_id]:
            # Remove a specific link type
            if target_id in self._memory_links[source_id][link_type]:
                self._memory_links[source_id][link_type].remove(target_id)
                removed = True
                
                # Clean up empty link sets
                if not self._memory_links[source_id][link_type]:
                    del self._memory_links[source_id][link_type]
        
        if removed:
            logger.debug(f"Unlinked memories: {source_id} -> {target_id}")
        
        return removed
    
    def get_related_memories(
        self,
        memory_id: str,
        link_type: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Get memories that are linked to the specified memory.
        
        Args:
            memory_id: The ID of the memory to get related memories for.
            link_type: The type of link to follow. If None, all link types are followed.
            
        Returns:
            A list of memory items that are linked to the specified memory.
        """
        if memory_id not in self._memory_links:
            return []
        
        related_ids = set()
        
        if link_type is None:
            # Get all related memories
            for lt in self._memory_links[memory_id]:
                related_ids.update(self._memory_links[memory_id][lt])
        elif link_type in self._memory_links[memory_id]:
            # Get memories related by a specific link type
            related_ids = self._memory_links[memory_id][link_type]
        
        # Get the actual memory items
        related_memories = []
        for rid in related_ids:
            memory = self.get_memory(rid)
            if memory:
                related_memories.append(memory)
        
        logger.debug(f"Found {len(related_memories)} related memories for {memory_id}")
        return related_memories
    
    def query_memories(
        self,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        max_importance: Optional[float] = None,
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None,
        metadata_query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        """
        Query memories based on various criteria.
        
        Args:
            memory_type: Filter by memory type.
            min_importance: Filter by minimum importance.
            max_importance: Filter by maximum importance.
            before_timestamp: Filter by maximum creation timestamp.
            after_timestamp: Filter by minimum creation timestamp.
            metadata_query: Filter by metadata fields.
            limit: Maximum number of memories to return.
            offset: Starting offset for pagination.
            
        Returns:
            A list of memory items matching the criteria.
        """
        # Construct the query
        query = {}
        
        if memory_type is not None:
            query["memory_type"] = memory_type
        
        if min_importance is not None:
            query["min_importance"] = min_importance
        
        if max_importance is not None:
            query["max_importance"] = max_importance
        
        if before_timestamp is not None:
            query["before_timestamp"] = before_timestamp
        
        if after_timestamp is not None:
            query["after_timestamp"] = after_timestamp
        
        if metadata_query is not None:
            query["metadata"] = metadata_query
        
        # Execute the query
        results = self.storage.query(query, limit=limit, offset=offset)
        logger.debug(f"Query returned {len(results)} results")
        return results
    
    def get_all_memories(self, limit: int = 1000, offset: int = 0) -> List[MemoryItem]:
        """
        Get all memories in the system.
        
        Args:
            limit: Maximum number of memories to return.
            offset: Starting offset for pagination.
            
        Returns:
            A list of all memory items.
        """
        return self.storage.query({}, limit=limit, offset=offset)
    
    def clear(self) -> None:
        """
        Clear all memories from the system.
        """
        self.storage.clear()
        self._memory_links = {}
        logger.warning("Cleared all memories from the system")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.
        
        Returns:
            A dictionary containing statistics about the memory system.
        """
        memories = self.get_all_memories()
        
        # Count memory types
        memory_types = {}
        for memory in memories:
            if memory.memory_type in memory_types:
                memory_types[memory.memory_type] += 1
            else:
                memory_types[memory.memory_type] = 1
        
        # Count links
        total_links = 0
        for source_id in self._memory_links:
            for link_type in self._memory_links[source_id]:
                total_links += len(self._memory_links[source_id][link_type])
        
        # Compute average importance
        if memories:
            avg_importance = sum(memory.importance for memory in memories) / len(memories)
        else:
            avg_importance = 0
        
        return {
            "total_memories": len(memories),
            "memory_types": memory_types,
            "total_links": total_links,
            "avg_importance": avg_importance
        } 