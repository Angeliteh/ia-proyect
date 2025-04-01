#!/usr/bin/env python
"""
Pruebas Avanzadas para Sistema Multi-Agente.

Este script implementa pruebas más complejas y realistas para evaluar 
el rendimiento del sistema en escenarios del mundo real.
"""

import os
import sys
import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Asegurar que el directorio raíz esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("advanced_testing")

# Importaciones del sistema
from models.core.model_manager import ModelManager
from mcp_servers.memory import MemoryServer
from mcp.clients import SimpleDirectClient
from agents.specialized.memory_agent import MemoryAgent
from agents.main_assistant.main_assistant import MainAssistant
from agents.agent_communication import setup_communication_system, communicator, shutdown_communication_system
from multi_agent_demo import setup_memory_system, setup_agents, add_example_memories

# Escenarios de prueba avanzados
class TestScenarios:
    """Define escenarios de prueba realistas para el sistema."""
    
    @staticmethod
    def code_development_scenario() -> List[Dict]:
        """
        Escenario: Un desarrollador trabajando en un proyecto de Python.
        
        Evalúa el sistema en su capacidad para asistir en tareas de programación
        reales, debugging, y consultas relacionadas con desarrollo.
        """
        return [
            {
                "name": "Inicio de proyecto",
                "query": "Quiero crear un proyecto de Python para analizar datos de ventas desde archivos CSV. ¿Cómo organizarías la estructura del proyecto?",
                "expected_agent": "code",
                "expected_concepts": ["estructura de proyecto", "análisis datos", "python", "csv"]
            },
            {
                "name": "Solicitud de código específico",
                "query": "Escribe una función que lea archivos CSV y los convierta en un DataFrame de pandas, manejando errores comunes como celdas vacías",
                "expected_agent": "code",
                "expected_concepts": ["pandas", "dataframe", "csv", "manejo errores"]
            },
            {
                "name": "Consulta de error",
                "query": "Estoy recibiendo el error 'KeyError: 'ventas'' cuando intento acceder a una columna del DataFrame. ¿Qué puede estar pasando?",
                "expected_agent": "code",
                "expected_concepts": ["keyerror", "dataframe", "debugging", "pandas"]
            },
            {
                "name": "Mejora de rendimiento",
                "query": "El procesamiento es muy lento con archivos grandes. ¿Cómo puedo optimizar mi código de pandas para manejar millones de filas?",
                "expected_agent": "code",
                "expected_concepts": ["optimización", "pandas", "rendimiento", "big data"]
            },
            {
                "name": "Integración con otras herramientas",
                "query": "¿Cómo puedo integrar mi análisis de datos con una visualización web usando Dash o Streamlit?",
                "expected_agent": "code",
                "expected_concepts": ["dash", "streamlit", "visualización", "web"]
            }
        ]
    
    @staticmethod
    def system_operations_scenario() -> List[Dict]:
        """
        Escenario: Un administrador de sistemas gestionando servidores.
        
        Evalúa el sistema en su capacidad para asistir con operaciones
        de sistema, automatización y gestión de infraestructura.
        """
        return [
            {
                "name": "Consulta de configuración",
                "query": "¿Cómo puedo configurar un servidor Nginx para servir una aplicación web Python con uWSGI?",
                "expected_agent": "system",
                "expected_concepts": ["nginx", "uwsgi", "servidor web", "configuración"]
            },
            {
                "name": "Script de automatización",
                "query": "Necesito un script para hacer backups automáticos de una base de datos PostgreSQL y subirlos a S3",
                "expected_agent": "system",
                "expected_concepts": ["backup", "postgresql", "s3", "automatización"]
            },
            {
                "name": "Troubleshooting",
                "query": "Mi servidor Linux tiene el CPU al 100% constantemente. ¿Qué comandos puedo usar para diagnosticar el problema?",
                "expected_agent": "system",
                "expected_concepts": ["linux", "cpu", "diagnóstico", "rendimiento"]
            },
            {
                "name": "Seguridad",
                "query": "¿Cuáles son las mejores prácticas para asegurar un servidor web expuesto a internet?",
                "expected_agent": "system",
                "expected_concepts": ["seguridad", "hardening", "firewall", "https"]
            }
        ]
    
    @staticmethod
    def knowledge_inquiry_scenario() -> List[Dict]:
        """
        Escenario: Consultas de conocimiento sobre tecnología y desarrollo.
        
        Evalúa el sistema en su capacidad para proporcionar información
        técnica precisa y útil desde su base de conocimientos.
        """
        return [
            {
                "name": "Conceptos fundamentales",
                "query": "Explícame el concepto de contenedores y cómo difieren de las máquinas virtuales",
                "expected_agent": "memory",
                "expected_concepts": ["contenedores", "docker", "máquinas virtuales", "virtualización"]
            },
            {
                "name": "Arquitectura software",
                "query": "¿Qué es la arquitectura hexagonal y en qué situaciones es útil aplicarla?",
                "expected_agent": "memory",
                "expected_concepts": ["arquitectura hexagonal", "puertos y adaptadores", "clean architecture"]
            },
            {
                "name": "Tecnologías emergentes",
                "query": "¿Cómo funcionan los modelos de aprendizaje por refuerzo y dónde se aplican?",
                "expected_agent": "memory",
                "expected_concepts": ["refuerzo", "RL", "machine learning", "aplicaciones"]
            },
            {
                "name": "Historia tecnológica",
                "query": "¿Cómo ha evolucionado JavaScript desde sus inicios hasta hoy?",
                "expected_agent": "memory",
                "expected_concepts": ["javascript", "evolución", "ecmascript", "historia"]
            }
        ]
    
    @staticmethod
    def multi_step_conversation() -> List[Dict]:
        """
        Escenario: Conversación multi-paso sobre un tema complejo.
        
        Evalúa la capacidad del sistema para mantener contexto y
        manejar una conversación extendida sobre un tema.
        """
        return [
            {
                "name": "Inicio de proyecto",
                "query": "Quiero desarrollar una aplicación web para gestionar tareas en equipo",
                "expected_agent": "orchestrator",
                "expected_concepts": ["aplicación web", "gestión tareas", "planificación"]
            },
            {
                "name": "Seguimiento tecnológico",
                "query": "¿Qué stack tecnológico me recomiendas para este tipo de aplicación?",
                "expected_agent": "code",
                "expected_concepts": ["stack", "tecnologías", "recomendación", "web"]
            },
            {
                "name": "Arquitectura de datos",
                "query": "¿Cómo debería diseñar la base de datos para las tareas, usuarios y equipos?",
                "expected_agent": "code",
                "expected_concepts": ["modelo datos", "relaciones", "entidades", "database"]
            },
            {
                "name": "Implementación específica",
                "query": "Muéstrame cómo implementaría un sistema de notificaciones en tiempo real",
                "expected_agent": "code",
                "expected_concepts": ["notificaciones", "tiempo real", "websockets", "implementación"]
            },
            {
                "name": "Despliegue",
                "query": "¿Cuál sería el mejor enfoque para desplegar esta aplicación?",
                "expected_agent": "system",
                "expected_concepts": ["despliegue", "infraestructura", "cloud", "CI/CD"]
            }
        ]
    
    @staticmethod
    def get_all_scenarios() -> Dict[str, List[Dict]]:
        """Devuelve todos los escenarios de prueba disponibles."""
        return {
            "code_development": TestScenarios.code_development_scenario(),
            "system_operations": TestScenarios.system_operations_scenario(),
            "knowledge_inquiry": TestScenarios.knowledge_inquiry_scenario(),
            "multi_step_conversation": TestScenarios.multi_step_conversation()
        }


