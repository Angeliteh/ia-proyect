"""
Long-Term Memory Module

This module provides a long-term memory implementation that stores important
memories persistently and provides methods for retrieval and management.
"""

import logging
import json
import os
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import sqlite3

from ..core.memory_system import MemorySystem
from ..core.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """
    SQLite storage backend for long-term memories.
    
    This class provides persistent storage for memory items using SQLite.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize a new SQLite storage backend.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """
        Initialize the SQLite database with the necessary tables.
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memories table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            importance REAL NOT NULL,
            created_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            access_count INTEGER NOT NULL,
            metadata TEXT,
            related_memories TEXT
        )
        ''')
        
        # Create index on memory_type for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
        ''')
        
        # Create index on source for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_source ON memories(source)
        ''')
        
        # Create index on importance for faster queries
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Initialized SQLite database at {self.db_path}")
    
    def store(self, memory: MemoryItem) -> bool:
        """
        Store a memory item in the SQLite database.
        
        Args:
            memory: The memory item to store
            
        Returns:
            True if stored successfully, False on error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener source de los metadatos o usar un valor por defecto
            source = memory.metadata.get("source", "unknown")
            
            # Convert memory to row format
            row = (
                memory.id,
                json.dumps(memory.content),
                source,  # Usar el source obtenido de los metadatos
                memory.memory_type,
                memory.importance,
                memory.created_at.isoformat(),
                memory.last_accessed.isoformat(),
                memory.access_count,
                json.dumps(memory.metadata),
                json.dumps(getattr(memory, 'related_memories', []))
            )
            
            # Insert or replace
            cursor.execute('''
            INSERT OR REPLACE INTO memories
            (id, content, source, memory_type, importance, created_at, last_accessed, 
             access_count, metadata, related_memories)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', row)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored memory in SQLite: {memory.id}")
            return True
        except Exception as e:
            logger.error(f"Error storing memory in SQLite: {e}")
            return False
    
    def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory item from the SQLite database.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory item if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, content, source, memory_type, importance, created_at, 
                   last_accessed, access_count, metadata, related_memories
            FROM memories
            WHERE id = ?
            ''', (memory_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.debug(f"Memory not found in SQLite: {memory_id}")
                return None
            
            # Prepare metadata with source
            metadata = json.loads(row[8]) if row[8] else {}
            metadata["source"] = row[2]  # Add source to metadata
            
            # Convert row to memory item
            memory_data = {
                "id": row[0],
                "content": json.loads(row[1]),
                "memory_type": row[3],
                "importance": row[4],
                "metadata": metadata,
                "created_at": row[5],
                "last_accessed": row[6],
                "access_count": row[7],
            }
            
            memory = MemoryItem.from_dict(memory_data)
            logger.debug(f"Retrieved memory from SQLite: {memory_id}")
            return memory
        except Exception as e:
            logger.error(f"Error retrieving memory from SQLite: {e}")
            return None
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory item from the SQLite database.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if deleted successfully, False on error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM memories
            WHERE id = ?
            ''', (memory_id,))
            
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                logger.debug(f"Deleted memory from SQLite: {memory_id}")
            else:
                logger.debug(f"Memory not found for deletion in SQLite: {memory_id}")
            
            return deleted
        except Exception as e:
            logger.error(f"Error deleting memory from SQLite: {e}")
            return False
    
    def list(self, limit: int = 100, offset: int = 0) -> List[MemoryItem]:
        """
        List memory items from the SQLite database.
        
        Args:
            limit: Maximum number of items to return
            offset: Starting offset for pagination
            
        Returns:
            A list of memory items
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, content, source, memory_type, importance, created_at, 
                   last_accessed, access_count, metadata, related_memories
            FROM memories
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memory_data = {
                    "id": row[0],
                    "content": json.loads(row[1]),
                    "source": row[2],
                    "memory_type": row[3],
                    "importance": row[4],
                    "created_at": row[5],
                    "last_accessed": row[6],
                    "access_count": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {},
                    "related_memories": json.loads(row[9]) if row[9] else []
                }
                
                memory = MemoryItem.from_dict(memory_data)
                memories.append(memory)
            
            logger.debug(f"Listed {len(memories)} memories from SQLite")
            return memories
        except Exception as e:
            logger.error(f"Error listing memories from SQLite: {e}")
            return []
    
    def clear(self) -> bool:
        """
        Clear all memory items from the SQLite database.
        
        Returns:
            True if cleared successfully, False on error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM memories')
            
            count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Cleared {count} memories from SQLite database")
            return True
        except Exception as e:
            logger.error(f"Error clearing memories from SQLite: {e}")
            return False
    
    def search(self, query: Dict[str, Any], limit: int = 10) -> List[MemoryItem]:
        """
        Search for memory items in the SQLite database.
        
        Args:
            query: A dictionary of search parameters
            limit: Maximum number of items to return
            
        Returns:
            A list of memory items matching the query
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build SQL query
            sql_parts = ["SELECT id, content, source, memory_type, importance, created_at, " 
                        "last_accessed, access_count, metadata, related_memories "
                        "FROM memories WHERE 1=1"]
            params = []
            
            for key, value in query.items():
                if key == "memory_type":
                    sql_parts.append("AND memory_type = ?")
                    params.append(value)
                elif key == "source":
                    sql_parts.append("AND source = ?")
                    params.append(value)
                elif key == "min_importance":
                    sql_parts.append("AND importance >= ?")
                    params.append(value)
                elif key == "max_importance":
                    sql_parts.append("AND importance <= ?")
                    params.append(value)
                elif key == "created_after":
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    sql_parts.append("AND created_at >= ?")
                    params.append(value)
                elif key == "created_before":
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    sql_parts.append("AND created_at <= ?")
                    params.append(value)
            
            # Add order and limit
            sql_parts.append("ORDER BY importance DESC, created_at DESC LIMIT ?")
            params.append(limit)
            
            # Execute query
            sql = " ".join(sql_parts)
            cursor.execute(sql, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memory_data = {
                    "id": row[0],
                    "content": json.loads(row[1]),
                    "source": row[2],
                    "memory_type": row[3],
                    "importance": row[4],
                    "created_at": row[5],
                    "last_accessed": row[6],
                    "access_count": row[7],
                    "metadata": json.loads(row[8]) if row[8] else {},
                    "related_memories": json.loads(row[9]) if row[9] else []
                }
                
                memory = MemoryItem.from_dict(memory_data)
                memories.append(memory)
            
            logger.debug(f"Found {len(memories)} memories in SQLite matching query")
            return memories
        except Exception as e:
            logger.error(f"Error searching memories in SQLite: {e}")
            return []
    
    def count(self) -> int:
        """
        Count the number of memory items in the SQLite database.
        
        Returns:
            The number of memory items
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM memories')
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return count
        except Exception as e:
            logger.error(f"Error counting memories in SQLite: {e}")
            return 0


