"""
Agent Communication System.

This module provides the infrastructure for inter-agent communication,
allowing agents to send requests to each other and share context.
"""

import uuid
import time
import logging
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable

from .base import BaseAgent, AgentResponse


class MessageType(Enum):
    """Enumeration of possible message types for inter-agent communication."""
    REQUEST = "request"       # Request for action from another agent
    RESPONSE = "response"     # Response to a request
    NOTIFICATION = "notification"  # Informational message, no response needed
    STATUS = "status"         # Status update
    ERROR = "error"           # Error notification


class Message:
    """
    Message for inter-agent communication.
    
    This class represents a message sent between agents, containing
    all necessary metadata and content.
    
    Attributes:
        message_id: Unique identifier for this message
        sender_id: ID of the agent sending the message
        receiver_id: ID of the intended recipient agent
        msg_type: Type of message (request, response, etc.)
        content: Main content of the message
        context: Optional context dictionary
        timestamp: Time when the message was created
        reference_id: Optional ID of a message this one responds to
    """
    
    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        msg_type: MessageType,
        content: str,
        context: Optional[Dict] = None,
        message_id: Optional[str] = None,
        reference_id: Optional[str] = None
    ):
        """
        Initialize a new message.
        
        Args:
            sender_id: ID of the agent sending the message
            receiver_id: ID of the intended recipient agent
            msg_type: Type of message
            content: Main content of the message
            context: Optional context dictionary
            message_id: Optional custom message ID (generated if None)
            reference_id: Optional ID of a message this one responds to
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.msg_type = msg_type
        self.content = content
        self.context = context or {}
        self.timestamp = time.time()
        self.reference_id = reference_id
    
    def to_dict(self) -> Dict:
        """Convert the message to a dictionary."""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "type": self.msg_type.value,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp,
            "reference_id": self.reference_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create a Message object from a dictionary."""
        return cls(
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            msg_type=MessageType(data["type"]),
            content=data["content"],
            context=data.get("context", {}),
            message_id=data.get("message_id"),
            reference_id=data.get("reference_id")
        )
    
    def create_response(self, content: str, context: Optional[Dict] = None) -> 'Message':
        """
        Create a response message to this message.
        
        Args:
            content: Content of the response
            context: Optional context for the response
            
        Returns:
            A new Message object representing the response
        """
        return Message(
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            msg_type=MessageType.RESPONSE,
            content=content,
            context=context or {},
            reference_id=self.message_id
        )


