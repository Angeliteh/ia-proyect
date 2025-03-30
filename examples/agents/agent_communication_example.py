#!/usr/bin/env python
"""
Agent Communication Example.

This script demonstrates how agents can communicate with each other
using the agent communication system.
"""

import os
import sys
import time
import asyncio
import argparse
import logging
import json
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = str(current_dir.parent.parent)  # Updated to point to project root
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Setup logging first
logging = __import__('logging')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("agent_communication_example")

# Try to import the actual modules
USING_REAL_MODULES = True

try:
    from agents import (
        EchoAgent, 
        CodeAgent, 
        SystemAgent,
        AgentCommunicator,
        setup_communication_system,
        shutdown_communication_system
    )
    logger.info("Using real agent modules")
except ImportError as e:
    logger.warning(f"Error importing real agent modules: {e}")
    logger.info("Using minimal implementation for demonstration")
    USING_REAL_MODULES = False
    
    # Minimal implementations for demonstration
    # These will be filled out later if needed

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from the .env file in the parent directory (project root)
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Environment variables loaded from {env_path}")
        # Verify that the API key was loaded
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if google_api_key:
            print(f"Google API key found: {google_api_key[:10]}...")
        else:
            print("Warning: GOOGLE_API_KEY not found in environment variables")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables may not be loaded.")


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


async def setup_agents() -> dict:
    """
    Set up the agents that will communicate with each other.
    
    Returns:
        Dictionary of initialized agents
    """
    # Create echo agent
    echo_config = {
        "name": "Echo Service",
        "description": "Simple echo agent that returns what it receives."
    }
    echo_agent = EchoAgent("echo_service", echo_config)
    
    # Create code agent
    from models import ModelManager
    from models.core.model_manager import ModelInfo, ModelType
    
    # Create custom model configuration for Gemini
    models_config = {
        "models": [
            {
                "name": "gemini-2.0-flash",
                "model_type": "gemini",
                "local": False,
                "api_key_env": "GOOGLE_API_KEY",
                "context_length": 8192
            }
        ]
    }
    
    # Write temporary config file
    config_path = os.path.join(current_dir, "temp_model_config.json")
    with open(config_path, "w") as f:
        json.dump(models_config, f, indent=2)
    
    # Load model manager with our config
    model_manager = ModelManager(config_path)
    
    # Clean up temporary file
    os.remove(config_path)
    
    code_config = {
        "name": "Code Assistant",
        "description": "Agent that can generate and analyze code.",
        "model_manager": model_manager,
        "default_model": "gemini-2.0-flash"
    }
    code_agent = CodeAgent("code_assistant", code_config)
    
    # Create system agent
    system_config = {
        "name": "System Manager",
        "description": "Agent that can control system operations.",
        "working_dir": os.getcwd(),
        "allowed_executables": ["notepad", "calc", "explorer"]
    }
    system_agent = SystemAgent("system_manager", system_config)
    
    # Return all agents
    return {
        "echo": echo_agent,
        "code": code_agent,
        "system": system_agent
    }


async def run_echo_example(agents):
    """
    Run a simple example of communication with EchoAgent.
    
    Args:
        agents: Dictionary of agent instances
    """
    print("\n=== Echo Agent Communication Test ===")
    
    # Get agents
    system_agent = agents["system"]
    echo_agent = agents["echo"]
    
    # Send a request from system agent to echo agent
    message = "Hello from System Agent!"
    
    print(f"System Agent sending message to Echo Agent: '{message}'")
    response = await system_agent.send_request_to_agent(
        "echo_service",
        message
    )
    
    if response:
        print(f"Response from Echo Agent: '{response.content}'")
    else:
        print("No response received (timeout)")


async def run_system_example(agents):
    """
    Run an example where Code Agent asks System Agent for system info.
    
    Args:
        agents: Dictionary of agent instances
    """
    print("\n=== System Agent Communication Test ===")
    
    # Get agents
    code_agent = agents["code"]
    
    # Send a request from code agent to system agent
    query = "Get system information"
    context = {"action": "system_info"}
    
    print(f"Code Agent asking System Agent for: '{query}'")
    response = await code_agent.send_request_to_agent(
        "system_manager",
        query,
        context
    )
    
    if response:
        print("\nSystem information received by Code Agent:")
        print("-" * 50)
        print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
        print("-" * 50)
    else:
        print("No response received (timeout)")


