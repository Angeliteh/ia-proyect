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