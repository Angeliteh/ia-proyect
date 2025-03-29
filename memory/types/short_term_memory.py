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
        
        # Register with the memory system
        self.memory_system.register_storage_backend("short_term", self.storage)
        
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
        memories = self.storage.list(limit=1000)  # Get all memories
        
        # Find memories to forget
        to_forget = []
        
        # First, identify memories older than the retention period
        for memory in memories:
            if memory.created_at < cutoff_time:
                to_forget.append(memory.id)
        
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
            self.memory_system.forget_memory(memory_id)
        
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
        memory = MemoryItem(
            content=content,
            source=source,
            memory_type="short_term",
            importance=importance,
            metadata=metadata
        )
        
        return self.memory_system.add_memory(memory)
    
    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """
        Get the most recent memories from short-term memory.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            A list of recent memory items
        """
        return self.memory_system.search_by_recency(
            memory_type="short_term",
            limit=limit
        )
    
    def clear(self) -> None:
        """
        Clear all memories from short-term memory.
        """
        memories = self.memory_system.search_by_type("short_term", limit=1000)
        for memory in memories:
            self.memory_system.forget_memory(memory.id)
        
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
        memories = self.memory_system.search_by_source(source, limit=1000)
        # Filter to only short-term memories
        filtered = [m for m in memories if m.memory_type == "short_term"]
        return filtered[:limit] 