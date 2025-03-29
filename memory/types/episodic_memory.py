"""
Episodic Memory Module

This module provides an episodic memory implementation that stores sequences
of related events or experiences with temporal context.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import sqlite3
from uuid import uuid4

from ..core.memory_system import MemorySystem
from ..core.memory_item import MemoryItem
from ..storage.in_memory_storage import InMemoryStorage

logger = logging.getLogger(__name__)


class Episode:
    """
    Represents a sequence of related memory items forming an episode.
    
    An episode is a collection of memory items that are related by a common
    context or theme, and typically occur within a specific time frame.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        title: str = "",
        description: str = "",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a new episode.
        
        Args:
            id: Optional ID for the episode (generated if not provided)
            title: The title of the episode
            description: A description of the episode
            importance: The importance of the episode (0-1)
            metadata: Additional metadata for the episode
        """
        self.id = id or str(uuid4())
        self.title = title
        self.description = description
        self.importance = max(0.0, min(1.0, importance))
        self.created_at = datetime.now()
        self.last_accessed = self.created_at
        self.access_count = 0
        self.metadata = metadata or {}
        self.memory_ids = []  # IDs of memories in this episode
        self.is_active = True  # Whether this episode is currently active
        
    def add_memory(self, memory_id: str) -> None:
        """
        Add a memory to this episode.
        
        Args:
            memory_id: The ID of the memory to add
        """
        if memory_id not in self.memory_ids:
            self.memory_ids.append(memory_id)
            
    def access(self) -> None:
        """
        Record an access to this episode.
        Updates the last_accessed timestamp and increments access_count.
        """
        self.last_accessed = datetime.now()
        self.access_count += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the episode to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the episode
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "metadata": self.metadata,
            "memory_ids": self.memory_ids,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        """
        Create an episode from a dictionary.
        
        Args:
            data: A dictionary representation of an episode
            
        Returns:
            A new Episode instance
        """
        episode = cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            importance=data["importance"],
            metadata=data.get("metadata", {})
        )
        
        episode.created_at = datetime.fromisoformat(data["created_at"])
        episode.last_accessed = datetime.fromisoformat(data["last_accessed"])
        episode.access_count = data["access_count"]
        episode.memory_ids = data.get("memory_ids", [])
        episode.is_active = data.get("is_active", True)
        
        return episode


class EpisodicStorage:
    """
    Storage backend for episodic memories.
    
    This class provides persistent storage for episodes and their
    associated memories using SQLite.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize a new episodic storage backend.
        
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
        
        # Create episodes table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            importance REAL NOT NULL,
            created_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            access_count INTEGER NOT NULL,
            metadata TEXT,
            is_active INTEGER NOT NULL
        )
        ''')
        
        # Create episode_memories table (for many-to-many relationship)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS episode_memories (
            episode_id TEXT NOT NULL,
            memory_id TEXT NOT NULL,
            added_at TEXT NOT NULL,
            PRIMARY KEY (episode_id, memory_id),
            FOREIGN KEY (episode_id) REFERENCES episodes (id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episode_importance ON episodes(importance)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episode_active ON episodes(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episode_memories_memory ON episode_memories(memory_id)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Initialized episodic storage at {self.db_path}")
    
    def store_episode(self, episode: Episode) -> bool:
        """
        Store an episode in the database.
        
        Args:
            episode: The episode to store
            
        Returns:
            True if stored successfully, False on error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store episode
            cursor.execute('''
            INSERT OR REPLACE INTO episodes
            (id, title, description, importance, created_at, last_accessed, 
             access_count, metadata, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                episode.id,
                episode.title,
                episode.description,
                episode.importance,
                episode.created_at.isoformat(),
                episode.last_accessed.isoformat(),
                episode.access_count,
                json.dumps(episode.metadata),
                1 if episode.is_active else 0
            ))
            
            # Store memory associations
            # First, delete any existing associations
            cursor.execute('DELETE FROM episode_memories WHERE episode_id = ?', (episode.id,))
            
            # Then insert the current associations
            now = datetime.now().isoformat()
            for memory_id in episode.memory_ids:
                cursor.execute('''
                INSERT INTO episode_memories (episode_id, memory_id, added_at)
                VALUES (?, ?, ?)
                ''', (episode.id, memory_id, now))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Stored episode in database: {episode.id}")
            return True
        except Exception as e:
            logger.error(f"Error storing episode in database: {e}")
            return False
    
    def retrieve_episode(self, episode_id: str) -> Optional[Episode]:
        """
        Retrieve an episode from the database.
        
        Args:
            episode_id: The ID of the episode to retrieve
            
        Returns:
            The episode if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get episode
            cursor.execute('''
            SELECT id, title, description, importance, created_at, 
                   last_accessed, access_count, metadata, is_active
            FROM episodes
            WHERE id = ?
            ''', (episode_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.debug(f"Episode not found in database: {episode_id}")
                conn.close()
                return None
            
            # Convert row to episode
            episode_data = {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "importance": row[3],
                "created_at": row[4],
                "last_accessed": row[5],
                "access_count": row[6],
                "metadata": json.loads(row[7]) if row[7] else {},
                "is_active": bool(row[8])
            }
            
            # Get memory IDs for this episode
            cursor.execute('''
            SELECT memory_id FROM episode_memories
            WHERE episode_id = ?
            ''', (episode_id,))
            
            memory_ids = [r[0] for r in cursor.fetchall()]
            episode_data["memory_ids"] = memory_ids
            
            conn.close()
            
            episode = Episode.from_dict(episode_data)
            logger.debug(f"Retrieved episode from database: {episode_id}")
            return episode
        except Exception as e:
            logger.error(f"Error retrieving episode from database: {e}")
            return None
    
    def list_episodes(
        self,
        active_only: bool = False,
        min_importance: float = 0.0,
        limit: int = 100,
        offset: int = 0
    ) -> List[Episode]:
        """
        List episodes from the database.
        
        Args:
            active_only: Whether to only include active episodes
            min_importance: Minimum importance threshold
            limit: Maximum number of episodes to return
            offset: Starting offset for pagination
            
        Returns:
            A list of episodes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = '''
            SELECT id, title, description, importance, created_at, 
                   last_accessed, access_count, metadata, is_active
            FROM episodes
            WHERE importance >= ?
            '''
            params = [min_importance]
            
            if active_only:
                query += " AND is_active = 1"
            
            query += " ORDER BY importance DESC, last_accessed DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            episodes = []
            for row in rows:
                episode_data = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "importance": row[3],
                    "created_at": row[4],
                    "last_accessed": row[5],
                    "access_count": row[6],
                    "metadata": json.loads(row[7]) if row[7] else {},
                    "is_active": bool(row[8])
                }
                
                # Get memory IDs for this episode
                cursor.execute('''
                SELECT memory_id FROM episode_memories
                WHERE episode_id = ?
                ''', (episode_data["id"],))
                
                memory_ids = [r[0] for r in cursor.fetchall()]
                episode_data["memory_ids"] = memory_ids
                
                episodes.append(Episode.from_dict(episode_data))
            
            conn.close()
            
            logger.debug(f"Listed {len(episodes)} episodes from database")
            return episodes
        except Exception as e:
            logger.error(f"Error listing episodes from database: {e}")
            return []
    
    def delete_episode(self, episode_id: str) -> bool:
        """
        Delete an episode from the database.
        
        Args:
            episode_id: The ID of the episode to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete episode (will cascade to episode_memories due to foreign key)
            cursor.execute('DELETE FROM episodes WHERE id = ?', (episode_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                logger.debug(f"Deleted episode from database: {episode_id}")
            else:
                logger.debug(f"Episode not found for deletion: {episode_id}")
            
            return deleted
        except Exception as e:
            logger.error(f"Error deleting episode from database: {e}")
            return False
    
    def get_episodes_for_memory(self, memory_id: str) -> List[str]:
        """
        Get all episode IDs that contain a specific memory.
        
        Args:
            memory_id: The ID of the memory to find episodes for
            
        Returns:
            List of episode IDs
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT episode_id FROM episode_memories
            WHERE memory_id = ?
            ''', (memory_id,))
            
            episode_ids = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            return episode_ids
        except Exception as e:
            logger.error(f"Error getting episodes for memory: {e}")
            return []
    
    def clear(self) -> bool:
        """
        Clear all episodes from the database.
        
        Returns:
            True if cleared successfully, False on error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM episode_memories')
            cursor.execute('DELETE FROM episodes')
            
            conn.commit()
            conn.close()
            
            logger.warning("Cleared all episodes from database")
            return True
        except Exception as e:
            logger.error(f"Error clearing episodes from database: {e}")
            return False


class EpisodicMemory:
    """
    Episodic memory implementation that stores sequences of related memories.
    
    This class provides a system for organizing memories into episodes,
    which represent sequences of related events or experiences.
    """
    
    def __init__(
        self,
        memory_system: MemorySystem,
        db_path: str = "data/memory/episodic.db",
        max_active_episodes: int = 5
    ):
        """
        Initialize a new episodic memory system.
        
        Args:
            memory_system: The central memory system to integrate with
            db_path: Path to the SQLite database file
            max_active_episodes: Maximum number of concurrently active episodes
        """
        self.memory_system = memory_system
        self.storage = EpisodicStorage(db_path)
        self.max_active_episodes = max_active_episodes
        self._active_episodes = {}  # Cache of active episodes
        
        # Load active episodes
        self._load_active_episodes()
        
        logger.info(
            f"Initialized episodic memory with db_path={db_path}, "
            f"max_active_episodes={max_active_episodes}"
        )
    
    def _load_active_episodes(self) -> None:
        """
        Load active episodes from storage into memory.
        """
        episodes = self.storage.list_episodes(active_only=True)
        for episode in episodes:
            self._active_episodes[episode.id] = episode
            
        if len(self._active_episodes) > self.max_active_episodes:
            logger.warning(
                f"Found {len(self._active_episodes)} active episodes, "
                f"which exceeds the maximum of {self.max_active_episodes}"
            )
    
    def create_episode(
        self,
        title: str,
        description: str = "",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        initial_memories: Optional[List[str]] = None
    ) -> str:
        """
        Create a new episode.
        
        Args:
            title: The title of the episode
            description: A description of the episode
            importance: The importance of the episode (0-1)
            metadata: Additional metadata for the episode
            initial_memories: Optional list of memory IDs to add to the episode
            
        Returns:
            The ID of the created episode
        """
        # Create the episode
        episode = Episode(
            title=title,
            description=description,
            importance=importance,
            metadata=metadata
        )
        
        # Add initial memories if provided
        if initial_memories:
            for memory_id in initial_memories:
                # Verify the memory exists
                if self.memory_system.get_memory(memory_id):
                    episode.add_memory(memory_id)
        
        # Store the episode
        self.storage.store_episode(episode)
        
        # Add to active episodes if we have room
        if len(self._active_episodes) < self.max_active_episodes:
            self._active_episodes[episode.id] = episode
        else:
            # Otherwise, make it inactive
            episode.is_active = False
            self.storage.store_episode(episode)
            logger.info(
                f"Created episode {episode.id} as inactive "
                f"because max_active_episodes limit reached"
            )
        
        logger.info(f"Created episode: {episode.id} - {title}")
        return episode.id
    
    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """
        Get an episode by its ID.
        
        Args:
            episode_id: The ID of the episode to retrieve
            
        Returns:
            The episode if found, None otherwise
        """
        # Check cache first
        if episode_id in self._active_episodes:
            episode = self._active_episodes[episode_id]
            episode.access()
            return episode
        
        # Not in cache, try storage
        episode = self.storage.retrieve_episode(episode_id)
        if episode:
            episode.access()
            # Update access count in storage
            self.storage.store_episode(episode)
        
        return episode
    
    def add_memory_to_episode(
        self,
        episode_id: str,
        memory_id: str
    ) -> bool:
        """
        Add a memory to an episode.
        
        Args:
            episode_id: The ID of the episode
            memory_id: The ID of the memory to add
            
        Returns:
            True if added successfully, False otherwise
        """
        # Verify the memory exists
        memory = self.memory_system.get_memory(memory_id)
        if not memory:
            logger.warning(f"Cannot add non-existent memory {memory_id} to episode")
            return False
        
        # Get the episode
        episode = self.get_episode(episode_id)
        if not episode:
            logger.warning(f"Cannot add memory to non-existent episode {episode_id}")
            return False
        
        # Add the memory
        episode.add_memory(memory_id)
        
        # Update the episode in storage
        success = self.storage.store_episode(episode)
        
        # Update cache if needed
        if success and episode.is_active:
            self._active_episodes[episode.id] = episode
        
        logger.debug(f"Added memory {memory_id} to episode {episode_id}")
        return success
    
    def set_episode_active(self, episode_id: str, active: bool = True) -> bool:
        """
        Set whether an episode is active.
        
        Args:
            episode_id: The ID of the episode
            active: Whether the episode should be active
            
        Returns:
            True if updated successfully, False otherwise
        """
        # Get the episode
        episode = self.get_episode(episode_id)
        if not episode:
            logger.warning(f"Cannot update non-existent episode {episode_id}")
            return False
        
        # Check if we're trying to activate too many episodes
        if active and episode.is_active == False:
            if len(self._active_episodes) >= self.max_active_episodes:
                logger.warning(
                    f"Cannot activate episode {episode_id} "
                    f"because max_active_episodes limit reached"
                )
                return False
        
        # Update the episode
        episode.is_active = active
        
        # Update the episode in storage
        success = self.storage.store_episode(episode)
        
        # Update cache
        if success:
            if active:
                self._active_episodes[episode.id] = episode
            elif episode.id in self._active_episodes:
                del self._active_episodes[episode.id]
        
        logger.debug(f"Set episode {episode_id} active={active}")
        return success
    
    def get_active_episodes(self) -> List[Episode]:
        """
        Get all currently active episodes.
        
        Returns:
            List of active episodes
        """
        return list(self._active_episodes.values())
    
    def get_memories_for_episode(self, episode_id: str) -> List[MemoryItem]:
        """
        Get all memories in an episode.
        
        Args:
            episode_id: The ID of the episode
            
        Returns:
            List of memory items in the episode
        """
        # Get the episode
        episode = self.get_episode(episode_id)
        if not episode:
            logger.warning(f"Cannot get memories for non-existent episode {episode_id}")
            return []
        
        # Get the memories
        memories = []
        for memory_id in episode.memory_ids:
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                memories.append(memory)
        
        return memories
    
    def get_episodes_for_memory(self, memory_id: str) -> List[Episode]:
        """
        Get all episodes that contain a specific memory.
        
        Args:
            memory_id: The ID of the memory
            
        Returns:
            List of episodes containing the memory
        """
        # Verify the memory exists
        memory = self.memory_system.get_memory(memory_id)
        if not memory:
            logger.warning(f"Cannot get episodes for non-existent memory {memory_id}")
            return []
        
        # Get the episode IDs
        episode_ids = self.storage.get_episodes_for_memory(memory_id)
        
        # Get the episodes
        episodes = []
        for episode_id in episode_ids:
            episode = self.get_episode(episode_id)
            if episode:
                episodes.append(episode)
        
        return episodes
    
    def search_episodes(
        self,
        query: str,
        min_importance: float = 0.0,
        active_only: bool = False,
        limit: int = 10
    ) -> List[Episode]:
        """
        Search for episodes by title or description.
        
        Args:
            query: The search query
            min_importance: Minimum importance threshold
            active_only: Whether to only include active episodes
            limit: Maximum number of episodes to return
            
        Returns:
            List of matching episodes
        """
        # Get all episodes that meet the criteria
        episodes = self.storage.list_episodes(
            active_only=active_only,
            min_importance=min_importance,
            limit=1000  # Get a lot, we'll filter and limit later
        )
        
        # Filter by query
        query = query.lower()
        matching_episodes = []
        
        for episode in episodes:
            if (query in episode.title.lower() or
                query in episode.description.lower()):
                matching_episodes.append(episode)
                
                # Stop if we've reached the limit
                if len(matching_episodes) >= limit:
                    break
        
        return matching_episodes
    
    def delete_episode(self, episode_id: str) -> bool:
        """
        Delete an episode.
        
        Args:
            episode_id: The ID of the episode to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Remove from cache if present
        if episode_id in self._active_episodes:
            del self._active_episodes[episode_id]
        
        # Delete from storage
        return self.storage.delete_episode(episode_id)
    
    def clear_all(self) -> bool:
        """
        Clear all episodes.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        # Clear cache
        self._active_episodes.clear()
        
        # Clear storage
        return self.storage.clear()
    
    def get_episode_summary(self, episode_id: str) -> Dict[str, Any]:
        """
        Get a summary of an episode.
        
        Args:
            episode_id: The ID of the episode
            
        Returns:
            Dictionary with episode summary information
        """
        # Get the episode
        episode = self.get_episode(episode_id)
        if not episode:
            return {"error": f"Episode {episode_id} not found"}
        
        # Get the memories
        memories = self.get_memories_for_episode(episode_id)
        
        # Create summary
        return {
            "id": episode.id,
            "title": episode.title,
            "description": episode.description,
            "importance": episode.importance,
            "created_at": episode.created_at.isoformat(),
            "is_active": episode.is_active,
            "memory_count": len(memories),
            "first_memory": memories[0].content if memories else None,
            "last_memory": memories[-1].content if memories else None
        } 