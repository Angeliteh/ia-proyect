"""
Agents package.

This package contains various agent implementations that can be orchestrated by the MCP.
"""

from .base import BaseAgent, AgentResponse
from .echo_agent import EchoAgent
from .code_agent import CodeAgent
from .system_agent import SystemAgent

__all__ = ['BaseAgent', 'AgentResponse', 'EchoAgent', 'CodeAgent', 'SystemAgent'] 