async def run_code_example(agents):
    """
    Run an example where System Agent asks Code Agent to generate code.
    
    Args:
        agents: Dictionary of agent instances
    """
    print("\n=== Code Agent Communication Test ===")
    
    # Get agents
    system_agent = agents["system"]
    
    # Send a request from system agent to code agent
    query = "Write a Python function to calculate the Fibonacci sequence"
    context = {
        "task": "generate",
        "language": "python"
    }
    
    print(f"System Agent asking Code Agent to: '{query}'")
    response = await system_agent.send_request_to_agent(
        "code_assistant",
        query,
        context
    )
    
    if response:
        print("\nCode generated by Code Agent:")
        print("-" * 50)
        print(response.content[:500] + "..." if len(response.content) > 500 else response.content)
        print("-" * 50)
    else:
        print("No response received (timeout)")


async def run_chain_example(agents):
    """
    Run an example where agents cooperate in a chain.
    
    Echo -> Code -> System
    
    Args:
        agents: Dictionary of agent instances
    """
    print("\n=== Multi-Agent Chain Communication Test ===")
    
    # Get agents
    echo_agent = agents["echo"]
    
    # Initial query to Echo Agent
    initial_query = "Write a Python function to list files in a directory and save it to a file"
    
    print(f"Sending initial query to Echo Agent: '{initial_query}'")
    
    # Step 1: Echo Agent relays to Code Agent
    echo_response = await echo_agent.process(initial_query)
    print(f"Echo Agent response: '{echo_response.content}'")
    
    code_response = await echo_agent.send_request_to_agent(
        "code_assistant",
        echo_response.content,
        {"task": "generate", "language": "python"}
    )
    
    if not code_response:
        print("No response received from Code Agent (timeout)")
        return
    
    print("\nCode generated by Code Agent:")
    print("-" * 50)
    print(code_response.content[:500] + "..." if len(code_response.content) > 500 else code_response.content)
    print("-" * 50)
    
    # Step 2: Save the generated code to a file using System Agent
    print("\nAsking System Agent to save the code to a file...")
    
    save_path = "temp_file_lister.py"
    system_response = await echo_agent.send_request_to_agent(
        "system_manager",
        f"Save this code to {save_path}",
        {
            "action": "write_file",
            "parameters": {
                "path": save_path,
                "content": code_response.content
            }
        }
    )
    
    if system_response:
        print(f"System Agent response: '{system_response.content}'")
        
        # Step 3: Run the saved file using System Agent
        print("\nAsking System Agent to list files in current directory using the saved script...")
        
        run_response = await echo_agent.send_request_to_agent(
            "system_manager",
            "Execute the file lister script",
            {
                "action": "execute_command",
                "parameters": {
                    "command": f"{sys.executable} {save_path} ."
                }
            }
        )
        
        if run_response:
            print("\nExecution result:")
            print("-" * 50)
            print(run_response.content[:500] + "..." if len(run_response.content) > 500 else run_response.content)
            print("-" * 50)
        else:
            print("No execution response received (timeout)")
    else:
        print("No response received from System Agent (timeout)")


async def run_communication_example(test_type):
    """
    Run the communication example with the specified test type.
    
    Args:
        test_type: Type of test to run (echo, system, code, chain, all)
    """
    logging.info("Setting up communication system")
    
    # Initialize communication system
    communicator = await setup_communication_system()
    
    logging.info("Setting up agents")
    agents = await setup_agents()
    
    # Make sure all agents are registered with the communicator
    for agent in agents.values():
        await agent.register_with_communicator()
    
    # Wait for the communicator to start
    await asyncio.sleep(1)
    
    try:
        if test_type == "echo" or test_type == "all":
            await run_echo_example(agents)
        
        if test_type == "system" or test_type == "all":
            await run_system_example(agents)
        
        if test_type == "code" or test_type == "all":
            await run_code_example(agents)
        
        if test_type == "chain" or test_type == "all":
            await run_chain_example(agents)
    
    finally:
        # Clean up
        logging.info("Shutting down communication system")
        await shutdown_communication_system()


def main():
    """Main function to parse arguments and run the example."""
    parser = argparse.ArgumentParser(description="Agent Communication Example")
    parser.add_argument(
        "--test", 
        choices=["echo", "system", "code", "chain", "all"],
        default="all",
        help="Type of communication test to run"
    )
    parser.add_argument(
        "--check-real-modules",
        action="store_true",
        help="Check if using real modules"
    )
    
    args = parser.parse_args()
    
    # Check if we're using real modules
    if args.check_real_modules:
        print(f"USING_REAL_MODULES = {USING_REAL_MODULES}")
        return
    
    setup_logging()
    asyncio.run(run_communication_example(args.test))


if __name__ == "__main__":
    main() 