class AgentCommunicator:
    """
    Manages communication between agents.
    
    This class handles the routing and delivery of messages between agents,
    and maintains a registry of all active agents.
    
    Attributes:
        agents: Dictionary of registered agents by ID
        message_queue: Queue of pending messages
        logger: Logger instance
    """
    
    def __init__(self):
        """Initialize a new agent communicator."""
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue = asyncio.Queue()
        self.logger = logging.getLogger("agent.communicator")
        self._running = False
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._response_waiters: Dict[str, asyncio.Future] = {}
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the communicator.
        
        Args:
            agent: The agent to register
        """
        if agent.agent_id in self.agents:
            self.logger.warning(f"Agent {agent.agent_id} is already registered")
            return
        
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Agent {agent.agent_id} registered with communicator")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the communicator.
        
        Args:
            agent_id: ID of the agent to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.logger.info(f"Agent {agent_id} unregistered from communicator")
    
    async def start(self) -> None:
        """Start the message processing loop."""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Agent communicator started")
        
        # Start message processing loop
        asyncio.create_task(self._process_messages())
    
    async def stop(self) -> None:
        """Stop the message processing loop."""
        self._running = False
        self.logger.info("Agent communicator stopped")
    
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                message = await self.message_queue.get()
                await self._deliver_message(message)
                self.message_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    async def _deliver_message(self, message: Message) -> None:
        """
        Deliver a message to its intended recipient.
        
        Args:
            message: The message to deliver
        """
        receiver_id = message.receiver_id
        
        # Check if this is a response to a waiting request
        if message.reference_id and message.reference_id in self._response_waiters:
            future = self._response_waiters[message.reference_id]
            if not future.done():
                self.logger.info(f"Entregando respuesta para solicitud {message.reference_id} de {message.sender_id}")
                future.set_result(message)
            return
        
        # Check if the recipient agent exists
        if receiver_id not in self.agents:
            self.logger.error(f"Agent {receiver_id} not found for message delivery")
            
            # Create an error response
            error_msg = message.create_response(
                f"Agent {receiver_id} not found",
                {"error": "recipient_not_found"}
            )
            error_msg.msg_type = MessageType.ERROR
            
            # Send the error response back to the sender
            await self.send_message(error_msg)
            return
        
        # Obtener el agente directamente
        agent = self.agents[receiver_id]
        self.logger.info(f"Entregando mensaje de {message.sender_id} a {receiver_id}: {message.content[:50]}...")
        
        # Si es un mensaje de solicitud, intenta procesar directamente primero
        if message.msg_type == MessageType.REQUEST:
            try:
                # Intentar procesar directamente con el agente para mejorar la confiabilidad
                response = await agent.process(message.content, message.context)
                
                # Crear y enviar la respuesta
                response_msg = message.create_response(
                    content=response.content,
                    context=response.metadata
                )
                
                # Ajustar el tipo de mensaje según el estado de la respuesta
                if response.status != "success":
                    response_msg.msg_type = MessageType.ERROR
                    
                self.logger.info(f"Procesado directo exitoso, enviando respuesta a {message.sender_id}")
                await self.send_message(response_msg)
                return
            except Exception as e:
                self.logger.warning(f"Procesamiento directo falló: {str(e)}, intentando handlers...")
        
        # Si el procesamiento directo falla o no es una solicitud, usa los handlers registrados
        if receiver_id in self._message_handlers:
            for handler in self._message_handlers[receiver_id]:
                try:
                    self.logger.info(f"Invocando handler para {receiver_id}")
                    await handler(message)
                    self.logger.info(f"Handler para {receiver_id} completado exitosamente")
                    return
                except Exception as e:
                    self.logger.error(f"Error in message handler for {receiver_id}: {e}")
        else:
            self.logger.warning(f"No hay handlers registrados para {receiver_id}, mensaje no será procesado")
    
    async def send_message(self, message: Message) -> None:
        """
        Queue a message for delivery.
        
        Args:
            message: The message to send
        """
        self.logger.debug(f"Queuing message from {message.sender_id} to {message.receiver_id}")
        await self.message_queue.put(message)
    
    async def send_request(
        self, 
        sender_id: str, 
        receiver_id: str, 
        content: str, 
        context: Optional[Dict] = None,
        timeout: float = 10.0
    ) -> Optional[Message]:
        """
        Send a request and wait for a response.
        
        Args:
            sender_id: ID of the sending agent
            receiver_id: ID of the receiving agent
            content: Content of the request
            context: Optional context for the request
            timeout: Timeout in seconds for waiting for a response
            
        Returns:
            Response message or None if timed out
        """
        # Create and send the request message
        request = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            msg_type=MessageType.REQUEST,
            content=content,
            context=context
        )
        
        # Create a future to wait for the response
        response_future = asyncio.Future()
        self._response_waiters[request.message_id] = response_future
        
        # Send the request
        await self.send_message(request)
        
        try:
            # Wait for the response with timeout
            response = await asyncio.wait_for(response_future, timeout)
            return response
        except asyncio.TimeoutError:
            self.logger.warning(f"Request {request.message_id} timed out")
            return None
        finally:
            # Clean up the response waiter
            if request.message_id in self._response_waiters:
                del self._response_waiters[request.message_id]
    
    def register_message_handler(
        self, 
        agent_id: str, 
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """
        Register a handler for messages to a specific agent.
        
        Args:
            agent_id: ID of the agent to handle messages for
            handler: Async function that will be called with each message
        """
        if agent_id not in self._message_handlers:
            self._message_handlers[agent_id] = []
        
        self._message_handlers[agent_id].append(handler)
        self.logger.debug(f"Registered message handler for agent {agent_id}")
    
    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """
        Get the capabilities of a registered agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of capability strings or empty list if agent not found
        """
        if agent_id in self.agents:
            return self.agents[agent_id].get_capabilities()
        return []
    
    def list_agents(self) -> List[Dict]:
        """
        Get information about all registered agents.
        
        Returns:
            List of agent info dictionaries
        """
        return [agent.get_info() for agent in self.agents.values()]

    def find_agent(self, agent_id: str) -> Optional[Any]:
        """
        Encuentra un agente registrado por su ID.
        
        Args:
            agent_id: ID del agente a buscar
            
        Returns:
            Instancia del agente si se encuentra, None en caso contrario
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        return None


# Create a global communicator instance
communicator = AgentCommunicator()


async def setup_communication_system() -> AgentCommunicator:
    """
    Initialize the agent communication system.
    
    Returns:
        The global communicator instance
    """
    await communicator.start()
    return communicator


async def shutdown_communication_system() -> None:
    """Shutdown the agent communication system."""
    await communicator.stop()


async def send_agent_request(
    sender_id: str, 
    receiver_id: str, 
    content: str, 
    context: Optional[Dict] = None,
    timeout: float = 30.0
) -> Optional[AgentResponse]:
    """
    Send a request from one agent to another and get the response.
    
    This is a convenience function that handles converting between
    AgentResponse and Message formats.
    
    Args:
        sender_id: ID of the sending agent
        receiver_id: ID of the receiving agent
        content: Content of the request
        context: Optional context for the request
        timeout: Timeout in seconds
        
    Returns:
        AgentResponse from the receiving agent or None if timed out
    """
    response = await communicator.send_request(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        context=context,
        timeout=timeout
    )
    
    if response is None:
        return None
    
    # Convert response message to AgentResponse
    return AgentResponse(
        content=response.content,
        status="success" if response.msg_type == MessageType.RESPONSE else "error",
        metadata=response.context
    ) 