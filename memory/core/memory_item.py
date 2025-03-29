"""
Memory Item Module

This module defines the MemoryItem class, which represents a single 
memory item within the memory system.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class MemoryItem:
    """
    Represents a single memory item stored in the memory system.
    
    A memory item contains the actual content of the memory, along with
    metadata such as its type, importance, creation time, etc.
    """
    
    def __init__(
        self,
        content: Any,
        memory_type: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        """
        Initialize a new memory item.
        
        Args:
            content: The content of the memory. Can be text, a dictionary, 
                    or any serializable data.
            memory_type: The type of memory (e.g., "fact", "conversation", "task").
            importance: A value between 0 and 1 indicating the importance of the memory.
            metadata: Additional metadata about the memory.
            id: Optional ID for the memory (generated if not provided).
            created_at: Optional creation timestamp (current time if not provided).
        """
        self.id = id or str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type
        self.importance = max(0.0, min(1.0, importance))  # Clamp between 0 and 1
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()
        self.last_accessed = self.created_at
        self.access_count = 0
        
        logger.debug(f"Created memory item: {self.id} of type {memory_type}")
    
    def access(self) -> None:
        """
        Record an access to this memory item.
        Updates the last_accessed timestamp and increments access_count.
        """
        self.last_accessed = datetime.now()
        self.access_count += 1
        logger.debug(f"Accessed memory item: {self.id} (count: {self.access_count})")
    
    def update_importance(self, new_importance: float) -> None:
        """
        Update the importance of this memory item.
        
        Args:
            new_importance: The new importance value (0-1).
        """
        self.importance = max(0.0, min(1.0, new_importance))
        logger.debug(f"Updated importance of memory item: {self.id} to {self.importance}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the memory item to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the memory item.
        """
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        """
        Create a memory item from a dictionary.
        
        Args:
            data: A dictionary representation of a memory item.
            
        Returns:
            A new MemoryItem instance.
        """
        # Handle datetime strings
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        
        memory = cls(
            content=data["content"],
            memory_type=data["memory_type"],
            importance=data["importance"],
            metadata=data.get("metadata", {}),
            id=data["id"],
            created_at=created_at
        )
        
        # Set additional fields if they exist
        if "last_accessed" in data:
            memory.last_accessed = datetime.fromisoformat(data["last_accessed"])
        if "access_count" in data:
            memory.access_count = data["access_count"]
        
        return memory
    
    def __str__(self) -> str:
        """
        Get a string representation of the memory item.
        
        Returns:
            A string representation of the memory item.
        """
        content_str = str(self.content)
        if len(content_str) > 50:
            content_str = content_str[:50] + "..."
        
        return f"Memory({self.id}, type={self.memory_type}, content={content_str})" 