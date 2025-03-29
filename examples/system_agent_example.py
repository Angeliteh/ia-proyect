#!/usr/bin/env python
"""
System Agent Example.

This script demonstrates the usage of the SystemAgent for system control tasks.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = str(current_dir.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from agents import SystemAgent


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


async def run_system_agent(task_type, specific_task=None):
    """
    Run the system agent with the specified task.
    
    Args:
        task_type: Type of task to perform (info, file, process, execute)
        specific_task: Specific task parameters
    """
    logging.info(f"Initializing System Agent")
    
    # Configure the system agent
    config = {
        "working_dir": os.getcwd(),
        # Define allowed executables and restricted dirs as needed
        "allowed_executables": ["notepad", "calc", "explorer"],
    }
    
    # Create agent instance
    agent = SystemAgent("system_controller", config)
    
    # Define parameters based on task type
    if task_type == "info":
        logging.info("Getting system information")
        params = {"action": "system_info"}
        query = "Tell me about this system"
    
    elif task_type == "files":
        path = specific_task or "."
        logging.info(f"Listing files in {path}")
        params = {
            "action": "list_files",
            "parameters": {"path": path}
        }
        query = f"List files in {path}"
    
    elif task_type == "read":
        if not specific_task:
            logging.error("File path is required for read operation")
            return
        logging.info(f"Reading file: {specific_task}")
        params = {
            "action": "read_file",
            "parameters": {"path": specific_task}
        }
        query = f"Read file {specific_task}"
    
    elif task_type == "write":
        if not specific_task or ":" not in specific_task:
            logging.error("File path and content are required for write operation (path:content)")
            return
        path, content = specific_task.split(":", 1)
        logging.info(f"Writing to file: {path}")
        params = {
            "action": "write_file",
            "parameters": {"path": path, "content": content}
        }
        query = f"Write to file {path}"
    
    elif task_type == "process":
        pid = int(specific_task) if specific_task and specific_task.isdigit() else None
        logging.info(f"Getting process info: {'All processes' if pid is None else f'PID {pid}'}")
        params = {
            "action": "process_info",
            "parameters": {"pid": pid}
        }
        query = "Get process information"
    
    elif task_type == "execute":
        if not specific_task:
            logging.error("Command is required for execute operation")
            return
        logging.info(f"Executing command: {specific_task}")
        params = {
            "action": "execute_command",
            "parameters": {"command": specific_task}
        }
        query = f"Execute command: {specific_task}"
    
    else:
        logging.error(f"Unknown task type: {task_type}")
        return
    
    # Process the request
    response = await agent.process(query, context=params)
    
    # Display the result
    if response.status == "error":
        logging.error(f"Error: {response.content}")
    else:
        print("\n" + "="*50)
        print("SYSTEM AGENT RESPONSE:")
        print("="*50)
        print(response.content)
        print("="*50)
    
    return response


def main():
    """Main function to parse arguments and run the example."""
    parser = argparse.ArgumentParser(description="System Agent Example")
    parser.add_argument(
        "--task", 
        choices=["info", "files", "read", "write", "process", "execute"],
        default="info",
        help="Type of system task to perform"
    )
    parser.add_argument(
        "--param", 
        help=(
            "Task-specific parameter:\n"
            "- For 'files': directory path (default: current)\n"
            "- For 'read': file path to read\n"
            "- For 'write': file_path:content\n"
            "- For 'process': PID (optional)\n"
            "- For 'execute': command to execute"
        )
    )
    
    args = parser.parse_args()
    
    setup_logging()
    asyncio.run(run_system_agent(args.task, args.param))


if __name__ == "__main__":
    main() 