"""
Agents package.

This package contains various agent implementations that can be orchestrated by the MCP.
"""

from .base import BaseAgent, AgentResponse
from .echo_agent import EchoAgent

__all__ = ['BaseAgent', 'AgentResponse', 'EchoAgent'] 