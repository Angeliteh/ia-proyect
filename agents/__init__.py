"""
Agents package.

This package contains various agent implementations that can be orchestrated by the MCP.
"""

from .base import BaseAgent, AgentResponse
from .echo_agent import EchoAgent
from .code_agent import CodeAgent
from .system_agent import SystemAgent
from .agent_communication import (
    MessageType, 
    Message, 
    AgentCommunicator, 
    communicator,
    setup_communication_system,
    shutdown_communication_system,
    send_agent_request
)

__all__ = [
    'BaseAgent', 
    'AgentResponse', 
    'EchoAgent', 
    'CodeAgent', 
    'SystemAgent',
    'MessageType',
    'Message',
    'AgentCommunicator',
    'communicator',
    'setup_communication_system',
    'shutdown_communication_system',
    'send_agent_request'
] 