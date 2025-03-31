#!/usr/bin/env python
"""
Agent Memory Integration Test

Este script demuestra cómo los agentes pueden usar el sistema de memoria
para recordar información y mejorar sus respuestas a lo largo del tiempo.
"""

import os
import sys
import time
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta


# Add parent directory to path
current_dir = Path(__file__).resolve().parent
parent_dir = str(current_dir.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    env_path = os.path.join(parent_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Variables de entorno cargadas desde {env_path}")
        
        # Verificar que la API key de Google se haya cargado
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if google_api_key:
            print(f"✅ Google API key encontrada: {google_api_key[:10]}...")
        else:
            print("⚠️ ADVERTENCIA: GOOGLE_API_KEY no encontrada en variables de entorno")
    else:
        print(f"⚠️ ADVERTENCIA: Archivo .env no encontrado en {env_path}")
except ImportError:
    print("⚠️ ADVERTENCIA: python-dotenv no está instalado. No se pudieron cargar variables de entorno.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("agent_memory_test")

# Import agent modules
from agents import (
    EchoAgent, 
    CodeAgent, 
    SystemAgent,
    AgentCommunicator,
    setup_communication_system,
    shutdown_communication_system
)

# Import memory modules
from memory.core.memory_manager import MemoryManager


async def setup_memory_manager():
    """
    Configurar un sistema de memoria para los agentes.
    
    Returns:
        MemoryManager: El gestor de memoria configurado
    """
    # Crear directorio temporal para la memoria
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="agent_memory_test_")
    logger.info(f"Directorio temporal para memoria: {temp_dir}")
    
    # Configurar MemoryManager
    memory_config = {
        "use_long_term_memory": True,
        "use_episodic_memory": True,
        "use_semantic_memory": True,
        "short_term_memory": {
            "retention_minutes": 60,
            "capacity": 100
        }
    }
    
    memory_manager = MemoryManager(
        config=memory_config,
        data_dir=temp_dir
    )
    
    logger.info("Sistema de memoria inicializado")
    return memory_manager


async def setup_agents_with_memory(memory_manager):
    """
    Configurar agentes con el sistema de memoria.
    
    Args:
        memory_manager: El gestor de memoria a utilizar
        
    Returns:
        dict: Diccionario con los agentes configurados
    """
    # Configurar ModelManager con Gemini prioritariamente
    from models.core.model_manager import ModelManager
    
    # Verificar si existe la API key de Google (ya debería estar cargada del .env)
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if google_api_key:
        print(f"ℹ️ Usando API key de Google: {google_api_key[:10]}...")
    else:
        print("⚠️ ADVERTENCIA: Variable de entorno GOOGLE_API_KEY no encontrada.")
        print("   Se usará un modelo simulado o Mistral local para las pruebas")
    
    # Crear configuración temporal para el ModelManager
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
    
    # Verificar si existe el modelo local Mistral como respaldo
    mistral_path = os.path.join(os.getcwd(), "models", "local", "Mistral-7B-Instruct-v0.3.Q4_K_M.gguf")
    if os.path.exists(mistral_path):
        # Añadir modelo local Mistral como alternativa
        models_config["models"].append({
            "name": "mistral-7b-instruct",
            "model_type": "mistral",
            "local": True,
            "path": mistral_path,
            "context_length": 4096,
            "quantization": "q4_k_m"
        })
        print(f"✅ Modelo Mistral encontrado en: {mistral_path}")
    else:
        print(f"⚠️ Modelo Mistral no encontrado en: {mistral_path}")
    
    # Escribir configuración temporal a archivo
    config_path = os.path.join(os.getcwd(), "temp_model_config.json")
    with open(config_path, "w") as f:
        json.dump(models_config, f, indent=2)
    
    # Inicializar ModelManager con la configuración
    model_manager = ModelManager(config_path)
    print(f"ℹ️ ModelManager configurado con {len(models_config['models'])} modelos")
    
    # Eliminar el archivo temporal
    try:
        os.remove(config_path)
    except:
        pass
    
    # Crear EchoAgent
    echo_config = {
        "name": "Echo con Memoria",
        "description": "Agente que recuerda consultas anteriores"
    }
    echo_agent = EchoAgent("echo_memory", echo_config)
    echo_agent.setup_memory(shared_memory_manager=memory_manager)
    
    # Crear CodeAgent con el ModelManager
    code_config = {
        "name": "Asistente de Código con Memoria",
        "description": "Asistente que recuerda soluciones de código anteriores",
        "model_manager": model_manager,
        "model": "gemini-2.0-flash"  # Establecer explícitamente el modelo 
    }
    code_agent = CodeAgent("code_memory", code_config)
    code_agent.setup_memory(shared_memory_manager=memory_manager)
    
    # Crear SystemAgent
    system_config = {
        "name": "Gestor de Sistema con Memoria",
        "description": "Agente que recuerda operaciones anteriores",
        "working_dir": os.getcwd()
    }
    system_agent = SystemAgent("system_memory", system_config)
    system_agent.setup_memory(shared_memory_manager=memory_manager)
    
    # Devolver todos los agentes
    return {
        "echo": echo_agent,
        "code": code_agent,
        "system": system_agent
    }


async def test_echo_memory(echo_agent):
    """
    Demostrar cómo el EchoAgent puede recordar consultas anteriores.
    
    Args:
        echo_agent: Instancia de EchoAgent con memoria
    """
    print("\n=== Prueba de Memoria con EchoAgent ===")
    
    # Primera consulta
    print("\n1. Primera consulta (nueva):")
    query1 = "Hola, ¿cómo estás?"
    response1 = await echo_agent.process(query1)
    print(f"Query: '{query1}'")
    print(f"Response: '{response1.content}'")
    
    # Esperar un momento para asegurar que se guarde en memoria
    await asyncio.sleep(1)
    
    # Segunda consulta (distinta)
    print("\n2. Segunda consulta (distinta):")
    query2 = "¿Cuál es tu nombre?"
    response2 = await echo_agent.process(query2)
    print(f"Query: '{query2}'")
    print(f"Response: '{response2.content}'")
    
    # Esperar un momento
    await asyncio.sleep(1)
    
    # Tercera consulta (idéntica a la primera)
    print("\n3. Tercera consulta (repetida):")
    query3 = "Hola, ¿cómo estás?"  # Misma que query1
    response3 = await echo_agent.process(query3)
    print(f"Query: '{query3}'")
    print(f"Response: '{response3.content}'")
    
    # Verificar si ha detectado la repetición
    if "remembered" in response3.content.lower() or "before" in response3.content.lower():
        print("\n✅ ÉXITO: EchoAgent recordó haber visto la consulta antes")
    else:
        print("\n❌ FALLO: EchoAgent no detectó que era una consulta repetida")


async def test_code_memory(code_agent):
    """
    Demostrar cómo el CodeAgent puede recordar soluciones de código anteriores.
    
    Args:
        code_agent: Instancia de CodeAgent con memoria
    """
    print("\n=== Prueba de Memoria con CodeAgent ===")
    
    print("\n1. Almacenando memoria de código directamente:")
    factorial_code = """```python
def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n-1)
```"""
    
    # Almacenar directamente en memoria
    memory_id = code_agent.remember(
        content={
            "query": "Escribe una función en Python para calcular el factorial de un número",
            "language": "python",
            "task": "generate",
            "code": "",
            "response": factorial_code
        },
        importance=0.8,
        memory_type="code_interaction",
        metadata={
            "language": "python",
            "task": "generate",
            "contains_code": True
        }
    )
    print(f"Memoria almacenada con ID: {memory_id}")
    
    # Esperar un momento para asegurar que se guarde en memoria
    await asyncio.sleep(1)
    
    # Verificar si podemos recuperar la memoria
    print("\n2. Verificando si podemos recuperar la memoria:")
    memories = code_agent.recall(query="factorial", limit=5)
    
    if memories:
        print(f"✅ ÉXITO: Se encontraron {len(memories)} memorias para 'factorial'")
        for i, memory in enumerate(memories):
            if isinstance(memory.content, dict) and 'response' in memory.content:
                print(f"  {i+1}. Memory ID: {memory.id}")
                print(f"     Query original: {memory.content.get('query', 'N/A')}")
                print(f"     Código:\n{memory.content.get('response', '')[:150]}...")
            else:
                print(f"  {i+1}. {str(memory.content)[:150]}...")
    else:
        print("❌ FALLO: No se encontraron memorias para 'factorial'")
    
    # Prueba con una segunda consulta relacionada
    print("\n3. Probando consultas relacionadas:")
    
    # Probar múltiples variantes de consulta para debug
    test_queries = [
        "factorial de un número en Python",
        "factorial",
        "calcular factorial",
        "Python factorial function",
        "factorial recursive"
    ]
    
    for query in test_queries:
        # Verificar si podemos recuperar la memoria con la consulta relacionada
        memories = code_agent.recall(query=query, limit=5)
        print(f"\nConsulta: '{query}'")
        
        if memories:
            print(f"   ✅ Se encontraron {len(memories)} memorias")
            # Mostrar el primer resultado para ver relevancia
            mem = memories[0]
            if isinstance(mem.content, dict) and 'query' in mem.content:
                print(f"   Primera memoria: {mem.content['query']}")
                print(f"   Relevancia: {mem.metadata.get('relevance', 'N/A')}")
        else:
            print(f"   ❌ No se encontraron memorias")
    
    print("\n4. Análisis del sistema de memoria:")
    # Verificar la implementación de búsqueda directamente
    if hasattr(code_agent.memory_manager, "get_memory_system_details"):
        details = code_agent.memory_manager.get_memory_system_details()
        print(f"   Sistema de memoria: {details}")
    else:
        print("   No se puede obtener detalles del sistema de memoria")
        
    # Guardar otra memoria con contenido diferente para comparar
    print("\nGuardando memoria adicional para comparación:")
    code_agent.remember(
        content={
            "query": "Función para calcular suma de números",
            "language": "python",
            "task": "generate",
            "code": "",
            "response": """```python
def sum_numbers(numbers):
    return sum(numbers)
```"""
        },
        importance=0.7,
        memory_type="code_interaction",
        metadata={
            "language": "python",
            "task": "generate",
            "contains_code": True
        }
    )
    
    # Verificar todas las memorias directamente por tipo
    all_code_memories = []
    try:
        all_memories = code_agent.memory_manager.memory_system.get_all_memories(limit=50)
        for mem in all_memories:
            if mem.memory_type == "code_interaction":
                all_code_memories.append(mem)
                
        print(f"\nTotal memorias de código: {len(all_code_memories)}")
        for i, mem in enumerate(all_code_memories):
            if isinstance(mem.content, dict):
                query = mem.content.get("query", "N/A")
                print(f"  {i+1}. ID: {mem.id} - Query: {query}")
    except Exception as e:
        print(f"Error analizando memorias: {str(e)}")


async def test_system_memory(system_agent):
    """
    Demostrar cómo el SystemAgent puede recordar operaciones anteriores.
    
    Args:
        system_agent: Instancia de SystemAgent con memoria
    """
    print("\n=== Prueba de Memoria con SystemAgent ===")
    
    # Primera operación de sistema
    print("\n1. Primera operación (listar archivos):")
    query1 = "Listar archivos en el directorio actual"
    context1 = {"action": "list_files", "parameters": {"path": "."}}
    response1 = await system_agent.process(query1, context1)
    print(f"Query: '{query1}'")
    print(f"Response (extracto):\n{response1.content[:200]}...")
    
    # Esperar un momento
    await asyncio.sleep(1)
    
    # Segunda operación sin especificar path (debería usar el de memoria)
    print("\n2. Segunda operación (sin especificar path):")
    query2 = "Muéstrame otra vez los archivos del directorio anterior que consulté hace un momento"
    # Forzamos uso de memoria añadiendo una referencia explícita al pasado
    # y no especificando un path
    context2 = {
        "action": "list_files",
        "use_memory": True  # Indicador explícito para usar memoria
    }  # Sin especificar path
    response2 = await system_agent.process(query2, context2)
    print(f"Query: '{query2}'")
    print(f"Response (extracto):\n{response2.content[:200]}...")
    
    # Verificar si ha utilizado la memoria
    memory_used = response2.metadata.get("memory_used", False)
    used_memory_for_params = response2.metadata.get("used_memory_for_params", False)
    
    if memory_used or used_memory_for_params:
        print(f"\n✅ ÉXITO: SystemAgent utilizó la memoria para determinar la ruta")
        if "operations_found" in response2.metadata:
            print(f"Encontró {response2.metadata.get('operations_found', 0)} operaciones previas")
        if used_memory_for_params:
            print(f"Utilizó memoria para deducir parámetros: {used_memory_for_params}")
    else:
        print("\n❓ INFO: SystemAgent no utilizó memorias anteriores (verificar logs)")
        # Verificar si hay memorias relevantes
        memories = system_agent.recall(query="list_files", limit=3)
        if memories:
            print(f"  ⚠️ NOTA: Encontré {len(memories)} memorias sobre operaciones de archivos que no se utilizaron:")
            for i, memory in enumerate(memories):
                if isinstance(memory.content, dict):
                    print(f"    {i+1}. {json.dumps(memory.content)[:150]}...")
                else:
                    print(f"    {i+1}. {str(memory.content)[:150]}...")


async def test_cross_agent_memory(agents, memory_manager):
    """
    Demostrar cómo los agentes pueden compartir memoria entre ellos.
    
    Args:
        agents: Diccionario con las instancias de agentes
        memory_manager: El gestor de memoria compartido
    """
    print("\n=== Prueba de Memoria Compartida entre Agentes ===")
    
    # SystemAgent guarda información sobre archivos en un directorio
    print("\n1. SystemAgent guarda información sobre archivos:")
    system_query = "Listar archivos en el directorio examples"
    system_context = {"action": "list_files", "parameters": {"path": "examples"}}
    
    try:
        system_response = await agents["system"].process(system_query, system_context)
        print(f"SystemAgent responde con {len(system_response.content)} caracteres")
        
        # Si la respuesta fue exitosa, esperar para que se guarde en memoria
        await asyncio.sleep(1)
    except Exception as e:
        print(f"⚠️ Error con SystemAgent: {str(e)}")
        # En caso de error, guardamos manualmente una entrada en memoria
        print("Guardando una entrada manual en memoria...")
        
        agents["system"].remember(
            content={
                "action": "list_files",
                "query": system_query,
                "path": "examples",
                "result": "integration/\nmemory/\nagents/\nREADME.md\nbrave_mcp_test.log\nmcp/\nconfig/\nmodels/"
            },
            importance=0.7,
            memory_type="system_operation",
            metadata={
                "action_type": "list_files",
                "working_dir": os.getcwd()
            }
        )
    
    # Esperar un momento para asegurar que se guarde en memoria
    await asyncio.sleep(1)
    
    # CodeAgent busca información sobre archivos (puede ser directamente de la memoria)
    print("\n2. CodeAgent busca información sobre archivos en examples:")
    code_query = "¿Qué archivos hay en el directorio examples?"
    
    try:
        code_response = await agents["code"].process(code_query)
        print(f"CodeAgent responde:")
        print(f"Response (extracto):\n{code_response.content[:200]}...")
    except Exception as e:
        print(f"⚠️ Error con CodeAgent: {str(e)}")
    
    # Verificar directamente en la memoria compartida (esto siempre debería funcionar)
    print("\n3. Verificación directa de memoria compartida:")
    # Usar la versión correcta del memory_manager, que sí admite content_query
    all_memories = memory_manager.query_memories(content_query="examples", limit=10)
    
    if all_memories:
        print(f"\n✅ INFO: Se encontraron {len(all_memories)} memorias relacionadas con 'examples'")
        for i, mem in enumerate(all_memories):
            source = mem.metadata.get("agent_id", "unknown")
            if isinstance(mem.content, dict):
                content_str = json.dumps(mem.content, ensure_ascii=False)[:100]
            else:
                content_str = str(mem.content)[:100]
            print(f"  {i+1}. Memoria de {source}: {content_str}...")
    else:
        print("\n❓ INFO: No se encontraron memorias compartidas relacionadas con 'examples'")
        
    # Verificar cuántas memorias tiene cada agente
    print("\n4. Verificación de memoria por agente:")
    for agent_id, agent in agents.items():
        if agent.has_memory():
            try:
                # 1. Obtener todas las memorias del sistema de memoria
                all_memories = agent.memory_manager.memory_system.get_all_memories(limit=500)
                
                # 2. Filtrado manual considerando diferentes formatos posibles de metadata
                agent_memories = []
                for mem in all_memories:
                    # Verificar diferentes posibles ubicaciones/formatos del agent_id
                    memoria_del_agente = False
                    
                    # Formato directo en metadata
                    if mem.metadata.get("agent_id") == agent_id:
                        memoria_del_agente = True
                    
                    # En metadata.source
                    elif mem.metadata.get("source") == agent_id:
                        memoria_del_agente = True
                    
                    # En metadata.metadata.agent_id (anidado)
                    elif isinstance(mem.metadata.get("metadata"), dict) and mem.metadata["metadata"].get("agent_id") == agent_id:
                        memoria_del_agente = True
                    
                    # En content.agent_id si content es un diccionario
                    elif isinstance(mem.content, dict) and mem.content.get("agent_id") == agent_id:
                        memoria_del_agente = True
                    
                    # Verificar si hay una mención al agente en cualquier parte del content como string
                    elif isinstance(mem.content, str) and agent_id in mem.content:
                        memoria_del_agente = True
                    
                    # Si encuentro agent_id en cualquier valor de metadata como string
                    else:
                        for key, value in mem.metadata.items():
                            if isinstance(value, str) and agent_id in value:
                                memoria_del_agente = True
                                break
                    
                    if memoria_del_agente:
                        agent_memories.append(mem)
                
                print(f"Agente '{agent_id}' tiene {len(agent_memories)} memorias almacenadas.")
                
                # Mostrar los tipos de memoria
                memory_types = {}
                for mem in agent_memories:
                    memory_type = mem.memory_type
                    if memory_type not in memory_types:
                        memory_types[memory_type] = 0
                    memory_types[memory_type] += 1
                
                for mem_type, count in memory_types.items():
                    print(f"  - Tipo '{mem_type}': {count} memorias")
                
                # Si no encontramos ninguna por ID, mostrar información adicional para debug
                if not agent_memories:
                    print(f"  ⚠️ Advertencia: No se encontraron memorias para el agent_id '{agent_id}'")
                    print(f"  ℹ️ Mostrando metadatos de algunas memorias como referencia:")
                    for i, mem in enumerate(all_memories[:3]):
                        print(f"    Memoria {i+1}: {mem.memory_type}, metadata: {mem.metadata}")
                
            except Exception as e:
                print(f"Error al obtener memorias del agente '{agent_id}': {str(e)}")
        else:
            print(f"Agente '{agent_id}' no tiene memoria configurada.")


async def main():
    """Función principal"""
    logger.info("Iniciando pruebas de integración de memoria con agentes")
    
    try:
        # Configurar sistema de comunicación
        communicator = await setup_communication_system()
        logger.info("Sistema de comunicación inicializado")
        
        # Configurar sistema de memoria
        memory_manager = await setup_memory_manager()
        
        # Configurar agentes con memoria
        agents = await setup_agents_with_memory(memory_manager)
        logger.info("Agentes configurados con memoria")
        
        # Registrar agentes con el comunicador
        for agent in agents.values():
            await agent.register_with_communicator()
        
        # Ejecutar pruebas de memoria
        await test_echo_memory(agents["echo"])
        await test_code_memory(agents["code"])
        await test_system_memory(agents["system"])
        await test_cross_agent_memory(agents, memory_manager)
        
        print("\n✅ Pruebas de integración de memoria completadas")
        
    except Exception as e:
        logger.error(f"Error en pruebas: {str(e)}", exc_info=True)
        print(f"\n❌ Error en pruebas: {str(e)}")
    finally:
        # Cerrar sistema de comunicación
        await shutdown_communication_system()
        logger.info("Sistema de comunicación cerrado")


if __name__ == "__main__":
    asyncio.run(main()) 