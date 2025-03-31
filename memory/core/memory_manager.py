"""
Memory Manager Module

This module provides the MemoryManager class, which serves as a central coordinator
for all memory subsystems, providing a unified interface for accessing and managing
different types of memory.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Type
from datetime import datetime
import uuid
from pathlib import Path

from .memory_system import MemorySystem
from .memory_item import MemoryItem
from ..storage.base_storage import BaseStorage
from ..storage.in_memory_storage import InMemoryStorage
from ..types.episodic_memory import EpisodicMemory
from ..types.semantic_memory import SemanticMemory
from ..types.short_term_memory import ShortTermMemory
from ..types.long_term_memory import LongTermMemory
from ..processors.embedder import Embedder
from ..processors.summarizer import Summarizer

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Central coordinator for all memory subsystems.
    
    The MemoryManager provides a unified interface to work with different memory types
    and handles cross-memory operations like transferring items between memory types,
    search across multiple memory systems, and centralized configuration.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        base_storage: Optional[BaseStorage] = None,
        embedder: Optional[Embedder] = None,
        summarizer: Optional[Summarizer] = None,
        data_dir: Optional[str] = None
    ):
        """
        Initialize the memory manager.
        
        Args:
            config: Configuration dictionary for memory systems
            base_storage: Base storage system to use (if None, uses InMemoryStorage)
            embedder: Embedder processor for vector embeddings
            summarizer: Summarizer processor for creating summaries
            data_dir: Directory to store persistent data (if None, uses in-memory only)
        """
        self.config = config or {}
        self.data_dir = Path(data_dir) if data_dir else None
        
        # Initialize base memory system
        self.base_storage = base_storage or InMemoryStorage()
        self.memory_system = MemorySystem(storage=self.base_storage)
        
        # Initialize processors
        self.embedder = embedder
        self.summarizer = summarizer
        
        # Initialize specialized memory systems
        self._initialize_specialized_memories()
        
        # Setup event listeners for cross-memory propagation
        self._setup_event_listeners()
        
        logger.info(f"MemoryManager initialized with {len(self._specialized_memories)} specialized memory systems")
    
    def _initialize_specialized_memories(self):
        """Initialize all specialized memory subsystems."""
        self._specialized_memories = {}
        
        # Short-term memory (always initialized)
        stm_config = self.config.get("short_term_memory", {})
        self._specialized_memories["short_term"] = ShortTermMemory(
            memory_system=self.memory_system,
            retention_minutes=stm_config.get("retention_minutes", 60),  # 1 hour default
            capacity=stm_config.get("capacity", 100),
            cleanup_interval_seconds=stm_config.get("cleanup_interval_seconds", 300)  # 5 min default
        )
        
        # Long-term memory
        if self.config.get("use_long_term_memory", True):
            ltm_config = self.config.get("long_term_memory", {})
            ltm_storage_path = None
            if self.data_dir:
                ltm_storage_path = self.data_dir / "long_term_memory.db"
            
            self._specialized_memories["long_term"] = LongTermMemory(
                memory_system=self.memory_system,
                db_path=ltm_storage_path,
                min_importance=ltm_config.get("min_importance", 0.3)
            )
        
        # Episodic memory
        if self.config.get("use_episodic_memory", True):
            episodic_config = self.config.get("episodic_memory", {})
            episodic_storage_path = None
            if self.data_dir:
                episodic_storage_path = self.data_dir / "episodic_memory.db"
            
            self._specialized_memories["episodic"] = EpisodicMemory(
                memory_system=self.memory_system,
                db_path=episodic_storage_path
            )
        
        # Semantic memory
        if self.config.get("use_semantic_memory", True):
            semantic_config = self.config.get("semantic_memory", {})
            semantic_storage_path = None
            if self.data_dir:
                semantic_storage_path = self.data_dir / "semantic_memory.db"
            
            self._specialized_memories["semantic"] = SemanticMemory(
                memory_system=self.memory_system,
                db_path=semantic_storage_path
            )
    
    def _setup_event_listeners(self):
        """Setup event listeners to handle cross-memory propagation."""
        # To be implemented when event system is added
        pass
    
    # Memory Access Methods
    
    def get_memory_system(self, memory_type: Optional[str] = None) -> Union[MemorySystem, Any]:
        """
        Get a specific memory system by its type.
        
        Args:
            memory_type: The type of memory system to return, or None for the base system
            
        Returns:
            The requested memory system
        """
        if memory_type is None:
            return self.memory_system
        
        if memory_type in self._specialized_memories:
            return self._specialized_memories[memory_type]
        
        logger.warning(f"Requested memory type '{memory_type}' not found")
        return None
    
    def add_memory(
        self,
        content: Any,
        memory_type: str = "general",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        target_memories: Optional[List[str]] = None
    ) -> str:
        """
        Add a memory item to the system.
        
        Args:
            content: The content of the memory
            memory_type: The type of memory (e.g., "fact", "conversation", "task")
            importance: Importance value between 0 and 1
            metadata: Additional metadata about the memory
            target_memories: List of memory systems to add to (if None, uses heuristics)
            
        Returns:
            The ID of the newly created memory
        """
        # Add to base memory system first
        memory_id = self.memory_system.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        # Determine target memory systems if not specified
        if target_memories is None:
            target_memories = self._determine_target_memories(memory_type, importance)
        
        # Add to all target memory systems
        for memory_system_type in target_memories:
            if memory_system_type in self._specialized_memories:
                self._add_to_specialized_memory(
                    memory_system_type, 
                    memory_id, 
                    memory_type, 
                    content,
                    importance,
                    metadata
                )
        
        return memory_id
    
    def _determine_target_memories(self, memory_type: str, importance: float) -> List[str]:
        """
        Determine which specialized memory systems a memory should be added to.
        
        Args:
            memory_type: The type of memory
            importance: The importance value
            
        Returns:
            List of memory system types to add to
        """
        targets = ["short_term"]  # Always add to short-term memory
        
        # Add important memories to long-term
        if importance >= 0.3 and "long_term" in self._specialized_memories:
            targets.append("long_term")
        
        # Add facts to semantic memory
        if memory_type in ["fact", "concept"] and "semantic" in self._specialized_memories:
            targets.append("semantic")
        
        # Add interactions to episodic memory
        if memory_type in ["conversation", "interaction", "event"] and "episodic" in self._specialized_memories:
            targets.append("episodic")
        
        return targets
    
    def _add_to_specialized_memory(
        self,
        memory_system_type: str,
        memory_id: str,
        memory_type: str,
        content: Any,
        importance: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a memory to a specialized memory system.
        
        Args:
            memory_system_type: Type of specialized memory system
            memory_id: ID of the memory to add
            memory_type: Type of the memory
            content: Content of the memory
            importance: Importance value
            metadata: Additional metadata
        """
        memory_system = self._specialized_memories[memory_system_type]
        # Asegurarse de que metadata nunca sea None
        safe_metadata = metadata or {}
        
        if memory_system_type == "short_term":
            # Get the memory from the base system
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                # Use the add method, passing the source as the memory ID to maintain traceability
                memory_system.add(
                    content=memory.content,
                    source=f"memory:{memory_id}",
                    importance=importance,
                    metadata=safe_metadata
                )
        
        elif memory_system_type == "long_term":
            # Get the memory from the base system
            memory = self.memory_system.get_memory(memory_id)
            if memory:
                # Use the add method for LongTermMemory
                memory_system.add(
                    content=memory.content,
                    source=f"memory:{memory_id}",
                    importance=importance,
                    metadata=safe_metadata
                )
        
        elif memory_system_type == "episodic":
            # For episodic memory, we need to handle episodes
            active_episode_id = safe_metadata.get("episode_id")
            if not active_episode_id:
                # Try to find or create an active episode
                active_episodes = memory_system.get_active_episodes()
                if active_episodes:
                    # Limit manually - take just the first one
                    active_episode_id = active_episodes[0].id
                else:
                    episode_title = safe_metadata.get("episode_title", f"Episode {datetime.now().isoformat()}")
                    active_episode_id = memory_system.create_episode(
                        title=episode_title,
                        description=safe_metadata.get("episode_description", ""),
                        importance=importance
                    )
            
            # Add memory to episode if we have an active episode
            if active_episode_id:
                memory_system.add_memory_to_episode(active_episode_id, memory_id)
        
        elif memory_system_type == "semantic":
            # For semantic memory, extract subject-predicate-object if available
            memory = self.memory_system.get_memory(memory_id)
            if memory and isinstance(memory.metadata, dict):
                # Check if we have semantic metadata
                subject = memory.metadata.get("subject")
                predicate = memory.metadata.get("predicate")
                object_ = memory.metadata.get("object")
                
                if subject and predicate and object_ is not None:
                    # Use add_fact for explicit triples
                    memory_system.add_fact(
                        subject=subject,
                        predicate=predicate,
                        object_=object_,
                        confidence=memory.metadata.get("confidence", 1.0),
                        source=f"memory:{memory_id}",
                        create_memory=False  # We already have the base memory
                    )
                else:
                    # If no explicit triple, try to add as content
                    if isinstance(memory.content, str):
                        # Use the first sentence as subject and "contains" as predicate
                        first_sentence = memory.content.split(". ")[0]
                        subject = first_sentence[:50] + "..." if len(first_sentence) > 50 else first_sentence
                        
                        memory_system.add_fact(
                            subject=subject,
                            predicate="contains",
                            object_=memory.content,
                            confidence=0.8,  # Less confidence for auto-generated facts
                            source=f"memory:{memory_id}",
                            create_memory=False
                        )
    
    def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory by its ID.
        
        Args:
            memory_id: The ID of the memory to retrieve
            
        Returns:
            The memory item if found, None otherwise
        """
        return self.memory_system.get_memory(memory_id)
    
    def query_memories(
        self,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        max_importance: Optional[float] = None,
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None,
        metadata_query: Optional[Dict[str, Any]] = None,
        content_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        target_memory_system: Optional[str] = None
    ) -> List[MemoryItem]:
        """
        Query for memories matching specific criteria.
        
        Args:
            memory_type: Filter by memory type
            min_importance: Minimum importance value
            max_importance: Maximum importance value
            before_timestamp: Filter for memories created before this time
            after_timestamp: Filter for memories created after this time
            metadata_query: Filter by metadata fields
            content_query: Full-text search in content (if available)
            limit: Maximum number of results to return
            offset: Number of results to skip
            target_memory_system: Specific memory system to query (or None for base)
            
        Returns:
            List of memory items matching the criteria
        """
        # Determine which memory system to query
        memory_sys = self.get_memory_system(target_memory_system)
        if not memory_sys:
            return []
        
        # Normalizar la consulta de contenido si está presente
        normalized_content_query = content_query.lower().strip() if content_query else None
        
        # Special case for short-term memory which doesn't implement query_memories
        if target_memory_system == "short_term":
            # Get all memories from short-term memory
            stm = self._specialized_memories["short_term"]
            all_memories = []
            
            # Get all memories tracked in short-term memory
            for memory_id in stm.get_all_item_ids():
                memory = self.memory_system.get_memory(memory_id)
                if memory:
                    # Apply filters
                    if memory_type and memory.memory_type != memory_type:
                        continue
                    if min_importance is not None and memory.importance < min_importance:
                        continue
                    if max_importance is not None and memory.importance > max_importance:
                        continue
                    if before_timestamp and memory.created_at > before_timestamp:
                        continue
                    if after_timestamp and memory.created_at < after_timestamp:
                        continue
                    
                    # Check metadata query
                    if metadata_query:
                        match = True
                        for key, value in metadata_query.items():
                            if key not in memory.metadata or memory.metadata[key] != value:
                                match = False
                                break
                        if not match:
                            continue
                    
                    # Check content query (substring search)
                    if normalized_content_query:
                        # Convertir el contenido a texto y normalizar
                        if isinstance(memory.content, str):
                            memory_content = memory.content.lower()
                        elif isinstance(memory.content, dict):
                            # Para diccionarios, convertimos a JSON string
                            try:
                                memory_content = json.dumps(memory.content, ensure_ascii=False).lower()
                            except:
                                memory_content = str(memory.content).lower()
                        else:
                            memory_content = str(memory.content).lower()
                            
                        if normalized_content_query not in memory_content:
                            continue
                    
                    all_memories.append(memory)
            
            # Sort by recency (newest first)
            all_memories.sort(key=lambda m: m.created_at, reverse=True)
            
            # Apply offset and limit
            return all_memories[offset:offset+limit]
        
        # Handle semantic search with embedder if content_query is provided
        if content_query and self.embedder and hasattr(memory_sys, "semantic_search"):
            try:
                return memory_sys.semantic_search(
                    query=content_query,
                    limit=limit,
                    offset=offset
                )
            except Exception as e:
                logger.error(f"Error in semantic search: {e}")
                # Fall back to regular query
        
        # Regular query through base memory system
        if target_memory_system is None and normalized_content_query:
            # Si estamos consultando el sistema base y tenemos una consulta de contenido
            # realizamos una búsqueda manual sobre todas las memorias
            all_memories = self.memory_system.get_all_memories(limit=1000)
            filtered_memories = []
            
            for memory in all_memories:
                # Aplicar otros filtros primero
                if memory_type and memory.memory_type != memory_type:
                    continue
                if min_importance is not None and memory.importance < min_importance:
                    continue
                if max_importance is not None and memory.importance > max_importance:
                    continue
                if before_timestamp and memory.created_at > before_timestamp:
                    continue
                if after_timestamp and memory.created_at < after_timestamp:
                    continue
                
                # Filtrar por metadata
                if metadata_query:
                    match = True
                    for key, value in metadata_query.items():
                        if key not in memory.metadata or memory.metadata[key] != value:
                            match = False
                            break
                    if not match:
                        continue
                
                # Filtrar por contenido
                if normalized_content_query:
                    # Convertir el contenido a texto y normalizar
                    if isinstance(memory.content, str):
                        memory_content = memory.content.lower()
                    elif isinstance(memory.content, dict):
                        try:
                            memory_content = json.dumps(memory.content, ensure_ascii=False).lower()
                        except:
                            memory_content = str(memory.content).lower()
                    else:
                        memory_content = str(memory.content).lower()
                        
                    if normalized_content_query not in memory_content:
                        continue
                
                filtered_memories.append(memory)
            
            # Ordenar por relevancia (ahora mismo sólo por fecha)
            filtered_memories.sort(key=lambda m: m.created_at, reverse=True)
            
            # Aplicar offset y limit
            return filtered_memories[offset:offset+limit]
        
        # Regular query using the memory system's query method
        return memory_sys.query_memories(
            memory_type=memory_type,
            min_importance=min_importance,
            max_importance=max_importance,
            before_timestamp=before_timestamp,
            after_timestamp=after_timestamp,
            metadata_query=metadata_query,
            limit=limit,
            offset=offset
        )
    
    def get_related_memories(
        self, 
        memory_id: str,
        link_type: Optional[str] = None,
        recursive: bool = False,
        max_depth: int = 2
    ) -> List[MemoryItem]:
        """
        Get memories related to a specific memory.
        
        Args:
            memory_id: ID of the memory to find relations for
            link_type: Type of links to follow (or None for all)
            recursive: Whether to recursively follow links
            max_depth: Maximum depth for recursive search
            
        Returns:
            List of related memory items
        """
        return self.memory_system.get_related_memories(
            memory_id=memory_id,
            link_type=link_type
        )
    
    def summarize_memories(
        self,
        memories: List[MemoryItem],
        max_length: int = 500
    ) -> str:
        """
        Generate a summary of a set of memories.
        
        Args:
            memories: List of memories to summarize
            max_length: Maximum length of the summary
            
        Returns:
            A summary of the provided memories
        """
        if not memories:
            return ""
        
        if self.summarizer:
            # Use summarizer processor if available
            memory_texts = [
                f"{m.memory_type}: {str(m.content)}" for m in memories
            ]
            return self.summarizer.summarize(
                texts=memory_texts,
                max_length=max_length
            )
        else:
            # Simple fallback for summarization
            memory_texts = []
            total_length = 0
            
            # Sort by importance and recency
            sorted_memories = sorted(
                memories, 
                key=lambda m: (m.importance, m.last_accessed),
                reverse=True
            )
            
            for memory in sorted_memories:
                content_str = str(memory.content)
                if total_length + len(content_str) > max_length:
                    # Truncate to fit within max_length
                    available_space = max_length - total_length
                    if available_space > 10:  # Only add if we have reasonable space
                        content_str = content_str[:available_space] + "..."
                        memory_texts.append(content_str)
                    break
                
                memory_texts.append(content_str)
                total_length += len(content_str)
            
            return " ".join(memory_texts)
    
    # Memory Management Methods
    
    def link_memories(
        self, 
        source_id: str, 
        target_id: str, 
        link_type: str = "related"
    ) -> bool:
        """
        Create a link between two memories.
        
        Args:
            source_id: ID of the source memory
            target_id: ID of the target memory
            link_type: Type of the link
            
        Returns:
            True if the link was created, False otherwise
        """
        return self.memory_system.link_memories(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type
        )
    
    def update_memory_importance(
        self, 
        memory_id: str, 
        new_importance: float
    ) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            new_importance: New importance value (0-1)
            
        Returns:
            True if the memory was updated, False otherwise
        """
        return self.memory_system.update_memory(
            memory_id=memory_id,
            importance=new_importance
        )
    
    def consolidate_memories(self) -> None:
        """
        Consolidate memories by moving items between memory systems.
        
        This method implements the memory consolidation process, moving
        memories from short-term to long-term based on access frequency,
        importance, and other factors.
        """
        # Only proceed if we have both short-term and long-term memory
        if "short_term" not in self._specialized_memories or "long_term" not in self._specialized_memories:
            logger.debug("Skipping memory consolidation: missing required memory systems")
            return
        
        stm = self._specialized_memories["short_term"]
        ltm = self._specialized_memories["long_term"]
        
        # Get memories from short-term that need consolidation
        stm_items = stm.get_all_item_ids()
        
        for memory_id in stm_items:
            memory = self.memory_system.get_memory(memory_id)
            if not memory:
                continue
            
            # Check if memory should be consolidated to long-term memory
            should_consolidate = (
                # High importance memories are always consolidated
                memory.importance >= 0.7 or
                # Frequently accessed memories are consolidated
                memory.access_count >= 3 or
                # Old memories with some importance are consolidated
                (
                    memory.importance >= 0.4 and
                    (datetime.now() - memory.created_at).total_seconds() > 60*60*24  # 1 day
                )
            )
            
            if should_consolidate:
                logger.debug(f"Consolidating memory {memory_id} to long-term storage")
                # Use add() method with the appropriate parameters
                ltm.add(
                    content=memory.content,
                    source=f"memory:{memory_id}",
                    importance=memory.importance,
                    metadata=memory.metadata
                )
                stm.remove_item(memory_id)
    
    def forget_memory(self, memory_id: str) -> bool:
        """
        "Forget" a memory by removing it from all memory systems.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if the memory was forgotten, False otherwise
        """
        # Remove from specialized memory systems first
        for memory_type, memory_system in self._specialized_memories.items():
            if hasattr(memory_system, "remove_item"):
                memory_system.remove_item(memory_id)
            elif hasattr(memory_system, "remove_memory"):
                memory_system.remove_memory(memory_id)
        
        # Then remove from base memory system
        return self.memory_system.delete_memory(memory_id)
    
    def clear_short_term_memory(self) -> None:
        """Clear all items from short-term memory."""
        if "short_term" in self._specialized_memories:
            self._specialized_memories["short_term"].clear()
    
    # Persistence Methods
    
    def save_state(self, file_path: Optional[str] = None) -> bool:
        """
        Save the current state of memory systems to a file.
        
        Args:
            file_path: Path to save the state to (or None to use default)
            
        Returns:
            True if the state was saved successfully, False otherwise
        """
        if not file_path and self.data_dir:
            file_path = self.data_dir / "memory_state.json"
        
        if not file_path:
            logger.error("Cannot save state: no file path provided and no data directory set")
            return False
        
        try:
            # Get all memories
            all_memories = self.memory_system.get_all_memories()
            
            # Convert to serializable format using to_dict() method
            serialized_memories = []
            for memory in all_memories:
                try:
                    serialized_memories.append(memory.to_dict())
                except Exception as e:
                    logger.warning(f"Error serializing memory {memory.id}: {e}")
            
            # Create state object
            state = {
                "memories": serialized_memories,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Memory state saved to {file_path} ({len(all_memories)} memories)")
            return True
        
        except Exception as e:
            logger.error(f"Error saving memory state: {e}")
            return False
    
    def load_state(self, file_path: Optional[str] = None) -> bool:
        """
        Load a previously saved state into the memory system.
        
        Args:
            file_path: Path to load the state from (or None to use default)
            
        Returns:
            True if the state was loaded successfully, False otherwise
        """
        if not file_path and self.data_dir:
            file_path = self.data_dir / "memory_state.json"
        
        if not file_path or not os.path.exists(file_path):
            logger.error(f"Cannot load state: file does not exist: {file_path}")
            return False
        
        try:
            # Load state from file
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # Validate state format
            if not isinstance(state, dict) or "memories" not in state:
                logger.error(f"Invalid state format in {file_path}")
                return False
            
            # Clear current memory system
            self.memory_system.clear()
            
            # Load memories from state
            memory_map = {}  # Map of old IDs to new IDs
            loaded_count = 0
            
            for memory_data in state["memories"]:
                try:
                    # Crear una nueva instancia de MemoryItem
                    memory = MemoryItem(
                        content=memory_data["content"],
                        memory_type=memory_data["memory_type"],
                        importance=memory_data["importance"],
                        metadata=memory_data.get("metadata", {}),
                        id=memory_data["id"],  # Mantener el mismo ID
                    )
                    
                    # Establecer campos adicionales si existen
                    if "created_at" in memory_data:
                        memory.created_at = datetime.fromisoformat(memory_data["created_at"])
                    if "last_accessed" in memory_data:
                        memory.last_accessed = datetime.fromisoformat(memory_data["last_accessed"])
                    if "access_count" in memory_data:
                        memory.access_count = memory_data["access_count"]
                    
                    # Agregar la memoria al sistema directamente
                    self.memory_system.storage.store(memory)
                    memory_map[memory_data["id"]] = memory.id
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Error loading memory: {e}")
            
            # Load links (if present in state)
            if "links" in state:
                for source_id, links in state["links"].items():
                    if source_id in memory_map:
                        new_source_id = memory_map[source_id]
                        for link_type, target_ids in links.items():
                            for target_id in target_ids:
                                if target_id in memory_map:
                                    new_target_id = memory_map[target_id]
                                    self.memory_system.link_memories(
                                        new_source_id, new_target_id, link_type
                                    )
            
            logger.info(f"Loaded memory state from {file_path}: {loaded_count} memories")
            return True
            
        except Exception as e:
            logger.error(f"Error loading memory state: {e}")
            return False
    
    # Statistics and Diagnostics
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the memory systems.
        
        Returns:
            Dictionary containing statistics about all memory systems
        """
        stats = {
            "base_system": self.memory_system.get_statistics(),
            "specialized_systems": {}
        }
        
        for memory_type, memory_system in self._specialized_memories.items():
            if hasattr(memory_system, "get_statistics"):
                stats["specialized_systems"][memory_type] = memory_system.get_statistics()
        
        return stats
    
    def update_memory(
        self,
        memory_id: str,
        content: Optional[Any] = None,
        memory_type: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Actualiza una memoria existente.
        
        Args:
            memory_id: ID de la memoria a actualizar
            content: Nuevo contenido (opcional)
            memory_type: Nuevo tipo de memoria (opcional)
            importance: Nuevo valor de importancia (opcional)
            metadata: Nuevos metadatos a fusionar con los existentes (opcional)
            
        Returns:
            True si la memoria fue actualizada, False si no se encontró
        """
        # Obtener la memoria original
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"No se puede actualizar una memoria inexistente: {memory_id}")
            return False
        
        # Actualizar directamente en el sistema de memoria base
        return self.memory_system.update_memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
    
    def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryItem]:
        """
        Buscar memorias usando búsqueda semántica (vectorial) si está disponible.
        
        Args:
            query: Consulta de búsqueda
            memory_type: Tipo de memoria a buscar (opcional)
            limit: Número máximo de resultados
            threshold: Umbral mínimo de similitud
            metadata: Filtrado adicional por metadatos
            
        Returns:
            Lista de memorias encontradas
        """
        # Verificar si tenemos embedder para búsqueda semántica
        if self.embedder:
            try:
                # Preparar un filtro para las memorias
                def memory_filter(memory):
                    # Filtrar por tipo de memoria si se especifica
                    if memory_type and memory.memory_type != memory_type:
                        return False
                    
                    # Filtrar por metadatos si se especifican
                    if metadata:
                        for key, value in metadata.items():
                            if key not in memory.metadata or memory.metadata[key] != value:
                                return False
                    
                    # Si pasa todos los filtros
                    return True
                
                # Obtener todas las memorias que cumplen con el filtro base
                all_memories = self.memory_system.get_all_memories()
                filtered_memories = [m for m in all_memories if memory_filter(m)]
                
                # Realizar búsqueda semántica si hay embedder
                results = self.embedder.find_similar_memories(
                    query=query,
                    memories=filtered_memories,
                    top_k=limit,
                    threshold=threshold
                )
                
                # Extraer solo las memorias (sin puntuaciones)
                return [memory for memory, _ in results]
            except Exception as e:
                logger.error(f"Error en búsqueda semántica: {e}")
                # Caer al método de búsqueda por palabras clave
        
        # Si no hay embedder o falla la búsqueda semántica, usar búsqueda por palabras clave
        return self.search_memories_by_keyword(
            keywords=query.split(),
            memory_type=memory_type,
            limit=limit,
            metadata=metadata
        )
    
    def search_memories_by_keyword(
        self,
        keywords: List[str],
        memory_type: Optional[str] = None,
        limit: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[MemoryItem]:
        """
        Buscar memorias por palabras clave.
        
        Args:
            keywords: Lista de palabras clave
            memory_type: Tipo de memoria a buscar
            limit: Número máximo de resultados
            metadata: Filtrado adicional por metadatos
            
        Returns:
            Lista de memorias encontradas
        """
        # Normalizar palabras clave
        normalized_keywords = [k.lower() for k in keywords if k.strip()]
        
        if not normalized_keywords:
            return []
        
        # Preparar filtro de metadatos completo
        full_metadata = {}
        if metadata:
            full_metadata.update(metadata)
        
        # Realizar la consulta usando query_memories
        all_memories = self.memory_system.get_all_memories()
        
        # Filtrar por metadatos y tipo si es necesario
        filtered_memories = []
        for memory in all_memories:
            # Filtrar por tipo de memoria
            if memory_type and memory.memory_type != memory_type:
                continue
                
            # Filtrar por metadatos
            if metadata:
                match = True
                for key, value in metadata.items():
                    if key not in memory.metadata or memory.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            # Agregar a la lista filtrada
            filtered_memories.append(memory)
        
        # Buscar por palabras clave en el contenido
        scored_memories = []
        for memory in filtered_memories:
            # Convertir contenido a texto
            if isinstance(memory.content, str):
                content_text = memory.content.lower()
            else:
                content_text = str(memory.content).lower()
            
            # Calcular puntuación simple: número de palabras clave encontradas
            score = sum(1 for keyword in normalized_keywords if keyword in content_text)
            
            # Si al menos una palabra clave coincide, agregar a resultados
            if score > 0:
                scored_memories.append((memory, score))
        
        # Ordenar por puntuación (más coincidencias primero)
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Devolver solo las memorias, limitadas según parámetro
        return [memory for memory, _ in scored_memories[:limit]] 