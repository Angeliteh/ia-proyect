"""
V.I.O. (Virtual Intelligence Operator) implementation.

Este módulo implementa a V.I.O., el asistente central y segundo al mando,
encargado de coordinar a todos los agentes del sistema, gestionar la memoria persistente
y optimizar el desempeño general del sistema para el usuario.

V.I.O. actúa como un punto central de interacción, priorizando siempre las necesidades
del usuario y mostrando una personalidad relajada pero segura, amigable pero responsable.
"""

import logging
from typing import Dict, List, Optional, Any
import os
import re

from ..base import BaseAgent, AgentResponse

class MainAssistant(BaseAgent):
    """
    V.I.O. (Virtual Intelligence Operator) - Tu asistente central y mano derecha.
    
    Este agente:
    1. Coordina todos los agentes del sistema en tu nombre
    2. Gestiona memoria persistente para mejorar constantemente
    3. Procesa tus consultas con un estilo relajado y directo
    4. Sugiere mejoras proactivamente
    5. Prioriza tus necesidades por encima de todo
    
    Attributes:
        specialized_agents: Diccionario de agentes especializados disponibles
        default_voice: Voz a usar para TTS
        conversation_history: Historial de la conversación
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Inicializa a V.I.O., tu asistente de confianza.
        
        Args:
            agent_id: Identificador único del agente
            config: Configuración del agente
        """
        # Always enable TTS for V.I.O.
        config["use_tts"] = config.get("use_tts", True)
        
        # Set a descriptive name if not provided
        if "name" not in config:
            config["name"] = "V.I.O."
            
        if "description" not in config:
            config["description"] = "Virtual Intelligence Operator - Tu asistente central y mano derecha"
            
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
            
        self.logger.info(f"V.I.O. '{self.name}' inicializado y listo para servirte")
    
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
            # MEJORA: Consultar memoria primero para enriquecer contexto
            memory_context = await self._enrich_with_memory(query, context)
            if memory_context.get("memory_results"):
                self.logger.info(f"Encontradas {len(memory_context['memory_results'])} memorias relevantes")
                # Agregar contexto de memoria al contexto original
                context.update(memory_context)
            
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
    
    async def _enrich_with_memory(self, query: str, context: Dict) -> Dict:
        """
        Consulta la memoria para enriquecer el contexto antes de procesar.
        
        Args:
            query: Consulta del usuario
            context: Contexto actual
            
        Returns:
            Diccionario con información de memoria
        """
        memory_context = {}
        
        # Solo consultar memoria si está disponible
        if not self.has_memory():
            return memory_context
            
        try:
            # Consultar memoria semántica
            memories = self.memory_manager.search_memories(
                query=query,
                limit=5,
                threshold=0.15  # Umbral más permisivo para esta búsqueda inicial
            )
            
            if memories:
                # Guardar resultados para uso posterior
                memory_context["memory_results"] = memories
                memory_context["memory_used"] = True
                memory_context["memories_found"] = len(memories)
                
                # Extraer contenido relevante para contexto
                relevant_content = []
                for mem in memories:
                    # Manejar diferentes formatos de memoria
                    if isinstance(mem.content, dict) and "content" in mem.content:
                        relevant_content.append(mem.content["content"])
                    elif isinstance(mem.content, dict) and "response" in mem.content:
                        relevant_content.append(mem.content["response"])
                    else:
                        relevant_content.append(str(mem.content))
                
                # Añadir al contexto
                memory_context["relevant_content"] = relevant_content
                
                # Crear resumen para decisión de agente
                memory_context["memory_summary"] = "\n".join(relevant_content[:2])
                
                self.logger.info(f"Memoria consultada. Encontrados {len(memories)} resultados relevantes.")
            else:
                self.logger.info("No se encontraron memorias relevantes para la consulta.")
                memory_context["memory_used"] = False
                memory_context["memories_found"] = 0
        
        except Exception as e:
            self.logger.error(f"Error consultando memoria: {str(e)}")
            memory_context["memory_error"] = str(e)
        
        return memory_context
    
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
            
            # Set play_audio to True by default for V.I.O.
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
        # Si el contexto especifica explícitamente un agente, usar ese
        if context and "agent_type" in context:
            self.logger.info(f"Usando agente explícito desde contexto: {context['agent_type']}")
            return context["agent_type"], None
        
        # MEJORA: Revisar si hay resultados de memoria relevantes para la consulta
        if context and context.get("memory_used") and context.get("memories_found", 0) > 0:
            # Verificar si la memoria contiene información sobre la consulta directa
            memories = context.get("memory_results", [])
            
            # Verificar si alguna memoria es altamente relevante (importance > 0.8)
            highly_relevant = False
            for memory in memories:
                if memory.importance > 0.8:
                    highly_relevant = True
                    break
                    
            # Si hay memorias relevantes y son consultas sobre conocimiento general
            # y no hay indicios de que se requiera generación de código, preferir memoria
            if highly_relevant:
                query_normalized = self._normalize_query(query)
                code_indicators = [
                    "genera", "generar", "crea", "crear", "escribe", "escribir", 
                    "implementa", "implementar", "programa", "programar"
                ]
                
                # Si no parece ser una solicitud de generación de código, usar memoria
                if not any(indicator in query_normalized for indicator in code_indicators):
                    self.logger.info("Memorias altamente relevantes encontradas, priorizando respuesta basada en memoria")
                    
                    # Preferir usar memory_agent para gestionar la respuesta con contexto completo
                    self.logger.info("Delegando a memory_agent para respuesta detallada")
                    agent_id = self._find_agent_id_by_type("memory")
                    if agent_id:
                        return agent_id, None
                    
                    # Fallback: preparar una respuesta directa basada en la memoria más relevante
                    memory_content = str(memories[0].content)
                    
                    # Verificar si es una conversación tipo pregunta-respuesta
                    if "Pregunta:" in memory_content and "Respuesta:" in memory_content:
                        parts = memory_content.split("Respuesta:", 1)
                        if len(parts) > 1:
                            memory_content = parts[1].strip()
                    
                    # Si la memoria es muy grande, usarla como contexto pero no responder directamente
                    if len(memory_content) > 500:
                        self.logger.info("Memoria relevante pero extensa, derivando a memory_agent")
                        return "memory", None
                        
                    response = AgentResponse(
                        content=memory_content,
                        status="success",
                        metadata={
                            "memory_used": True,
                            "memories_found": len(memories),
                            "direct_memory_response": True
                        }
                    )
                    return "direct", response
                    
        # Normalizar consulta para patrones más robustos (elimina acentos, signos, y corrige palabras pegadas)
        query_lower = query.lower().strip()
        query_normalized = self._normalize_query(query)
        
        self.logger.debug(f"Consulta original: '{query}', normalizada: '{query_normalized}'")
        
        # 1. DETECCIÓN DE PATRONES DE ALTO NIVEL - Respuestas directas
        # ===========================================================
        
        # PATRONES CONVERSACIONALES: Saludos, cómo estás, etc.
        conversation_patterns = {
            "greetings": ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "saludos", "que tal"],
            "farewells": ["adios", "hasta luego", "nos vemos", "chao", "bye", "hasta pronto"],
            "how_are_you": ["como estas", "como te va", "como te encuentras", "que tal estas", "como te sientes"],
            "thank_you": ["gracias", "te lo agradezco", "muy amable", "gracias por tu ayuda"]
        }
        
        # Verificar patrones conversacionales
        for pattern_type, patterns in conversation_patterns.items():
            for pattern in patterns:
                if pattern in query_normalized or query_normalized.startswith(pattern):
                    self.logger.info(f"Detectado patrón conversacional: {pattern_type} - '{pattern}'")
                    
                    # Estos patrones básicos deben manejarse directamente
                    return "direct", None
        
        # 1.1 CONSULTAS EMOCIONALES Y DE EXPERIENCIA DE USUARIO
        # Estas deben manejarse directamente por V.I.O.
        emotion_experience_patterns = [
            "me siento", "siento que", "se siente", "me parece", 
            "es frustrante", "estoy frustrado", "frustracion", 
            "no funciona", "no sirve", "no entiendo", 
            "no se que hacer", "ayudame", "necesito ayuda",
            "experiencia", "opinion", "te parece", "crees que",
            "estas sintiendo", "que sientes", "como se siente"
        ]
        
        if any(pattern in query_normalized for pattern in emotion_experience_patterns):
            self.logger.info(f"Detectada consulta emocional o de experiencia: '{query_normalized}'")
            return "direct", None
        
        # Despedidas - responder directamente
        farewell_phrases = ["me voy", "hasta luego", "nos vemos despues", "hablamos luego"]
        if any(phrase in query_normalized for phrase in farewell_phrases):
            self.logger.info("Detectada frase de despedida, respondiendo directamente")
            return "direct", AgentResponse(content="¡Hasta pronto! Estaré aquí cuando me necesites.")
        
        # 2. CLASIFICACIÓN DE CONSULTAS POR TIPO
        # ======================================
        
        # A. DETECTAR SOLICITUDES DE GENERACIÓN DE CÓDIGO
        # Patrón 1: Verbos específicos de creación + programación
        code_generation_verbs = [
            "crea", "crear", "genera", "generar", "escribe", "escribir", "implementa", "implementar", 
            "programa", "programar", "desarrolla", "desarrollar", "codifica", "codificar"
        ]
        
        code_objects = [
            "programa", "codigo", "funcion", "script", "clase", "metodo", "aplicacion", 
            "app", "algoritmo", "modulo", "libreria", "codigo fuente"
        ]
        
        languages = ["python", "javascript", "java", "c++", "typescript", "html", "css", "php", "ruby", "go"]
        
        # Patrón muy específico: verbo + objeto de código + lenguaje
        is_code_generation = False
        
        # Verificación de patrones de generación de código - usando consulta normalizada
        for verb in code_generation_verbs:
            if verb in query_normalized:
                # Buscar objetos de código cerca del verbo
                for obj in code_objects:
                    if obj in query_normalized:
                        is_code_generation = True
                        self.logger.info(f"Detectada solicitud de generación de código: verbo='{verb}' + objeto='{obj}'")
                        break
                
                # Buscar lenguajes de programación
                for lang in languages:
                    if lang in query_normalized:
                        is_code_generation = True
                        self.logger.info(f"Detectada solicitud de generación de código: verbo='{verb}' + lenguaje='{lang}'")
                        break
        
        # Expresiones específicas que indican generación de código
        code_generation_patterns = [
            "codigo para", "funcion que", "programa que", "implementacion de",
            "escribir un algoritmo", "desarrollar una clase", "crear un script"
        ]
        
        if any(pattern in query_normalized for pattern in code_generation_patterns):
            is_code_generation = True
            self.logger.info(f"Patrón específico de generación de código detectado")
        
        if is_code_generation:
            self.logger.info("Solicitud de generación de código confirmada, asignando a CodeAgent")
            return "code", None
        
        # B. DETECTAR SOLICITUDES DE EXPLICACIÓN DE CONCEPTOS
        # (Estas van al memory_agent para búsqueda de conocimiento)
        explanation_patterns = [
            "que es", "explica", "explicame", "explicacion de", "definicion de", 
            "significado de", "dime que", "cuentame sobre",
            "hablame de", "que significa"
        ]
        
        # Verificar patrones de solicitud de explicación usando consulta normalizada
        is_explanation_request = False
        for pattern in explanation_patterns:
            if pattern in query_normalized and not is_code_generation:
                is_explanation_request = True
                self.logger.info(f"Detectada solicitud de explicación: '{pattern}'")
                break
        
        # Si tenemos una solicitud de explicación sobre un lenguaje de programación
        # pero no es de generación de código, asignar al memory_agent
        if is_explanation_request and any(lang in query_normalized for lang in languages):
            self.logger.info("Solicitud de explicación sobre lenguaje de programación, asignando a MemoryAgent")
            return "memory", None
        
        # C. DETECTAR CONSULTAS SOBRE HARDWARE/SISTEMA
        # Esto debe tener alta prioridad para evitar confusiones con "memoria"
        hardware_terms = ["ram", "cpu", "procesador", "disco", "almacenamiento", "hardware", 
                         "sistema operativo", "windows", "linux", "mac", "red", "driver"]
        
        system_verbs = ["ejecuta", "abre", "cierra", "configura", "instala", "desinstala", 
                       "actualiza", "reinicia", "apaga", "muestra"]
        
        # Patrones específicos de sistema
        system_patterns = [
            "sistema operativo", "archivos de", "carpeta", "directorio", "espacio en disco",
            "uso de memoria", "memoria ram", "proceso", "comando", "terminal", "consola"
        ]
        
        # Verificar patrones de sistema usando consulta normalizada
        if (any(term in query_normalized for term in hardware_terms) or
            any(pattern in query_normalized for pattern in system_patterns) or
            any(verb in query_normalized for verb in system_verbs)):
            self.logger.info("Detectada consulta sobre hardware/sistema, asignando a SystemAgent")
            return "system", None
        
        # D. DETECTAR TAREAS COMPLEJAS QUE REQUIEREN ORQUESTACIÓN
        orchestration_indicators = [
            "paso a paso", "workflow", "flujo de trabajo", "secuencia de pasos",
            "primero", "luego", "despues", "finalmente", "coordina", "coordinar",
            "y posteriormente", "a continuacion", "trabajo en equipo"
        ]
        
        # Verificar indicadores de orquestación usando consulta normalizada
        if any(indicator in query_normalized for indicator in orchestration_indicators) and self.orchestrator_id:
            self.logger.info("Detectada tarea compleja que requiere orquestación")
            return "orchestrator", None
        
        # 3. PUNTUACIÓN DE AGENTES BASADA EN TÉRMINOS DETECTADOS
        # =====================================================
        
        # Mejora: Patrones más específicos y prioritarios para cada tipo de agente
        agent_patterns = {
            "code": [
                # Patrones explícitos de programación
                "código", "función", "programa", "script", "clase", "método", 
                "algoritmo", "implementación", "biblioteca", "librería", "api",
                "desarrollo", "programación", "compilador", "intérprete",
                # Lenguajes de programación
                "python", "javascript", "java", "c++", "c#", "typescript",
                "bash", "php", "ruby", "golang", "rust", "swift",
                # Términos de desarrollo
                "bug", "error", "depuración", "debugging", "código fuente", "variable", 
                "constante", "bucle", "loop", "condicional", "if", "else", "for", "while"
            ],
            "system": [
                # Operaciones de sistema
                "ejecuta", "abre", "archivo", "directorio", "sistema operativo", 
                "comando", "lista archivos", "muestra el contenido", "crea carpeta",
                "elimina archivo", "renombra", "copia", "mueve", "ruta",
                "permisos", "terminal", "proceso", "ram", "cpu", "disco", "espacio",
                "windows", "linux", "mac", "macos", "ubuntu", "debian", "fedora"
            ],
            "memory": [
                # Términos de conocimiento/información
                "información", "conocimiento", "dato", "recuerda", "olvida", 
                "aprende", "memoriza", "búsqueda", "busca", "encuentra",
                "qué es", "que es", "explica", "definición", "significado",
                "háblame", "cuéntame", "dime", "sabes", "conoces",
                # Áreas de conocimiento
                "historia", "ciencia", "matemáticas", "geografía", "literatura",
                "filosofía", "medicina", "biología", "química", "física",
                "economía", "política", "sociedad", "tecnología", "arte"
            ]
        }
        
        # Verificar coincidencias para cada agente, con ponderaciones mejoradas
        match_scores = {"code": 0, "system": 0, "memory": 0}
        
        # Registro de coincidencias para debugging
        matches_log = {"code": [], "system": [], "memory": []}
        
        # Analizar cada palabra de la consulta
        query_words = query_normalized.split()
        
        for agent_type, patterns in agent_patterns.items():
            for pattern in patterns:
                # Buscar coincidencias exactas de términos completos
                if f" {pattern} " in f" {query_normalized} " or query_normalized.startswith(f"{pattern} ") or query_normalized.endswith(f" {pattern}"):
                    match_scores[agent_type] += 2
                    matches_log[agent_type].append(f"{pattern}(+2)")
                # Coincidencia parcial
                elif pattern in query_normalized:
                    match_scores[agent_type] += 1
                    matches_log[agent_type].append(f"{pattern}(+1)")
        
        # Verificar términos específicos que podrían causar confusión
        if "memoria" in query_normalized and not any(h_term in query_normalized for h_term in hardware_terms):
            if any(term in query_normalized for term in ["guardar", "recordar", "olvidar", "información"]):
                # Probablemente se refiere a la funcionalidad de memoria de la IA
                match_scores["memory"] += 3
                matches_log["memory"].append("memoria_semántica(+3)")
            else:
                # Podría referirse a RAM, verificar contexto
                context_terms = ["sistema", "computadora", "ordenador", "pc", "libre", "disponible"]
                if any(term in query_normalized for term in context_terms):
                    match_scores["system"] += 3
                    match_scores["memory"] -= 1  # Penalizar memory
                    matches_log["system"].append("memoria_hardware(+3)")
                    matches_log["memory"].append("penalización(-1)")
        
        # Log detallado para debugging
        for agent_type, matches in matches_log.items():
            if matches:
                self.logger.info(f"Coincidencias para {agent_type}: {', '.join(matches)}")
        
        self.logger.info(f"Puntuaciones finales: code={match_scores['code']}, system={match_scores['system']}, memory={match_scores['memory']}")
        
        # Determinar el agente ganador
        max_score = max(match_scores.values())
        if max_score > 0:
            # Encontrar todos los agentes con la puntuación máxima
            best_agents = [agent for agent, score in match_scores.items() if score == max_score]
            
            if len(best_agents) == 1:
                # Claro ganador
                winner = best_agents[0]
                self.logger.info(f"Claro ganador: {winner} con puntuación {max_score}")
            else:
                # Empate - aplicar reglas de desempate
                # Prioridad: code > system > memory
                priority_order = ["code", "system", "memory"]
                for agent_type in priority_order:
                    if agent_type in best_agents:
                        winner = agent_type
                        self.logger.info(f"Empate resuelto. Ganador por prioridad: {winner}")
                        break
                else:
                    # Si por alguna razón no se encuentra, usar el primero
                    winner = best_agents[0]
            
            # Verificaciones adicionales para casos especiales
            if winner == "memory" and "crear" in query_normalized and any(obj in query_normalized for obj in code_objects):
                self.logger.info("Reclasificando de memory a code debido a contexto de creación")
                return "code", None
            
            return winner, None
        
        # Default a manejo directo
        self.logger.info("Sin coincidencias claras, usando manejo directo")
        return "direct", None
    
    def setup_memory(self, config: Dict):
        """
        Set up memory system for the agent.
        
        Args:
            config: Memory configuration
        """
        try:
            from memory.core import MemoryManager
            
            # Ensure we have a valid directory for memory storage
            data_dir = config.get("data_dir")
            if not data_dir:
                # Use a default directory if none specified
                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/memory")
                self.logger.warning(f"No memory data_dir specified, using default: {data_dir}")
            
            # Ensure directory exists
            os.makedirs(data_dir, exist_ok=True)
            self.logger.info(f"Using memory data directory: {data_dir}")
                
            # Crear la configuración correcta para el MemoryManager
            memory_config = {
                "short_term_memory": {
                    "retention_minutes": config.get("retention_minutes", 60),
                    "capacity": config.get("capacity", 100)
                },
                "long_term_memory": {
                    "min_importance": config.get("importance_threshold", 0.3)
                },
                "semantic_memory": {
                    "min_confidence": config.get("min_confidence", 0.0)
                },
                "use_long_term_memory": config.get("use_long_term_memory", True),
                "use_semantic_memory": config.get("use_semantic_memory", True),
                "use_episodic_memory": config.get("use_episodic_memory", False)
            }
            
            # Create MemoryManager with correct parameters
            self.memory_manager = MemoryManager(
                config=memory_config,
                data_dir=data_dir
            )
            
            # Configure memory options
            memory_threshold = config.get("threshold", 0.75)
            relevance_threshold = config.get("relevance_threshold", 0.65)
            importance_threshold = config.get("importance_threshold", 0.3)
            
            self.memory_options = {
                "threshold": memory_threshold,
                "relevance_threshold": relevance_threshold,
                "importance_threshold": importance_threshold
            }
            
            self.logger.info(f"Memory system initialized successfully with threshold={memory_threshold}")
            
        except Exception as e:
            self.logger.error(f"Error setting up memory manager: {str(e)}")
            self.logger.exception("Detailed memory initialization error:")
            self.memory_manager = None

    def _normalize_query(self, query: str) -> str:
        """
        Normaliza la consulta para hacer la detección de patrones más robusta.
        Corrige errores comunes de espacio y tipográficos.
        
        Args:
            query: Consulta original
            
        Returns:
            Consulta normalizada
        """
        # Convertir a minúsculas y eliminar espacios en blanco adicionales
        normalized = query.lower().strip()
        
        # Guardar números y operaciones matemáticas antes de normalizar
        # Crear un mapa de dígitos y operaciones matemáticas para preservarlos
        numeric_expressions = re.findall(r'\d+[\+\-\*\/\d\s]*\d*', normalized)
        numeric_map = {}
        for i, expr in enumerate(numeric_expressions):
            placeholder = f"__NUM_{i}__"
            numeric_map[placeholder] = expr
            normalized = normalized.replace(expr, placeholder)
            
        # Reemplazar caracteres especiales y acentos pero preservar signos matemáticos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ü': 'u', 'ñ': 'n', '?': ' ', '¿': ' ', '!': ' ', 
            '¡': ' ', '.': ' ', ',': ' ', ';': ' ', ':': ' '
        }
        
        for char, replacement in replacements.items():
            normalized = normalized.replace(char, replacement)
        
        # Detectar y separar palabras pegadas comunes
        common_compounds = {
            'comote': 'como te',
            'quienes': 'quien es',
            'quiénes': 'quién es',
            'quees': 'que es',
            'erestu': 'eres tu',
            'comofunciona': 'como funciona',
            'comose': 'como se',
            'comoestas': 'como estas',
            'quehaces': 'que haces',
            'cuentahasta': 'cuenta hasta'
        }
        
        for compound, separated in common_compounds.items():
            normalized = normalized.replace(compound, separated)
        
        # Preservar frases comunes que deben mantenerse juntas
        phrases_to_preserve = [
            'cuenta hasta', 'escribe un', 'genera un', 'crea un',
            'dime como', 'explica como', 'cuéntame sobre', 'dime sobre',
            'te quiero', 'cuenta un chiste', 'cuentame un'
        ]
        
        # Reemplazar espacios en frases a preservar con guiones bajos
        for phrase in phrases_to_preserve:
            if phrase in normalized:
                normalized = normalized.replace(phrase, phrase.replace(' ', '_'))
        
        # Eliminar duplicación de espacios
        normalized = ' '.join(normalized.split())
        
        # Restaurar números y operaciones matemáticas
        for placeholder, expr in numeric_map.items():
            normalized = normalized.replace(placeholder, expr)
            
        # Restaurar frases preservadas
        for phrase in phrases_to_preserve:
            phrase_with_underscores = phrase.replace(' ', '_')
            normalized = normalized.replace(phrase_with_underscores, phrase)
        
        return normalized

    async def _handle_direct_query(self, query: str, context: Dict) -> AgentResponse:
        """
        Handle a query directly without using specialized agents.
        
        Args:
            query: User's query
            context: Request context
            
        Returns:
            AgentResponse with the result
        """
        # Obtener versiones normalizadas y originales para mayor robustez
        query_lower = query.lower().strip()
        query_normalized = self._normalize_query(query)
        
        # MEJORA: Verificar si tenemos información de memoria disponible
        if context.get("memory_used") and context.get("relevant_content"):
            # Intentar usar la memoria directamente para responder consultas de conocimiento
            # Esto solo aplica si la consulta parece ser una solicitud de información
            knowledge_patterns = ["que es", "como funciona", "explica", "dime sobre", "sabes sobre"]
            if any(pattern in query_normalized for pattern in knowledge_patterns):
                memory_content = context.get("memory_summary", "")
                # Si tenemos memorias relevantes, usarlas para responder
                if memory_content and len(memory_content) > 50:
                    return AgentResponse(
                        content=memory_content,
                        status="success",
                        metadata={
                            "memory_used": True,
                            "direct_memory_response": True,
                            "memories_found": context.get("memories_found", 0)
                        }
                    )
        
        # 1. PATRONES DE CONVERSACIÓN BÁSICA
        # ==================================
        
        # Patrones de saludo mejorados
        greetings = ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "saludos", 
                    "que tal", "como estas", "como vas", "que hay"]
        
        # Verificar si es un saludo simple - usando consulta normalizada
        is_greeting = False
        for greeting in greetings:
            if greeting in query_normalized or query_normalized.startswith(greeting):
                is_greeting = True
                break
        
        if is_greeting and len(query_normalized.split()) <= 5:
            # Respuestas de saludo variadas
            greeting_responses = [
                "Hola, ¿en qué puedo ayudarte hoy?",
                "Hola. Dime, ¿en qué te puedo ayudar?",
                "Hola, estoy listo para asistirte. ¿Qué necesitas?",
                "Saludos. ¿En qué puedo serte útil?",
                "Hola. ¿Qué tienes en mente hoy?"
            ]
            import random
            response_text = random.choice(greeting_responses)
            return AgentResponse(content=response_text)
        
        # 1.0 DETECTAR EXPRESIONES DE AFECTO O PERSONALES
        personal_patterns = {
            "te quiero": [
                "Me alegra escuchar eso. Estoy aquí para asistirte lo mejor posible.",
                "Gracias, es agradable escucharlo. ¿En qué puedo ayudarte hoy?",
                "Aprecio tus palabras. Estoy para lo que necesites."
            ],
            "te amo": [
                "Gracias por expresar eso. Estoy aquí para brindarte la mejor asistencia posible.",
                "Agradezco tu entusiasmo. Mi objetivo es darte la mejor experiencia posible.",
                "Me alegra que estés a gusto con mi asistencia. ¿En qué puedo ayudarte ahora?"
            ],
            "eres genial": [
                "¡Gracias! Trato de hacer mi mejor esfuerzo. ¿En qué puedo ayudarte hoy?",
                "Me alegra que te resulte útil. ¿Qué necesitas ahora?",
                "Aprecio el cumplido. Estoy aquí para lo que necesites."
            ]
        }
        
        for pattern, responses in personal_patterns.items():
            if pattern in query_normalized:
                import random
                return AgentResponse(content=random.choice(responses))
        
        # 1.1 RESPUESTAS A CONSULTAS DE DISCULPA Y CONFUSIÓN
        # ==================================================
        
        # Patrones de disculpa, confusión y no saber qué hacer
        confusion_patterns = [
            "lo siento", "perdon", "disculpa", "no se", "no sé", "no entiendo", 
            "estoy confundido", "estoy confundida", "no se que pensar", "no se que hacer",
            "no hay", "no ahy", "no existe", "que opciones hay", "opciones", "alternativas",
            "que otra cosa", "otra opcion", "otra alternativa", "algo mas", "algo mejor"
        ]
        
        is_confusion = False
        for pattern in confusion_patterns:
            if pattern in query_normalized:
                is_confusion = True
                break
        
        if is_confusion:
            # Presentar opciones claras y significativas
            clear_options = """
📋 OPCIONES DISPONIBLES:

1️⃣ AYUDA CON CÓDIGOS - Puedo generar, explicar o corregir código en varios lenguajes
   Ejemplo: "Crea una función en Python que ordene una lista"

2️⃣ INFORMACIÓN DEL SISTEMA - Puedo consultar datos de tu equipo
   Ejemplo: "Cuánta memoria RAM tengo disponible"

3️⃣ BÚSQUEDA DE CONOCIMIENTO - Puedo buscar información en mi memoria
   Ejemplo: "Explícame qué es la inteligencia artificial"

4️⃣ TAREAS COMPLEJAS - Puedo coordinar múltiples agentes para tareas elaboradas
   Ejemplo: "Crea un programa que analice archivos y muestre estadísticas"

5️⃣ CONVERSACIÓN GENERAL - Puedo charlar contigo sobre diversos temas
   Ejemplo: "Hablemos sobre tecnología"

Por favor, selecciona una opción escribiendo tu consulta específica.
"""
            return AgentResponse(
                content=clear_options.strip(),
                metadata={"response_type": "options_menu", "user_confused": True}
            )
        
        # 1.2 MANEJO DE CONTEO Y MATEMÁTICAS SIMPLES
        # ==========================================
        
        # Patrón "cuenta hasta X"
        import re
        count_match = re.search(r'cuenta hasta (\d+)', query_normalized)
        if count_match:
            try:
                count_to = int(count_match.group(1))
                if 1 <= count_to <= 100:  # Límite razonable
                    numbers = list(range(1, count_to + 1))
                    count_text = ", ".join(str(n) for n in numbers)
                    return AgentResponse(content=count_text)
                else:
                    return AgentResponse(content=f"El número {count_to} está fuera de rango. Por favor, usa un número entre 1 y 100.")
            except ValueError:
                pass
        
        # Operaciones matemáticas simples
        math_pattern = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', query_normalized)
        if math_pattern:
            try:
                num1 = int(math_pattern.group(1))
                operator = math_pattern.group(2)
                num2 = int(math_pattern.group(3))
                
                result = None
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/' and num2 != 0:
                    result = num1 / num2
                
                if result is not None:
                    return AgentResponse(content=f"El resultado de {num1} {operator} {num2} es {result}")
                else:
                    return AgentResponse(content="No puedo realizar esa operación matemática. Asegúrate de que sea válida.")
            except (ValueError, ZeroDivisionError):
                pass
        
        # 1.3 CHISTES Y ENTRETENIMIENTO
        # ============================
        
        joke_patterns = ["cuenta un chiste", "dime un chiste", "cuéntame algo gracioso", "hazme reír"]
        
        if any(pattern in query_normalized for pattern in joke_patterns):
            jokes = [
                "¿Por qué los programadores prefieren el frío? Porque odian los bugs.",
                "¿Qué le dice un bit al otro? Nos vemos en el bus.",
                "¿Cuántos programadores hacen falta para cambiar una bombilla? Ninguno, es un problema de hardware.",
                "Un programador va al supermercado. Su esposa le dice: 'Compra una barra de pan y si hay huevos, trae 6'. Volvió con 6 barras de pan: 'Había huevos'.",
                "¿Cómo se llama un programador zombi? Un dead-veloper.",
                "No es magia, es inteligencia artificial... bueno, en realidad es solo un montón de if/else statements."
            ]
            import random
            return AgentResponse(content=random.choice(jokes))
        
        # Patrones de despedida
        farewells = ["adios", "hasta luego", "nos vemos", "chao", "bye", "hasta pronto"]
        
        is_farewell = False
        for farewell in farewells:
            if farewell in query_normalized or query_normalized.startswith(farewell):
                is_farewell = True
                break
        
        if is_farewell:
            # Respuestas de despedida variadas
            farewell_responses = [
                "¡Hasta pronto! Estoy aquí cuando me necesites.",
                "Adiós. Regresa cuando necesites mi ayuda.",
                "Nos vemos. Estaré aquí para la próxima consulta.",
                "Hasta luego. Ha sido un placer asistirte."
            ]
            import random
            return AgentResponse(content=random.choice(farewell_responses))
        
        # 1.4 RESPUESTAS A CONSULTAS EMOCIONALES Y EXPERIENCIA DE USUARIO
        # ===============================================================
        
        # Patrones de experiencia negativa o dificultad
        frustration_patterns = [
            "no funciona", "no sirve", "no entiendo", "no se que hacer",
            "es frustrante", "frustracion", "estoy frustrado", "siento frustracion",
            "se siente mal", "experiencia", "decepcionado", "decepcion", 
            "mal servicio", "mala respuesta", "no me gusta", "no me sirve"
        ]
        
        is_frustration = False
        for pattern in frustration_patterns:
            if pattern in query_normalized:
                is_frustration = True
                break
        
        if is_frustration:
            empathetic_responses = [
                "Entiendo tu frustración. Estoy trabajando para mejorar. ¿Podrías decirme específicamente qué esperabas que hiciera diferente?",
                "Lamento que la experiencia no esté siendo satisfactoria. Permíteme intentar ayudarte de otra manera. ¿Qué estás intentando lograr exactamente?",
                "Comprendo tu frustración. Todavía estoy aprendiendo. ¿Podríamos intentar un enfoque diferente para resolver tu problema?",
                "Siento que esto no esté funcionando como esperabas. Intentemos otra aproximación. ¿Puedes describir nuevamente lo que necesitas, quizás con otras palabras?"
            ]
            import random
            return AgentResponse(
                content=random.choice(empathetic_responses),
                metadata={"response_type": "empathetic", "frustration_detected": True}
            )
        
        # Patrones de consulta emocional sobre el sistema
        emotion_query_patterns = [
            "como te sientes", "que sientes", "estas sintiendo", "tienes emociones",
            "tienes sentimientos", "te gusta", "te emociona", "te entristece",
            "eres feliz", "eres triste", "te preocupa", "te molesta"
        ]
        
        is_emotion_query = False
        for pattern in emotion_query_patterns:
            if pattern in query_normalized:
                is_emotion_query = True
                break
        
        if is_emotion_query:
            ai_emotion_responses = [
                "Como asistente, no tengo emociones reales, pero estoy programado para entender emociones humanas y responder adecuadamente. Mi enfoque está completamente en ayudarte lo mejor posible.",
                "No experimento emociones como los humanos, pero puedo reconocerlas y responder a ellas. Mi objetivo principal es brindarte la mejor asistencia que pueda.",
                "No siento emociones en el sentido humano, pero sí estoy diseñado para entender contextos emocionales y adaptarme a ellos. Estoy aquí para apoyarte con cualquier tarea que necesites."
            ]
            import random
            return AgentResponse(
                content=random.choice(ai_emotion_responses),
                metadata={"response_type": "emotion_explanation"}
            )
        
        # 2. CONSULTAS SOBRE EL SISTEMA Y CAPACIDADES
        # =========================================== 
        
        # Patrones de consulta sobre capacidades - Significativamente ampliados
        capability_patterns = [
            "que puedes hacer", "cuales son tus habilidades", "dime que haces", 
            "tus funcionalidades", "como me puedes ayudar", "que sabes hacer",
            "quiero saber que puedes hacer", "explicame que puedes hacer",
            "cuales son tus capacidades", "de que eres capaz", "ayuda",
            "que eres capaz de hacer", "para que sirves", "como funcionas",
            "que funciones tienes", "dime tus capacidades", "cual es tu proposito",
            "para que te usan", "que se puede hacer contigo"
        ]
        
        # Verificar consultas de capacidades
        is_capability_query = False
        for pattern in capability_patterns:
            if pattern in query_normalized:
                is_capability_query = True
                break
        
        if is_capability_query or "que haces" in query_normalized:
            capabilities = self._get_system_capabilities_description()
            capability_responses = [
                f"Puedo ayudarte con varias tareas, incluyendo: {capabilities}. ¿En qué área necesitas asistencia ahora?",
                f"Mis capacidades incluyen: {capabilities}. ¿Con qué te gustaría comenzar?",
                f"Estoy diseñado para asistirte con: {capabilities}. ¿En qué puedo ayudarte específicamente?"
            ]
            import random
            response_text = random.choice(capability_responses)
            return AgentResponse(content=response_text)
        
        # Preguntas de identidad - con mayor tolerancia a variaciones
        identity_patterns = [
            "quien eres", "como te llamas", "cual es tu nombre", "presentate",
            "quien eres tu", "quien es vio", "que es vio", "que significa vio",
            "quien esta ahi", "con quien hablo", "a quien le hablo", "identificate", 
            "tu identidad", "eres un asistente", "eres una ia", "eres un agente"
        ]
        
        is_identity_query = False
        for pattern in identity_patterns:
            if pattern in query_normalized:
                is_identity_query = True
                break
        
        if is_identity_query:
            identity_responses = [
                f"Soy {self.name}, tu asistente virtual. Coordino diferentes agentes especializados para ayudarte con tus tareas y consultas.",
                f"Me llamo {self.name} (Virtual Intelligence Operator). Estoy diseñado para asistirte gestionando un sistema de agentes especializados.",
                f"{self.name} a tu servicio. Mi función es coordinar agentes especializados y mantener memoria persistente para brindarte la mejor asistencia posible."
            ]
            import random
            response_text = random.choice(identity_responses)
            return AgentResponse(content=response_text)
        
        # 3. CONSULTAS DE MEMORIA
        # ======================
        
        # Consultas de memoria básicas
        memory_queries = [
            "recuerdas", "me dijiste", "mencionaste", "dijimos antes",
            "hablamos de", "te conté", "te dije", "ya te había dicho",
            "comentaste", "habíamos hablado", "dije antes"
        ]
        
        if any(term in query_lower for term in memory_queries):
            if self.has_memory():
                memories = self.recall(query=query, limit=3)
                if memories:
                    memory_content = memories[0].content
                    if isinstance(memory_content, dict) and "response" in memory_content:
                        memory_text = memory_content["response"]
                    else:
                        memory_text = str(memory_content)
                    
                    memory_responses = [
                        f"Sí, recuerdo que: {memory_text}",
                        f"Según lo que hablamos antes: {memory_text}",
                        f"Tengo registro de eso: {memory_text}"
                    ]
                    import random
                    return AgentResponse(
                        content=random.choice(memory_responses),
                        metadata={"memory_used": True, "memories_found": len(memories)}
                    )
            
            # Si llegamos aquí, no se encontraron memorias relevantes
            no_memory_responses = [
                "No recuerdo nada específico sobre eso. ¿Podrías darme más detalles?",
                "No tengo registro de esa información en mi memoria. ¿Puedes ser más específico?",
                "No encuentro información relacionada con esa consulta en mi memoria."
            ]
            import random
            return AgentResponse(
                content=random.choice(no_memory_responses),
                metadata={"memory_used": False}
            )
        
        # 4. CONSULTAS SOBRE USUARIO
        # ========================
        
        # Consultas específicas sobre el perfil del usuario
        user_queries = [
            "quién soy", "cómo me llamo", "qué sabes de mí", "mi perfil", "mis intereses",
            "mi información", "qué recuerdas de mí", "mis datos", "información sobre mí"
        ]
        
        if any(term in query_lower for term in user_queries) and self.has_memory():
            # Buscar en memoria con metadatos específicos
            user_memories = self.memory_manager.search_memories(
                query=query,
                memory_type="user_profile",
                limit=2
            )
            
            if user_memories:
                memory = user_memories[0]
                # Extraer un fragmento relevante
                content = str(memory.content)
                if len(content) > 200:
                    content = content[:200] + "..."
                    
                user_responses = [
                    f"Según tu perfil: {content}",
                    f"Tengo esta información sobre ti: {content}",
                    f"En mi memoria sobre ti: {content}"
                ]
                import random
                return AgentResponse(
                    content=random.choice(user_responses),
                    metadata={"memory_used": True, "memory_type": "user_profile"}
                )
        
        # 5. CONSULTAS ESPECÍFICAS SOBRE ESTE SISTEMA
        # =========================================
        
        system_queries = [
            "cómo funciona este sistema", "qué agentes hay", "qué es este sistema",
            "arquitectura del sistema", "componentes del sistema", "explicame este sistema",
            "cómo están organizados los agentes", "quién te desarrolló"
        ]
        
        if any(term in query_lower for term in system_queries):
            system_description = f"""
Este sistema, liderado por V.I.O. (Virtual Intelligence Operator), utiliza una arquitectura multiagente con el Model Context Protocol (MCP).

Los principales componentes incluyen:
- Agente principal (V.I.O.): Coordinador central que delega tareas
- Agentes especializados: Code, System, Memory y otros según la configuración
- Sistema de memoria: Almacena información persistente con búsqueda semántica
- MCP: Protocolo que facilita la comunicación entre componentes

Actualmente hay {len(self.specialized_agents)} agentes especializados disponibles para procesar diferentes tipos de consultas.
"""
            return AgentResponse(content=system_description.strip())
        
        # 6. RESPUESTA GENÉRICA PARA CONSULTAS NO RECONOCIDAS
        # =================================================
        
        # Intentar extraer palabras clave para dar una respuesta más personalizada
        important_terms = []
        for word in query_lower.split():
            if len(word) > 4 and word not in ["como", "cómo", "para", "poder", "puedes", "dónde", "cuándo", "cuáles"]:
                important_terms.append(word)
        
        if important_terms:
            generic_responses = [
                f"Entiendo que preguntas sobre {', '.join(important_terms[:2])}. ¿Podrías reformular tu consulta?",
                f"No estoy seguro de cómo responderte sobre {', '.join(important_terms[:2])}. ¿Puedes ser más específico?",
                f"Para ayudarte mejor con {', '.join(important_terms[:2])}, ¿podrías dar más contexto?"
            ]
        else:
            generic_responses = [
                "No estoy seguro de entender tu consulta. ¿Podrías expresarla de otra forma?",
                "Necesito más detalles para poder ayudarte adecuadamente.",
                "No tengo suficiente contexto para responder. ¿Podrías elaborar más tu pregunta?"
            ]
        
        import random
        return AgentResponse(
            content=random.choice(generic_responses),
            metadata={"action": "suggest_reformulation"}
        )
    
    async def _handle_via_orchestrator(self, query: str, context: Dict) -> AgentResponse:
        """
        Handle a complex query using the orchestrator agent.
        
        Args:
            query: User's query
            context: Request context
            
        Returns:
            Response from the orchestrator
        """
        if not self.orchestrator_id:
            return AgentResponse(
                content="No tengo un orquestador configurado para manejar tareas complejas.",
                status="error",
                metadata={"error": "orchestrator_not_configured"}
            )
            
        self.logger.info(f"Delegando consulta compleja al orquestador: {query[:50]}...")
        
        try:
            from ..agent_communication import communicator
            orchestrator = communicator.get_agent_by_id(self.orchestrator_id)
            
            if not orchestrator:
                return AgentResponse(
                    content="No se puede conectar con el orquestador en este momento.",
                    status="error",
                    metadata={"error": "orchestrator_unavailable"}
                )
                
            # Preparar contexto enriquecido para el orquestador
            orchestrator_context = context.copy() if context else {}
            
            # Incluir información de memoria como contexto adicional si existe
            if context.get("memory_used") and context.get("memories_found", 0) > 0:
                orchestrator_context["has_memory_context"] = True
                
                # Extraer información relevante para el orquestador
                if context.get("relevant_content"):
                    # Formatear memorias como contexto útil para la orquestación
                    orchestrator_context["background_knowledge"] = context.get("relevant_content")
                    
                    # Añadir explicación sobre el contexto proporcionado
                    orchestrator_context["context_message"] = "Las siguientes memorias contienen información relevante para esta tarea:"
            
            # Enviar la consulta al orquestador
            response = await orchestrator.process(query, orchestrator_context)
            
            # Añadir metadatos sobre la orquestación
            if response:
                response.metadata["orchestrated"] = True
                response.metadata["agent_used"] = self.orchestrator_id
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error en orquestación: {str(e)}")
            return AgentResponse(
                content=f"Ocurrió un error al procesar tu solicitud mediante el orquestador: {str(e)}",
                status="error",
                metadata={"error": "orchestration_error"}
            )
    
    async def _handle_via_specialized_agent(self, agent_id: str, query: str, context: Dict) -> AgentResponse:
        """
        Handle a query via a specialized agent.
        
        Args:
            agent_id: ID of the agent to use
            query: User's query
            context: Request context
            
        Returns:
            AgentResponse with the result
        """
        self.logger.info(f"Delegando consulta a agente especializado: {agent_id}")
        
        try:
            # CORRECCIÓN: Obtener el agente desde el comunicador usando la importación apropiada
            from ..agent_communication import communicator
            agent = communicator.get_agent_by_id(agent_id)
            
            if not agent:
                return AgentResponse(
                    content=f"Lo siento, no puedo encontrar el agente '{agent_id}' en este momento.",
                    status="error",
                    metadata={"error": "agent_not_found"}
                )
                
            # Preparar contexto enriquecido para el agente especializado
            specialized_context = context.copy() if context else {}
            
            # Incluir información de memoria si existe y es relevante
            if context and context.get("memory_used") and context.get("memories_found", 0) > 0:
                specialized_context["has_memory_context"] = True
                
                # Añadir contenido relevante si existe
                if context.get("relevant_content"):
                    specialized_context["background_knowledge"] = context.get("relevant_content")
                    specialized_context["relevant_memory_fragments"] = context.get("relevant_memory_fragments", [])
                    
                    # Añadir mensaje de contexto
                    specialized_context["context_message"] = "La siguiente información de memoria puede ser relevante:"
            
            # Enviar consulta al agente especializado
            response = await agent.process(query, specialized_context)
            
            # Añadir metadatos sobre la delegación
            if response:
                response.metadata["delegated"] = True
                response.metadata["agent_used"] = agent_id
                
            return response
            
        except Exception as e:
            self.logger.error(f"Error al procesar consulta con agente {agent_id}: {str(e)}")
            return AgentResponse(
                content=f"Error al procesar tu solicitud con el agente especializado: {str(e)}",
                status="error",
                metadata={"error": "specialized_agent_error", "agent_id": agent_id}
            )
    
    def _find_agent_id_by_type(self, agent_type: str) -> Optional[str]:
        """
        Find a suitable agent ID based on the agent type.
        
        Args:
            agent_type: Type of agent to find
            
        Returns:
            Agent ID if found, None otherwise
        """
        # Mapeo directo mejorado para tipos de agentes comunes
        type_to_id_map = {
            "code": "code",
            "system": "system",
            "echo": "echo",
            "memory": "memory",
            "orchestrator": "orchestrator"
        }
        
        # Mapeo de tipos alternativos a los tipos estándar
        alternative_types = {
            # Programación
            "programming": "code",
            "development": "code",
            "coding": "code",
            "developer": "code",
            "script": "code",
            "python": "code",
            "javascript": "code",
            # Sistema
            "os": "system",
            "filesystem": "system",
            "file": "system",
            "directory": "system",
            "command": "system",
            "hardware": "system",
            # Memoria
            "semantic": "memory",
            "knowledge": "memory",
            "recall": "memory",
            "information": "memory",
            "query": "memory"
        }
        
        # Normalizar el tipo de agente
        normalized_type = alternative_types.get(agent_type, agent_type)
        
        # Primero intentar mapeo directo con el tipo normalizado
        if normalized_type in type_to_id_map:
            agent_id = type_to_id_map[normalized_type]
            # Verificar si este agente está registrado
            if agent_id in self.specialized_agents:
                self.logger.info(f"Usando mapeo directo: {agent_type} -> {normalized_type} -> {agent_id}")
                return agent_id
            else:
                self.logger.warning(f"Agente mapeado {agent_id} no está registrado. Buscando alternativas.")
        
        # Capacidades específicas que deben coincidir con tipos de agentes    
        capability_to_type = {
            "code": ["code", "programming", "development", "python", "javascript"],
            "system": ["system", "filesystem", "command", "file_operations", "system_operations"],
            "memory": ["memory", "remember", "recall", "vector_search", "semantic_search"]
        }
        
        # Buscar agentes que tengan capacidades relacionadas con el tipo
        candidates = {}
        for agent_id, info in self.specialized_agents.items():
            capabilities = info["capabilities"]
            score = 0
            
            # Verificar coincidencia directa
            if normalized_type in capabilities:
                score += 5
                
            # Verificar coincidencias en capacidades según el tipo normalizado
            if normalized_type in capability_to_type:
                relevant_capabilities = capability_to_type[normalized_type]
                for capability in capabilities:
                    if capability in relevant_capabilities:
                        score += 3
                    elif any(rel_cap in capability for rel_cap in relevant_capabilities):
                        score += 1
            
            if score > 0:
                candidates[agent_id] = score
        
        # Elegir el agente con la puntuación más alta
        if candidates:
            best_agent = max(candidates, key=candidates.get)
            self.logger.info(f"Mejor agente para {agent_type}: {best_agent} con puntuación {candidates[best_agent]}")
            return best_agent
                
        # Si no se encuentra mapeo, buscar cualquier agente disponible que pueda servir
        self.logger.warning(f"No se encontró agente específico para tipo {agent_type}, buscando agente genérico")
        
        # Si necesitamos un agente de memoria y no lo encontramos, intentar usar cualquier agente disponible
        if agent_type == "memory" and self.specialized_agents:
            fallback_id = next(iter(self.specialized_agents.keys()))
            self.logger.warning(f"Usando agente genérico {fallback_id} como último recurso para consulta de memoria")
            return fallback_id
            
        self.logger.warning(f"No se encontró ningún agente para el tipo {agent_type}")
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