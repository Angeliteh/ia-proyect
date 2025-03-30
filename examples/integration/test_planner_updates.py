#!/usr/bin/env python
"""
Test de Actualización de Tareas entre OrchestratorAgent y PlannerAgent

Este script prueba específicamente la funcionalidad de actualización de tareas
implementada entre el OrchestratorAgent y el PlannerAgent.
"""

import os
import sys
import logging
import asyncio
import json
from datetime import datetime

# Configurar logging con salida a consola
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # Asegurarse de que logs vayan a consola
    ]
)
logger = logging.getLogger("planner_updates_test")

# Imprimir mensaje de inicio
print("=== INICIANDO SCRIPT DE PRUEBA DE ACTUALIZACIÓN DE TAREAS ===")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_dir)

print(f"Path del proyecto: {project_dir}")
print("Importando módulos necesarios...")

# Importar los módulos necesarios
try:
    from agents import OrchestratorAgent, PlannerAgent, EchoAgent, CodeAgent, SystemAgent
    from agents.planning.task import TaskStatus
    from agents.agent_communication import setup_communication_system, shutdown_communication_system, send_agent_request
    print("Módulos importados correctamente")
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    sys.exit(1)

async def run_planner_update_test():
    """
    Ejecuta una prueba específica para la funcionalidad de actualización de tareas.
    """
    try:
        # Inicializar sistema de comunicación entre agentes
        print("Inicializando sistema de comunicación...")
        await setup_communication_system()
        
        print("\n=== INICIANDO PRUEBA DE ACTUALIZACIÓN DE TAREAS ===")
        
        # Crear agentes
        print("Creando agentes...")
        echo_agent = EchoAgent("echo_agent", {"name": "Echo"})
        code_agent = CodeAgent("code_agent", {"name": "Code"})
        system_agent = SystemAgent("system_agent", {"name": "System"})
        
        # Crear el agente planificador
        planner_agent = PlannerAgent("planner_agent", {
            "name": "Planner",
            "description": "Agente especializado en planificación de tareas",
            "max_history_size": 5
        })
        
        # Crear el agente orquestador
        orchestrator_agent = OrchestratorAgent("orchestrator_agent", {
            "name": "Orchestrator",
            "description": "Agente orquestador que coordina la ejecución de tareas",
            "max_concurrent_tasks": 3
        })
        
        # Registrar agentes con el orquestador
        print("Registrando agentes con el orquestador...")
        await orchestrator_agent.register_available_agent(
            "echo_agent", echo_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "code_agent", code_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "system_agent", system_agent.get_capabilities()
        )
        await orchestrator_agent.register_available_agent(
            "planner_agent", planner_agent.get_capabilities()
        )
        
        # Paso 1: Crear un plan utilizando el PlannerAgent
        # Usar una tarea más compleja que generará múltiples subtareas
        task_description = "Desarrollar una aplicación de gestión de tareas con frontend en HTML y backend en Python"
        print(f"\nPASO 1: Creando plan para: '{task_description}'")
        
        print("Enviando solicitud al PlannerAgent...")
        plan_response = await planner_agent.process(task_description)
        
        print("\nPlan creado con éxito:")
        print(plan_response.content)
        
        # Extraer información del plan
        plan_id = plan_response.metadata.get('plan_id', '')
        plan = plan_response.metadata.get('plan', {})
        
        print(f"ID del plan: {plan_id}")
        
        # Verificar que tenemos al menos una tarea para actualizar
        if not plan.get('execution_order') or not plan.get('tasks'):
            print("ERROR: El plan no contiene tareas para probar")
            return
            
        print(f"El plan contiene {len(plan['execution_order'])} tareas:")
        for i, task_id in enumerate(plan['execution_order']):
            task = plan['tasks'][task_id]
            print(f"  {i+1}. {task['description']} (ID: {task_id})")
        
        # Paso 2: Simular la ejecución de tareas y actualizaciones de estado
        print("\nPASO 2: Simulando ejecución y actualizaciones de tareas")
        
        # Procesar todas las tareas en el plan
        for i, task_id in enumerate(plan['execution_order']):
            task = plan['tasks'][task_id]
            task_desc = task['description']
            
            print(f"\nProcesando tarea {i+1}/{len(plan['execution_order'])}: {task_desc}")
            
            # Actualización 1: IN_PROGRESS
            print(f"Enviando actualización IN_PROGRESS para tarea {task_id}")
            update_msg = f"update_task:{task_id}:IN_PROGRESS"
            update_context = {
                "update_type": "task_status",
                "plan_id": plan_id,
                "task_id": task_id,
                "status": "IN_PROGRESS",
                "assigned_agent": "code_agent" if "código" in task_desc.lower() or "html" in task_desc.lower() else "system_agent"
            }
            
            update_response = await planner_agent.process(update_msg, update_context)
            print(f"Respuesta: {update_response.content}")
            
            # Simular trabajo en progreso
            print("  Simulando trabajo en progreso...")
            await asyncio.sleep(1)
            
            # Determinar si la tarea "falla" (para demostración, hacemos fallar la segunda tarea)
            should_fail = i == 1  # La segunda tarea fallará
            
            if should_fail:
                # Actualización: FAILED
                print(f"Enviando actualización FAILED para tarea {task_id}")
                update_msg = f"update_task:{task_id}:FAILED"
                update_context = {
                    "update_type": "task_status",
                    "plan_id": plan_id,
                    "task_id": task_id,
                    "status": "FAILED",
                    "error": "Error durante la implementación: Recurso no disponible"
                }
            else:
                # Actualización: COMPLETED
                print(f"Enviando actualización COMPLETED para tarea {task_id}")
                update_msg = f"update_task:{task_id}:COMPLETED"
                
                # Generar un resultado apropiado según el tipo de tarea
                result = ""
                if "frontend" in task_desc.lower() or "html" in task_desc.lower():
                    result = """<!DOCTYPE html>
<html>
<head>
    <title>Gestor de Tareas</title>
    <style>/* CSS básico para el gestor de tareas */</style>
</head>
<body>
    <h1>Gestor de Tareas</h1>
    <div id="task-container">
        <!-- Lista de tareas -->
    </div>
    <script src="app.js"></script>
</body>
</html>"""
                elif "backend" in task_desc.lower() or "python" in task_desc.lower():
                    result = """from flask import Flask, jsonify, request

app = Flask(__name__)
tasks = []

@app.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    task = request.json
    tasks.append(task)
    return jsonify(task), 201

if __name__ == '__main__':
    app.run(debug=True)"""
                else:
                    result = f"Tarea {i+1} completada con éxito"
                
                update_context = {
                    "update_type": "task_status",
                    "plan_id": plan_id,
                    "task_id": task_id,
                    "status": "COMPLETED",
                    "result": result
                }
            
            update_response = await planner_agent.process(update_msg, update_context)
            print(f"Respuesta: {update_response.content}")
        
        # Paso 3: Verificar el estado final del plan
        print("\nPASO 3: Verificando estado final del plan")
        
        # Obtener el plan actualizado
        plan_info = await planner_agent.get_plan(plan_id)
        
        if plan_info:
            print(f"Estado final del plan: {plan_info.status.name}")
            
            # Mostrar estado de todas las tareas
            print("Estado de las tareas:")
            for task_id, task in plan_info.tasks.items():
                print(f"- Tarea {task_id}: {task.description} - {task.status.name}")
                if task.result:
                    result_preview = task.result.split('\n')[0] + "..." if '\n' in task.result else task.result[:50] + "..."
                    print(f"  Resultado: {result_preview}")
                if task.error:
                    print(f"  Error: {task.error}")
        else:
            print(f"ERROR: No se pudo recuperar el plan con ID {plan_id}")
        
        print("\n=== PRUEBA DE ACTUALIZACIÓN DE TAREAS COMPLETADA ===")
        
    except Exception as e:
        print(f"ERROR en la prueba: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        # Limpiar recursos
        print("Cerrando sistema de comunicación...")
        await shutdown_communication_system()

def main():
    """Función principal del ejemplo."""
    # Ejecutar la prueba de forma asíncrona
    print("Iniciando ejecución de prueba...")
    asyncio.run(run_planner_update_test())
    
    print("\nScript de prueba completado")

if __name__ == "__main__":
    main() 