async def run_scenario_tests(main_assistant, scenario_name, scenario_queries):
    """
    Ejecuta un escenario de prueba completo.
    
    Args:
        main_assistant: Instancia del MainAssistant
        scenario_name: Nombre del escenario
        scenario_queries: Lista de consultas del escenario
    
    Returns:
        Resultados del escenario
    """
    logger.info(f"\n\n=== ESCENARIO: {scenario_name} ===")
    
    results = {
        "scenario": scenario_name,
        "queries": [],
        "summary": {
            "total": len(scenario_queries),
            "success": 0,
            "agent_match": 0,
            "avg_response_time": 0
        }
    }
    
    total_time = 0
    
    # Contexto compartido para la conversación
    conversation_context = {}
    
    for i, query_info in enumerate(scenario_queries):
        query = query_info["query"]
        expected_agent = query_info.get("expected_agent", "any")
        expected_concepts = query_info.get("expected_concepts", [])
        
        logger.info(f"\n--- Paso {i+1}: {query_info['name']} ---")
        logger.info(f"Consulta: {query}")
        logger.info(f"Agente esperado: {expected_agent}")
        logger.info(f"Conceptos esperados: {', '.join(expected_concepts)}")
        
        query_result = {
            "name": query_info["name"],
            "query": query,
            "expected_agent": expected_agent,
            "expected_concepts": expected_concepts,
        }
        
        try:
            # Procesar la consulta
            start_time = time.time()
            response = await main_assistant.process(query, conversation_context)
            elapsed_time = time.time() - start_time
            
            # Actualizar contexto de conversación
            conversation_context["last_query"] = query
            conversation_context["last_response"] = response.content
            if "conversation_history" not in conversation_context:
                conversation_context["conversation_history"] = []
            conversation_context["conversation_history"].append({
                "query": query,
                "response": response.content
            })
            
            # Analizar respuesta
            logger.info(f"Respuesta ({elapsed_time:.2f}s): {response.content[:200]}...")
            logger.info(f"Estado: {response.status}")
            
            # Analizar agente utilizado
            agent_used = response.metadata.get("agent_used", "directa")
            logger.info(f"Agente utilizado: {agent_used}")
            
            # Verificar conceptos esperados
            concepts_found = 0
            for concept in expected_concepts:
                if concept.lower() in response.content.lower():
                    concepts_found += 1
                    logger.info(f"✓ Concepto encontrado: {concept}")
                else:
                    logger.info(f"✗ Concepto no encontrado: {concept}")
            
            concept_coverage = concepts_found / len(expected_concepts) if expected_concepts else 1.0
            logger.info(f"Cobertura de conceptos: {concept_coverage:.2f}")
            
            # Actualizar estadísticas
            total_time += elapsed_time
            
            if response.status == "success":
                results["summary"]["success"] += 1
            
            # Verificar si el agente coincide con el esperado
            agent_match = (expected_agent == "any" or 
                          agent_used == expected_agent or 
                          (agent_used is None and expected_agent == "directa"))
            
            if agent_match:
                results["summary"]["agent_match"] += 1
                logger.info("✅ Agente correcto")
            else:
                logger.info(f"❌ Agente incorrecto (se esperaba {expected_agent})")
            
            # Guardar resultados de esta consulta
            query_result.update({
                "response": response.content,
                "agent_used": agent_used,
                "response_time": elapsed_time,
                "status": response.status,
                "agent_match": agent_match,
                "concept_coverage": concept_coverage,
                "concepts_found": concepts_found,
                "total_concepts": len(expected_concepts)
            })
            
            results["queries"].append(query_result)
            
            # Esperar entre consultas
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error procesando consulta: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            query_result.update({
                "error": str(e),
                "status": "error",
                "agent_match": False,
                "concept_coverage": 0
            })
            results["queries"].append(query_result)
    
    # Calcular estadísticas finales
    if results["queries"]:
        results["summary"]["avg_response_time"] = total_time / len(results["queries"])
    
    # Mostrar resumen
    logger.info(f"\n=== RESUMEN DEL ESCENARIO: {scenario_name} ===")
    logger.info(f"Consultas exitosas: {results['summary']['success']}/{results['summary']['total']}")
    logger.info(f"Agente correcto: {results['summary']['agent_match']}/{results['summary']['total']}")
    logger.info(f"Tiempo promedio de respuesta: {results['summary']['avg_response_time']:.2f}s")
    
    return results


