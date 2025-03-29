#!/usr/bin/env python
"""
Echo Agent Example.

This example demonstrates the basic usage of the EchoAgent,
which simply echoes back the input it receives.
"""

import os
import sys
import asyncio
import logging

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the agent
from agents import EchoAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("echo_agent_example")

async def main():
    """Main function to run the example."""
    logger.info("Initializing Echo Agent")
    
    # Create the agent
    agent = EchoAgent(
        agent_id="basic_echo", 
        config={
            "name": "Basic Echo Agent",
            "description": "Simple agent that echoes back input"
        }
    )
    
    # Print agent capabilities
    logger.info(f"Agent capabilities: {agent.get_capabilities()}")
    
    # Test the agent with some inputs
    test_inputs = [
        "Hello, agent!",
        "This is a test of the echo functionality.",
        "Can you repeat this for me?"
    ]
    
    for i, test_input in enumerate(test_inputs, 1):
        logger.info(f"\n=== Test {i}: {test_input} ===")
        
        # Process the input
        response = await agent.process(test_input)
        
        # Print the response
        logger.info(f"Response: {response.content}")
        logger.info(f"Metadata: {response.metadata}")
    
    logger.info("\nExample completed")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 