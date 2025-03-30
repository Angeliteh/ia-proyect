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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("code_agent_example")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/agents
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

# Intentar importar el agente real
try:
    # Importar directamente desde el módulo de agentes
    from agents import CodeAgent
    logger.info("Módulo CodeAgent importado correctamente")
    USING_REAL_MODULES = True
except ImportError as e:
    logger.warning(f"No se pudo importar CodeAgent: {e}")
    logger.info("Usando implementación simulada para demostración")
    USING_REAL_MODULES = False
    
    # Implementación mínima para demostración
    class AgentResponse:
        def __init__(self, content, metadata=None):
            self.content = content
            self.metadata = metadata or {}
    
    class CodeAgent:
        def __init__(self, agent_id, config=None):
            self.agent_id = agent_id
            self.config = config or {}
            self.model = config.get("model", "demo-model") if config else "demo-model"
            logger.info(f"Iniciando CodeAgent simulado con modelo: {self.model}")
        
        def get_capabilities(self):
            return ["generate", "explain", "improve", "fix"]
        
        async def process(self, query, context=None):
            """Procesa una solicitud y devuelve una respuesta simulada."""
            await asyncio.sleep(1)  # Simular procesamiento
            
            task = context.get("task", "generate") if context else "generate"
            
            if task == "generate":
                return AgentResponse(
                    content='''def sieve_of_eratosthenes(limit):
    """Encuentra todos los números primos hasta un límite usando el Algoritmo de Eratóstenes."""
    # Inicializar array booleano con True
    primes = [True for _ in range(limit + 1)]
    p = 2
    
    while p * p <= limit:
        # Si p es primo, marcar todos sus múltiplos como no primos
        if primes[p]:
            for i in range(p * p, limit + 1, p):
                primes[i] = False
        p += 1
    
    # Crear lista de números primos
    prime_numbers = []
    for p in range(2, limit + 1):
        if primes[p]:
            prime_numbers.append(p)
            
    return prime_numbers

# Ejemplo de uso
if __name__ == "__main__":
    limit = 50
    print(f"Números primos hasta {limit}: {sieve_of_eratosthenes(limit)}")
''',
                    metadata={"model": self.model, "tokens_generated": 250}
                )
            elif task == "explain":
                return AgentResponse(
                    content='''Explicación del código:

Este código implementa dos funciones matemáticas clásicas:

1. `factorial(n)`: Calcula el factorial de un número n utilizando recursión.
   - Caso base: Si n es 0, devuelve 1
   - Caso recursivo: Devuelve n multiplicado por factorial(n-1)
   
2. `fibonacci(n)`: Calcula el n-ésimo número de la secuencia de Fibonacci usando recursión.
   - Caso base 1: Si n ≤ 0, devuelve 0
   - Caso base 2: Si n = 1, devuelve 1
   - Caso recursivo: Devuelve fibonacci(n-1) + fibonacci(n-2)

Problemas identificados:
1. La implementación de fibonacci es muy ineficiente, con complejidad O(2^n) debido a la recursión.
2. No hay validación de entrada, lo que podría llevar a un desbordamiento de pila si se usan números negativos o muy grandes.
3. Para fibonacci, incluso números moderadamente grandes causarán tiempos de ejecución muy largos debido a la redundancia de cálculos.''',
                    metadata={"model": self.model, "tokens_generated": 180}
                )
            elif task == "improve":
                return AgentResponse(
                    content='''# Versión mejorada

def factorial(n):
    """Calcula el factorial de n de forma iterativa."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("El factorial requiere un entero no negativo")
    
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

def fibonacci(n):
    """Calcula el n-ésimo número de Fibonacci de forma iterativa."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Fibonacci requiere un entero no negativo")
    
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Cálculos
try:
    # Factorial de 5
    result = factorial(5)
    print("Factorial de 5:", result)
    
    # 10º número de Fibonacci
    fib_result = fibonacci(10)
    print("10º número de Fibonacci:", fib_result)
except ValueError as e:
    print(f"Error: {e}")''',
                    metadata={"model": self.model, "tokens_generated": 220}
                )
            else:  # fix
                return AgentResponse(
                    content='''def calculate_average(numbers):
    """Calcula el promedio de una lista de números."""
    if not numbers:
        return 0  # Retornar 0 si la lista está vacía en lugar de causar división por cero
    
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
    
# Test con lista vacía
result = calculate_average([])
print("Average:", result)

# Test con lista no vacía
test_list = [1, 2, 3, 4, 5]
result = calculate_average(test_list)
print(f"Average of {test_list}: {result}")''',
                    metadata={"model": self.model, "tokens_generated": 150}
                )

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
    """Run the code agent example."""
    parser = argparse.ArgumentParser(description="Code Agent Example")
    parser.add_argument(
        "--task", 
        choices=["generate", "explain", "improve", "fix", "all"],
        default="all",
        help="Task to perform with the code agent"
    )
    parser.add_argument(
        "--model", 
        choices=["gemini-pro", "gemini-2.0-flash", "phi-2", "mistral-7b-instruct"],
        default="phi-2",
        help="Model to use for the agent"
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