"""
Echo Agent module.

This is a simple agent that echoes back the input it receives.
Useful for testing the agent infrastructure.
"""

from typing import Dict, List, Optional

from .base import BaseAgent, AgentResponse

class EchoAgent(BaseAgent):
    """
    Simple agent that echoes back the input it receives.
    
    This agent is primarily used for testing the agent infrastructure
    without requiring complex model integrations.
    """
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process the query by echoing it back.
        
        Args:
            query: The input text
            context: Optional context (unused)
            
        Returns:
            AgentResponse containing the echoed input
        """
        self.logger.info(f"Processing query with echo agent: {query[:30]}...")
        self.set_state("processing")
        
        # Simply echo the input back
        response = AgentResponse(
            content=f"Echo: {query}",
            metadata={
                "agent_id": self.agent_id,
                "query_length": len(query),
                "context": context or {}
            }
        )
        
        self.set_state("idle")
        return response
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List containing the 'echo' capability
        """
        return ["echo"] 