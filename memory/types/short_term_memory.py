"""
Short-Term Memory Module

This module provides a short-term memory implementation that automatically
forgets memories after a configurable time period.
"""

import logging
import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..core.memory_system import MemorySystem
from ..core.memory_item import MemoryItem
from ..storage.in_memory_storage import InMemoryStorage

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Short-term memory implementation that automatically forgets old memories.
    
    This class provides a memory store with automatic forgetting based on
    time, capacity limits, and access frequency.
    """
    
    def __init__(
        self,
        memory_system: MemorySystem,
        retention_minutes: int = 30,
        capacity: int = 100,
        cleanup_interval_seconds: int = 60
    ):
        """
        Initialize a new short-term memory.
        
        Args:
            memory_system: The central memory system to integrate with
            retention_minutes: How long memories should be retained (in minutes)
            capacity: Maximum number of memories to keep before forcing forgetting
            cleanup_interval_seconds: How often to run the cleanup process
        """
        self.memory_system = memory_system
        self.storage = InMemoryStorage()
        self.retention_minutes = retention_minutes
        self.capacity = capacity
        self.cleanup_interval = cleanup_interval_seconds
        
        # Instead of registering with the memory system, just maintain our own cache of memory IDs
        self.memory_ids = set()
        
        # Setup cleanup thread
        self._stop_cleanup = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_task,
            daemon=True,
            name="ShortTermMemory-Cleanup"
        )
        self._cleanup_thread.start()
        
        logger.info(
            f"Initialized short-term memory with retention={retention_minutes}m, "
            f"capacity={capacity}, cleanup_interval={cleanup_interval_seconds}s"
        )
    
    def _cleanup_task(self) -> None:
        """
        Background task to periodically clean up old memories.
        """
        while not self._stop_cleanup.is_set():
            try:
                self._perform_cleanup()
            except Exception as e:
                logger.error(f"Error during short-term memory cleanup: {e}")
            
            # Sleep for the cleanup interval or until stopped
            self._stop_cleanup.wait(self.cleanup_interval)
    
    def _perform_cleanup(self) -> None:
        """
        Perform the actual cleanup operation.
        """
        cutoff_time = datetime.now() - timedelta(minutes=self.retention_minutes)
        
        # Get all memories in our tracked set
        memories = []
        to_forget = []
        
        for memory_id in list(self.memory_ids):
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                memories.append(memory)
                # Check if memory is older than the retention period
                if memory.created_at < cutoff_time:
                    to_forget.append(memory.id)
            else:
                # Memory no longer exists in the base system
                to_forget.append(memory_id)
        
        # If we're still over capacity after time-based forgetting,
        # forget the least recently accessed memories
        if len(memories) - len(to_forget) > self.capacity:
            # Sort by last accessed time (oldest first)
            remaining = [m for m in memories if m.id not in to_forget]
            remaining.sort(key=lambda m: m.last_accessed)
            
            # Add enough to the forget list to get down to capacity
            extra_to_forget = len(remaining) - self.capacity
            if extra_to_forget > 0:
                to_forget.extend([m.id for m in remaining[:extra_to_forget]])
        
        # Forget all identified memories
        for memory_id in to_forget:
            if memory_id in self.memory_ids:
                self.memory_ids.remove(memory_id)
        
        if to_forget:
            logger.debug(f"Short-term memory cleanup: forgot {len(to_forget)} memories")
    
    def stop(self) -> None:
        """
        Stop the cleanup thread and shut down the short-term memory.
        """
        self._stop_cleanup.set()
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        logger.info("Short-term memory stopped")
    
    def add(
        self,
        content: Any,
        source: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new item to short-term memory.
        
        Args:
            content: The content of the memory
            source: The source of the memory
            importance: The importance of the memory (0-1)
            metadata: Additional metadata for the memory
            
        Returns:
            The ID of the created memory
        """
        # Add metadata about short-term memory
        full_metadata = metadata or {}
        full_metadata["source"] = source

        # Create memory in the base system
        memory_id = self.memory_system.add_memory(
            content=content,
            memory_type="short_term",
            importance=importance,
            metadata=full_metadata
        )
        
        # Track this memory ID in our short-term memory
        self.memory_ids.add(memory_id)
        
        return memory_id
    
    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """
        Get the most recent memories from short-term memory.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            A list of recent memory items
        """
        # Get all memories tracked in our short-term memory
        memories = []
        for memory_id in self.memory_ids:
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                memories.append(memory)
        
        # Sort by recency (created_at) and return the most recent
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]
    
    def clear(self) -> None:
        """
        Clear all memories from short-term memory.
        """
        # Note: We don't delete memories from the base system, just stop tracking them
        self.memory_ids.clear()
        logger.info("Short-term memory cleared")
    
    def get_by_source(self, source: str, limit: int = 10) -> List[MemoryItem]:
        """
        Get memories from a specific source.
        
        Args:
            source: The source to filter by
            limit: Maximum number of memories to return
            
        Returns:
            A list of memory items from the specified source
        """
        # Get all memories tracked in our short-term memory
        all_memories = []
        for memory_id in self.memory_ids:
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                all_memories.append(memory)
        
        # Filter by source
        filtered = [m for m in all_memories if m.metadata.get("source") == source]
        
        # Sort by recency and limit
        filtered.sort(key=lambda m: m.created_at, reverse=True)
        return filtered[:limit]
    
    def get_all_item_ids(self) -> List[str]:
        """
        Get all memory IDs tracked in short-term memory.
        
        Returns:
            A list of memory IDs
        """
        return list(self.memory_ids)
    
    def remove_item(self, memory_id: str) -> bool:
        """
        Remove a memory from short-term tracking (without deleting it).
        
        Args:
            memory_id: The ID of the memory to remove
            
        Returns:
            True if the memory was removed, False if it wasn't tracked
        """
        if memory_id in self.memory_ids:
            self.memory_ids.remove(memory_id)
            return True
        return False 