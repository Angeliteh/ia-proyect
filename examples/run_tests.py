#!/usr/bin/env python
"""
Test runner for the MCP system
"""

import os
import sys
import time
import glob
import json
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Test configuration
TEST_CONFIG = {
    "brave": {
        # The name of the test case
        "server": {
            # The test module
            "module": "brave_search_server_test.py",
            # The directory relative to this file
            "dir": ".",
            # Arguments to pass to the test
            "args": "--auto-exit",
            # Optional expected result (0 = success)
            "expected_result": 0
        },
        "api": {
            "module": "brave_search_api_test.py",
            "dir": ".",
            "args": "",
            "expected_result": 0
        },
        "mcp_test": {
            "module": "brave_api_mcp_test.py",
            "dir": ".",
            "args": "",
            "expected_result": 0
        }
    },
    "gemini": {
        "api": {
            "module": "gemini_api_test.py",
            "dir": ".",
            "args": "--no-interactive",
            "expected_result": 0
        }
    },
    "sqlite": {
        "api": {
            "module": "sqlite_test.py",
            "dir": ".",
            "args": "",
            "expected_result": 0
        }
    },
    "agents": {
        "echo": {
            "module": "echo_agent_example.py",
            "dir": ".",
            "args": "",
            "expected_result": 0
        },
        "code": {
            "module": "code_agent_example.py",
            "dir": ".",
            "args": "--task generate --model gemini-2.0-flash",
            "expected_result": 0
        },
        "system": {
            "module": "system_agent_example.py",
            "dir": ".",
            "args": "--task info",
            "expected_result": 0
        },
        "system_files": {
            "module": "system_agent_example.py",
            "dir": ".",
            "args": "--task files",
            "expected_result": 0
        },
        "communication": {
            "module": "agent_communication_example.py",
            "dir": ".",
            "args": "--test echo",
            "expected_result": 0
        },
        "communication_chain": {
            "module": "agent_communication_example.py",
            "dir": ".",
            "args": "--test chain",
            "expected_result": 0
        }
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_python_executable() -> str:
    """Find the Python executable to use for tests."""
    # Use sys.executable if available
    if sys.executable:
        return sys.executable
    
    # Try some common Python executable names
    for cmd in ["python", "python3", "py"]:
        try:
            result = subprocess.run([cmd, "--version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            if result.returncode == 0:
                return cmd
        except FileNotFoundError:
            continue
    
    # Default to "python" if nothing else found
    return "python"


def run_test(category: str, test_name: str, config: Dict[str, Any]) -> Tuple[int, str, str]:
    """Run a single test and return the result."""
    module = config["module"]
    directory = config["dir"]
    args = config["args"]
    expected_result = config.get("expected_result", 0)
    
    # Get the full path to the test module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, directory)
    test_path = os.path.join(test_dir, module)
    
    if not os.path.exists(test_path):
        logger.error(f"Test module not found: {test_path}")
        return 1, "", f"Test module not found: {test_path}"
    
    # Command to run the test
    python_exe = find_python_executable()
    cmd = [python_exe, test_path]
    
    # Add arguments if provided
    if args:
        cmd.extend(args.split())
    
    # Run the test
    logger.info(f"Running test: {category}:{test_name} - {' '.join(cmd)}")
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=test_dir
        )
        stdout, stderr = process.communicate(timeout=60)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if process.returncode == expected_result:
            logger.info(f"Test {category}:{test_name} completed successfully in {duration:.2f}s")
            return 0, stdout, stderr
        else:
            logger.error(f"Test {category}:{test_name} failed with code {process.returncode}")
            return process.returncode, stdout, stderr
            
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"Test {category}:{test_name} timed out after 60s")
        return 1, "", "Timeout expired"
    except Exception as e:
        logger.error(f"Error running test {category}:{test_name}: {str(e)}")
        return 1, "", str(e)


def run_category(category: str) -> bool:
    """Run all tests in a category."""
    if category not in TEST_CONFIG:
        logger.error(f"Unknown test category: {category}")
        return False
    
    logger.info(f"Running all tests in category: {category}")
    tests = TEST_CONFIG[category]
    all_passed = True
    
    for test_name, test_config in tests.items():
        result, stdout, stderr = run_test(category, test_name, test_config)
        
        if result != 0:
            all_passed = False
            logger.error(f"Test {category}:{test_name} failed")
            logger.error(f"STDOUT:\n{stdout}")
            logger.error(f"STDERR:\n{stderr}")
        else:
            logger.info(f"Test {category}:{test_name} passed")
    
    return all_passed


def run_specific_test(test_spec: str) -> bool:
    """Run a specific test identified by category:test_name."""
    parts = test_spec.split(":")
    if len(parts) != 2:
        logger.error(f"Invalid test specification: {test_spec}. Use format 'category:test_name'")
        return False
    
    category, test_name = parts
    
    if category not in TEST_CONFIG:
        logger.error(f"Unknown test category: {category}")
        return False
    
    if test_name not in TEST_CONFIG[category]:
        logger.error(f"Unknown test name: {test_name} in category {category}")
        return False
    
    test_config = TEST_CONFIG[category][test_name]
    result, stdout, stderr = run_test(category, test_name, test_config)
    
    if result == 0:
        logger.info(f"Test {category}:{test_name} passed")
        logger.info(f"STDOUT:\n{stdout}")
        if stderr:
            logger.info(f"STDERR:\n{stderr}")
        return True
    else:
        logger.error(f"Test {category}:{test_name} failed with code {result}")
        logger.error(f"STDOUT:\n{stdout}")
        logger.error(f"STDERR:\n{stderr}")
        return False


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="MCP Test Runner")
    
    # Define mutually exclusive group for test selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-all", action="store_true", help="Run all tests")
    group.add_argument("--run-category", help="Run all tests in the specified category")
    group.add_argument("--run", help="Run a specific test (format: category:test_name)")
    group.add_argument("--list", action="store_true", help="List all available tests")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available tests:")
        for category, tests in TEST_CONFIG.items():
            print(f"\n{category}:")
            for test_name, test_config in tests.items():
                print(f"  - {test_name}: {test_config['module']}")
        return 0
    
    if args.run_all:
        logger.info("Running all tests")
        all_passed = True
        for category in TEST_CONFIG:
            if not run_category(category):
                all_passed = False
        return 0 if all_passed else 1
    
    if args.run_category:
        logger.info(f"Running all tests in category: {args.run_category}")
        return 0 if run_category(args.run_category) else 1
    
    if args.run:
        logger.info(f"Running test: {args.run}")
        return 0 if run_specific_test(args.run) else 1


if __name__ == "__main__":
    sys.exit(main()) 