"""
Main Assistant implementation.

This class implements the MainAssistant agent that serves as the 
central point of interaction with the user, routing requests to
specialized agents as needed.
"""

import logging
from typing import Dict, List, Optional, Any

from ..base import BaseAgent, AgentResponse

class MainAssistant(BaseAgent):
    """
    Main Assistant agent that acts as the central point of interaction with the user.
    
    This agent:
    1. Presents a unified interface for the user
    2. Processes user queries and decides whether to handle them directly or delegate
    3. Coordinates with specialized agents through the orchestrator
    4. Maintains consistent voice interface with TTS
    5. Manages conversation context and history
    
    Attributes:
        specialized_agents: Dictionary of available specialized agents
        default_voice: Voice to use for TTS responses
        conversation_history: List of conversation turns
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the main assistant.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary
        """
        # Always enable TTS for MainAssistant
        config["use_tts"] = config.get("use_tts", True)
        
        # Set a descriptive name if not provided
        if "name" not in config:
            config["name"] = "Jarvis"
            
        if "description" not in config:
            config["description"] = "Main Assistant that coordinates all interactions"
            
        super().__init__(agent_id, config)
        
        # Track available specialized agents
        self.specialized_agents = {}
        
        # Voice configuration
        self.default_voice = config.get("default_voice", "Carlos")
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Track if we have an orchestrator agent available
        self.orchestrator_id = config.get("orchestrator_id")
        
        # Memory settings
        memory_config = config.get("memory_config")
        if memory_config:
            self.setup_memory(memory_config)
            
        self.logger.info(f"MainAssistant '{self.name}' initialized")
    
    async def register_specialized_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """
        Register a specialized agent as available for delegation.
        
        Args:
            agent_id: ID of the agent to register
            capabilities: List of capabilities the agent offers
        """
        self.specialized_agents[agent_id] = {
            "capabilities": capabilities,
            "status": "idle",
            "last_used": None
        }
        self.logger.info(f"Specialized agent {agent_id} registered with capabilities: {capabilities}")
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        # Basic capabilities
        capabilities = ["conversation", "routing", "tts"]
        
        # Add capabilities from specialized agents
        for agent_id, agent_info in self.specialized_agents.items():
            capabilities.extend([f"delegated:{cap}" for cap in agent_info["capabilities"]])
            
        return list(set(capabilities))  # Remove duplicates
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a user query and return a response.
        
        This method:
        1. Analyzes the query to determine the best way to handle it
        2. Either handles directly or delegates to specialized agents
        3. Processes the response with TTS if enabled
        4. Maintains conversation history
        
        Args:
            query: User's query text
            context: Optional context information
            
        Returns:
            AgentResponse with the results
        """
        self.logger.info(f"Processing query: {query[:50]}...")
        self.set_state("processing")
        context = context or {}
        
        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": query,
            "timestamp": context.get("timestamp")
        })
        
        try:
            # Determine if this query needs specialized handling
            agent_type, response = await self._determine_agent_for_query(query, context)
            
            # If we already have a response (e.g. from agent determination), return it
            if response:
                return self._finalize_response(response, query, context)
            
            # Handle based on the determined agent type
            if agent_type == "direct":
                # Handle directly - simple responses that don't need specialized agents
                response = await self._handle_direct_query(query, context)
            elif agent_type == "orchestrator" and self.orchestrator_id:
                # Use orchestrator for complex tasks requiring multiple agents
                response = await self._handle_via_orchestrator(query, context)
            else:
                # Use a specific specialized agent
                response = await self._handle_via_specialized_agent(agent_type, query, context)
            
            # Process the response (add to history, apply TTS)
            return self._finalize_response(response, query, context)
            
        except Exception as e:
            self.logger.error(f"Error processing query: {str(e)}")
            self.set_state("error")
            
            error_response = AgentResponse(
                content=f"Lo siento, no pude procesar esa solicitud debido a un error: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
            
            return self._finalize_response(error_response, query, context)
    
    def _finalize_response(self, response: AgentResponse, query: str, context: Dict) -> AgentResponse:
        """
        Finalize the response by adding to history and processing TTS.
        
        Args:
            response: The response to finalize
            query: Original query
            context: Request context
            
        Returns:
            Processed response
        """
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content,
            "status": response.status,
            "timestamp": context.get("timestamp")
        })
        
        # Store in memory if available
        if self.has_memory():
            convo_entry = {
                "query": query,
                "response": response.content,
                "status": response.status
            }
            self.remember(
                content=convo_entry,
                memory_type="conversation",
                metadata={"query": query}
            )
        
        # Process TTS if enabled
        if self.has_tts():
            # Force TTS voice based on assistant name
            tts_context = context.copy() if context else {}
            tts_context["tts_params"] = tts_context.get("tts_params", {})
            tts_context["tts_params"]["voice_name"] = self.default_voice
            tts_context["use_tts"] = True
            
            # Set play_audio to True by default for MainAssistant
            if "play_audio" not in tts_context:
                tts_context["play_audio"] = True
                
            response = self._process_tts_response(response, tts_context)
        
        # Reset state
        self.set_state("idle")
        
        return response
    
    async def _determine_agent_for_query(self, query: str, context: Optional[Dict] = None) -> tuple:
        """
        Determine which agent should handle the given query.
        
        Args:
            query: User's query to analyze
            context: Optional context information
            
        Returns:
            tuple: (agent_type, optional_response)
        """
        # If context explicitly specifies an agent, use that
        if context and "agent_type" in context:
            return context["agent_type"], None
        
        # Convert query to lowercase for easier matching
        query_lower = query.lower()
        
        # Check for explicit agent mentions
        explicit_patterns = {
            "code": ["genera código", "crea una función", "escribe un programa", "código para", "código en"],
            "system": ["ejecuta", "abre archivo", "directorio", "sistema operativo", "comando"],
            "memory": ["recuerda", "memoria", "olvidar", "recordar", "memorizar", "hecho"]
        }
        
        # Check for explicit agent requests first
        for agent_type, patterns in explicit_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    self.logger.info(f"Matched explicit pattern '{pattern}' for {agent_type} agent")
                    return agent_type, None
        
        # Check for memory-related patterns
        memory_keywords = ["qué sabes sobre", "qué recuerdas de", "búsqueda", "busca información",
                         "qué información tienes", "busca en tu memoria"]
        
        for keyword in memory_keywords:
            if keyword in query_lower:
                self.logger.info(f"Matched memory pattern '{keyword}' - using memory agent")
                return "memory", None
        
        # Default to direct handling for simple queries
        return "direct", None
    
    async def _handle_direct_query(self, query: str, context: Dict) -> AgentResponse:
        """
        Handle a query directly without using specialized agents.
        
        Args:
            query: User's query
            context: Request context
            
        Returns:
            AgentResponse with the result
        """
        query_lower = query.lower()
        
        # Simple greeting
        if any(x in query_lower for x in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
            response = f"Hola, soy {self.name}, tu asistente personal. ¿En qué puedo ayudarte hoy?"
            return AgentResponse(content=response)
            
        # Help request
        if "ayuda" in query_lower or "qué puedes hacer" in query_lower:
            capabilities = self._get_system_capabilities_description()
            response = f"Soy {self.name}, tu asistente personal. Puedo {capabilities}. ¿En qué puedo ayudarte?"
            return AgentResponse(content=response)
            
        # Identity question
        if "quién eres" in query_lower or "cómo te llamas" in query_lower:
            response = f"Soy {self.name}, tu asistente virtual. Estoy aquí para ayudarte con diversas tareas, desde programación hasta operaciones del sistema."
            return AgentResponse(content=response)
            
        # Simple echo for direct queries
        if len(query_lower) < 20 and not any(char in query_lower for char in "?!¿¡"):
            response = f"Entendido. {query}"
            return AgentResponse(content=response)
            
        # Default response for unrecognized direct queries
        return AgentResponse(
            content=f"No estoy seguro de cómo manejar esa solicitud directamente. Déjame intentar delegarla a un agente especializado.",
            metadata={"action": "delegate_query"}
        )
    
    async def _handle_via_orchestrator(self, query: str, context: Dict) -> AgentResponse:
        """
        Handle a query via the orchestrator agent.
        
        Args:
            query: User's query
            context: Request context
            
        Returns:
            AgentResponse with the result
        """
        self.logger.info(f"Delegating query to orchestrator: {query[:50]}...")
        
        # Ensure we're registered with communicator
        await self.register_with_communicator()
        
        # Prepare context for orchestrator
        orchestrator_context = {
            "from_main_assistant": True,
            "original_query": query,
            **(context or {})
        }
        
        # Send request to orchestrator
        response = await self.send_request_to_agent(
            self.orchestrator_id,
            query,
            orchestrator_context
        )
        
        if not response:
            return AgentResponse(
                content="Lo siento, el orquestador no está disponible en este momento. Puedo intentar manejar tu solicitud de otra manera.",
                status="error",
                metadata={"error": "orchestrator_unavailable"}
            )
            
        return response
    
    async def _handle_via_specialized_agent(self, agent_type: str, query: str, context: Dict) -> AgentResponse:
        """
        Handle a query by delegating to a specialized agent.
        
        Args:
            agent_type: Type of agent to use
            query: User's query
            context: Request context
            
        Returns:
            AgentResponse with the result
        """
        self.logger.info(f"Delegating query to {agent_type} agent: {query[:50]}...")
        
        # Find an appropriate agent ID based on type
        agent_id = self._find_agent_id_by_type(agent_type)
        
        if not agent_id:
            return AgentResponse(
                content=f"Lo siento, no tengo un agente de tipo {agent_type} disponible en este momento.",
                status="error",
                metadata={"error": "agent_unavailable"}
            )
            
        # Ensure we're registered with communicator
        await self.register_with_communicator()
        
        # Prepare context for specialized agent
        agent_context = {
            "from_main_assistant": True,
            "original_query": query,
            **(context or {})
        }
        
        # Add task-specific context
        if agent_type == "code":
            agent_context["task"] = "generate"  # Default task for code agent
            
            # Detect language from query
            for lang in ["python", "javascript", "java", "c++", "c#"]:
                if lang in query.lower():
                    agent_context["language"] = lang
                    break
        
        # Send request to specialized agent
        response = await self.send_request_to_agent(
            agent_id,
            query,
            agent_context
        )
        
        if not response:
            return AgentResponse(
                content=f"Lo siento, el agente especializado no está disponible en este momento.",
                status="error",
                metadata={"error": "agent_unavailable"}
            )
            
        return response
    
    def _find_agent_id_by_type(self, agent_type: str) -> Optional[str]:
        """
        Find a suitable agent ID based on the agent type.
        
        Args:
            agent_type: Type of agent to find
            
        Returns:
            Agent ID if found, None otherwise
        """
        # Direct mapping for common agent types
        type_to_id_map = {
            "code": "code_assistant",
            "system": "system_manager",
            "echo": "echo_service",
            "memory": "memory" # Mapeo directo para agente de memoria
        }
        
        # Try direct mapping first
        if agent_type in type_to_id_map:
            return type_to_id_map[agent_type]
            
        # Otherwise, search registered agents for matching capabilities
        for agent_id, info in self.specialized_agents.items():
            capabilities = info["capabilities"]
            
            # Check if the agent has a capability matching the type
            if agent_type in capabilities:
                return agent_id
                
            # Check for partial matches in capabilities
            for capability in capabilities:
                if agent_type in capability:
                    return agent_id
            
            # Check for semantic search capability for memory
            if agent_type == "memory" and "semantic_search" in capabilities:
                return agent_id
                
        return None
    
    def _get_system_capabilities_description(self) -> str:
        """
        Get a human-readable description of system capabilities.
        
        Returns:
            String describing capabilities
        """
        has_code = any("code" in agent_info["capabilities"] for agent_info in self.specialized_agents.values())
        has_system = any("system" in agent_info["capabilities"] for agent_info in self.specialized_agents.values())
        has_orchestrator = self.orchestrator_id is not None
        
        capabilities = []
        
        if has_code:
            capabilities.append("generar y analizar código")
            
        if has_system:
            capabilities.append("interactuar con el sistema de archivos")
            
        if has_orchestrator:
            capabilities.append("resolver tareas complejas coordinando agentes especializados")
            
        capabilities.append("responder a tus preguntas")
        capabilities.append("conversar contigo por voz")
        
        if len(capabilities) == 1:
            return capabilities[0]
        elif len(capabilities) == 2:
            return f"{capabilities[0]} y {capabilities[1]}"
        else:
            return ", ".join(capabilities[:-1]) + f" y {capabilities[-1]}" 