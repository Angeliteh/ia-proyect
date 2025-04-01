"""
Orchestrator Agent module.

This module implements an orchestrator agent that coordinates multiple specialized
agents to solve complex tasks by breaking them down into simpler subtasks.
"""

import uuid
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import re

from .base import BaseAgent, AgentResponse
from .agent_communication import communicator, send_agent_request

class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates multiple specialized agents.
    
    This agent can:
    1. Break down complex tasks into simpler subtasks
    2. Select appropriate agents for each subtask
    3. Execute workflows of subtasks in sequence or parallel
    4. Handle dependencies between subtasks
    5. Provide consolidated results
    
    Attributes:
        available_agents: Dictionary of registered agents and their capabilities
        workflows: Dictionary of active workflows
        workflow_history: Dictionary of completed workflows
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the orchestrator agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary
        """
        super().__init__(agent_id, config)
        
        # Registry of available agents and their capabilities
        self.available_agents: Dict[str, Dict] = {}
        
        # Active workflows
        self.workflows: Dict[str, Dict] = {}
        
        # Completed workflow history
        self.workflow_history: Dict[str, Dict] = {}
        
        # Maximum number of concurrent tasks (can be configured)
        self.max_concurrent_tasks = config.get("max_concurrent_tasks", 3)
        
        self.logger.info(f"Orchestrator agent initialized with {self.max_concurrent_tasks} concurrent tasks limit")
    
    async def register_available_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register an agent as available for task delegation.
        
        Args:
            agent_id: ID of the agent to register
            capabilities: List of capabilities the agent offers
        """
        self.available_agents[agent_id] = {
            "capabilities": capabilities,
            "status": "idle",
            "last_used": None
        }
        self.logger.info(f"Agent {agent_id} registered with capabilities: {capabilities}")
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a request by orchestrating specialized agents.
        
        This method:
        1. Plans a workflow of steps needed to complete the task
        2. For each step, selects an appropriate specialized agent
        3. Executes each step in sequence, passing results between steps
        4. Returns the final result
        
        Args:
            query: User query or task description
            context: Optional context information
            
        Returns:
            AgentResponse with the result of the orchestration
        """
        self.set_state("processing")
        context = context or {}
        
        try:
            # Generate a unique workflow ID
            workflow_id = self._generate_id()
            self.logger.info(f"Planning workflow {workflow_id} for task: {query[:50]}...")
            
            # Plan the workflow (sequence of steps)
            try:
                workflow_steps = await self._plan_workflow(query, context)
                
                if not workflow_steps:
                    raise ValueError("Could not generate a valid workflow plan")
                    
                self.logger.info(f"Workflow {workflow_id} planned with {len(workflow_steps)} steps")
                self.workflows[workflow_id] = {
                    "query": query,
                    "steps": workflow_steps,
                    "current_step": 0,
                    "results": [],
                    "status": "in_progress",
                    "context": context
                }
                
                # Execute the workflow
                self.logger.info(f"Executing workflow {workflow_id} with {len(workflow_steps)} steps")
                result = await self._execute_workflow(workflow_id)
                
                # Mark workflow as completed
                self.workflows[workflow_id]["status"] = "completed"
                
                # Build the result response with workflow information
                step_results = []
                for i, step in enumerate(workflow_steps):
                    agent_id = step.get("assigned_agent", "unknown")
                    step_results.append(f"- Step {i+1}: {step.get('description', 'Unknown step')}... "
                                        f"({step.get('status', 'unknown')}, agent: {agent_id})")
                
                final_response = f"Task completed: {query}\n\n" + \
                                f"Workflow executed with {len(workflow_steps)} steps:\n" + \
                                "\n".join(step_results) + \
                                "\n\nFINAL RESULTS:\n\n" + \
                                result
                
                self.set_state("idle")
                return AgentResponse(
                    content=final_response,
                    metadata={
                        "workflow_id": workflow_id,
                        "steps_count": len(workflow_steps),
                        "orchestrator_id": self.agent_id
                    }
                )
                
            except Exception as plan_error:
                self.logger.error(f"Error planning workflow: {str(plan_error)}")
                # If planning fails, try a direct approach with the most appropriate agent
                self.logger.info("Falling back to direct agent handling")
                return await self._direct_agent_handling(query, context)
                
        except Exception as e:
            self.logger.error(f"Error in orchestration: {str(e)}")
            self.set_state("error")
            return AgentResponse(
                content=f"Error orchestrating the task: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
    
    async def _execute_workflow(self, workflow_id: str) -> str:
        """
        Execute a workflow by processing each step in sequence.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Final result of the workflow execution
        """
        workflow = self.workflows[workflow_id]
        steps = workflow["steps"]
        results = []
        
        # Verificar si este workflow viene de un PlannerAgent
        from_planner = any("task_id" in step for step in steps)
        planner_id = None
        
        # Si el workflow viene de un PlannerAgent, identificar el planner para actualizaciones
        if from_planner:
            for agent_id, agent_info in self.available_agents.items():
                if "task_planning" in agent_info["capabilities"]:
                    planner_id = agent_id
                    break
        
        for i, step in enumerate(steps):
            self.logger.info(f"Executing workflow {workflow_id} step {i}: {step.get('description', 'Unknown')[:50]}...")
            
            # Update current step
            workflow["current_step"] = i
            
            # Determine the type of agent needed for this step
            agent_type = step.get("type")
            description = step.get("description", "")
            
            # Variables para actualizar el PlannerAgent
            task_id = step.get("task_id")
            
            # Get an available agent of the appropriate type
            try:
                # Selección de agente: ahora también considera las capacidades requeridas
                if "required_capabilities" in step and step["required_capabilities"]:
                    agent_id = await self._select_agent_for_capabilities(
                        step["required_capabilities"], 
                        description, 
                        workflow["context"]
                    )
                else:
                    agent_id = await self._select_agent_for_task(
                        agent_type, 
                        description, 
                        workflow["context"]
                    )
                    
                step["assigned_agent"] = agent_id
                
                if not agent_id:
                    self.logger.warning(f"No suitable agent found for step {i} (type: {agent_type})")
                    step["status"] = "failed"
                    results.append(f"Step {i+1} failed: No suitable agent available for {agent_type} tasks")
                    
                    # Notificar al PlannerAgent si corresponde
                    if from_planner and planner_id and task_id:
                        await self._update_planner_task_status(
                            planner_id, 
                            workflow_id, 
                            task_id, 
                            "FAILED", 
                            error="No se encontró un agente adecuado"
                        )
                    
                    continue
                    
                # Determine input for this step based on previous results
                step_input = description
                if i > 0 and results:
                    # Include previous results as context
                    previous_result = results[-1]
                    if not previous_result.startswith("Step"):  # Only if it's a real result, not an error message
                        step_input = f"{description}\n\nResultado previo: {previous_result}"
                
                # Execute the step with the selected agent
                self.logger.info(f"Delegating step to agent {agent_id}")
                
                # Notify PlannerAgent that task is starting
                if from_planner and planner_id and task_id:
                    await self._update_planner_task_status(
                        planner_id, 
                        workflow_id, 
                        task_id, 
                        "IN_PROGRESS", 
                        agent_id=agent_id
                    )
                
                # Prepare step context
                step_context = {
                    "workflow_id": workflow_id,
                    "step_number": i + 1,
                    "from_orchestrator": True,
                    **(workflow["context"] or {})
                }
                
                # Add original task details
                step_context["original_task"] = workflow["query"]
                
                # Execute the step
                response = await self._send_agent_request(
                    self.agent_id, 
                    agent_id, 
                    step_input, 
                    step_context
                )
                
                if not response:
                    error_msg = f"Step {i+1} failed: Agent {agent_id} did not respond in time"
                    self.logger.warning(error_msg)
                    step["status"] = "failed"
                    results.append(error_msg)
                    
                    # Notificar al PlannerAgent si corresponde
                    if from_planner and planner_id and task_id:
                        await self._update_planner_task_status(
                            planner_id, 
                            workflow_id, 
                            task_id, 
                            "FAILED", 
                            error="Agent timeout"
                        )
                    
                    continue
                
                # Process the response
                step["status"] = "completed" if response.status == "success" else "failed"
                results.append(response.content)
                
                # Store the result in the workflow
                if "results" not in workflow:
                    workflow["results"] = []
                workflow["results"].append({
                    "step": i,
                    "agent": agent_id,
                    "content": response.content,
                    "status": response.status
                })
                
                # Notify PlannerAgent of task completion
                if from_planner and planner_id and task_id:
                    if response.status == "success":
                        await self._update_planner_task_status(
                            planner_id, 
                            workflow_id, 
                            task_id, 
                            "COMPLETED", 
                            result=response.content
                        )
                    else:
                        await self._update_planner_task_status(
                            planner_id, 
                            workflow_id, 
                            task_id, 
                            "FAILED", 
                            error=f"Agent {agent_id} failed: {response.status}"
                        )
                
            except Exception as e:
                self.logger.error(f"Error executing step {i}: {str(e)}")
                step["status"] = "failed"
                results.append(f"Step {i+1} failed: {str(e)}")
                
                # Notificar al PlannerAgent si corresponde
                if from_planner and planner_id and task_id:
                    await self._update_planner_task_status(
                        planner_id, 
                        workflow_id, 
                        task_id, 
                        "FAILED", 
                        error=str(e)
                    )
        
        # Combine the results
        if not results:
            return "No results were produced"
            
        # For tasks that expect specific outputs (like code generation), 
        # prefer to return only the last step's result
        if any(step.get("type") == "code" for step in steps):
            for result in reversed(results):
                if "```" in result or "function" in result.lower() or "class" in result.lower():
                    return result
        
        # Otherwise, return a combined result
        return "\n\n".join(results)
    
    def _detect_code_language(self, description: str, query: str) -> str:
        """
        Detecta el lenguaje de programación mencionado en la descripción o consulta.
        
        Args:
            description: Descripción del paso actual
            query: Consulta original completa
            
        Returns:
            Lenguaje detectado o "python" por defecto
        """
        text = (description + " " + query).lower()
        
        # Detectar menciones directas de lenguajes
        if "python" in text or "script en python" in text or "código python" in text:
            return "python"
        elif "javascript" in text or "js" in text:
            return "javascript"
        elif "typescript" in text or "ts" in text:
            return "typescript"
        elif "java" in text and "javascript" not in text:
            return "java"
        elif "c#" in text or "csharp" in text or ".net" in text:
            return "c#"
        elif "c++" in text or "cpp" in text:
            return "c++"
        elif "sql" in text:
            return "sql"
        elif "go" in text or "golang" in text:
            return "go"
        elif "rust" in text:
            return "rust"
        
        # Para algoritmos comunes, preferir Python
        if any(word in text for word in ["algoritmo", "secuencia", "fibonacci", "factorial", "ordenamiento", "búsqueda"]):
            return "python"
            
        # Por defecto, devolver Python
        return "python"
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        return ["task_planning", "agent_selection", "workflow_management"]
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel an active workflow.
        
        Args:
            workflow_id: ID of the workflow to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        workflow["status"] = "cancelled"
        
        # Move to history
        self.workflow_history[workflow_id] = workflow
        del self.workflows[workflow_id]
        
        self.logger.info(f"Workflow {workflow_id} cancelled")
        return True
    
    async def plan_workflow(self, task: str, context: Optional[Dict] = None) -> Dict:
        """
        Plan a workflow by breaking down a complex task into subtasks.
        
        This method uses a specialized agent (typically CodeAgent) to analyze
        the task and break it down into sequential steps that can be assigned
        to different specialized agents.
        
        Args:
            task: The complex task to break down
            context: Optional context information
            
        Returns:
            Dictionary containing the planned workflow
        """
        workflow_id = str(uuid.uuid4())
        context = context or {}
        
        self.logger.info(f"Planning workflow {workflow_id} for task: {task[:100]}...")
        
        # Choose a planning agent - preferably one with code capabilities
        planner_id = self._select_planning_agent()
        
        steps = []
        
        # Try using the external planner if available
        if planner_id:
            try:
                # Create a planning prompt
                planning_prompt = self._create_planning_prompt(task)
                
                # Send planning request to the planning agent
                planning_response = await send_agent_request(
                    sender_id=self.agent_id,
                    receiver_id=planner_id,
                    content=planning_prompt,
                    context={"original_task": task, **context}
                )
                
                if planning_response and planning_response.status == "success":
                    # Parse the planning response to extract steps
                    steps = self._parse_planning_response(planning_response.content)
                    self.logger.info(f"External planning successful with {len(steps)} steps")
                else:
                    error_msg = planning_response.content if planning_response else "No response"
                    self.logger.warning(f"External planning failed: {error_msg}. Falling back to internal planning.")
                    steps = []  # Reset steps to use internal planning
            except Exception as e:
                self.logger.warning(f"External planning error: {str(e)}. Falling back to internal planning.")
                steps = []  # Reset steps to use internal planning
        
        # If external planning failed or wasn't available, use internal planning
        if not steps:
            self.logger.info("Using internal planning mechanism")
            steps = self._internal_task_planning(task)
        
        # Create the workflow structure
        workflow = {
            "id": workflow_id,
            "original_task": task,
            "context": context,
            "steps": steps,
            "current_step": 0,
            "status": "planned",
            "results": [],
            "start_time": None,
            "end_time": None,
            "created_at": datetime.now().isoformat()
        }
        
        # Store the workflow
        self.workflows[workflow_id] = workflow
        self.logger.info(f"Workflow {workflow_id} planned with {len(steps)} steps")
        
        return workflow
    
    def _create_planning_prompt(self, task: str) -> str:
        """
        Create a prompt for the planning agent.
        
        Args:
            task: The original task
            
        Returns:
            String prompt for the planning agent
        """
        # Get list of available agents and their capabilities
        available_capabilities = {}
        for agent_id, info in self.available_agents.items():
            for cap in info["capabilities"]:
                if cap not in available_capabilities:
                    available_capabilities[cap] = []
                available_capabilities[cap].append(agent_id)
        
        # Create the prompt
        prompt = f"""
        Task Planning Request
        
        I need to break down the following task into sequential steps that can be executed
        by specialized agents. Each step should be assigned to an agent type that can handle it.
        
        TASK: {task}
        
        Available agent capabilities:
        {', '.join(available_capabilities.keys())}
        
        Please analyze the task and break it down into 2-8 sequential steps.
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        1. [agent_type] Step description
        2. [agent_type] Step description
        ...
        
        Each step should be clear and actionable. The agent_type should match one of the available capabilities.
        If a step requires multiple capabilities, choose the most relevant one.
        """
        
        return prompt
    
    def _select_planning_agent(self) -> Optional[str]:
        """
        Select an agent that can handle planning tasks.
        
        Returns:
            Agent ID of the selected planning agent, or None if none available
        """
        # Prefer agents with code or planning capabilities
        for agent_id, info in self.available_agents.items():
            capabilities = info["capabilities"]
            if "task_planning" in capabilities:
                return agent_id
            if "code" in capabilities or "generate" in capabilities:
                return agent_id
        
        # Fall back to any available agent
        if self.available_agents:
            return next(iter(self.available_agents.keys()))
        
        return None
    
    def _internal_task_planning(self, task: str) -> List[Dict]:
        """
        Planificación interna de tareas cuando no se puede usar un agente externo.
        
        Esta función analiza la consulta y determina los pasos necesarios.
        
        Args:
            task: La descripción de la tarea
            
        Returns:
            Lista de pasos para el workflow
        """
        task_lower = task.lower()
        steps = []
        
        # Detectar patrones específicos y crear planes adecuados
        
        # Caso 1: Tareas de echo simples
        if any(x in task_lower for x in ["repite", "repiteme", "eco", "echo"]):
            steps.append({
                "type": "echo",
                "description": task,
                "status": "pending"
            })
            return steps
            
        # Caso 2: Tareas de generación de código
        if "código" in task_lower or "script" in task_lower or "programa" in task_lower or "genera" in task_lower:
            language = "python"  # Por defecto
            
            # Detectar lenguaje de programación
            if "python" in task_lower:
                language = "python"
            elif "javascript" in task_lower or "js" in task_lower:
                language = "javascript"
            elif "java" in task_lower and "javascript" not in task_lower:
                language = "java"
            elif "c++" in task_lower or "cpp" in task_lower:
                language = "c++"
            elif "c#" in task_lower:
                language = "c#"
                
            # Detectar qué tipo de código (Fibonacci es un caso especial común)
            if "fibonacci" in task_lower:
                steps.append({
                    "type": "code",
                    "description": f"Genera un script en {language} que calcule la secuencia de Fibonacci",
                    "status": "pending",
                    "language": language,
                    "task": "generate"
                })
                return steps
                
            # Programación general
            steps.append({
                "type": "code",
                "description": task,
                "status": "pending",
                "language": language,
                "task": "generate"
            })
            return steps
            
        # Caso 3: Tareas del sistema
        if any(x in task_lower for x in ["archivo", "directorio", "sistema", "ejecuta", "comando"]):
            steps.append({
                "type": "system",
                "description": task,
                "status": "pending"
            })
            return steps
            
        # Caso 4: Tareas complejas que pueden requerir múltiples pasos
        if any(x in task_lower for x in ["analiza", "investiga", "resuelve", "encuentra"]):
            # Paso 1: Investigación/análisis
            steps.append({
                "type": "echo" if "echo" in self.available_agents else "code",
                "description": f"Análisis inicial de la tarea: {task}",
                "status": "pending"
            })
            
            # Paso 2: Generación de solución
            steps.append({
                "type": "code",
                "description": f"Generación de solución para: {task}",
                "status": "pending"
            })
            
            return steps
        
        # Plan por defecto: usamos un solo paso con el agente más apropiado
        if "código" in task_lower or "programación" in task_lower or "script" in task_lower:
            agent_type = "code"
        elif any(x in task_lower for x in ["archivo", "sistema", "comando"]):
            agent_type = "system"
        else:
            agent_type = "echo"  # Fallback
            
        steps.append({
            "type": agent_type,
            "description": task,
            "status": "pending"
        })
        
        return steps
    
    def _create_step_from_description(self, description: str) -> Dict:
        """
        Crea un paso de workflow basado en la descripción de texto.
        
        Args:
            description: Descripción textual del paso
            
        Returns:
            Diccionario con la información del paso
        """
        desc_lower = description.lower()
        
        # Determinar el tipo de agente basado en keywords
        if any(kw in desc_lower for kw in ["code", "codigo", "código", "script", "program", "generar", "generate", "crear", "implementar"]):
            agent_type = "code"
        elif any(kw in desc_lower for kw in ["system", "sistema", "file", "archivo", "directory", "directorio", "ejecutar", "execute", "run", "command", "comando"]):
            agent_type = "system"
        else:
            agent_type = "echo"  # Default fallback
        
        return {
            "agent_type": agent_type,
            "description": description,
            "status": "pending"
        }
    
    def _parse_planning_response(self, response: str) -> List[Dict]:
        """
        Analiza la respuesta del agente planificador para extraer pasos.
        
        Args:
            response: Respuesta del agente planificador
            
        Returns:
            Lista de pasos para el workflow
        """
        self.logger.info(f"Analizando respuesta de planificación: {response[:100]}...")
        steps = []
        
        # Intentar detectar formato estructurado: 1. [tipo] Descripción
        structured_steps = re.findall(r'^\s*(\d+)[\.:\)]\s*\[([^\]]+)\]\s*(.+?)$', response, re.MULTILINE)
        
        if structured_steps:
            self.logger.info(f"Detectados {len(structured_steps)} pasos estructurados")
            for step_num, agent_type, description in structured_steps:
                agent_type = agent_type.strip().lower()
                description = description.strip()
                
                # Normalizar el tipo de agente
                if agent_type in ["código", "code", "programming", "programación", "desarrollo"]:
                    agent_type = "code"
                elif agent_type in ["system", "sistema", "shell", "comando", "command", "file", "archivo"]:
                    agent_type = "system"
                elif agent_type in ["echo", "eco", "texto", "text", "simple"]:
                    agent_type = "echo"
                
                # Ignorar pasos vacíos
                if not description:
                    continue
                    
                steps.append({
                    "type": agent_type,
                    "description": description,
                    "status": "pending"
                })
                
            return steps
            
        # Intentar formato alternativo: Paso 1: Tipo - Descripción
        alt_steps = re.findall(r'(?:Paso|Step)\s+(\d+):\s*([^-]+?)\s*-\s*(.+?)$', response, re.MULTILINE)
        
        if alt_steps:
            self.logger.info(f"Detectados {len(alt_steps)} pasos (formato alternativo)")
            for step_num, agent_type, description in alt_steps:
                agent_type = agent_type.strip().lower()
                description = description.strip()
                
                # Normalizar el tipo de agente
                if agent_type in ["código", "code", "programming", "programación", "desarrollo"]:
                    agent_type = "code"
                elif agent_type in ["system", "sistema", "shell", "comando", "command", "file", "archivo"]:
                    agent_type = "system"
                elif agent_type in ["echo", "eco", "texto", "text", "simple"]:
                    agent_type = "echo"
                    
                steps.append({
                    "type": agent_type,
                    "description": description,
                    "status": "pending"
                })
                
            return steps
            
        # Si no detectamos ningún formato estructurado, ver si es código (común en Fibonacci)
        if "def " in response and "fibonacci" in response.lower():
            # Es un script de Fibonacci - crear un solo paso de código
            return [{
                "type": "code",
                "description": "Genera un script en Python que calcule los primeros 10 números de la secuencia Fibonacci",
                "status": "pending",
                "language": "python",
                "task": "generate"
            }]
            
        # Si no se detectaron pasos estructurados, intentamos crear pasos a partir del texto
        if not steps:
            self.logger.warning("No se detectaron pasos estructurados. Creando plan a partir del texto completo.")
            
            # Si el texto parece código, crear un paso de código
            if any(kw in response for kw in ["def ", "function", "class", "import", "for ", "while ", "return"]):
                return [{
                    "type": "code",
                    "description": response[:200] + "..." if len(response) > 200 else response,
                    "status": "pending"
                }]
                
            # Dividir el texto en líneas/párrafos y crear pasos simples
            paragraphs = re.split(r'\n\s*\n', response)
            
            if paragraphs and len(paragraphs) > 1:
                for i, para in enumerate(paragraphs[:3]):  # Máximo 3 pasos
                    steps.append({
                        "type": "echo",
                        "description": para[:200] + "..." if len(para) > 200 else para,
                        "status": "pending"
                    })
                    self.logger.info(f"Paso inferido {i+1}: tipo=echo, descripción={para[:50]}...")
            else:
                # Si no hay párrafos claros, usar el texto completo
                steps.append({
                    "type": "echo",
                    "description": response[:200] + "..." if len(response) > 200 else response,
                    "status": "pending"
                })
                
        return steps
    
    def _infer_agent_type_from_description(self, description: str) -> str:
        """
        Infiere el tipo de agente más apropiado basado en la descripción del paso.
        
        Args:
            description: Descripción textual del paso
            
        Returns:
            Tipo de agente inferido: "code", "system", o "echo"
        """
        description_lower = description.lower()
        
        # Verificar keywords para código
        code_keywords = [
            "código", "code", "program", "script", "función", "function", 
            "python", "javascript", "java", "c++", "generar", "desarrollar",
            "implementar", "escribir", "programar", "class", "clase"
        ]
        
        # Verificar keywords para sistema
        system_keywords = [
            "sistema", "system", "archivo", "file", "directorio", "directory",
            "ejecutar", "execute", "run", "correr", "command", "comando",
            "buscar", "search", "find", "path", "ruta", "ubicación", "location"
        ]
        
        # Contar coincidencias
        code_matches = sum(1 for kw in code_keywords if kw in description_lower)
        system_matches = sum(1 for kw in system_keywords if kw in description_lower)
        
        # Determinar el tipo basado en la mayor cantidad de coincidencias
        if code_matches > system_matches:
            return "code"
        elif system_matches > 0:
            return "system"
        else:
            return "echo"  # Tipo por defecto
    
    async def _select_agent_for_task(self, task_type: str, step_description: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Select the most appropriate agent for a specific task type and description.
        
        This method implements a sophisticated agent selection algorithm that considers:
        1. Required capabilities for the task
        2. Agent availability and current workload
        3. Past performance for similar tasks
        4. Context-specific requirements
        5. Fallback mechanisms when ideal agents aren't available
        
        Args:
            task_type: The type of task (e.g., "code", "system", "echo")
            step_description: Detailed description of the step
            context: Context information that might influence selection
            
        Returns:
            ID of the selected agent, or None if no suitable agent is available
        """
        self.logger.info(f"Selecting agent for task type: {task_type}, description: {step_description[:50]}...")
        
        context = context or {}
        
        # Mapa de tipos de tareas a capacidades de agentes
        capability_map = {
            "code": ["code_generation", "generate", "code"],
            "system": ["execute_command", "read_file", "write_file", "system"],
            "echo": ["echo"],
            "task_planning": ["task_planning"],
            "agent_selection": ["agent_selection"],
        }
        
        # Obtener capacidades relevantes para este tipo de tarea
        relevant_capabilities = capability_map.get(task_type, [task_type])
        
        self.logger.info(f"Capacidades relevantes para '{task_type}': {relevant_capabilities}")
        
        # 1. Filter agents by required capability
        candidates = {}
        for agent_id, info in self.available_agents.items():
            agent_capabilities = info["capabilities"]
            
            # Verificar si el agente tiene al menos una capacidad relevante
            if any(cap in agent_capabilities for cap in relevant_capabilities):
                candidates[agent_id] = {
                    **info,
                    "score": 0  # Initial score
                }
                self.logger.info(f"Agente candidato encontrado: {agent_id} con capacidades: {agent_capabilities}")
        
        if not candidates:
            self.logger.warning(f"No agents available with capability matching: {relevant_capabilities}")
            
            # Try fallback to generic capabilities
            fallback_candidates = {}
            for agent_id, info in self.available_agents.items():
                # Try to find agents with general capabilities
                if any(cap in info["capabilities"] for cap in ["general", "default", "echo"]):
                    fallback_candidates[agent_id] = {
                        **info,
                        "score": 0,
                        "is_fallback": True
                    }
            
            if fallback_candidates:
                self.logger.info(f"Found {len(fallback_candidates)} fallback agents")
                candidates = fallback_candidates
            else:
                self.logger.error("No suitable agents available, even for fallback")
                return None
        
        # 2. Score candidates based on multiple factors
        for agent_id, info in candidates.items():
            score = 0
            
            # Base capability match score
            capabilities = info["capabilities"]
            
            exact_match = task_type in capabilities
            related_match = any(cap in capabilities for cap in relevant_capabilities)
            
            if exact_match:
                score += 100  # Exact capability match
            elif related_match:
                score += 80   # Related capability match
            elif "general" in capabilities:
                score += 50   # General capability
            
            # Adjust score based on agent status
            if info["status"] == "idle":
                score += 30   # Available agent
            else:
                score -= 20   # Busy agent penalty
            
            # Consider history and context (hypothetical metrics)
            if "success_rate" in info:
                score += info["success_rate"] * 10  # Higher success rate is better
            
            # Task-specific adjustments
            if task_type == "code" and any(cap in capabilities for cap in ["code_generation", "generate"]):
                score += 15  # Bonus for code generation capability
            
            if task_type == "system" and any(cap in capabilities for cap in ["execute_command", "system"]):
                score += 15  # Bonus for command execution capability
            
            # Context-specific requirements
            if context.get("preferred_agent") == agent_id:
                score += 25  # User preference bonus
            
            # Update the score
            candidates[agent_id]["score"] = score
            self.logger.info(f"Agente {agent_id} tiene puntuación: {score}")
        
        # 3. Select the best candidate
        if not candidates:
            return None
        
        # Sort by score in descending order
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        # Select the highest scoring agent
        best_agent_id = sorted_candidates[0][0]
        best_score = sorted_candidates[0][1]["score"]
        
        self.logger.info(f"Selected agent {best_agent_id} with score {best_score}")
        
        # Update agent status
        self.available_agents[best_agent_id]["status"] = "busy"
        self.available_agents[best_agent_id]["last_used"] = datetime.now().isoformat()
        
        return best_agent_id
    
    async def _release_agent(self, agent_id: str) -> None:
        """
        Mark an agent as idle after task completion.
        
        Args:
            agent_id: ID of the agent to release
        """
        if agent_id in self.available_agents:
            self.available_agents[agent_id]["status"] = "idle"
            self.logger.debug(f"Agent {agent_id} released and marked as idle")
    
    async def _get_agent_status(self) -> Dict[str, List[str]]:
        """
        Get the current status of all registered agents.
        
        Returns:
            Dictionary mapping status to list of agent IDs
        """
        status_map = {
            "idle": [],
            "busy": []
        }
        
        for agent_id, info in self.available_agents.items():
            status = info["status"]
            if status not in status_map:
                status_map[status] = []
            status_map[status].append(agent_id)
        
        return status_map
    
    async def execute_workflow(self, workflow_id: str) -> AgentResponse:
        """
        Execute a previously planned workflow.
        
        This method executes the steps in a workflow, respecting dependencies
        between steps and handling errors appropriately.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            AgentResponse with the consolidated results
        """
        # Check if workflow exists
        if workflow_id not in self.workflows:
            return AgentResponse(
                content=f"Workflow {workflow_id} not found",
                status="error",
                metadata={"error_type": "not_found"}
            )
        
        workflow = self.workflows[workflow_id]
        workflow["status"] = "running"
        workflow["start_time"] = datetime.now().isoformat()
        
        self.logger.info(f"Executing workflow {workflow_id} with {len(workflow['steps'])} steps")
        
        try:
            # Process steps according to their dependencies
            steps_to_execute = list(range(len(workflow["steps"])))
            steps_completed = set()
            steps_failed = set()
            
            # Keep track of results to pass to dependent steps
            step_results = {}
            
            # Execute steps while there are steps remaining and no failures
            while steps_to_execute and not steps_failed:
                # Find steps that can be executed now (dependencies satisfied)
                executable_steps = []
                for step_idx in steps_to_execute[:]:
                    step = workflow["steps"][step_idx]
                    
                    # Check if this step has dependencies
                    dependencies = step.get("depends_on", [])
                    if not dependencies and "depends_on" in step:
                        dependencies = [step["depends_on"]]  # Convert scalar to list
                    
                    # If dependencies are empty or all satisfied, we can execute
                    if (not dependencies or 
                        all(dep_idx in steps_completed for dep_idx in dependencies)):
                        executable_steps.append(step_idx)
                        steps_to_execute.remove(step_idx)
                
                if not executable_steps:
                    # We have a circular dependency or all steps require unsatisfied dependencies
                    self.logger.error(f"Workflow {workflow_id} has circular dependencies or invalid dependencies")
                    raise Exception("Circular dependencies detected in workflow")
                
                # Execute the steps that are ready
                # In this version, we execute sequentially - you can make this parallel if needed
                for step_idx in executable_steps:
                    workflow["current_step"] = step_idx
                    step = workflow["steps"][step_idx]
                    
                    try:
                        # Execute the step
                        step_result = await self._execute_workflow_step(
                            workflow_id=workflow_id,
                            step_idx=step_idx,
                            step=step,
                            context=workflow["context"],
                            previous_results=step_results
                        )
                        
                        # Store the result
                        step_results[step_idx] = step_result
                        
                        # Mark the step as completed
                        step["status"] = "completed" if step_result["status"] == "success" else "failed"
                        
                        if step_result["status"] == "success":
                            steps_completed.add(step_idx)
                        else:
                            steps_failed.add(step_idx)
                            # Stop executing if a step fails
                            break
                    
                    except Exception as e:
                        self.logger.error(f"Error executing step {step_idx}: {str(e)}")
                        step["status"] = "failed"
                        step["error"] = str(e)
                        steps_failed.add(step_idx)
                        break
            
            # Update workflow status based on execution results
            if steps_failed:
                workflow["status"] = "failed"
                failed_steps = [workflow["steps"][idx] for idx in steps_failed]
                
                failure_message = f"Workflow failed at step(s): {', '.join(str(idx) for idx in steps_failed)}\n"
                if step_results and any(idx in step_results for idx in steps_failed):
                    failure_details = [step_results[idx]["content"] for idx in steps_failed if idx in step_results]
                    failure_message += f"Failure details: {'; '.join(failure_details)}"
                
                return AgentResponse(
                    content=failure_message,
                    status="error",
                    metadata={
                        "workflow_id": workflow_id,
                        "failed_steps": failed_steps,
                        "completed_steps": len(steps_completed),
                        "total_steps": len(workflow["steps"])
                    }
                )
            else:
                # All steps completed successfully
                workflow["status"] = "completed"
                
                # Generate final result by combining step results
                final_result = self._generate_final_result(workflow, step_results)
                
                workflow["end_time"] = datetime.now().isoformat()
                
                # Move to history
                self.workflow_history[workflow_id] = workflow
                del self.workflows[workflow_id]
                
                return AgentResponse(
                    content=final_result,
                    status="success",
                    metadata={
                        "workflow_id": workflow_id,
                        "steps_completed": len(steps_completed),
                        "total_steps": len(workflow["steps"]),
                        "execution_time": (
                            datetime.fromisoformat(workflow["end_time"]) - 
                            datetime.fromisoformat(workflow["start_time"])
                        ).total_seconds()
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_id}: {str(e)}")
            workflow["status"] = "failed"
            workflow["error"] = str(e)
            
            return AgentResponse(
                content=f"Error executing workflow: {str(e)}",
                status="error",
                metadata={"workflow_id": workflow_id, "error": str(e)}
            )
    
    async def _execute_workflow_step(self, workflow_id: str, step_idx: int, step: Dict, 
                                   context: Dict, previous_results: Dict) -> Dict:
        """
        Execute a single workflow step.
        
        Args:
            workflow_id: ID of the workflow
            step_idx: Index of the step
            step: The step dictionary
            context: Workflow context
            previous_results: Results from previous steps
            
        Returns:
            Step execution result dictionary
        """
        step_description = step["description"]
        agent_type = step["agent_type"]
        
        self.logger.info(f"Executing workflow {workflow_id} step {step_idx}: {step_description[:50]}...")
        
        # Check if this step depends on previous steps
        dependencies = step.get("depends_on", [])
        if not isinstance(dependencies, list):
            dependencies = [dependencies]  # Convert to list if it's a single value
        
        # Ensure all dependencies are completed
        missing_deps = [dep for dep in dependencies if str(dep) not in previous_results]
        if missing_deps:
            self.logger.warning(f"Step {step_idx} depends on uncompleted steps: {missing_deps}")
            return {
                "status": "skipped",
                "content": f"Skipped due to missing dependencies: {missing_deps}",
                "error": "missing_dependencies"
            }
        
        # Select appropriate agent based on the task type
        agent_id = await self._select_agent_for_task(agent_type, step_description, context)
        
        if not agent_id:
            self.logger.error(f"No suitable agent found for task type: {agent_type}")
            return {
                "status": "error",
                "content": f"Could not find suitable agent for task type: {agent_type}",
                "error": "no_agent_available"
            }
        
        # Update the step with assigned agent
        step["agent_id"] = agent_id
        
        # Create enhanced prompt based on step description and previous results
        step_prompt = self._build_enhanced_step_prompt(step, previous_results, dependencies)
        
        # Prepare context with workflow information
        step_context = {
            "workflow_id": workflow_id,
            "step_idx": step_idx,
            "agent_type": agent_type,
            "original_task": context.get("original_task", ""),
            "sender_id": self.agent_id,  # Identificar al orquestrador como remitente
            "from_orchestrator": True,   # Indicar que viene del orquestrador
            **context  # Include original context
        }
        
        # Add relevant previous results
        for dep in dependencies:
            dep_str = str(dep)
            if dep_str in previous_results:
                step_context[f"step_{dep}_result"] = previous_results[dep_str]["content"]
        
        # Execute the step by sending request to the agent
        try:
            self.logger.info(f"Sending request to agent {agent_id} for step {step_idx}")
            
            response = await send_agent_request(
                sender_id=self.agent_id,
                receiver_id=agent_id,
                content=step_prompt,
                context=step_context
            )
            
            # Release the agent after use
            await self._release_agent(agent_id)
            
            if not response:
                self.logger.error(f"No response from agent {agent_id} for step {step_idx}")
                return {
                    "status": "error",
                    "content": f"No response from agent {agent_id}",
                    "error": "no_response"
                }
            
            # Update step status
            step["status"] = "completed"
            
            # Return step result
            return {
                "status": "success",
                "content": response.content,
                "metadata": response.metadata,
                "agent_id": agent_id
            }
            
        except Exception as e:
            self.logger.error(f"Error executing step {step_idx}: {str(e)}")
            
            # Update step status
            step["status"] = "error"
            
            # Return error result
            return {
                "status": "error",
                "content": f"Error executing step: {str(e)}",
                "error": str(e),
                "agent_id": agent_id
            }
    
    def _build_enhanced_step_prompt(self, step: Dict, previous_results: Dict, dependencies: List[int]) -> str:
        """
        Build an enhanced prompt for a step, including context from previous steps.
        
        Args:
            step: The step information
            previous_results: Results from previous steps
            dependencies: Indices of steps this step depends on
            
        Returns:
            Enhanced prompt string
        """
        description = step["description"]
        
        # Start with the original description
        prompt = f"{description}\n\n"
        
        # Add context from dependency steps
        if dependencies and previous_results:
            prompt += "CONTEXT FROM PREVIOUS STEPS:\n"
            for dep_idx in dependencies:
                if dep_idx in previous_results:
                    result = previous_results[dep_idx]
                    prompt += f"Step {dep_idx+1} result:\n{result['content']}\n\n"
        
        return prompt
    
    def _generate_final_result(self, workflow: Dict, step_results: Dict) -> str:
        """
        Generate a consolidated final result from all workflow steps.
        
        Args:
            workflow: The workflow dictionary
            step_results: Dictionary of step results
            
        Returns:
            Consolidated result string
        """
        task = workflow["original_task"]
        steps = workflow["steps"]
        
        # Sección de encabezado con la descripción de la tarea
        result = f"Task completed: {task}\n\n"
        
        # Sección de resumen del workflow
        result += f"Workflow executed with {len(steps)} steps:\n"
        for i, step in enumerate(steps):
            step_status = step["status"]
            agent_id = step.get("agent_id", "unknown")
            result += f"- Step {i+1}: {step['description'][:50]}... ({step_status}, agent: {agent_id})\n"
        
        result += "\nFINAL RESULTS:\n"
        
        # Para tareas de código, dar prioridad a las respuestas del agente de código
        code_responses = []
        other_responses = []
        
        for step_idx, result_data in step_results.items():
            step_idx = int(step_idx)
            if step_idx < len(steps) and steps[step_idx]["agent_type"] == "code":
                code_responses.append(result_data["content"])
            else:
                other_responses.append(result_data["content"])
        
        # Si hay respuestas de código, mostrarlas primero y con más prominencia
        if code_responses:
            # Filtrar salidas que son simples ecos, ya que no son útiles
            code_responses = [resp for resp in code_responses if not resp.startswith("Echo:")]
            if code_responses:
                result += "\n".join(code_responses)
            else:
                result += "No code output was generated.\n"
        
        # Si no hay respuestas de código, o si son insuficientes, incluir otras respuestas
        if not code_responses or len("\n".join(code_responses)) < 50:
            for resp in other_responses:
                # No incluir respuestas vacías o simples ecos a menos que sean la única respuesta
                if resp and (not resp.startswith("Echo:") or len(other_responses) == 1):
                    result += f"\n{resp}"
        
        # Instrucciones finales si es apropiado
        task_lower = task.lower()
        if "código" in task_lower or "program" in task_lower or "script" in task_lower:
            result += "\n\nPara ejecutar este código, cópielo a un archivo y ejecútelo con el intérprete apropiado."
        
        return result
    
    async def get_workflow_status(self, workflow_id: str) -> Dict:
        """
        Get the current status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Dictionary with workflow status information or error
        """
        if workflow_id in self.workflows:
            return self.workflows[workflow_id]
        elif workflow_id in self.workflow_history:
            return self.workflow_history[workflow_id]
        
        return {"error": "Workflow not found"}
    
    async def list_workflows(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all workflows, optionally filtered by status.
        
        Args:
            status: Optional status filter (e.g., "running", "completed", "failed")
            
        Returns:
            List of workflow summary dictionaries
        """
        result = []
        
        # Add active workflows
        for wf_id, workflow in self.workflows.items():
            if status is None or workflow["status"] == status:
                # Create a summary version
                summary = {
                    "id": wf_id,
                    "task": workflow["original_task"],
                    "status": workflow["status"],
                    "progress": f"{workflow.get('current_step', 0) + 1}/{len(workflow['steps'])}",
                    "start_time": workflow.get("start_time"),
                    "active": True
                }
                result.append(summary)
        
        # Add completed/historical workflows
        for wf_id, workflow in self.workflow_history.items():
            if status is None or workflow["status"] == status:
                # Create a summary version
                summary = {
                    "id": wf_id,
                    "task": workflow["original_task"],
                    "status": workflow["status"],
                    "start_time": workflow.get("start_time"),
                    "end_time": workflow.get("end_time"),
                    "active": False
                }
                result.append(summary)
        
        # Sort by start time (most recent first)
        result.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        
        return result
    
    async def execute_task(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Main entry point to execute a complex task.
        Plans and executes a complete workflow.
        
        Args:
            task: The complex task to execute
            context: Optional context information
            
        Returns:
            AgentResponse with the consolidated results
        """
        # Plan the workflow
        workflow = await self.plan_workflow(task, context)
        
        # Execute the workflow
        return await self.execute_workflow(workflow["id"])
    
    async def _handle_concurrency(self) -> Dict[str, int]:
        """
        Handle concurrency limits and resource allocation.
        
        Returns:
            Dictionary with concurrency statistics
        """
        # Get current agent status
        agent_status = await self._get_agent_status()
        
        # Calculate current concurrency
        busy_agents = len(agent_status.get("busy", []))
        idle_agents = len(agent_status.get("idle", []))
        total_agents = busy_agents + idle_agents
        
        # Log concurrency information
        self.logger.debug(f"Concurrency status: {busy_agents} busy, {idle_agents} idle, {total_agents} total")
        
        return {
            "busy_agents": busy_agents,
            "idle_agents": idle_agents,
            "total_agents": total_agents,
            "max_concurrent": self.max_concurrent_tasks
        }
    
    def _generate_id(self) -> str:
        """
        Genera un ID único para un workflow, tarea o paso.
        
        Returns:
            String con un identificador único
        """
        return str(uuid.uuid4())
        
    async def _plan_workflow(self, query: str, context: Optional[Dict] = None) -> List[Dict]:
        """
        Planifica un workflow basado en la consulta del usuario.
        
        Este método analiza la consulta y la divide en pasos que pueden ser 
        ejecutados por diferentes agentes especializados.
        
        Args:
            query: La consulta del usuario
            context: Contexto opcional
            
        Returns:
            Lista de pasos para el workflow
        """
        self.logger.info(f"Planificando workflow para: {query[:50]}...")
        
        steps = []
        
        # Comprobar si hay un PlannerAgent disponible
        planner_id = None
        for agent_id, agent_info in self.available_agents.items():
            if "task_planning" in agent_info["capabilities"]:
                planner_id = agent_id
                break
                
        # Intentar usar el PlannerAgent si está disponible
        if planner_id:
            try:
                self.logger.info(f"Delegando planificación al agente especializado {planner_id}")
                steps = await self._delegate_to_planner_agent(planner_id, query, context)
                if steps:
                    self.logger.info(f"Planificación exitosa usando PlannerAgent con {len(steps)} pasos")
                    return steps
                else:
                    self.logger.warning("La planificación con PlannerAgent falló o devolvió un plan vacío")
            except Exception as e:
                self.logger.warning(f"Error delegando a PlannerAgent: {str(e)}")
        
        # Si no hay PlannerAgent disponible o falló, intentar usar un CodeAgent como planificador
        code_planner_id = await self._select_agent_for_task("code", query, context or {})
        
        # Intentar usar un planificador de código externo si está disponible
        if code_planner_id:
            try:
                # Crear un prompt de planificación
                planning_prompt = f"""
                Planificación de Tareas
                
                Necesito dividir la siguiente tarea en pasos secuenciales que puedan ser ejecutados
                por agentes especializados. Cada paso debe asignarse a un tipo de agente.
                
                TAREA: {query}
                
                Tipos de agentes disponibles:
                - code: Para tareas de programación, generación y análisis de código
                - system: Para operaciones del sistema, archivos y comandos
                - echo: Para tareas simples de procesamiento de texto
                
                Por favor, analiza la tarea y divídela en 1-5 pasos secuenciales.
                
                FORMATO DE RESPUESTA:
                1. [tipo_agente] Descripción del paso
                2. [tipo_agente] Descripción del paso
                ...
                
                Cada paso debe ser claro y procesable. El tipo_agente debe ser uno de los disponibles.
                Si un paso requiere múltiples capacidades, elige la más relevante.
                """
                
                # Enviar la solicitud de planificación al agente planificador
                planning_response = await self._send_agent_request(
                    self.agent_id,
                    code_planner_id,
                    planning_prompt,
                    {"original_task": query, **(context or {})}
                )
                
                if planning_response:
                    # Analizar la respuesta para extraer los pasos
                    steps = self._parse_planning_response(planning_response.content)
                    self.logger.info(f"Planificación externa exitosa con {len(steps)} pasos")
                else:
                    self.logger.warning("No se recibió respuesta del planificador externo. Utilizando planificación interna.")
                    steps = []  # Resetear para usar planificación interna
            except Exception as e:
                self.logger.warning(f"Error en planificación externa: {str(e)}. Utilizando planificación interna.")
                steps = []  # Resetear para usar planificación interna
        
        # Si la planificación externa falló o no estaba disponible, usar planificación interna
        if not steps:
            self.logger.info("Usando mecanismo de planificación interna")
            steps = self._internal_task_planning(query)
        
        return steps
        
    async def _delegate_to_planner_agent(self, planner_id: str, query: str, context: Optional[Dict] = None) -> List[Dict]:
        """
        Delega la planificación al PlannerAgent especializado.
        
        Args:
            planner_id: ID del PlannerAgent
            query: La consulta del usuario
            context: Contexto opcional
            
        Returns:
            Lista de pasos para el workflow generada por el PlannerAgent
        """
        self.logger.info(f"Delegando planificación a PlannerAgent {planner_id} para: {query[:50]}...")
        
        planner_context = {
            "from_orchestrator": True,
            "available_agents": {
                agent_id: info["capabilities"] 
                for agent_id, info in self.available_agents.items()
            },
            **(context or {})
        }
        
        # Enviar la solicitud al PlannerAgent
        try:
            response = await self._send_agent_request(
                self.agent_id,
                planner_id,
                query,
                planner_context
            )
            
            if not response:
                self.logger.warning("No se recibió respuesta del PlannerAgent")
                return []
                
            # Extraer el plan de la respuesta
            plan_data = response.metadata.get("plan", {})
            
            if not plan_data:
                self.logger.warning("El PlannerAgent no devolvió un plan válido")
                return []
                
            # Convertir el plan a formato de pasos de workflow
            steps = []
            execution_order = plan_data.get("execution_order", [])
            tasks = plan_data.get("tasks", {})
            
            for task_id in execution_order:
                task = tasks.get(task_id, {})
                if not task:
                    continue
                    
                # Determinar el tipo de agente basado en las capacidades requeridas
                agent_type = self._determine_agent_type_from_capabilities(task.get("required_capabilities", []))
                
                steps.append({
                    "type": agent_type,
                    "description": task.get("description", ""),
                    "status": "pending",
                    "required_capabilities": task.get("required_capabilities", []),
                    "task_id": task_id
                })
                
            self.logger.info(f"Plan generado por PlannerAgent con {len(steps)} pasos")
            return steps
                
        except Exception as e:
            self.logger.error(f"Error al delegar la planificación: {str(e)}")
            return []
            
    def _determine_agent_type_from_capabilities(self, capabilities: List[str]) -> str:
        """
        Determina el tipo de agente más apropiado basado en las capacidades requeridas.
        
        Args:
            capabilities: Lista de capacidades requeridas
            
        Returns:
            Tipo de agente (code, system, echo)
        """
        # Crear un mapa de capacidades a tipos de agentes
        capability_map = {
            # Capacidades del CodeAgent
            "code_generation": "code",
            "analysis": "code",
            "problem_solving": "code",
            "testing": "code",
            "verification": "code",
            
            # Capacidades del SystemAgent
            "system_operations": "system",
            "file_management": "system",
            "execute_command": "system",
            "process_management": "system",
            
            # Capacidades del EchoAgent y generales
            "echo": "echo",
            "test": "echo",
            "general_processing": "echo",
            "information_retrieval": "echo",
            "search": "echo",
            "summarization": "echo"
        }
        
        # Contar los tipos de agentes que coinciden con cada capacidad
        type_counts = {"code": 0, "system": 0, "echo": 0}
        
        for capability in capabilities:
            agent_type = capability_map.get(capability, "echo")  # Por defecto, usar echo
            type_counts[agent_type] += 1
            
        # Seleccionar el tipo con más coincidencias
        if type_counts["code"] > 0:
            return "code"
        elif type_counts["system"] > 0:
            return "system"
        else:
            return "echo"
    
    async def _direct_agent_handling(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Maneja una tarea directamente con el agente más apropiado cuando falla la orquestación.
        
        Args:
            query: La consulta del usuario
            context: Contexto opcional
            
        Returns:
            AgentResponse con el resultado
        """
        self.logger.info(f"Manejando directamente la tarea: {query[:50]}...")
        
        # Caso especial: si es una tarea de generación de código de Fibonacci, usar método especializado
        if "fibonacci" in query.lower() and any(kw in query.lower() for kw in ["generar", "genera", "script", "código", "programa"]):
            self.logger.info("Detectada tarea de Fibonacci, usando método especializado de código")
            return await self._execute_direct_code_task(query, context)
            
        # Caso especial: cualquier tarea de código, usar método especializado
        if any(kw in query.lower() for kw in ["código", "script", "programa", "generar", "function", "python", "javascript"]):
            self.logger.info("Detectada tarea de generación de código, usando método especializado")
            return await self._execute_direct_code_task(query, context)
            
        # Analizar el tipo de tarea para seleccionar el agente más apropiado
        if any(kw in query.lower() for kw in ["archivo", "sistema", "ejecutar", "comando"]):
            agent_type = "system"
        else:
            agent_type = "echo"  # Por defecto, usar el echo agent
            
        agent_id = await self._select_agent_for_task(agent_type, query, context or {})
        
        if not agent_id:
            self.logger.warning(f"No se encontró un agente disponible para {agent_type}. Usando respuesta genérica.")
            return AgentResponse(
                content=f"No pude encontrar un agente adecuado para procesar tu solicitud. Por favor, intenta reformular o especificar más tu tarea.",
                status="error",
                metadata={"error": "no_agent_available"}
            )
        
        # Enviar la solicitud directamente al agente seleccionado
        try:
            self.logger.info(f"Enviando solicitud directamente al agente {agent_id}")
            
            # Preparar contexto específico para el tipo de agente
            agent_context = {"from_orchestrator": True, "direct_handling": True, **(context or {})}
            
            # Agregar contexto adicional basado en el tipo de agente
            if agent_type == "system":
                task_type = "file_operation" if any(kw in query.lower() for kw in ["archivo", "carpeta", "directorio"]) else "system_info"
                agent_context.update({
                    "task_type": task_type,
                    "sender_id": self.agent_id
                })
            
            response = await self._send_agent_request(self.agent_id, agent_id, query, agent_context)
            
            if response:
                return response
            else:
                return AgentResponse(
                    content=f"El agente {agent_id} no respondió a tiempo. Por favor, intenta nuevamente más tarde.",
                    status="timeout",
                    metadata={"agent_id": agent_id}
                )
                
        except Exception as e:
            self.logger.error(f"Error en manejo directo: {str(e)}")
            return AgentResponse(
                content=f"Error al procesar tu solicitud: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
            
    async def _send_agent_request(self, sender_id: str, receiver_id: str, content: str, 
                                 context: Optional[Dict] = None) -> Optional[AgentResponse]:
        """
        Envía una solicitud a un agente y espera la respuesta.
        
        Args:
            sender_id: ID del remitente
            receiver_id: ID del agente receptor
            content: Contenido de la solicitud
            context: Contexto opcional
            
        Returns:
            AgentResponse o None si no hay respuesta
        """
        try:
            self.logger.info(f"Enviando solicitud a {receiver_id}: {content[:50]}...")
            
            # Usar la función de comunicación de agentes
            from .agent_communication import send_agent_request
            
            # Intentar con un timeout mayor para asegurar la respuesta
            response = await send_agent_request(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content,
                context=context,
                timeout=15.0  # Timeout más largo (15 segundos)
            )
            
            return response
        except Exception as e:
            self.logger.error(f"Error enviando solicitud a {receiver_id}: {str(e)}")
            return None
    
    async def _execute_direct_code_task(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Ejecuta una tarea de código directamente con el CodeAgent.
        Útil para casos específicos como Fibonacci que necesitan tratamiento especial.
        
        Args:
            task: La descripción de la tarea de código
            context: Contexto opcional
            
        Returns:
            AgentResponse con el resultado
        """
        # Buscar un agente de código disponible
        agent_type = "code"
        agent_id = None
        
        # Encontrar un agente de código
        for id, info in self.available_agents.items():
            if any(cap in info["capabilities"] for cap in ["code_generation", "generate", "code"]):
                agent_id = id
                break
                
        if not agent_id:
            return AgentResponse(
                content="No hay agentes de código disponibles para ejecutar esta tarea.",
                status="error"
            )
            
        # Preparar contexto específico para CodeAgent con lenguaje explícito
        code_context = {
            "from_orchestrator": True,
            "sender_id": self.agent_id,
            **(context or {})
        }
        
        # Detectar lenguaje y tipo de tarea
        if "fibonacci" in task.lower():
            code_context.update({
                "language": "python",
                "task": "generate"
            })
        else:
            # Intentar detectar lenguaje
            for lang in ["python", "javascript", "java", "c++", "c#"]:
                if lang in task.lower():
                    code_context["language"] = lang
                    break
            
            # Por defecto, usar Python
            if "language" not in code_context:
                code_context["language"] = "python"
                
            # Intentar detectar tipo de tarea
            if any(kw in task.lower() for kw in ["explica", "explique", "analiza", "entiende"]):
                code_context["task"] = "explain"
            elif any(kw in task.lower() for kw in ["mejora", "optimiza", "refactoriza"]):
                code_context["task"] = "improve"
            elif any(kw in task.lower() for kw in ["corrige", "arregla", "fix", "bug"]):
                code_context["task"] = "fix"
            else:
                code_context["task"] = "generate"
        
        # Enviar solicitud al CodeAgent con timeout extendido
        self.logger.info(f"Enviando tarea de código directamente a {agent_id} con contexto: {code_context}")
        
        try:
            # Usar un timeout más largo para tareas complejas
            response = await self._send_agent_request(
                self.agent_id,
                agent_id,
                task,
                code_context,
            )
            
            if response:
                return response
            else:
                return AgentResponse(
                    content=f"El agente {agent_id} no respondió dentro del tiempo límite establecido.",
                    status="timeout"
                )
        except Exception as e:
            self.logger.error(f"Error al procesar la tarea de código: {str(e)}")
            return AgentResponse(
                content=f"Error al procesar la tarea de código: {str(e)}",
                status="error"
            )
    
    async def _select_agent_for_capabilities(self, required_capabilities: List[str], description: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Select the most appropriate agent based on required capabilities.
        
        Args:
            required_capabilities: List of required capabilities
            description: Description of the task
            context: Additional context
            
        Returns:
            ID of the selected agent or None if no suitable agent found
        """
        self.logger.info(f"Seleccionando agente para capacidades {required_capabilities}")
        
        # Verificar primero si la descripción menciona código o programación
        description_lower = description.lower()
        
        # Detectar si es una tarea de programación
        programming_indicators = [
            "python", "javascript", "java", "código", "code", "script", "programa", 
            "function", "función", "class", "clase", "programación", "programming",
            "algorithm", "algoritmo", "implementation", "implementación", "development",
            "desarrollo", "software", "app", "aplicación", "module", "módulo"
        ]
        
        # Si es claramente una tarea de programación, priorizar el CodeAgent
        is_programming_task = any(indicator in description_lower for indicator in programming_indicators)
        
        if is_programming_task:
            self.logger.info("Detectada tarea de programación, buscando agente de código")
            
            # Buscar agente con capacidades de código
            for agent_id, info in self.available_agents.items():
                if any(cap in info["capabilities"] for cap in ["code", "code_generation", "programming"]):
                    self.logger.info(f"Seleccionado agente de código: {agent_id}")
                    return agent_id
        
        # Para tareas generales, verificar las capacidades específicas requeridas
        matches = {}
        for agent_id, info in self.available_agents.items():
            agent_capabilities = info["capabilities"]
            
            # Contar coincidencias exactas de capacidades
            exact_matches = sum(1 for cap in required_capabilities if cap in agent_capabilities)
            
            # Si hay alguna coincidencia, añadir a los candidatos
            if exact_matches > 0:
                matches[agent_id] = exact_matches
        
        if matches:
            # Seleccionar el agente con más coincidencias
            best_agent_id = max(matches.items(), key=lambda x: x[1])[0]
            self.logger.info(f"Agente con más coincidencias de capacidades: {best_agent_id} ({matches[best_agent_id]} coincidencias)")
            return best_agent_id
        
        # Si no hay coincidencias exactas, buscar coincidencias parciales
        for agent_id, info in self.available_agents.items():
            agent_capabilities = info["capabilities"]
            
            # Verificar si alguna de las capacidades del agente contiene alguna de las requeridas
            partial_matches = sum(1 for rcap in required_capabilities 
                                for acap in agent_capabilities 
                                if rcap in acap or acap in rcap)
            
            if partial_matches > 0:
                matches[agent_id] = partial_matches
        
        if matches:
            # Seleccionar el agente con más coincidencias parciales
            best_agent_id = max(matches.items(), key=lambda x: x[1])[0]
            self.logger.info(f"Agente con coincidencias parciales: {best_agent_id} ({matches[best_agent_id]} coincidencias)")
            return best_agent_id
        
        # Si aún no hay coincidencias, buscar un agente general o de propósito múltiple
        for agent_id, info in self.available_agents.items():
            if "general" in info["capabilities"] or "memory" in info["capabilities"]:
                self.logger.info(f"Usando agente general: {agent_id}")
                return agent_id
        
        # Si todo lo demás falla, devolver el primer agente disponible
        if self.available_agents:
            fallback_id = next(iter(self.available_agents.keys()))
            self.logger.warning(f"No se encontró agente ideal para {required_capabilities}, usando {fallback_id} como fallback")
            return fallback_id
        
        self.logger.error(f"No se encontró ningún agente para capacidades {required_capabilities}")
        return None
    
    async def _update_planner_task_status(self, planner_id: str, plan_id: str, task_id: str, status: str, result: Optional[str] = None, error: Optional[str] = None, agent_id: Optional[str] = None) -> None:
        """
        Actualiza el estado de una tarea en el PlannerAgent.
        
        Args:
            planner_id: ID del PlannerAgent
            plan_id: ID del plan
            task_id: ID de la tarea
            status: Nuevo estado de la tarea (PENDING, IN_PROGRESS, COMPLETED, FAILED)
            result: Resultado opcional (si la tarea se completó)
            error: Error opcional (si la tarea falló)
            agent_id: ID opcional del agente asignado a la tarea
        """
        try:
            # Crear contexto con la información de la tarea
            task_context = {
                "update_type": "task_status",
                "plan_id": plan_id,
                "task_id": task_id,
                "status": status
            }
            
            if agent_id:
                task_context["assigned_agent"] = agent_id
                
            if result:
                task_context["result"] = result
                
            if error:
                task_context["error"] = error
            
            # Construir mensaje de actualización
            message = f"update_task:{task_id}:{status}"
            
            # Enviar actualización al PlannerAgent
            self.logger.info(f"Actualizando tarea {task_id} en PlannerAgent {planner_id}: {status}")
            await self._send_agent_request(
                self.agent_id,
                planner_id,
                message,
                task_context
            )
            
        except Exception as e:
            self.logger.warning(f"Error actualizando tarea en PlannerAgent: {str(e)}") 