class LongTermMemory:
    """
    Long-term memory implementation with persistent storage.
    
    This class provides a persistent memory store for important memories
    that should be retained for longer periods.
    """
    
    def __init__(
        self,
        memory_system: MemorySystem,
        db_path: str = "data/memory/long_term.db",
        min_importance: float = 0.7
    ):
        """
        Initialize a new long-term memory.
        
        Args:
            memory_system: The central memory system to integrate with
            db_path: Path to the SQLite database file
            min_importance: Minimum importance threshold for memories to be stored
        """
        self.memory_system = memory_system
        self.storage = SQLiteStorage(db_path)
        self.min_importance = min_importance
        
        # Instead of registering with the memory system, we'll use our storage directly
        
        logger.info(
            f"Initialized long-term memory with db_path={db_path}, "
            f"min_importance={min_importance}"
        )
    
    def add(
        self,
        content: Any,
        source: str,
        importance: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new item to long-term memory.
        
        Args:
            content: The content of the memory
            source: The source of the memory
            importance: The importance of the memory (0-1)
            metadata: Additional metadata for the memory
            
        Returns:
            The ID of the created memory
        """
        # Ensure importance meets minimum threshold
        if importance < self.min_importance:
            importance = self.min_importance
        
        # Include source in metadata
        full_metadata = metadata or {}
        full_metadata["source"] = source
            
        # Creamos directamente la memoria en el sistema base
        memory_id = self.memory_system.add_memory(
            content=content,
            memory_type="long_term",  # Forzar el tipo a long_term
            importance=importance,
            metadata=full_metadata
        )
        
        # También guardamos la memoria en el SQLiteStorage para que sea visible
        # en las estadísticas y búsquedas específicas de long_term_memory
        memory = self.memory_system.get_memory(memory_id)
        if memory:
            self.storage.store(memory)
            logger.debug(f"Memory {memory_id} also stored in SQLiteStorage")
        
        return memory_id
    
    def promote_from_short_term(self, memory_id: str, new_importance: Optional[float] = None) -> Optional[str]:
        """
        Promote a memory from short-term to long-term storage.
        
        Args:
            memory_id: The ID of the short-term memory to promote
            new_importance: Optional new importance value (0-1)
            
        Returns:
            The ID of the new long-term memory, or None if promotion failed
        """
        # Get the original memory
        original = self.memory_system.get_memory(memory_id)
        if not original:
            logger.warning(f"Cannot promote unknown memory: {memory_id}")
            return None
            
        if original.memory_type != "short_term":
            logger.warning(f"Can only promote short-term memories, got: {original.memory_type}")
            return None
        
        # Set importance
        importance = new_importance if new_importance is not None else max(self.min_importance, original.importance)
        
        # Create new long-term memory
        memory = MemoryItem(
            content=original.content,
            source=original.source,
            memory_type="long_term",
            importance=importance,
            metadata=original.metadata
        )
        
        # Add related memories
        for related_id in original.related_memories:
            memory.link_to(related_id)
        
        # Add to memory system and forget the original
        new_id = self.memory_system.add_memory(memory)
        self.memory_system.forget_memory(memory_id)
        
        logger.info(f"Promoted memory from short-term to long-term: {memory_id} -> {new_id}")
        return new_id
    
    def get_by_importance(
        self,
        min_importance: float = 0.0,
        max_importance: float = 1.0,
        limit: int = 10
    ) -> List[MemoryItem]:
        """
        Get memories within an importance range.
        
        Args:
            min_importance: Minimum importance value (0-1)
            max_importance: Maximum importance value (0-1)
            limit: Maximum number of memories to return
            
        Returns:
            A list of memory items within the importance range
        """
        return self.memory_system.search_by_importance(
            min_importance=min_importance,
            max_importance=max_importance,
            memory_type="long_term",
            limit=limit
        )
    
    def search(self, query: Dict[str, Any], limit: int = 10) -> List[MemoryItem]:
        """
        Search for memories matching the query.
        
        Args:
            query: Dictionary of search parameters
            limit: Maximum number of memories to return
            
        Returns:
            A list of memory items matching the query
        """
        # Add memory_type to query
        query["memory_type"] = "long_term"
        
        # Use the storage backend to search
        return self.storage.search(query, limit=limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the long-term memory.
        
        Returns:
            A dictionary with memory statistics
        """
        try:
            # Get all memories tracked in long-term memory
            conn = sqlite3.connect(self.storage.db_path)
            cursor = conn.cursor()
            
            # Count total memories
            cursor.execute('SELECT COUNT(*) FROM memories WHERE memory_type = "long_term"')
            total_count = cursor.fetchone()[0] or 0
            
            # Get count by source
            cursor.execute('''
            SELECT source, COUNT(*) FROM memories
            WHERE memory_type = 'long_term'
            GROUP BY source
            ''')
            
            source_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                "total_memories": total_count,
                "sources": source_counts
            }
        except Exception as e:
            logger.error(f"Error getting long-term memory stats: {e}")
            # Return default stats if there's an error
            return {
                "total_memories": 0,
                "sources": {}
            } 