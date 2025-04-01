"""
Echo Agent module.

This is a simple agent that echoes back the input it receives.
Useful for testing the agent infrastructure.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from .base import BaseAgent, AgentResponse
from .agent_communication import Message, MessageType

class EchoAgent(BaseAgent):
    """
    Simple agent that echoes back the input it receives.
    
    This agent is primarily used for testing the agent infrastructure
    without requiring complex model integrations.
    """
    
    def __init__(self, agent_id: str = "echo", config: Dict = None):
        """
        Initialize the echo agent.
        
        Args:
            agent_id: Unique identifier for the agent (default 'echo')
            config: Additional configuration (optional)
        """
        super().__init__(agent_id, config or {})
        
        # Lista para almacenar mensajes recibidos (útil para pruebas)
        self._received_messages = []
        self.max_stored_messages = config.get("max_stored_messages", 20)
    
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
        
        # Almacenar el mensaje recibido para pruebas
        self._store_received_message(query, context)
        
        # Simular un pequeño retraso para realismo
        await asyncio.sleep(0.1)
        
        # Check memory first to see if we've seen similar queries
        relevant_memories = []
        memory_context = {}
        
        if self.has_memory():
            # Try to recall any similar queries from memory
            relevant_memories = self.recall(query=query, limit=3)
            
            if relevant_memories:
                memory_content = "\n".join([f"- {m.content}" for m in relevant_memories])
                self.logger.info(f"Found {len(relevant_memories)} relevant memories")
                
                # Add memory information to context
                memory_context = {
                    "memory_used": True,
                    "memories_found": len(relevant_memories),
                    "memory_content": memory_content
                }
        
        # Detectar si es una solicitud de planificación
        if "task planning request" in query.lower() and "format your response" in query.lower():
            response_content = self._handle_planning_request(query, context or {})
            response = AgentResponse(
                content=response_content,
                metadata={
                    "agent_id": self.agent_id,
                    "query_length": len(query),
                    "context": context or {},
                    "is_planning_response": True,
                    **memory_context
                }
            )
        else:
            # Check if this is a repeated query based on memory
            if relevant_memories and any(m.content == query for m in relevant_memories):
                response_content = f"Echo (remembered): {query}\n(I've seen this before!)"
            else:
                # Normal echo response
                response_content = f"Echo: {query}"
            
            response = AgentResponse(
                content=response_content,
                metadata={
                    "agent_id": self.agent_id,
                    "query_length": len(query),
                    "context": context or {},
                    **memory_context
                }
            )
        
        # Remember this interaction
        if self.has_memory():
            self.remember(
                content=query,
                importance=0.3,  # Echo queries are usually less important
                memory_type="echo_query",
                metadata={
                    "response": response_content,
                    "timestamp": datetime.now().isoformat(),
                    **(context or {})
                }
            )
        
        # Procesar respuesta a través del TTS si está habilitado
        if self.has_tts() and context and context.get("use_tts", self.use_tts):
            self.logger.info(f"Procesando respuesta TTS para: {response_content[:30]}...")
            response = self._process_tts_response(response, context)
        
        self.set_state("idle")
        return response
    
    def _store_received_message(self, query: str, context: Optional[Dict] = None):
        """
        Almacena el mensaje recibido para pruebas y depuración.
        
        Args:
            query: El mensaje recibido
            context: El contexto del mensaje
        """
        # Crear un registro del mensaje con timestamp
        message_record = {
            "query": query,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id
        }
        
        # Añadir a la lista de mensajes recibidos
        self._received_messages.append(message_record)
        
        # Limitar el número de mensajes almacenados
        if len(self._received_messages) > self.max_stored_messages:
            self._received_messages.pop(0)  # Eliminar el más antiguo
            
        self.logger.debug(f"Mensaje almacenado. Total de mensajes: {len(self._received_messages)}")
    
    async def _handle_message(self, message):
        """
        Manejador personalizado para mensajes de comunicación entre agentes.
        
        Sobrescribe el método de la clase base para asegurar que los mensajes
        se registren adecuadamente.
        
        Args:
            message: El mensaje recibido
            
        Returns:
            Respuesta al mensaje o None
        """
        # Registrar el mensaje para pruebas
        if isinstance(message, dict):
            self._store_received_message(
                message.get("content", ""),
                message
            )
        elif hasattr(message, "content") and hasattr(message, "to_dict"):
            self._store_received_message(
                message.content,
                message.to_dict()
            )
        
        # Delegar al manejador de la clase base
        return await super()._handle_message(message)
    
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
        return ["echo", "tts_enabled" if self.has_tts() else "tts_disabled"]
    
    def get_received_messages(self) -> List[Dict]:
        """
        Obtiene la lista de mensajes recibidos.
        
        Útil para pruebas y verificación.
        
        Returns:
            Lista de mensajes recibidos
        """
        return self._received_messages.copy()
    
    def clear_received_messages(self) -> None:
        """
        Limpia la lista de mensajes recibidos.
        
        Útil para reiniciar el estado entre pruebas.
        """
        self._received_messages.clear()
        self.logger.info("Lista de mensajes recibidos limpiada") 