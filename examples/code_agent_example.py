#!/usr/bin/env python
"""
Code Agent Example.

This example demonstrates how to use the CodeAgent to perform various coding tasks.
"""

import os
import sys
import asyncio
import logging
import argparse
from dotenv import load_dotenv

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the agent
from agents import CodeAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("code_agent_example")

# Sample code for explanation/improvement
SAMPLE_PYTHON_CODE = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Calculate factorial of 5
result = factorial(5)
print("Factorial of 5:", result)

# Calculate 10th Fibonacci number
fib_result = fibonacci(10)
print("10th Fibonacci number:", fib_result)
"""

async def test_code_generation(agent):
    """Test the code generation capability."""
    logger.info("\n=== Testing Code Generation ===")
    
    query = "Write a Python function to find all prime numbers up to a given limit using the Sieve of Eratosthenes algorithm."
    
    response = await agent.process(query)
    
    logger.info(f"Generated Code:\n{response.content}")
    logger.info(f"Metadata: {response.metadata}")
    
    return response

async def test_code_explanation(agent):
    """Test the code explanation capability."""
    logger.info("\n=== Testing Code Explanation ===")
    
    query = "Explain how this code works and identify any potential issues."
    
    response = await agent.process(
        query, 
        context={
            "code": SAMPLE_PYTHON_CODE,
            "task": "explain",
            "language": "python"
        }
    )
    
    logger.info(f"Explanation:\n{response.content}")
    logger.info(f"Metadata: {response.metadata}")
    
    return response

async def test_code_improvement(agent):
    """Test the code improvement capability."""
    logger.info("\n=== Testing Code Improvement ===")
    
    query = "Optimize this code to be more efficient, especially the fibonacci function which has exponential complexity."
    
    response = await agent.process(
        query, 
        context={
            "code": SAMPLE_PYTHON_CODE,
            "task": "improve",
            "language": "python"
        }
    )
    
    logger.info(f"Improved Code:\n{response.content}")
    logger.info(f"Metadata: {response.metadata}")
    
    return response

async def test_bug_fixing(agent):
    """Test the bug fixing capability."""
    logger.info("\n=== Testing Bug Fixing ===")
    
    buggy_code = """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
    
# Test with empty list
result = calculate_average([])
print("Average:", result)
"""
    
    query = "Fix the bug in this function that causes it to crash with an empty list."
    
    response = await agent.process(
        query, 
        context={
            "code": buggy_code,
            "task": "fix",
            "language": "python"
        }
    )
    
    logger.info(f"Fixed Code:\n{response.content}")
    logger.info(f"Metadata: {response.metadata}")
    
    return response

async def main():
    """Main function to run the example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Code Agent Example")
    parser.add_argument(
        "--task", 
        choices=["generate", "explain", "improve", "fix", "all"],
        default="all",
        help="Which coding task to demonstrate"
    )
    parser.add_argument(
        "--model", 
        choices=["gemini-pro", "gemini-2.0-flash", "phi-2", "mistral-7b-instruct"],
        default="phi-2",
        help="Model to use for the agent"
    )
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    logger.info(f"Initializing Code Agent with model: {args.model}")
    
    # Create the agent
    agent = CodeAgent(
        agent_id="code_assistant", 
        config={
            "name": "Code Assistant",
            "description": "AI agent specialized in coding tasks",
            "model": args.model
        }
    )
    
    # Print agent capabilities
    logger.info(f"Agent capabilities: {agent.get_capabilities()}")
    
    # Run the selected task(s)
    if args.task == "generate" or args.task == "all":
        await test_code_generation(agent)
    
    if args.task == "explain" or args.task == "all":
        await test_code_explanation(agent)
    
    if args.task == "improve" or args.task == "all":
        await test_code_improvement(agent)
    
    if args.task == "fix" or args.task == "all":
        await test_bug_fixing(agent)
    
    logger.info("Example completed")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 