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
        self.test_receiver = config.get("test_receiver", "echo")
    
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
        
        # Comprobar si es una solicitud para enviar un mensaje a otro agente
        if query.startswith("Enviar:") or query.startswith("Send:"):
            # Extraer el contenido del mensaje
            message_content = query.split(":", 1)[1].strip()
            
            # Determinar el destinatario
            receiver_id = context.get("receiver_id", self.test_receiver)
            
            # Enviar el mensaje y esperar respuesta
            self.logger.info(f"Enviando mensaje a {receiver_id}: {message_content[:50]}...")
            
            try:
                # Registrarnos con el comunicador si aún no lo hemos hecho
                await self.register_with_communicator()
                
                # Enviar el mensaje al destinatario
                response = await self.send_request_to_agent(
                    receiver_id=receiver_id,
                    content=message_content,
                    context={"sender_id": self.agent_id, "is_test": True},
                    timeout=10.0
                )
                
                if response:
                    self.logger.info(f"Respuesta recibida de {receiver_id}")
                    
                    # Guardar la respuesta
                    response_id = f"response_{len(self.responses)+1}"
                    self.responses[response_id] = {
                        "query": message_content,
                        "response": response.content,
                        "receiver_id": receiver_id,
                        "success": True
                    }
                    
                    return AgentResponse(
                        content=f"Mensaje enviado correctamente a {receiver_id} y se recibió respuesta: {response.content}",
                        metadata={
                            "original_message": message_content,
                            "receiver_id": receiver_id,
                            "response_content": response.content,
                            "response_id": response_id,
                            "success": True
                        }
                    )
                else:
                    self.logger.warning(f"No se recibió respuesta de {receiver_id}")
                    
                    return AgentResponse(
                        content=f"Mensaje enviado a {receiver_id} pero no se recibió respuesta en el tiempo límite",
                        status="error",
                        metadata={
                            "original_message": message_content,
                            "receiver_id": receiver_id,
                            "success": False,
                            "error": "timeout"
                        }
                    )
                    
            except Exception as e:
                self.logger.error(f"Error al enviar mensaje: {str(e)}")
                
                return AgentResponse(
                    content=f"Error al enviar mensaje a {receiver_id}: {str(e)}",
                    status="error",
                    metadata={
                        "original_message": message_content,
                        "receiver_id": receiver_id,
                        "success": False,
                        "error": str(e)
                    }
                )
        
        # Caso para recibir mensajes (comportamiento original)
        else:
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
    
    async def send_test_message(self, receiver_id: str, content: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Envía un mensaje de prueba a otro agente.
        
        Este método es más directo que usar process() con "Enviar:".
        
        Args:
            receiver_id: ID del agente destinatario
            content: Contenido del mensaje
            context: Contexto adicional (opcional)
            
        Returns:
            Respuesta del agente
        """
        self.logger.info(f"Método directo - Enviando mensaje a {receiver_id}: {content[:50]}...")
        
        try:
            # Registrarnos con el comunicador si aún no lo hemos hecho
            await self.register_with_communicator()
            
            # Preparar contexto
            ctx = context or {}
            ctx.update({
                "sender_id": self.agent_id,
                "is_test": True,
                "timestamp": self._get_timestamp()
            })
            
            # Enviar el mensaje y esperar respuesta
            response = await self.send_request_to_agent(
                receiver_id=receiver_id,
                content=content,
                context=ctx,
                timeout=10.0
            )
            
            if response:
                self.logger.info(f"Respuesta recibida de {receiver_id}: {response.content[:50]}...")
                
                # Guardar la respuesta
                response_id = f"direct_{len(self.responses)+1}"
                self.responses[response_id] = {
                    "query": content,
                    "response": response.content,
                    "receiver_id": receiver_id,
                    "success": True,
                    "direct_method": True
                }
                
                return AgentResponse(
                    content=f"Mensaje enviado correctamente a {receiver_id}",
                    metadata={
                        "original_message": content,
                        "receiver_id": receiver_id,
                        "response_content": response.content,
                        "response_id": response_id,
                        "success": True
                    }
                )
            else:
                self.logger.warning(f"No se recibió respuesta de {receiver_id}")
                return AgentResponse(
                    content=f"No se recibió respuesta de {receiver_id} en el tiempo límite",
                    status="error",
                    metadata={
                        "success": False,
                        "error": "timeout"
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error al enviar mensaje directo: {str(e)}")
            return AgentResponse(
                content=f"Error al enviar mensaje: {str(e)}",
                status="error",
                metadata={
                    "success": False,
                    "error": str(e)
                }
            )
    
    def _get_timestamp(self):
        """Obtiene una marca de tiempo para los mensajes."""
        import time
        return time.time()
    
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