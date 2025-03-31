"""
Base Agent module.

This module defines the base class that all specialized agents must inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class AgentResponse:
    """
    Standard response structure for all agents.
    
    Attributes:
        content: Main content of the response
        status: Status of the response (success, error, etc.)
        metadata: Additional metadata about the response
    """
    
    def __init__(
        self, 
        content: str, 
        status: str = "success", 
        metadata: Optional[Dict] = None
    ):
        self.content = content
        self.status = status
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        """Convert the response to a dictionary."""
        return {
            "content": self.content,
            "status": self.status,
            "metadata": self.metadata
        }

class BaseAgent(ABC):
    """
    Base abstract class that all agents must inherit from.
    
    This class defines the interface that all agents must implement.
    
    Attributes:
        agent_id: Unique identifier for the agent
        name: Human-readable name of the agent
        description: Detailed description of the agent's capabilities
        logger: Logger instance for this agent
        memory_manager: Optional memory manager for persistent memory
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the agent with configuration.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary for the agent
        """
        self.agent_id = agent_id
        self.config = config
        self.name = config.get("name", agent_id)
        self.description = config.get("description", "")
        
        # Set up logging
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.logger.info(f"Agent '{self.name}' initialized")
        
        # Track agent state
        self.state = "idle"
        
        # Communication-related attributes
        self._comm_registered = False
        
        # Memory-related attributes
        self.memory_manager = None
    
    def setup_memory(self, memory_config=None, shared_memory_manager=None):
        """
        Configure memory capabilities for this agent.
        
        The agent can either use a shared memory manager or create its own.
        
        Args:
            memory_config: Configuration for memory if creating a new manager
            shared_memory_manager: Existing memory manager to use (takes precedence)
            
        Returns:
            True if memory was set up successfully, False otherwise
        """
        if shared_memory_manager:
            self.memory_manager = shared_memory_manager
            self.logger.info(f"Agent '{self.name}' using shared memory manager")
            return True
            
        if memory_config:
            try:
                # Import the MemoryManager - we do this here to avoid circular imports
                from memory.core.memory_manager import MemoryManager
                
                # If data_dir is not specified, create one based on agent_id
                if "data_dir" not in memory_config and self.agent_id:
                    import os
                    from pathlib import Path
                    
                    # Create a directory for this agent's memory
                    data_dir = Path(os.getcwd()) / "data" / "agents" / self.agent_id / "memory"
                    data_dir.mkdir(parents=True, exist_ok=True)
                    memory_config["data_dir"] = str(data_dir)
                
                self.memory_manager = MemoryManager(config=memory_config)
                self.logger.info(f"Agent '{self.name}' created its own memory manager")
                return True
            except ImportError as e:
                self.logger.warning(f"Failed to import MemoryManager: {e}")
                return False
            except Exception as e:
                self.logger.error(f"Error setting up memory manager: {e}")
                return False
                
        return False
        
    def has_memory(self):
        """Check if this agent has memory capabilities enabled."""
        return self.memory_manager is not None
        
    def remember(self, content, importance=0.5, memory_type="general", metadata=None):
        """
        Store information in the agent's memory.
        
        Args:
            content: The content to remember
            importance: How important is this memory (0.0 to 1.0)
            memory_type: Type of memory (general, episodic, etc.)
            metadata: Additional metadata about the memory
            
        Returns:
            The memory_id if successful, None otherwise
        """
        if not self.has_memory():
            self.logger.debug(f"Cannot remember content - no memory manager available")
            return None
            
        # Add agent info to metadata
        meta = metadata or {}
        meta.update({
            "agent_id": self.agent_id,
            "source": f"agent:{self.agent_id}"
        })
        
        try:
            memory_id = self.memory_manager.add_memory(
                content=content,
                memory_type=memory_type,
                importance=importance,
                metadata=meta
            )
            self.logger.debug(f"Stored memory: {memory_id}")
            return memory_id
        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            return None
            
    def recall(self, query=None, memory_type=None, limit=5, min_importance=0.0):
        """
        Retrieve information from the agent's memory.
        
        Args:
            query: Optional search query
            memory_type: Optional type filter
            limit: Maximum number of memories to return
            min_importance: Minimum importance threshold
            
        Returns:
            List of matching memories, or empty list if none found or no memory available
        """
        if not self.has_memory():
            self.logger.debug(f"Cannot recall - no memory manager available")
            return []
            
        try:
            # Si no hay consulta, solo devolver por tipo de memoria
            if not query:
                memories = self.memory_manager.query_memories(
                    memory_type=memory_type,
                    min_importance=min_importance,
                    limit=limit
                )
                self.logger.debug(f"Recalled {len(memories)} memories by type {memory_type}")
                return memories
                
            # Estrategia 1: Búsqueda directa con la consulta completa
            memories = self.memory_manager.query_memories(
                memory_type=memory_type,
                min_importance=min_importance,
                content_query=query,
                limit=limit
            )
            
            # Si encontramos resultados, devolver
            if memories:
                self.logger.debug(f"Recalled {len(memories)} memories matching '{query}'")
                return memories
                
            # Estrategia 2: Si no hay resultados y la consulta tiene múltiples palabras,
            # probar con palabras clave individuales
            words = query.lower().split()
            if len(words) > 1:
                self.logger.debug(f"No memories found with full query, trying individual keywords")
                
                # Extraer palabras clave (excluyendo palabras comunes)
                stop_words = {
                    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by",
                    "about", "as", "of", "que", "cómo", "para", "por", "con", "de", "el", "la", "los", "las",
                    "un", "una", "unos", "unas", "en", "es", "son", "del", "me", "su", "sus"
                }
                keywords = [word for word in words if word not in stop_words and len(word) > 2]
                
                # Si no hay palabras clave sustanciales, usar todas las palabras
                if not keywords:
                    keywords = words
                
                # Intentar con cada palabra clave individualmente
                for keyword in keywords:
                    # Solo buscar con palabras de al menos 3 caracteres
                    if len(keyword) < 3:
                        continue
                        
                    keyword_memories = self.memory_manager.query_memories(
                        memory_type=memory_type,
                        min_importance=min_importance,
                        content_query=keyword,
                        limit=limit
                    )
                    
                    if keyword_memories:
                        self.logger.debug(f"Found {len(keyword_memories)} memories with keyword '{keyword}'")
                        return keyword_memories
            
            # No se encontraron memorias con ninguna estrategia
            self.logger.debug(f"No memories found matching '{query}'")
            return []
        except Exception as e:
            self.logger.error(f"Error recalling memories: {e}")
            return []
    
    def forget(self, memory_id):
        """
        Remove a specific memory from the agent's memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if successful, False otherwise
        """
        if not self.has_memory():
            return False
            
        try:
            result = self.memory_manager.forget_memory(memory_id)
            if result:
                self.logger.debug(f"Forgot memory: {memory_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error forgetting memory: {e}")
            return False
    
    @abstractmethod
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a query and return a response.
        
        Args:
            query: The text query to process
            context: Optional context information
            
        Returns:
            AgentResponse object with the results
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        pass
    
    def get_info(self) -> Dict:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "state": self.state
        }
    
    def set_state(self, new_state: str) -> bool:
        """
        Set the agent's state.
        
        Args:
            new_state: New state to set
            
        Returns:
            Boolean indicating success
        """
        # Validate the state transition
        valid_transitions = {
            "idle": ["processing"],
            "processing": ["idle", "error"],
            "error": ["idle"]
        }
        
        if new_state not in valid_transitions.get(self.state, []):
            self.logger.warning(
                f"Invalid state transition from '{self.state}' to '{new_state}'"
            )
            return False
        
        self.logger.info(f"Agent state changing from '{self.state}' to '{new_state}'")
        self.state = new_state
        return True
    
    async def register_with_communicator(self) -> None:
        """
        Register this agent with the global communicator.
        
        This is done lazily to avoid circular imports.
        """
        if self._comm_registered:
            return
        
        # Import here to avoid circular imports
        from .agent_communication import communicator
        
        # Register with communicator
        communicator.register_agent(self)
        
        # Register a message handler
        communicator.register_message_handler(self.agent_id, self._handle_message)
        
        self._comm_registered = True
        self.logger.info(f"Agent {self.agent_id} registered with communicator")
    
    async def _handle_message(self, message) -> None:
        """
        Handle an incoming message by processing it as a query.
        
        Args:
            message: The Message object to handle
        """
        # Import here to avoid circular imports
        from .agent_communication import Message, MessageType
        
        self.logger.info(f"Handling message from {message.sender_id}: {message.content[:50]}...")
        
        # Process the message as a query
        response = await self.process(message.content, message.context)
        
        # Create a response message
        response_msg = message.create_response(
            content=response.content,
            context=response.metadata
        )
        
        # Set appropriate message type based on response status
        if response.status != "success":
            response_msg.msg_type = MessageType.ERROR
        
        # Send the response
        from .agent_communication import communicator
        await communicator.send_message(response_msg)
    
    async def send_request_to_agent(
        self, 
        receiver_id: str, 
        content: str, 
        context: Optional[Dict] = None,
        timeout: float = 10.0
    ) -> Optional[AgentResponse]:
        """
        Send a request to another agent and wait for a response.
        
        Args:
            receiver_id: ID of the receiving agent
            content: Content of the request
            context: Optional context for the request
            timeout: Timeout in seconds
            
        Returns:
            Response from the receiving agent or None if timed out
        """
        # Ensure we're registered with the communicator
        await self.register_with_communicator()
        
        # Import here to avoid circular imports
        from .agent_communication import send_agent_request
        
        return await send_agent_request(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            context=context,
            timeout=timeout
        ) 