async def run_all_scenarios(main_assistant):
    """
    Ejecuta todos los escenarios de prueba disponibles.
    
    Args:
        main_assistant: Instancia del MainAssistant
    
    Returns:
        Resultados de todos los escenarios
    """
    all_scenarios = TestScenarios.get_all_scenarios()
    all_results = {}
    
    for scenario_name, scenario_queries in all_scenarios.items():
        scenario_results = await run_scenario_tests(
            main_assistant,
            scenario_name,
            scenario_queries
        )
        all_results[scenario_name] = scenario_results
    
    # Calcular estadísticas generales
    total_queries = sum(len(scenario["queries"]) for scenario in all_results.values())
    total_success = sum(scenario["summary"]["success"] for scenario in all_results.values())
    total_agent_match = sum(scenario["summary"]["agent_match"] for scenario in all_results.values())
    avg_response_time = sum(scenario["summary"]["avg_response_time"] * len(scenario["queries"]) 
                          for scenario in all_results.values()) / total_queries if total_queries else 0
    
    logger.info("\n\n=== RESUMEN GENERAL DE PRUEBAS ===")
    logger.info(f"Total de escenarios: {len(all_results)}")
    logger.info(f"Total de consultas: {total_queries}")
    logger.info(f"Consultas exitosas: {total_success}/{total_queries} ({total_success/total_queries*100:.1f}%)")
    logger.info(f"Agente correcto: {total_agent_match}/{total_queries} ({total_agent_match/total_queries*100:.1f}%)")
    logger.info(f"Tiempo promedio de respuesta: {avg_response_time:.2f}s")
    
    # Resultados por escenario
    logger.info("\nRendimiento por escenario:")
    for scenario_name, scenario in all_results.items():
        success_rate = scenario["summary"]["success"] / scenario["summary"]["total"] * 100
        agent_match_rate = scenario["summary"]["agent_match"] / scenario["summary"]["total"] * 100
        logger.info(f"- {scenario_name}: {success_rate:.1f}% éxito, {agent_match_rate:.1f}% agente correcto")
    
    return {
        "scenarios": all_results,
        "summary": {
            "total_scenarios": len(all_results),
            "total_queries": total_queries,
            "total_success": total_success,
            "total_agent_match": total_agent_match,
            "success_rate": total_success/total_queries if total_queries else 0,
            "agent_match_rate": total_agent_match/total_queries if total_queries else 0,
            "avg_response_time": avg_response_time
        }
    }


