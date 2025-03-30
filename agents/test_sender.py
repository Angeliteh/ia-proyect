"""
Test Sender Agent module.

Este agente sirve como remitente de prueba para verificar la comunicación
entre agentes. Proporciona un mecanismo para validar que los mensajes
se envían y reciben correctamente sin depender de un agente real.
"""

import logging
from typing import Dict, List, Any, Optional, Union

from .base import BaseAgent, AgentResponse

class TestSenderAgent(BaseAgent):
    """
    Agente para pruebas de envío de mensajes.
    
    Este agente actúa como un remitente de prueba para verificar la
    comunicación entre agentes, recibiendo y procesando respuestas
    de otros agentes.
    
    Attributes:
        responses: Diccionario que almacena las respuestas recibidas
        logger: Logger para esta clase
        id: Identificador único del agente (accesible como propiedad)
    """
    
    def __init__(self, agent_id: str = "test_sender", config: Dict = None):
        """
        Inicializa el agente de prueba.
        
        Args:
            agent_id: Identificador único para el agente (por defecto 'test_sender')
            config: Configuración adicional (opcional)
        """
        super().__init__(agent_id, config or {})
        self.responses = {}
        self.logger = logging.getLogger("agent.test_sender")
        self.logger.info(f"TestSenderAgent inicializado con ID: {agent_id}")
    
    @property
    def id(self) -> str:
        """
        Obtiene el ID del agente.
        
        Returns:
            ID del agente
        """
        return self.agent_id
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Procesa un mensaje de prueba.
        
        Args:
            query: El mensaje a procesar
            context: Contexto adicional (opcional)
            
        Returns:
            Respuesta del agente
        """
        self.set_state("processing")
        context = context or {}
        
        # Registrar que recibimos un mensaje
        message_id = context.get("message_id", "unknown")
        sender_id = context.get("sender_id", "unknown")
        
        self.logger.info(f"Mensaje recibido de {sender_id} con ID {message_id}: {query[:50]}...")
        
        # Almacenar la respuesta para recuperación posterior
        self.responses[message_id] = {
            "query": query,
            "sender_id": sender_id,
            "context": context
        }
        
        # Generar respuesta estándar de verificación
        response = AgentResponse(
            content=f"Mensaje de prueba recibido correctamente.",
            metadata={
                "original_message_id": message_id,
                "original_sender": sender_id,
                "is_test": True
            }
        )
        
        self.set_state("idle")
        return response
    
    def get_capabilities(self) -> List[str]:
        """
        Obtiene las capacidades del agente.
        
        Returns:
            Lista de capacidades
        """
        return ["test_messaging", "communication_verification"]
    
    def get_response(self, message_id: str) -> Dict:
        """
        Recupera una respuesta almacenada por su ID de mensaje.
        
        Args:
            message_id: ID del mensaje a recuperar
            
        Returns:
            Información de la respuesta o diccionario vacío si no existe
        """
        return self.responses.get(message_id, {})
    
    def clear_responses(self) -> None:
        """
        Limpia todas las respuestas almacenadas.
        """
        self.responses.clear()
        self.logger.info("Todas las respuestas han sido eliminadas") 