"""
Base Agent module.

This module defines the base class that all specialized agents must inherit from.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# Importación del TTS - lo hacemos dentro de un try para evitar errores si no está instalado
TTS_AVAILABLE = False
try:
    from tts.core.agent_tts_interface import AgentTTSInterface
    TTS_AVAILABLE = True
except ImportError:
    pass

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
        tts_interface: Optional interface for Text-to-Speech capabilities
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
        
        # TTS-related attributes
        self.tts_interface = None
        self.use_tts = config.get("use_tts", False)
        if self.use_tts:
            self._setup_tts()
    
    def _setup_tts(self):
        """
        Configure Text-to-Speech capabilities for this agent.
        
        This will create a TTS interface if TTS is available and enabled.
        """
        if not TTS_AVAILABLE:
            self.logger.warning(f"TTS requested for agent '{self.name}' but TTS module not available")
            return
        
        try:
            self.tts_interface = AgentTTSInterface()
            self.logger.info(f"Agent '{self.name}' initialized TTS capabilities")
        except Exception as e:
            self.logger.error(f"Error setting up TTS interface: {e}")
    
    def has_tts(self) -> bool:
        """Check if this agent has TTS capabilities enabled."""
        return self.tts_interface is not None
    
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
    
    def recall(self, query=None, memory_type=None, limit=5, threshold=0.0, metadata_filter=None):
        """
        Recall information from the agent's memory.
        
        Args:
            query: The query to search for
            memory_type: Type of memory to search
            limit: Maximum number of results
            threshold: Minimum relevance threshold
            metadata_filter: Filter memories by metadata
            
        Returns:
            List of memory items matching the query
        """
        if not self.has_memory():
            self.logger.debug(f"Cannot recall - no memory manager available")
            return []
        
        # Prepare metadata filter - always include this agent's ID
        meta_filter = metadata_filter or {}
        
        # Don't limit to agent ID unless specifically requested
        # This allows cross-agent memory search by default
        if meta_filter.get("agent_id", None) is not None:
            meta_filter["agent_id"] = self.agent_id
        
        try:
            # Try semantic search first
            if query:
                results = self.memory_manager.search_memories(
                    query=query,
                    memory_type=memory_type,
                    limit=limit,
                    threshold=threshold,
                    metadata=meta_filter
                )
                
                # If we got results, return them
                if results and len(results) > 0:
                    return results
                    
                # Otherwise, try keyword search as fallback
                self.logger.debug(f"Semantic search returned no results, trying keyword search")
                results = self.memory_manager.search_memories_by_keyword(
                    keywords=query.split(),
                    memory_type=memory_type,
                    limit=limit,
                    metadata=meta_filter
                )
                return results
            
            # If no query provided, get recent memories
            return self.memory_manager.get_recent_memories(
                memory_type=memory_type,
                limit=limit,
                metadata=meta_filter
            )
            
        except Exception as e:
            self.logger.error(f"Error recalling from memory: {e}")
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
    
    def _process_tts_response(self, response: AgentResponse, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a response through the TTS system if enabled.
        
        Args:
            response: The agent response to process
            context: The context that was provided with the query
            
        Returns:
            The original response with TTS metadata if successful
        """
        # Check if TTS is enabled and available
        if not self.has_tts():
            return response
        
        # Check if context explicitly disables TTS
        context_dict = context or {}
        if context_dict.get("use_tts", self.use_tts) is False:
            return response
        
        # Get TTS parameters from context if available
        tts_params = context_dict.get("tts_params", {})
        
        # Auto-play audio if requested in context
        play_immediately = context_dict.get("play_audio", False)
        
        try:
            # Generate TTS output
            tts_result = self.tts_interface.process_response(
                text=response.content,
                agent_name=self.name,
                tts_params=tts_params,
                play_immediately=play_immediately
            )
            
            # Add TTS information to response metadata
            if tts_result.get("success", False):
                response.metadata["tts"] = {
                    "audio_file": tts_result.get("audio_file"),
                    "voice": tts_result.get("voice"),
                    "success": True
                }
            else:
                response.metadata["tts"] = {
                    "success": False,
                    "error": tts_result.get("error", "Unknown TTS error")
                }
                
        except Exception as e:
            self.logger.error(f"Error processing TTS response: {e}")
            response.metadata["tts"] = {
                "success": False,
                "error": str(e)
            }
            
        return response
    
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
            "state": self.state,
            "has_memory": self.has_memory(),
            "has_tts": self.has_tts()
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
    
    async def _handle_message(self, message: Dict) -> Optional[Dict]:
        """
        Handle a message received from the communicator.
        
        This is a private method that should not be called directly.
        It's registered with the communicator to handle incoming messages.
        
        Args:
            message: The message to handle
            
        Returns:
            Response message or None
        """
        message_type = message.get("type")
        if message_type == "request":
            # Extract query and context from the message
            query = message.get("content", "")
            context = message.get("context", {})
            
            # Process the request
            self.logger.info(f"Processing request from {message.get('sender_id')}")
            response = await self.process(query, context)
            
            # Create response message
            return {
                "type": "response",
                "content": response.content,
                "metadata": response.metadata,
                "status": response.status
            }
            
        elif message_type == "notification":
            # Just log notifications for now
            self.logger.info(f"Received notification from {message.get('sender_id')}: {message.get('content')}")
            return None
            
        else:
            self.logger.warning(f"Received unknown message type: {message_type}")
            return None
    
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