async def run_selective_tests(main_assistant, scenarios=None):
    """
    Ejecuta escenarios selectivos.
    
    Args:
        main_assistant: Instancia del MainAssistant
        scenarios: Lista de nombres de escenarios a ejecutar (o None para todos)
    
    Returns:
        Resultados de los escenarios ejecutados
    """
    all_scenarios = TestScenarios.get_all_scenarios()
    
    if scenarios:
        selected_scenarios = {name: all_scenarios[name] for name in scenarios if name in all_scenarios}
    else:
        selected_scenarios = all_scenarios
    
    if not selected_scenarios:
        logger.error("No se encontraron escenarios válidos para ejecutar")
        return None
    
    results = {}
    for scenario_name, scenario_queries in selected_scenarios.items():
        scenario_results = await run_scenario_tests(
            main_assistant,
            scenario_name,
            scenario_queries
        )
        results[scenario_name] = scenario_results
    
    return results


async def main():
    """Función principal que ejecuta las pruebas avanzadas."""
    logger.info("Iniciando pruebas avanzadas del sistema multi-agente")
    
    try:
        # 1. Configurar directorio para datos
        data_dir = os.path.join(project_root, "examples/data/advanced_testing")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Directorio de datos: {os.path.abspath(data_dir)}")
        
        # Crear subdirectorios por agente
        agent_data_dirs = {
            "memory": os.path.join(data_dir, "memory_agent"),
            "main": os.path.join(data_dir, "main_assistant"),
            "code": os.path.join(data_dir, "code_agent"),
            "system": os.path.join(data_dir, "system_agent"),
            "echo": os.path.join(data_dir, "echo_agent"),
            "orchestrator": os.path.join(data_dir, "orchestrator_agent")
        }
        
        # Crear todos los subdirectorios
        for dir_path in agent_data_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # 2. Configurar sistema de memoria
        memory_server, memory_client = await setup_memory_system(agent_data_dirs["memory"])
        
        # 3. Configurar agentes
        agent_config = {
            "memory_client": memory_client,
            "data_dirs": agent_data_dirs,
            "data_dir": data_dir
        }
        agents = await setup_agents(memory_client, agent_config)
        
        # 4. Añadir memorias de ejemplo
        await add_example_memories(agents["memory"])
        
        # 5. Ejecutar pruebas avanzadas
        logger.info("\n=== INICIANDO PRUEBAS AVANZADAS ===")
        
        # Puedes cambiar esto para ejecutar solo escenarios específicos
        scenarios_to_run = [
            "code_development",
            "knowledge_inquiry"
        ]
        
        if len(sys.argv) > 1 and sys.argv[1] == "--all":
            # Ejecutar todos los escenarios
            results = await run_all_scenarios(agents["main_assistant"])
        elif len(sys.argv) > 1:
            # Ejecutar escenarios específicos desde la línea de comandos
            scenarios_to_run = sys.argv[1:]
            results = await run_selective_tests(agents["main_assistant"], scenarios_to_run)
        else:
            # Ejecutar escenarios predeterminados
            results = await run_selective_tests(agents["main_assistant"], scenarios_to_run)
        
        # 6. Guardar resultados en un archivo JSON
        results_path = os.path.join(data_dir, "test_results.json")
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Resultados guardados en: {results_path}")
        
        # 7. Limpiar y cerrar
        logger.info("Pruebas finalizadas. Cerrando conexiones...")
        memory_client.disconnect()
        await shutdown_communication_system()
        
        logger.info("Todas las pruebas completadas correctamente")
        return True
    
    except Exception as e:
        logger.error(f"Error en las pruebas: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Intentar limpiar recursos en caso de error
        try:
            if 'memory_client' in locals() and memory_client:
                memory_client.disconnect()
            await shutdown_communication_system()
        except Exception as cleanup_error:
            logger.error(f"Error al limpiar recursos: {cleanup_error}")
        return False


if __name__ == "__main__":
    asyncio.run(main()) 