"""
Echo Agent module.

This is a simple agent that echoes back the input it receives.
Useful for testing the agent infrastructure.
"""

import asyncio
from typing import Dict, List, Optional

from .base import BaseAgent, AgentResponse
from .agent_communication import Message, MessageType

class EchoAgent(BaseAgent):
    """
    Simple agent that echoes back the input it receives.
    
    This agent is primarily used for testing the agent infrastructure
    without requiring complex model integrations.
    """
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process the query by echoing it back.
        
        Args:
            query: The input text
            context: Optional context (unused)
            
        Returns:
            AgentResponse containing the echoed input
        """
        self.logger.info(f"Processing query with echo agent: {query[:30]}...")
        self.set_state("processing")
        
        # Simular un pequeño retraso para realismo
        await asyncio.sleep(0.1)
        
        # Detectar si es una solicitud de planificación
        if "task planning request" in query.lower() and "format your response" in query.lower():
            response_content = self._handle_planning_request(query, context or {})
            response = AgentResponse(
                content=response_content,
                metadata={
                    "agent_id": self.agent_id,
                    "query_length": len(query),
                    "context": context or {},
                    "is_planning_response": True
                }
            )
        else:
            # Respuesta de eco normal
            response = AgentResponse(
                content=f"Echo: {query}",
                metadata={
                    "agent_id": self.agent_id,
                    "query_length": len(query),
                    "context": context or {}
                }
            )
        
        self.set_state("idle")
        return response
    
    def _handle_planning_request(self, query: str, context: Dict) -> str:
        """
        Maneja solicitudes de planificación proporcionando un plan estructurado.
        
        Args:
            query: Solicitud de planificación
            context: Contexto de la solicitud
            
        Returns:
            Respuesta estructurada con pasos para el plan
        """
        # Extraer la tarea original
        task_start = query.find("TASK:")
        task_end = query.find("\n", task_start)
        
        if task_start > 0 and task_end > task_start:
            original_task = query[task_start + 5:task_end].strip()
        else:
            original_task = context.get("original_task", "Unknown task")
        
        self.logger.info(f"EchoAgent generando plan para: {original_task[:50]}...")
        
        # Detectar si la tarea está relacionada con código
        if any(kw in original_task.lower() for kw in ["código", "code", "script", "program", "python", "javascript"]):
            return """
1. [code] Analizar los requerimientos y generar el código solicitado
2. [echo] Proporcionar el resultado y explicación del código
"""
        
        # Detectar si la tarea está relacionada con el sistema
        elif any(kw in original_task.lower() for kw in ["sistema", "system", "archivo", "file", "ejecutar", "run"]):
            return """
1. [system] Ejecutar la operación solicitada en el sistema
2. [echo] Mostrar los resultados de la operación
"""
        
        # Si es una tarea de repetición
        elif "repite" in original_task.lower() or "echo" in original_task.lower():
            return """
1. [echo] Procesar el mensaje a repetir
2. [echo] Mostrar el mensaje repetido
"""
        
        # Plan genérico para otras tareas
        else:
            return """
1. [echo] Procesar la solicitud original
2. [echo] Proporcionar la respuesta final
"""
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List containing the 'echo' capability
        """
        return ["echo"]
    
    async def _handle_message(self, message: Message) -> None:
        """
        Implementación directa para manejar mensajes entrantes.
        Esta sobrescribe el método de la clase base para mayor eficiencia.
        
        Args:
            message: El mensaje entrante para procesar
        """
        self.logger.info(f"ECHO AGENT recibió mensaje: {message.content[:50]}...")
        
        # Procesar la consulta
        response = await self.process(message.content, message.context)
        
        # Crear un mensaje de respuesta
        response_msg = message.create_response(
            content=response.content,
            context=response.metadata
        )
        
        # Establecer el tipo de mensaje adecuado según el estado de la respuesta
        if response.status != "success":
            response_msg.msg_type = MessageType.ERROR
        
        # Enviar la respuesta directamente
        from .agent_communication import communicator
        self.logger.info(f"ECHO AGENT enviando respuesta: {response.content[:50]}...")
        await communicator.send_message(response_msg) 