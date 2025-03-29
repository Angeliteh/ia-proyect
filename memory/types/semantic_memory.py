"""
Semantic Memory Module

This module provides the SemanticMemory class for storing factual knowledge
and concepts in a structured format that enables semantic search and retrieval.
"""

import logging
import json
import sqlite3
import os
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime
import uuid

from ..core.memory_system import MemorySystem
from ..core.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class Fact:
    """
    Represents a single fact or piece of knowledge in semantic memory.
    
    A fact consists of a subject, predicate, and object, similar to an RDF triple,
    plus additional metadata for managing and querying the knowledge base.
    """
    
    def __init__(
        self,
        subject: str,
        predicate: str,
        object_: Any,
        confidence: float = 1.0,
        source: Optional[str] = None,
        memory_id: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_accessed: Optional[datetime] = None,
        access_count: int = 0
    ):
        """
        Initialize a new fact.
        
        Args:
            subject: The entity that the fact is about
            predicate: The relation or property
            object_: The value or related entity
            confidence: How confident we are that this fact is true (0.0-1.0)
            source: Where this fact came from
            memory_id: ID of the memory item this fact is associated with (if any)
            id: Optional ID for the fact (generated if not provided)
            created_at: When this fact was created (current time if not provided)
            last_accessed: When this fact was last accessed (created_at if not provided)
            access_count: Number of times this fact has been accessed
        """
        self.id = id or str(uuid.uuid4())
        self.subject = subject
        self.predicate = predicate
        self.object = object_
        self.confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        self.source = source
        self.memory_id = memory_id
        self.created_at = created_at or datetime.now()
        self.last_accessed = last_accessed or self.created_at
        self.access_count = access_count
        
    def access(self) -> None:
        """Record an access to this fact, updating last_accessed and access_count."""
        self.last_accessed = datetime.now()
        self.access_count += 1
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the fact to a dictionary for serialization."""
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "source": self.source,
            "memory_id": self.memory_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Fact':
        """Create a fact from a dictionary."""
        # Handle datetime strings
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else None
        last_accessed = datetime.fromisoformat(data["last_accessed"]) if "last_accessed" in data else None
        
        return cls(
            subject=data["subject"],
            predicate=data["predicate"],
            object_=data["object"],
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
            memory_id=data.get("memory_id"),
            id=data["id"],
            created_at=created_at,
            last_accessed=last_accessed,
            access_count=data.get("access_count", 0)
        )
    
    def __str__(self) -> str:
        """Get a string representation of the fact."""
        obj_str = str(self.object)
        if isinstance(self.object, dict):
            obj_str = json.dumps(self.object, ensure_ascii=False)
        elif isinstance(self.object, (list, tuple)):
            obj_str = str(self.object)
            
        return f"{self.subject} {self.predicate} {obj_str}"


class SemanticStorage:
    """
    Storage backend for semantic memory using SQLite.
    
    Provides persistent storage for facts with efficient querying capabilities.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the semantic storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()
        logger.info(f"Initialized semantic storage at {db_path}")
    
    def _init_db(self) -> None:
        """Initialize the database schema if it doesn't exist."""
        cursor = self.conn.cursor()
        
        # Create the facts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            object_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            source TEXT,
            memory_id TEXT,
            created_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            access_count INTEGER NOT NULL
        )
        ''')
        
        # Create indices for efficient querying
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subject ON facts(subject)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_predicate ON facts(predicate)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_subject_predicate ON facts(subject, predicate)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_id ON facts(memory_id)')
        
        self.conn.commit()
    
    def store_fact(self, fact: Fact) -> bool:
        """
        Store a fact in the database.
        
        Args:
            fact: The fact to store
            
        Returns:
            True if successful, False otherwise
        """
        cursor = self.conn.cursor()
        
        # Determine the type of the object for proper serialization
        object_type = type(fact.object).__name__
        
        # Serialize the object based on its type
        if isinstance(fact.object, (dict, list, tuple)):
            object_str = json.dumps(fact.object, ensure_ascii=False)
        else:
            object_str = str(fact.object)
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO facts
            (id, subject, predicate, object, object_type, confidence, source, memory_id, 
             created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fact.id,
                fact.subject,
                fact.predicate,
                object_str,
                object_type,
                fact.confidence,
                fact.source,
                fact.memory_id,
                fact.created_at.isoformat(),
                fact.last_accessed.isoformat(),
                fact.access_count
            ))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing fact: {e}")
            self.conn.rollback()
            return False
    
    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """
        Retrieve a fact by its ID.
        
        Args:
            fact_id: The ID of the fact to retrieve
            
        Returns:
            The fact if found, None otherwise
        """
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM facts WHERE id = ?', (fact_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_fact(row)
    
    def _row_to_fact(self, row: Tuple) -> Fact:
        """Convert a database row to a Fact object."""
        id, subject, predicate, object_str, object_type, confidence, source, memory_id, \
            created_at, last_accessed, access_count = row
        
        # Deserialize the object based on its type
        if object_type == 'dict':
            object_ = json.loads(object_str)
        elif object_type == 'list':
            object_ = json.loads(object_str)
        elif object_type == 'tuple':
            object_ = tuple(json.loads(object_str))
        elif object_type == 'int':
            object_ = int(object_str)
        elif object_type == 'float':
            object_ = float(object_str)
        elif object_type == 'bool':
            object_ = object_str.lower() == 'true'
        else:
            object_ = object_str
        
        return Fact(
            id=id,
            subject=subject,
            predicate=predicate,
            object_=object_,
            confidence=confidence,
            source=source,
            memory_id=memory_id,
            created_at=datetime.fromisoformat(created_at),
            last_accessed=datetime.fromisoformat(last_accessed),
            access_count=access_count
        )
    
    def delete_fact(self, fact_id: str) -> bool:
        """
        Delete a fact by its ID.
        
        Args:
            fact_id: The ID of the fact to delete
            
        Returns:
            True if successful, False otherwise
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('DELETE FROM facts WHERE id = ?', (fact_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting fact: {e}")
            self.conn.rollback()
            return False
    
    def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_: Optional[Any] = None,
        min_confidence: Optional[float] = None,
        source: Optional[str] = None,
        memory_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Fact]:
        """
        Query facts based on various criteria.
        
        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            object_: Filter by object
            min_confidence: Filter by minimum confidence
            source: Filter by source
            memory_id: Filter by associated memory ID
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            A list of facts matching the criteria
        """
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM facts WHERE 1=1'
        params = []
        
        if subject is not None:
            query += ' AND subject = ?'
            params.append(subject)
        
        if predicate is not None:
            query += ' AND predicate = ?'
            params.append(predicate)
        
        if object_ is not None:
            if isinstance(object_, (dict, list, tuple)):
                object_str = json.dumps(object_, ensure_ascii=False)
            else:
                object_str = str(object_)
            
            query += ' AND object = ?'
            params.append(object_str)
        
        if min_confidence is not None:
            query += ' AND confidence >= ?'
            params.append(min_confidence)
        
        if source is not None:
            query += ' AND source = ?'
            params.append(source)
        
        if memory_id is not None:
            query += ' AND memory_id = ?'
            params.append(memory_id)
        
        query += ' ORDER BY confidence DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_fact(row) for row in rows]
    
    def clear(self) -> bool:
        """
        Clear all facts from the database.
        
        Returns:
            True if successful, False otherwise
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('DELETE FROM facts')
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing facts: {e}")
            self.conn.rollback()
            return False
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __del__(self) -> None:
        """Ensure the database connection is closed when the object is deleted."""
        self.close()


class SemanticMemory:
    """
    Semantic memory system for storing and retrieving factual knowledge.
    
    This class provides methods for adding, querying, and managing facts
    in a structured knowledge base, with integration with the core memory system.
    """
    
    def __init__(
        self,
        memory_system: MemorySystem,
        db_path: str = "data/memory/semantic.db",
        min_confidence: float = 0.0
    ):
        """
        Initialize a new semantic memory system.
        
        Args:
            memory_system: The core memory system to use for storage
            db_path: Path to the SQLite database file for persistent storage
            min_confidence: Minimum confidence threshold for retrieving facts (0.0-1.0)
        """
        self.memory_system = memory_system
        self.storage = SemanticStorage(db_path)
        self.min_confidence = min_confidence
        
        logger.info(f"Initialized semantic memory with db_path={db_path}, min_confidence={min_confidence}")
    
    def add_fact(
        self,
        subject: str,
        predicate: str,
        object_: Any,
        confidence: float = 1.0,
        source: Optional[str] = None,
        create_memory: bool = True,
        memory_type: str = "fact",
        memory_importance: float = 0.7
    ) -> str:
        """
        Add a new fact to semantic memory.
        
        Args:
            subject: The entity that the fact is about
            predicate: The relation or property
            object_: The value or related entity
            confidence: How confident we are that this fact is true (0.0-1.0)
            source: Where this fact came from
            create_memory: Whether to create a memory item for this fact
            memory_type: Type of memory to create if create_memory is True
            memory_importance: Importance of the memory if create_memory is True
            
        Returns:
            The ID of the created fact
        """
        memory_id = None
        
        # Create a memory item if requested
        if create_memory:
            content = f"{subject} {predicate} {object_}"
            if isinstance(object_, (dict, list, tuple)):
                content = f"{subject} {predicate} {json.dumps(object_, ensure_ascii=False)}"
            
            metadata = {
                "subject": subject,
                "predicate": predicate,
                "object": object_ if not isinstance(object_, (dict, list, tuple)) 
                        else json.dumps(object_, ensure_ascii=False),
                "confidence": confidence,
                "source": source
            }
            
            memory_id = self.memory_system.add_memory(
                content=content,
                memory_type=memory_type,
                importance=memory_importance,
                metadata=metadata
            )
        
        # Create and store the fact
        fact = Fact(
            subject=subject,
            predicate=predicate,
            object_=object_,
            confidence=confidence,
            source=source,
            memory_id=memory_id
        )
        
        self.storage.store_fact(fact)
        logger.debug(f"Added fact: {fact}")
        
        return fact.id
    
    def get_fact(self, fact_id: str) -> Optional[Fact]:
        """
        Retrieve a fact by its ID.
        
        Args:
            fact_id: The ID of the fact to retrieve
            
        Returns:
            The fact if found, None otherwise
        """
        fact = self.storage.get_fact(fact_id)
        
        if fact:
            fact.access()
            self.storage.store_fact(fact)
            logger.debug(f"Retrieved fact: {fact}")
        
        return fact
    
    def delete_fact(self, fact_id: str, delete_memory: bool = False) -> bool:
        """
        Delete a fact from semantic memory.
        
        Args:
            fact_id: The ID of the fact to delete
            delete_memory: Whether to also delete the associated memory item
            
        Returns:
            True if successful, False otherwise
        """
        fact = self.storage.get_fact(fact_id)
        
        if not fact:
            logger.warning(f"Cannot delete non-existent fact: {fact_id}")
            return False
        
        # Delete the associated memory if requested
        if delete_memory and fact.memory_id:
            self.memory_system.delete_memory(fact.memory_id)
        
        # Delete the fact
        result = self.storage.delete_fact(fact_id)
        if result:
            logger.debug(f"Deleted fact: {fact_id}")
        else:
            logger.warning(f"Failed to delete fact: {fact_id}")
        
        return result
    
    def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        min_confidence: Optional[float] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Fact]:
        """
        Query facts based on various criteria.
        
        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            min_confidence: Filter by minimum confidence
            source: Filter by source
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            A list of facts matching the criteria
        """
        # Use the instance min_confidence if not specified
        if min_confidence is None:
            min_confidence = self.min_confidence
        
        facts = self.storage.query_facts(
            subject=subject,
            predicate=predicate,
            min_confidence=min_confidence,
            source=source,
            limit=limit,
            offset=offset
        )
        
        # Update access information
        for fact in facts:
            fact.access()
            self.storage.store_fact(fact)
        
        logger.debug(f"Query returned {len(facts)} facts")
        return facts
    
    def get_facts_about(
        self,
        subject: str,
        min_confidence: Optional[float] = None,
        limit: int = 100
    ) -> List[Fact]:
        """
        Get all facts about a specific subject.
        
        Args:
            subject: The subject to get facts about
            min_confidence: Minimum confidence threshold
            limit: Maximum number of facts to return
            
        Returns:
            A list of facts about the subject
        """
        return self.query_facts(
            subject=subject,
            min_confidence=min_confidence,
            limit=limit
        )
    
    def get_fact_value(
        self,
        subject: str,
        predicate: str,
        default: Any = None
    ) -> Any:
        """
        Get the object value for a specific subject and predicate.
        
        This is a convenience method for retrieving a single fact value.
        If multiple facts match, the one with the highest confidence is returned.
        
        Args:
            subject: The subject of the fact
            predicate: The predicate of the fact
            default: Default value to return if no fact is found
            
        Returns:
            The object value of the fact, or the default value if not found
        """
        facts = self.query_facts(
            subject=subject,
            predicate=predicate,
            limit=1
        )
        
        if facts:
            return facts[0].object
        
        return default
    
    def update_fact_confidence(
        self,
        fact_id: str,
        new_confidence: float
    ) -> bool:
        """
        Update the confidence of a fact.
        
        Args:
            fact_id: The ID of the fact to update
            new_confidence: The new confidence value
            
        Returns:
            True if successful, False otherwise
        """
        fact = self.storage.get_fact(fact_id)
        
        if not fact:
            logger.warning(f"Cannot update non-existent fact: {fact_id}")
            return False
        
        fact.confidence = new_confidence
        result = self.storage.store_fact(fact)
        
        if result and fact.memory_id:
            # Update the memory metadata
            memory = self.memory_system.get_memory(fact.memory_id)
            if memory:
                memory.metadata["confidence"] = new_confidence
                self.memory_system.update_memory(fact.memory_id, metadata=memory.metadata)
        
        return result
    
    def check_conflicts(
        self,
        subject: str,
        predicate: str,
        confidence_threshold: float = 0.5
    ) -> List[Tuple[Fact, Fact]]:
        """
        Check for conflicting facts about a subject.
        
        Args:
            subject: The subject to check for conflicts
            predicate: The predicate to check for conflicts
            confidence_threshold: Minimum confidence for facts to be considered
            
        Returns:
            A list of tuples containing pairs of conflicting facts
        """
        facts = self.query_facts(
            subject=subject,
            predicate=predicate,
            min_confidence=confidence_threshold
        )
        
        conflicts = []
        
        # If we have more than one fact with the same subject and predicate
        # but different objects, we have a conflict
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                if facts[i].object != facts[j].object:
                    conflicts.append((facts[i], facts[j]))
        
        return conflicts
    
    def merge_facts(
        self,
        fact_ids: List[str],
        keep_highest_confidence: bool = True
    ) -> Optional[str]:
        """
        Merge multiple facts into a single fact.
        
        Args:
            fact_ids: List of fact IDs to merge
            keep_highest_confidence: Whether to keep the highest confidence value
            
        Returns:
            The ID of the merged fact, or None if merging failed
        """
        if not fact_ids:
            return None
        
        facts = []
        for fact_id in fact_ids:
            fact = self.storage.get_fact(fact_id)
            if fact:
                facts.append(fact)
        
        if not facts:
            return None
        
        # Use the first fact as the base
        base_fact = facts[0]
        
        # Find the fact with the highest confidence if requested
        if keep_highest_confidence and len(facts) > 1:
            base_fact = max(facts, key=lambda f: f.confidence)
        
        # Delete all facts except the base
        for fact in facts:
            if fact.id != base_fact.id:
                self.delete_fact(fact.id, delete_memory=False)
        
        return base_fact.id
    
    def clear(self) -> bool:
        """
        Clear all facts from semantic memory.
        
        Returns:
            True if successful, False otherwise
        """
        return self.storage.clear()
    
    def get_subject_predicates(self, subject: str) -> List[str]:
        """
        Get all predicates used with a specific subject.
        
        Args:
            subject: The subject to get predicates for
            
        Returns:
            A list of distinct predicates
        """
        cursor = self.storage.conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT predicate FROM facts
        WHERE subject = ? AND confidence >= ?
        ORDER BY predicate
        ''', (subject, self.min_confidence))
        
        return [row[0] for row in cursor.fetchall()]
    
    def get_all_subjects(self, limit: int = 1000) -> List[str]:
        """
        Get all distinct subjects in the knowledge base.
        
        Args:
            limit: Maximum number of subjects to return
            
        Returns:
            A list of distinct subjects
        """
        cursor = self.storage.conn.cursor()
        
        cursor.execute('''
        SELECT DISTINCT subject FROM facts
        WHERE confidence >= ?
        ORDER BY subject
        LIMIT ?
        ''', (self.min_confidence, limit))
        
        return [row[0] for row in cursor.fetchall()]
    
    def create_facts_from_memory(
        self,
        memory_id: str,
        subject_key: str = "subject",
        predicate_key: str = "predicate",
        object_key: str = "object",
        confidence_key: str = "confidence"
    ) -> Optional[str]:
        """
        Create a fact from an existing memory item.
        
        This is useful for converting existing memories to semantic facts.
        
        Args:
            memory_id: The ID of the memory to convert
            subject_key: Key in memory metadata for the subject
            predicate_key: Key in memory metadata for the predicate
            object_key: Key in memory metadata for the object
            confidence_key: Key in memory metadata for the confidence
            
        Returns:
            The ID of the created fact, or None if creation failed
        """
        memory = self.memory_system.get_memory(memory_id)
        
        if not memory or not memory.metadata:
            logger.warning(f"Cannot create fact from non-existent memory: {memory_id}")
            return None
        
        # Extract fact components from memory metadata
        subject = memory.metadata.get(subject_key)
        predicate = memory.metadata.get(predicate_key)
        object_ = memory.metadata.get(object_key)
        confidence = memory.metadata.get(confidence_key, 1.0)
        
        if not subject or not predicate or object_ is None:
            logger.warning(f"Memory {memory_id} does not have the required metadata for fact creation")
            return None
        
        # Create the fact
        fact = Fact(
            subject=subject,
            predicate=predicate,
            object_=object_,
            confidence=confidence,
            source=memory.metadata.get("source"),
            memory_id=memory_id
        )
        
        self.storage.store_fact(fact)
        logger.debug(f"Created fact from memory {memory_id}: {fact}")
        
        return fact.id
    
    def get_fact_summary(self, subject: str, max_facts: int = 10) -> str:
        """
        Generate a summary of facts about a subject.
        
        Args:
            subject: The subject to summarize
            max_facts: Maximum number of facts to include
            
        Returns:
            A string summarizing the facts
        """
        facts = self.get_facts_about(subject, limit=max_facts)
        
        if not facts:
            return f"No facts found about {subject}."
        
        summary = f"Facts about {subject}:\n"
        
        for fact in facts:
            obj_str = str(fact.object)
            if isinstance(fact.object, dict):
                obj_str = json.dumps(fact.object, ensure_ascii=False)
            
            summary += f"- {fact.predicate}: {obj_str}"
            if fact.confidence < 1.0:
                summary += f" (confidence: {fact.confidence:.2f})"
            summary += "\n"
        
        return summary 