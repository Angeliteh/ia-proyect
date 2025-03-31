"""
Memory Agent module.

Este agente especializado gestiona la memoria semántica del sistema, permitiendo:
- Almacenar recuerdos con embeddings vectoriales
- Consultar información mediante búsqueda semántica
- Proporcionar respuestas basadas en contexto histórico
- Acceder a conocimiento persistente
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import os

from ..base import BaseAgent, AgentResponse
from models.core.model_manager import ModelManager

class MemoryAgent(BaseAgent):
    """
    Agente especializado en gestión de memoria y búsqueda semántica.
    
    Este agente aprovecha las capacidades semánticas de vectores para
    proporcionar memoria a largo plazo al sistema.
    
    Attributes:
        model_manager: Gestor de modelos para procesamiento semántico
    """
    
    def __init__(
        self,
        agent_id: str = "memory_agent",
        config: Dict = None
    ):
        """
        Inicializa el MemoryAgent con configuración de memoria y capacidades semánticas.
        
        Args:
            agent_id: Identificador único del agente
            config: Configuración del agente incluyendo:
                - memory_config: Configuración del sistema de memoria
                - model_config: Configuración del modelo
                - semantic_threshold: Umbral de similitud para búsquedas semánticas (default: 0.25)
                - keyword_fallback_threshold: Umbral para búsqueda por palabras clave (default: 0.2)
        """
        config = config or {}
        
        # Parámetros y valores por defecto
        self.semantic_threshold = config.get("semantic_threshold", 0.25)
        self.keyword_fallback_threshold = config.get("keyword_fallback_threshold", 0.2)
        
        # Inicializar agente base
        super().__init__(agent_id, config)
        
        # Configurar el modelo
        model_config = config.get("model_config", {})
        self.model_manager = model_config.get("model_manager")
        if not self.model_manager:
            self.model_manager = ModelManager()
            
        # El modelo por defecto para procesamiento
        self.model_name = model_config.get("model", "gemini-pro")
        
        # Configuración de memoria - necesaria para este agente
        memory_config = config.get("memory_config")
        if not memory_config:
            self.logger.error("MemoryAgent requiere configuración de memoria")
            raise ValueError("MemoryAgent requiere memory_config")
            
        # Configurar sistema de memoria
        if not self.setup_memory(memory_config):
            self.logger.error("No se pudo configurar el sistema de memoria")
            raise ValueError("Error al configurar memoria para MemoryAgent")
            
        self.logger.info(f"MemoryAgent inicializado con umbral semántico: {self.semantic_threshold}")
        self._setup_actions()
        
    def has_memory(self):
        """Verificar si la memoria está correctamente configurada.
        
        Returns:
            bool: True si la memoria está configurada, False en caso contrario.
        """
        if not hasattr(self, 'memory_system') or self.memory_system is None:
            return False
            
        if not hasattr(self, 'memory_manager') or self.memory_manager is None:
            return False
            
        # Verificar que tenemos acceso al cliente MCP
        if self.config.get('memory_config', {}).get('mcp_client') is None:
            return False
            
        return True
        
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Procesa una consulta relacionada con la memoria.
        
        Args:
            query: Consulta del usuario
            context: Contexto adicional que indica la acción a realizar
            
        Returns:
            Respuesta del agente
        """
        self.set_state("processing")
        context = context or {}
        action = context.get("action", "recall")
        
        try:
            # Determinar qué operación de memoria realizar
            if action == "remember":
                # Almacenar nueva memoria
                content = context.get("content", query)
                memory_type = context.get("memory_type", "general")
                importance = float(context.get("importance", 0.7))
                metadata = context.get("metadata", {})
                
                # Usar MCP directamente para almacenar con embeddings
                if self.memory_system and hasattr(self.memory_system, 'mcp_client'):
                    from mcp.core import MCPMessage, MCPAction, MCPResource
                    
                    # Crear mensaje MCP para almacenar memoria con embedding
                    create_msg = MCPMessage(
                        action=MCPAction.CREATE,
                        resource_type=MCPResource.MEMORY,
                        resource_path="/",
                        data={
                            "content": content,
                            "memory_type": memory_type,
                            "importance": importance,
                            "metadata": metadata,
                            "generate_embedding": True
                        }
                    )
                    
                    # Enviar mensaje de forma asíncrona
                    try:
                        response = await self.memory_system.mcp_client.send_message_async(create_msg)
                        if response and response.success:
                            memory_id = response.data.get('id')
                            self.set_state("idle")
                            return AgentResponse(
                                content=f"He recordado eso como memoria #{memory_id}.",
                                status="success",
                                metadata={"memory_id": memory_id}
                            )
                        else:
                            error_msg = response.error if response else "Error desconocido"
                            raise ValueError(f"Error al guardar la memoria: {error_msg}")
                    except Exception as e:
                        self.logger.error(f"Error en crear memoria con MCP: {str(e)}")
                        raise ValueError("No se pudo guardar en memoria")
                else:
                    # Fallback al método estándar
                    memory_id = self.remember(
                        content=content,
                        memory_type=memory_type,
                        importance=importance,
                        metadata=metadata
                    )
                    
                    if not memory_id:
                        raise ValueError("No se pudo guardar en memoria")
                    
                    self.set_state("idle")
                    return AgentResponse(
                        content=f"He recordado eso como memoria #{memory_id}.",
                        status="success",
                        metadata={"memory_id": memory_id}
                    )
                
            elif action == "recall":
                # Recuperar memorias existentes
                semantic = context.get("semantic", True)
                limit = int(context.get("limit", 5))
                memory_type = context.get("memory_type")
                threshold = float(context.get("threshold", self.semantic_threshold))
                
                # Usar búsqueda semántica o por palabras clave según se indique
                if semantic:
                    # Búsqueda vectorial
                    if self.memory_system and hasattr(self.memory_system, 'mcp_client'):
                        from mcp.core import MCPMessage, MCPAction
                        
                        # Crear mensaje MCP para búsqueda vectorial
                        search_msg = MCPMessage(
                            action=MCPAction.SEARCH,
                            resource_type="vector",
                            resource_path="/",
                            data={
                                "query": query,
                                "limit": limit,
                                "threshold": threshold,
                                "memory_type": memory_type
                            }
                        )
                        
                        try:
                            # Enviar mensaje asíncronamente
                            response = await self.memory_system.mcp_client.send_message_async(search_msg)
                            if response and response.success:
                                results = response.data.get('results', [])
                                
                                # Formatear resultados
                                if results:
                                    formatted_results = self._format_memory_results(results, include_similarity=True)
                                    self.set_state("idle")
                                    return AgentResponse(
                                        content=formatted_results,
                                        status="success",
                                        metadata={"count": len(results), "query": query}
                                    )
                                else:
                                    self.set_state("idle")
                                    return AgentResponse(
                                        content=f"No encontré recuerdos que coincidan con '{query}'",
                                        status="success",
                                        metadata={"count": 0, "query": query}
                                    )
                            else:
                                error_msg = response.error if response else "Error desconocido"
                                raise ValueError(f"Error en búsqueda vectorial: {error_msg}")
                        except Exception as e:
                            self.logger.error(f"Error en búsqueda vectorial MCP: {str(e)}")
                            # Intentar método alternativo
                
                # Búsqueda por palabras clave (o fallback si falló la búsqueda semántica)
                memories = self.recall(
                    query=query,
                    memory_type=memory_type,
                    limit=limit
                )
                
                if memories:
                    formatted_results = self._format_memory_results(memories)
                    self.set_state("idle")
                    return AgentResponse(
                        content=formatted_results,
                        status="success",
                        metadata={"count": len(memories), "query": query}
                    )
                else:
                    self.set_state("idle")
                    return AgentResponse(
                        content=f"No encontré recuerdos que coincidan con '{query}'",
                        status="success",
                        metadata={"count": 0, "query": query}
                    )
                
            elif action == "answer":
                # Responder a una pregunta basada en memoria
                
                # Primero intentar búsqueda semántica
                memories = []
                
                if self.memory_system and hasattr(self.memory_system, 'mcp_client'):
                    from mcp.core import MCPMessage, MCPAction
                    
                    # Crear mensaje MCP para búsqueda vectorial
                    search_msg = MCPMessage(
                        action=MCPAction.SEARCH,
                        resource_type="vector",
                        resource_path="/",
                        data={
                            "query": query,
                            "limit": 5,
                            "threshold": self.semantic_threshold
                        }
                    )
                    
                    try:
                        # Enviar mensaje asíncronamente
                        response = await self.memory_system.mcp_client.send_message_async(search_msg)
                        if response and response.success:
                            memories = response.data.get('results', [])
                    except Exception as e:
                        self.logger.error(f"Error en búsqueda vectorial para respuesta: {str(e)}")
                
                # Si no hay resultados semánticos, usar búsqueda por palabras clave
                if not memories:
                    try:
                        memories = self.recall(query=query, limit=5)
                    except Exception as e:
                        self.logger.error(f"Error en búsqueda por palabras clave: {str(e)}")
                
                # Si no hay memorias, indicar que no tenemos información
                if not memories:
                    self.set_state("idle")
                    return AgentResponse(
                        content="No tengo información para responder a esa pregunta.",
                        status="success",
                        metadata={"query": query}
                    )
                
                # Generar una respuesta basada en las memorias recuperadas
                response_content = self._generate_answer_from_memories(query, memories)
                
                self.set_state("idle")
                return AgentResponse(
                    content=response_content,
                    status="success", 
                    metadata={"query": query, "memory_count": len(memories)}
                )
                
            # Acción no reconocida
            else:
                self.set_state("idle")
                return AgentResponse(
                    content=f"No entiendo la acción solicitada: {action}",
                    status="error",
                    metadata={"query": query, "action": action}
                )
                
        except Exception as e:
            self.logger.error(f"Error procesando consulta de memoria: {str(e)}")
            self.set_state("error")
            return AgentResponse(
                content=f"Error procesando su consulta de memoria: {str(e)}",
                status="error",
                metadata={"error": str(e)}
            )
    
    def get_capabilities(self) -> List[str]:
        """Obtener las capacidades de este agente."""
        return [
            "memory_management",
            "semantic_search",
            "fact_storage",
            "knowledge_retrieval",
            "question_answering"
        ]
    
    def _detect_action(self, query: str) -> str:
        """
        Detectar la acción apropiada basada en la consulta.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Tipo de acción detectada
        """
        query_lower = query.lower()
        
        # Detectar acción basada en palabras clave
        if any(word in query_lower for word in ["recuerda", "guarda", "anota", "aprende", "almacena"]):
            return "remember"
            
        if any(word in query_lower for word in ["busca", "encuentra", "recuerda", "cuál", "qué"]):
            if "olvida" in query_lower or "elimina" in query_lower:
                return "forget"
            return "recall"
            
        if any(word in query_lower for word in ["organiza", "agrupa", "clasifica"]):
            return "organize"
            
        if any(word in query_lower for word in ["cuántas", "estadísticas", "estado"]):
            return "status"
            
        # Por defecto, tratarlo como una pregunta para responder
        return "answer"
    
    async def _remember(self, content: str, memory_type: str, importance: float, metadata: Dict) -> str:
        """
        Almacenar información en la memoria.
        
        Args:
            content: Contenido a recordar
            memory_type: Tipo de memoria
            importance: Importancia (0.0 a 1.0)
            metadata: Metadatos adicionales
            
        Returns:
            Mensaje de confirmación
        """
        # Añadir timestamp a los metadatos
        meta = metadata.copy()
        timestamp = datetime.now().isoformat()
        meta["timestamp"] = timestamp
        
        # Usar el método remember mejorado con embeddings
        memory_id = self.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=meta,
            generate_embedding=True  # Generar embedding para búsqueda semántica
        )
        
        if memory_id:
            return f"He guardado esa información en mi memoria (ID: {memory_id})"
        else:
            raise ValueError("No se pudo guardar en memoria")
    
    async def _recall(self, query: str, memory_type: Optional[str], use_semantic: bool, limit: int) -> str:
        """
        Recuperar información de la memoria.
        
        Args:
            query: Consulta para buscar
            memory_type: Tipo de memoria (opcional)
            use_semantic: Si usar búsqueda semántica
            limit: Número máximo de resultados
            
        Returns:
            Resultados formateados
        """
        if use_semantic:
            # Usar búsqueda semántica directa
            memories = self.recall_semantic(
                query=query,
                memory_type=memory_type,
                limit=limit,
                threshold=self.semantic_threshold
            )
            search_type = "semántica"
        else:
            # Usar búsqueda estándar
            memories = self.recall(
                query=query,
                memory_type=memory_type,
                limit=limit
            )
            search_type = "por palabras clave"
            
        # Formatear resultados
        if not memories:
            return f"No encontré recuerdos que coincidan con '{query}'"
            
        result = f"Encontré {len(memories)} resultados mediante búsqueda {search_type}:\n\n"
        
        for i, memory in enumerate(memories):
            # Obtener datos del recuerdo
            content = memory.content if hasattr(memory, 'content') else memory.get('content', 'Contenido desconocido')
            memory_id = memory.id if hasattr(memory, 'id') else memory.get('id', 'ID desconocido')
            memory_type = memory.memory_type if hasattr(memory, 'memory_type') else memory.get('memory_type', 'general')
            
            # Obtener puntuación de relevancia si está disponible
            relevance = ""
            if hasattr(memory, 'relevance'):
                relevance = f" (relevancia: {memory.relevance:.2f})"
            elif 'relevance' in memory:
                relevance = f" (relevancia: {memory['relevance']:.2f})"
            elif hasattr(memory, 'similarity'):
                relevance = f" (similitud: {memory.similarity:.2f})"
            elif 'similarity' in memory:
                relevance = f" (similitud: {memory['similarity']:.2f})"
                
            # Formatear recuerdo
            result += f"{i+1}. [{memory_type}]{relevance}\n"
            result += f"   {content}\n"
            result += f"   ID: {memory_id}\n\n"
            
        return result
    
    async def _organize_memories(self, query: str, context: Dict) -> str:
        """
        Organizar y categorizar recuerdos.
        
        Args:
            query: Consulta o criterio de organización
            context: Contexto adicional
            
        Returns:
            Resultado de la organización
        """
        # Esta función podría implementar clustering de memorias,
        # pero por ahora devolvemos un mensaje simple
        return "La organización automática de memorias está en desarrollo."
    
    async def _forget(self, memory_id: str) -> str:
        """
        Eliminar un recuerdo específico.
        
        Args:
            memory_id: ID del recuerdo a eliminar
            
        Returns:
            Mensaje de confirmación
        """
        if not memory_id:
            return "Se requiere un ID de memoria para olvidar"
            
        result = self.forget(memory_id)
        
        if result:
            return f"He eliminado el recuerdo con ID: {memory_id}"
        else:
            return f"No pude encontrar o eliminar el recuerdo con ID: {memory_id}"
    
    async def _answer_question(self, question: str, context: Dict) -> str:
        """
        Responder una pregunta usando memoria semántica.
        
        Args:
            question: Pregunta a responder
            context: Contexto adicional
            
        Returns:
            Respuesta basada en la memoria
        """
        # Buscar recuerdos relevantes semánticamente
        memories = self.recall_semantic(
            query=question,
            limit=5,
            threshold=self.semantic_threshold
        )
        
        if not memories:
            # Si no hay resultados semánticos, intentar con búsqueda por palabras clave
            memories = self.recall(query=question, limit=3)
            
        if not memories:
            return f"No tengo información para responder a esa pregunta."
            
        # Construir contexto para el modelo
        prompt = f"Pregunta: {question}\n\n"
        prompt += "Información relacionada encontrada en mi memoria:\n"
        
        for i, memory in enumerate(memories):
            content = memory.content if hasattr(memory, 'content') else memory.get('content', '')
            prompt += f"{i+1}. {content}\n\n"
            
        prompt += "Basándote únicamente en la información proporcionada, responde a la pregunta de forma concisa y útil."
        
        try:
            # Cargar modelo para generar respuesta
            model, model_info = await self.model_manager.load_model(self.model_name)
            
            # Generar respuesta
            response = await model.generate(prompt)
            
            return response
        except Exception as e:
            self.logger.error(f"Error generando respuesta con modelo: {str(e)}")
            
            # Fallback: respuesta simple basada en las memorias
            result = "Basado en mi memoria, puedo decir que:\n\n"
            for i, memory in enumerate(memories[:3]):
                content = memory.content if hasattr(memory, 'content') else memory.get('content', '')
                result += f"{i+1}. {content}\n\n"
                
            return result
    
    async def _get_memory_status(self) -> str:
        """
        Obtener estadísticas del sistema de memoria.
        
        Returns:
            Información sobre el estado de la memoria
        """
        try:
            # Verificar si podemos obtener estadísticas directamente vía MCP
            if hasattr(self.memory_manager, 'memory_system') and hasattr(self.memory_manager.memory_system, 'mcp_client'):
                from mcp.core import MCPMessage, MCPAction, MCPResource
                
                # Usar mensaje MCP para obtener estadísticas
                info_message = MCPMessage(
                    action=MCPAction.GET,
                    resource_type=MCPResource.SYSTEM,
                    resource_path="/info"
                )
                
                response = self.memory_manager.memory_system.mcp_client.send_message(info_message)
                
                if response.success:
                    info = response.data
                    vector_search = info.get('vector_search', False)
                    embedding_dim = info.get('embedding_dim', 'N/A')
                    
                    # Obtener recuento de memorias por tipo
                    count_message = MCPMessage(
                        action=MCPAction.SEARCH,
                        resource_type=MCPResource.MEMORY,
                        resource_path="/count"
                    )
                    
                    count_response = self.memory_manager.memory_system.mcp_client.send_message(count_message)
                    memory_counts = {}
                    
                    if count_response.success:
                        memory_counts = count_response.data.get('counts', {})
                    
                    # Formatear estadísticas
                    result = "Estado del sistema de memoria:\n\n"
                    result += f"- Búsqueda vectorial: {'Disponible' if vector_search else 'No disponible'}\n"
                    if vector_search:
                        result += f"- Dimensión de embeddings: {embedding_dim}\n"
                    
                    result += f"- Total memorias: {sum(memory_counts.values())}\n"
                    result += "- Memorias por tipo:\n"
                    
                    for memory_type, count in memory_counts.items():
                        result += f"  * {memory_type}: {count}\n"
                    
                    return result
            
            # Fallback simple si no podemos usar MCP
            return "Información de estado de memoria no disponible"
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estado de memoria: {str(e)}")
            return f"Error obteniendo estadísticas de memoria: {str(e)}"

    def setup_memory(self, memory_config=None):
        """
        Configurar memoria para el agente especializado en memoria.
        
        Args:
            memory_config: Configuración específica para la memoria
            
        Returns:
            True si se configuró correctamente, False en caso contrario
        """
        if not memory_config:
            self.logger.error("MemoryAgent requiere configuración de memoria")
            return False
        
        # Verificar que existe cliente MCP
        if not memory_config.get("mcp_client"):
            self.logger.error("MemoryAgent requiere un cliente MCP")
            return False
        
        try:
            # Import aquí para evitar importaciones circulares
            from memory.core.memory_manager import MemoryManager
            
            # Verificar que tenemos un data_dir
            data_dir = memory_config.get("data_dir")
            if not data_dir:
                self.logger.error("MemoryAgent requiere data_dir en la configuración")
                return False
            
            # Asegurar que data_dir existe
            os.makedirs(data_dir, exist_ok=True)
            
            # Crear una nueva configuración limpia con solo lo necesario
            config = {
                "mcp_client": memory_config["mcp_client"],
                "data_dir": data_dir
            }
            
            # La clase MemoryManager tiene sus propias reglas de nombrado
            # Necesitamos las rutas absolutas para asegurar que no haya problemas
            ltm_path = os.path.abspath(os.path.join(data_dir, "long_term_memory.db"))
            episodic_path = os.path.abspath(os.path.join(data_dir, "episodic_memory.db"))
            semantic_path = os.path.abspath(os.path.join(data_dir, "semantic_memory.db"))
            
            # Verificar que las rutas son válidas
            self.logger.info(f"Verificando rutas de memoria:")
            self.logger.info(f"- data_dir: {data_dir}")
            self.logger.info(f"- LongTerm: {ltm_path}")
            self.logger.info(f"- Episodic: {episodic_path}")
            self.logger.info(f"- Semantic: {semantic_path}")
            
            # Inicializar el MemoryManager directamente con datos mínimos
            self.memory_manager = MemoryManager(data_dir=data_dir)
            
            # Agregar cliente MCP a la memoria base
            self.memory_system = self.memory_manager.memory_system
            self.memory_system.mcp_client = memory_config["mcp_client"]
            
            self.logger.info(f"Sistema de memoria configurado para MemoryAgent '{self.name}'")
            return True
        except ImportError as e:
            self.logger.error(f"Error importando MemoryManager: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error configurando sistema de memoria: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False 

    def _format_memory_results(self, memories, include_similarity=False):
        """
        Formatea resultados de memoria para presentación.
        
        Args:
            memories: Lista de memorias o diccionarios de memoria
            include_similarity: Si incluir puntuación de similitud
            
        Returns:
            String formateado con los resultados
        """
        if not memories:
            return "No se encontraron resultados."
        
        result_lines = ["Resultados encontrados:"]
        
        for idx, memory in enumerate(memories):
            # Determinar si es un objeto MemoryItem o un diccionario
            if hasattr(memory, 'content'):
                # Es un objeto MemoryItem
                content = memory.content
                memory_type = memory.memory_type
                created_at = memory.created_at
                similarity = getattr(memory, 'similarity', None)
            else:
                # Es un diccionario
                content = memory.get('content', 'Contenido desconocido')
                memory_type = memory.get('memory_type', 'unknown')
                created_at = memory.get('created_at', 'fecha desconocida')
                similarity = memory.get('similarity')
                
            # Formatear la línea
            if include_similarity and similarity is not None:
                result_lines.append(f"{idx+1}. [{similarity:.2f}] {content}")
            else:
                result_lines.append(f"{idx+1}. {content}")
            
        return "\n".join(result_lines)

    def _generate_answer_from_memories(self, query, memories):
        """
        Genera una respuesta basada en memorias recuperadas.
        
        Args:
            query: Pregunta original
            memories: Memorias recuperadas
            
        Returns:
            Respuesta generada basada en las memorias
        """
        # Si tenemos un modelo, usarlo para generar una respuesta coherente
        if hasattr(self, 'model_manager') and self.model_manager:
            try:
                # Preparar contexto con las memorias
                memory_context = []
                for memory in memories:
                    if hasattr(memory, 'content'):
                        memory_context.append(str(memory.content))
                    else:
                        memory_context.append(str(memory.get('content', '')))
                    
                # Construir prompt
                prompt = f"""
                Pregunta: {query}
                
                Información disponible:
                {memory_context}
                
                Responde de manera concisa y clara basándote solo en la información proporcionada.
                """
                
                return "Basado en la información que tengo: " + memory_context[0]
                
            except Exception as e:
                self.logger.error(f"Error generando respuesta con modelo: {e}")
                # En caso de error, caer al método simple
        
        # Método simple (sin modelo): devolver la primera memoria relevante
        for memory in memories:
            if hasattr(memory, 'content'):
                return f"Según mi información: {memory.content}"
            else:
                return f"Según mi información: {memory.get('content', 'No tengo información específica.')}"
            
        return "No tengo información suficiente para responder a esa pregunta." 

    def _setup_actions(self):
        """Configurar acciones disponibles para este agente."""
        self.logger.debug("Configurando acciones del agente de memoria")
        # En una implementación completa, aquí se definirían las acciones disponibles
        # por ahora solo es un placeholder 

    def recall_semantic(self, query, memory_type=None, limit=5, metadata_filter=None):
        """
        Buscar información en la memoria usando búsqueda semántica (vectorial).
        
        Args:
            query: Consulta a buscar
            memory_type: Tipo de memoria a buscar
            limit: Número máximo de resultados
            metadata_filter: Filtro adicional por metadatos
            
        Returns:
            Lista de memorias similares a la consulta
        """
        if not self.has_memory():
            self.logger.warning("No se puede realizar búsqueda semántica - no hay memoria configurada")
            return []
        
        try:
            if hasattr(self.memory_manager.memory_system, 'mcp_client'):
                # Usar búsqueda por MCP
                from mcp.core import MCPMessage, MCPAction, MCPResource
                
                search_msg = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type=MCPResource.VECTOR,
                    resource_path="/search",
                    params={
                        "query": query,
                        "memory_type": memory_type,
                        "limit": limit,
                        "threshold": self.semantic_threshold,
                        "metadata_filter": metadata_filter or {}
                    }
                )
                
                response = self.memory_manager.memory_system.mcp_client.send_message(search_msg)
                if response.success:
                    # Deduplicar resultados por ID de memoria
                    seen_ids = set()
                    unique_results = []
                    
                    for item in response.data.get('results', []):
                        memory_id = item.get('id')
                        if memory_id not in seen_ids:
                            seen_ids.add(memory_id)
                            unique_results.append(item)
                    
                    self.logger.info(f"Búsqueda semántica MCP exitosa: {len(unique_results)} resultados únicos de {len(response.data.get('results', []))} totales")
                    return unique_results
                else:
                    self.logger.warning(f"Búsqueda semántica MCP falló: {response.error}")
            
            # Implementación estándar como fallback
            # 1. Obtener memorias de la memoria
            memories = self.memory_manager.query_memories(
                query=None,  # No usamos búsqueda de texto aquí
                memory_type=memory_type,
                metadata_filter=metadata_filter
            )
            
            if not memories:
                self.logger.warning(f"No se encontraron memorias del tipo {memory_type}")
                return []
            
            # 2. Usar el embedder para buscar similitudes
            if not hasattr(self.memory_manager, '_memory_embedder'):
                self.logger.warning("No hay embedder configurado - no se puede realizar búsqueda semántica")
                return []
            
            embedder = self.memory_manager._memory_embedder
            results = embedder.find_similar_memories(
                query=query,
                memories=memories,
                top_k=limit * 2,  # Pedimos más para luego deduplicar
                threshold=self.semantic_threshold
            )
            
            # Deduplicar resultados basados en contenido
            seen_contents = set()
            unique_results = []
            
            for memory, score in results:
                # Crear una representación simplificada del contenido para deduplicación
                content_hash = self._get_content_hash(memory.content)
                
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    unique_results.append((memory, score))
                    
                    # Si ya tenemos suficientes resultados únicos, paramos
                    if len(unique_results) >= limit:
                        break
            
            self.logger.info(f"Búsqueda semántica estándar exitosa: {len(unique_results)} resultados únicos de {len(results)} totales")
            return unique_results
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda semántica: {e}")
            return []

    def _get_content_hash(self, content):
        """
        Genera un hash simplificado del contenido para deduplicación.
        
        Args:
            content: Contenido a hashear (str, dict, list)
            
        Returns:
            String representando el hash del contenido
        """
        import hashlib
        
        if isinstance(content, str):
            # Para textos, usamos los primeros 100 caracteres
            content_str = content[:100].lower()
        elif isinstance(content, dict):
            # Para diccionarios, combinamos claves y valores principales
            main_items = sorted(list(content.items())[:5])
            content_str = str(main_items)
        elif isinstance(content, list):
            # Para listas, tomamos los primeros elementos
            content_str = str(content[:5])
        else:
            content_str = str(content)
        
        return hashlib.md5(content_str.encode()).hexdigest() 