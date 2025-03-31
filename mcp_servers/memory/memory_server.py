"""
Servidor MCP para el sistema de memoria.

Este servidor proporciona acceso al sistema de memoria a través del protocolo MCP,
permitiendo almacenar, recuperar y consultar memorias.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Union
import os
from pathlib import Path
import numpy as np

from mcp.core import (
    MCPServerBase, 
    MCPMessage, 
    MCPResponse, 
    MCPAction, 
    MCPResource, 
    MCPErrorCode
)

from memory.core.memory_manager import MemoryManager
from memory.core.memory_item import MemoryItem
from memory.processors.embedder import MemoryEmbedder

# Importar función para generar embeddings si está disponible
try:
    from models.core.model_manager import ModelManager
    HAS_MODEL_MANAGER = True
except ImportError:
    HAS_MODEL_MANAGER = False


class MemoryServer(MCPServerBase):
    """
    Servidor MCP para acceder al sistema de memoria.
    
    Este servidor permite almacenar, recuperar y consultar memorias a través
    del protocolo MCP, facilitando la integración con agentes.
    """
    
    def __init__(
        self, 
        name: str = "memory_server", 
        description: str = "Servidor MCP para acceso al sistema de memoria",
        memory_manager: Optional[MemoryManager] = None,
        data_dir: Optional[str] = None,
        embedding_function: Optional[callable] = None,
        embedding_dim: int = 768
    ):
        """
        Inicializa el servidor de memoria.
        
        Args:
            name: Nombre del servidor (por defecto: "memory_server")
            description: Descripción del servidor
            memory_manager: Gestor de memoria preexistente (opcional)
            data_dir: Directorio para almacenamiento persistente (opcional)
            embedding_function: Función para generar embeddings (opcional)
            embedding_dim: Dimensión de los vectores de embedding (por defecto: 768)
        """
        super().__init__(
            name=name,
            description=description,
            auth_required=False,
            supported_actions=[
                MCPAction.PING,
                MCPAction.CAPABILITIES,
                MCPAction.GET,     # Obtener una memoria específica
                MCPAction.LIST,    # Listar memorias según criterios
                MCPAction.SEARCH,  # Buscar memorias por contenido
                MCPAction.CREATE,  # Crear nuevas memorias
                MCPAction.UPDATE,  # Actualizar memorias existentes
                MCPAction.DELETE,  # Eliminar memorias
                MCPAction.QUERY    # Realizar consultas complejas
            ],
            supported_resources=[
                MCPResource.SYSTEM,
                MCPResource.MEMORY,
                "memory_item",     # Ítem individual de memoria
                "memory_type",     # Tipo de memoria (long_term, short_term, etc.)
                "vector"           # Recurso para búsquedas vectoriales
            ]
        )
        
        # Configurar el directorio de datos si se proporciona
        if data_dir:
            self.data_dir = Path(data_dir)
            os.makedirs(self.data_dir, exist_ok=True)
        else:
            self.data_dir = None
        
        # Usar el memory_manager proporcionado o crear uno nuevo
        self.memory_manager = memory_manager or MemoryManager(
            data_dir=str(self.data_dir) if self.data_dir else None
        )
        
        # Diccionario para almacenar información de debug
        self.debug_info = {
            "request_count": 0,
            "error_count": 0,
            "last_request": None,
            "last_error": None
        }
        
        # Configurar el embedding si se proporciona una función
        self.embedding_function = embedding_function
        self.embedding_dim = embedding_dim
        self.embedder = None
        
        # Intentar crear un embedder con la función proporcionada o una por defecto
        if self.embedding_function:
            self.embedder = MemoryEmbedder(
                embedding_function=self.embedding_function,
                embedding_dim=self.embedding_dim
            )
            self.logger.info("Embedder inicializado con función personalizada")
        else:
            # Intentar crear un embedder usando ModelManager si está disponible
            if HAS_MODEL_MANAGER:
                try:
                    model_manager = ModelManager()
                    # Obtener un modelo para embeddings
                    if model_manager.has_embedding_model():
                        self.embedding_function = model_manager.embed_text
                        self.embedder = MemoryEmbedder(
                            embedding_function=self.embedding_function,
                            embedding_dim=self.embedding_dim
                        )
                        self.logger.info("Embedder inicializado usando ModelManager")
                    else:
                        self.logger.warning("ModelManager no tiene un modelo para embeddings")
                except Exception as e:
                    self.logger.warning(f"Error al inicializar ModelManager: {e}")
            else:
                # Función de embedding mínima (solo para demostración)
                def simple_embedding(text: str) -> List[float]:
                    """Función de embedding simple basada en hash de palabras."""
                    # Esta función es solo para demostración y no debe usarse en producción
                    import hashlib
                    words = text.lower().split()
                    vector = [0.0] * self.embedding_dim
                    for i, word in enumerate(words):
                        # Hash de la palabra para generar un valor pseudo-aleatorio
                        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
                        # Distribuir el valor en varias posiciones del vector
                        for j in range(min(5, self.embedding_dim)):
                            pos = (hash_val + j) % self.embedding_dim
                            vector[pos] += (1.0 / (i + 1)) * (0.9 ** j)
                    
                    # Normalizar el vector
                    norm = sum(v**2 for v in vector) ** 0.5
                    if norm > 0:
                        vector = [v / norm for v in vector]
                    return vector
                
                self.embedding_function = simple_embedding
                self.embedder = MemoryEmbedder(
                    embedding_function=self.embedding_function,
                    embedding_dim=self.embedding_dim
                )
                self.logger.warning("Usando embedder simplificado (solo para demostración)")
        
        # Inicializar caché para embeddings
        self.embedding_cache = {}
        
        self.logger.info(f"Servidor de memoria inicializado: {name}")
    
    async def handle_action(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja las acciones recibidas por el servidor.
        
        Args:
            message: Mensaje MCP a procesar
            
        Returns:
            Respuesta al mensaje
        """
        try:
            # Actualizar información de debug
            self.debug_info["request_count"] += 1
            self.debug_info["last_request"] = {
                "action": message.action,
                "resource_type": message.resource_type,
                "resource_path": message.resource_path,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None
            }
            
            self.logger.info(f"MemoryServer recibió: {message.action} - {message.resource_type} - {message.resource_path}")
            
            # Manejar acciones según el tipo
            if message.action == MCPAction.GET.value:
                return await self._handle_get(message)
            elif message.action == MCPAction.LIST.value:
                return await self._handle_list(message)
            elif message.action == MCPAction.SEARCH.value:
                return await self._handle_search(message)
            elif message.action == MCPAction.CREATE.value:
                return await self._handle_create(message)
            elif message.action == MCPAction.UPDATE.value:
                return await self._handle_update(message)
            elif message.action == MCPAction.DELETE.value:
                return await self._handle_delete(message)
            elif message.action == MCPAction.QUERY.value:
                return await self._handle_query(message)
            else:
                # Acciones no implementadas
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message=f"Acción no implementada: {message.action}"
                )
        except Exception as e:
            # Actualizar información de error
            self.debug_info["error_count"] += 1
            self.debug_info["last_error"] = {
                "error": str(e),
                "action": message.action,
                "resource_path": message.resource_path
            }
            
            self.logger.error(f"Error procesando acción {message.action}: {str(e)}")
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.SERVER_ERROR,
                message=f"Error del servidor: {str(e)}"
            )

    async def _handle_get(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción GET para obtener memorias.
        
        Args:
            message: Mensaje MCP con acción GET
            
        Returns:
            Respuesta con los datos solicitados
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        # Para solicitudes del sistema
        if resource_type == MCPResource.SYSTEM.value:
            if resource_path == "/info":
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "server": self.name,
                        "description": self.description,
                        "memory_types": list(self.memory_manager._specialized_memories.keys()),
                        "data_dir": str(self.data_dir) if self.data_dir else None,
                        "vector_search": self.embedder is not None,
                        "embedding_dim": self.embedding_dim if self.embedder else None,
                        "stats": {
                            "requests": self.debug_info["request_count"],
                            "errors": self.debug_info["error_count"]
                        }
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Recurso de sistema no encontrado: {resource_path}"
                )
        
        # Para obtener una memoria específica
        elif resource_type == MCPResource.MEMORY.value or resource_type == "memory_item":
            # resource_path puede ser el ID de memoria o un tipo de memoria + ID
            memory_id = resource_path.strip("/")
            
            # Verificar si se proporcionó un ID de memoria
            if not memory_id:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un ID de memoria"
                )
            
            # Obtener la memoria del sistema
            memory = self.memory_manager.get_memory(memory_id)
            
            if memory:
                # Crear respuesta con datos de memoria
                memory_dict = memory.to_dict()
                
                # Si tenemos un embedder, podemos agregar el embedding
                if self.embedder and message.data and message.data.get("include_embedding", False):
                    # Generar embedding si no está en caché
                    if memory_id not in self.embedding_cache:
                        self.embedding_cache[memory_id] = self.embedder.generate_embedding(memory)
                    
                    # Añadir el embedding a la respuesta
                    memory_dict["embedding"] = self.embedding_cache[memory_id]
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data=memory_dict
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Memoria no encontrada: {memory_id}"
                )
        
        # Para información sobre un tipo de memoria
        elif resource_type == "memory_type":
            memory_type = resource_path.strip("/")
            
            if memory_type in self.memory_manager._specialized_memories:
                specialized_memory = self.memory_manager._specialized_memories[memory_type]
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "name": memory_type,
                        "type": type(specialized_memory).__name__,
                        "description": specialized_memory.__doc__.strip() if specialized_memory.__doc__ else "Sin descripción"
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Tipo de memoria no encontrado: {memory_type}"
                )
                
        # Para obtener un vector de embedding
        elif resource_type == "vector":
            # El path debe ser un ID de memoria o un texto para embedding
            path_parts = resource_path.strip("/").split("/")
            
            # Verificar si es un embedding para un ID de memoria
            if path_parts[0] == "memory" and len(path_parts) > 1:
                memory_id = path_parts[1]
                memory = self.memory_manager.get_memory(memory_id)
                
                if not memory:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Memoria no encontrada: {memory_id}"
                    )
                
                # Generar embedding si no está en caché
                if memory_id not in self.embedding_cache:
                    if not self.embedder:
                        return MCPResponse.error_response(
                            message_id=message.id,
                            code=MCPErrorCode.NOT_IMPLEMENTED,
                            message="Embedder no inicializado"
                        )
                    
                    self.embedding_cache[memory_id] = self.embedder.generate_embedding(memory)
                
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "memory_id": memory_id,
                        "embedding": self.embedding_cache[memory_id],
                        "dimensions": len(self.embedding_cache[memory_id])
                    }
                )
            
            # Si no es un ID específico, podría ser una solicitud para un texto directo
            elif message.data and "text" in message.data:
                text = message.data["text"]
                
                if not self.embedder:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.NOT_IMPLEMENTED,
                        message="Embedder no inicializado"
                    )
                
                try:
                    # Generar embedding para el texto proporcionado
                    embedding = self.embedding_function(text)
                    
                    return MCPResponse.success_response(
                        message_id=message.id,
                        data={
                            "text": text[:50] + "..." if len(text) > 50 else text,
                            "embedding": embedding,
                            "dimensions": len(embedding)
                        }
                    )
                except Exception as e:
                    return MCPResponse.error_response(
                        message_id=message.id,
                        code=MCPErrorCode.SERVER_ERROR,
                        message=f"Error generando embedding: {str(e)}"
                    )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un ID de memoria o texto para generar embedding"
                )
        
        # Tipo de recurso no soportado
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para GET: {resource_type}"
            )
    
    async def _handle_list(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción LIST para listar memorias.
        
        Args:
            message: Mensaje MCP con acción LIST
            
        Returns:
            Respuesta con la lista de memorias
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Para solicitudes del sistema
        if resource_type == MCPResource.SYSTEM.value:
            if resource_path == "/memory_types":
                return MCPResponse.success_response(
                    message_id=message.id,
                    data={
                        "types": list(self.memory_manager._specialized_memories.keys())
                    }
                )
            else:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Recurso de sistema no encontrado: {resource_path}"
                )
        
        # Para listar memorias
        elif resource_type == MCPResource.MEMORY.value or resource_type == "memory_item":
            # Convertir los datos del mensaje en un formato de consulta
            query = {}
            
            # Filtros
            if "memory_type" in data:
                query["memory_type"] = data["memory_type"]
            
            if "min_importance" in data:
                query["min_importance"] = float(data["min_importance"])
            
            if "max_importance" in data:
                query["max_importance"] = float(data["max_importance"])
            
            if "metadata" in data:
                query["metadata"] = data["metadata"]
            
            # Paginación
            limit = int(data.get("limit", 100))
            offset = int(data.get("offset", 0))
            
            # Para un tipo específico de memoria
            memory_system_type = resource_path.strip("/")
            memory_system = None
            
            if memory_system_type and memory_system_type in self.memory_manager._specialized_memories:
                memory_system = self.memory_manager.get_memory_system(memory_system_type)
            else:
                memory_system = self.memory_manager.memory_system
            
            # Ejecutar la consulta
            memories = memory_system.storage.query(query, limit=limit, offset=offset)
            
            # Convertir a diccionarios para la respuesta
            memory_dicts = [memory.to_dict() for memory in memories]
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "items": memory_dicts,
                    "total": len(memory_dicts),
                    "limit": limit,
                    "offset": offset
                }
            )
        
        # Para listar tipos de memoria
        elif resource_type == "memory_type":
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "types": list(self.memory_manager._specialized_memories.keys())
                }
            )
        
        # Tipo de recurso no soportado
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para LIST: {resource_type}"
            )
    
    async def _handle_search(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción SEARCH para buscar memorias.
        
        Args:
            message: Mensaje MCP con acción SEARCH
            
        Returns:
            Respuesta con los resultados de la búsqueda
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Solo soportamos búsqueda de memorias y vectores
        if resource_type not in [MCPResource.MEMORY.value, "memory_item", "vector"]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para SEARCH: {resource_type}"
            )
        
        # Para búsqueda vectorial (semántica)
        if resource_type == "vector":
            # Verificar si tenemos embedder
            if not self.embedder:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.NOT_IMPLEMENTED,
                    message="Búsqueda vectorial no disponible (embedder no inicializado)"
                )
            
            # Necesitamos una consulta de texto o un vector
            query_text = data.get("query", "").strip()
            query_vector = data.get("vector", None)
            
            if not query_text and not query_vector:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un término de búsqueda (query) o un vector"
                )
            
            # Parámetros adicionales
            top_k = int(data.get("limit", 5))
            threshold = float(data.get("threshold", 0.7))
            memory_type_filter = data.get("memory_type")
            
            # Determinamos el sistema de memoria a usar según el path
            memory_system_type = resource_path.strip("/")
            if memory_system_type and memory_system_type in self.memory_manager._specialized_memories:
                memory_system = self.memory_manager.get_memory_system(memory_system_type)
            else:
                memory_system = self.memory_manager.memory_system
            
            # Construir consulta básica para filtrar memorias
            db_query = {}
            
            if memory_type_filter:
                db_query["memory_type"] = memory_type_filter
            
            # Obtener todas las memorias que cumplen con los filtros base
            all_memories = memory_system.storage.query(db_query)
            
            # Realizar búsqueda vectorial
            query = query_text if query_text else query_vector
            results = self.embedder.find_similar_memories(
                query=query,
                memories=all_memories,
                top_k=top_k,
                threshold=threshold
            )
            
            # Convertir a formato de respuesta
            response_results = []
            for memory, similarity in results:
                memory_dict = memory.to_dict()
                memory_dict["score"] = float(similarity)  # Asegurar que sea un float y usar "score" como clave
                response_results.append(memory_dict)
            
            # Realizar deduplicación por contenido
            deduplicated_results = []
            seen_contents = set()

            for result in response_results:
                content_hash = str(result.get("content", ""))[:100].lower()  # Usar primeros 100 chars como hash
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    deduplicated_results.append(result)

            self.logger.info(f"Búsqueda vectorial: {len(deduplicated_results)} resultados únicos de {len(response_results)} totales")

            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "results": deduplicated_results,
                    "count": len(deduplicated_results),
                    "query": query_text if query_text else "vector_query"
                }
            )
        
        # Para búsqueda textual estándar
        else:
            # Parámetros de búsqueda
            query = data.get("query", "").strip()
            memory_type_filter = data.get("memory_type")
            limit = int(data.get("limit", 10))
            
            if not query:
                return MCPResponse.error_response(
                    message_id=message.id,
                    code=MCPErrorCode.INVALID_REQUEST,
                    message="Se requiere un término de búsqueda"
                )
            
            # Determinamos el sistema de memoria a usar según el path
            memory_system_type = resource_path.strip("/")
            if memory_system_type and memory_system_type in self.memory_manager._specialized_memories:
                memory_system = self.memory_manager.get_memory_system(memory_system_type)
            else:
                memory_system = self.memory_manager.memory_system
            
            # Construir consulta básica
            db_query = {}
            
            if memory_type_filter:
                db_query["memory_type"] = memory_type_filter
            
            # Obtener todas las memorias que cumplen con los filtros base
            all_memories = memory_system.storage.query(db_query)
            
            # Verificar si debemos usar búsqueda semántica
            use_semantic = data.get("semantic", False) and self.embedder is not None
            
            if use_semantic:
                # Usar búsqueda semántica con el embedder
                results_with_scores = self.embedder.find_similar_memories(
                    query=query,
                    memories=all_memories,
                    top_k=limit,
                    threshold=float(data.get("threshold", 0.5))
                )
                
                # Extraer solo las memorias
                results = [memory for memory, _ in results_with_scores]
                
                # Convertir a diccionarios para la respuesta con puntajes
                memory_dicts = []
                for memory, score in results_with_scores:
                    memory_dict = memory.to_dict()
                    memory_dict["relevance"] = score
                    memory_dicts.append(memory_dict)
            else:
                # Realizar búsqueda de texto simple en las memorias
                results = []
                for memory in all_memories:
                    content_str = str(memory.content).lower()
                    if query.lower() in content_str:
                        results.append(memory)
                        if len(results) >= limit:
                            break
                
                # Convertir a diccionarios para la respuesta
                memory_dicts = [memory.to_dict() for memory in results]
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "results": memory_dicts,
                    "count": len(memory_dicts),
                    "query": query,
                    "semantic": use_semantic
                }
            )

    async def _handle_create(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción CREATE para crear nuevas memorias.
        
        Args:
            message: Mensaje MCP con acción CREATE
            
        Returns:
            Respuesta con el resultado de la creación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Solo soportamos creación de memorias
        if resource_type not in [MCPResource.MEMORY.value, "memory_item"]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para CREATE: {resource_type}"
            )
        
        # Verificar datos requeridos
        if "content" not in data:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el campo 'content' para crear una memoria"
            )
        
        content = data["content"]
        memory_type = data.get("memory_type", "general")
        importance = float(data.get("importance", 0.5))
        metadata = data.get("metadata", {})
        
        # Determinamos dónde añadir la memoria
        target_memories = None
        if resource_path and resource_path != "/":
            # Extraer tipo(s) de memoria del path
            target_memories = [resource_path.strip("/")]
        
        # Crear la memoria
        memory_id = self.memory_manager.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata,
            target_memories=target_memories
        )
        
        # Obtener la memoria creada para devolverla
        memory = self.memory_manager.get_memory(memory_id)
        
        # Si tenemos embedder, generar y almacenar el embedding
        if self.embedder and data.get("generate_embedding", False):
            try:
                self.embedding_cache[memory_id] = self.embedder.generate_embedding(memory)
                embedding_generated = True
            except Exception as e:
                self.logger.error(f"Error generando embedding: {e}")
                embedding_generated = False
        else:
            embedding_generated = False
        
        return MCPResponse.success_response(
            message_id=message.id,
            data={
                "id": memory_id,
                "memory": memory.to_dict() if memory else {"id": memory_id},
                "embedding_generated": embedding_generated,
                "message": "Memoria creada correctamente"
            }
        )
    
    async def _handle_update(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción UPDATE para actualizar memorias existentes.
        
        Args:
            message: Mensaje MCP con acción UPDATE
            
        Returns:
            Respuesta con el resultado de la actualización
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Solo soportamos actualización de memorias
        if resource_type not in [MCPResource.MEMORY.value, "memory_item"]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para UPDATE: {resource_type}"
            )
        
        # Extraer ID de la memoria
        memory_id = resource_path.strip("/")
        
        if not memory_id:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere un ID de memoria para actualizar"
            )
        
        # Preparar datos para actualización
        update_data = {}
        
        if "content" in data:
            update_data["content"] = data["content"]
        
        if "memory_type" in data:
            update_data["memory_type"] = data["memory_type"]
        
        if "importance" in data:
            update_data["importance"] = float(data["importance"])
        
        if "metadata" in data:
            update_data["metadata"] = data["metadata"]
        
        # Actualizar la memoria
        result = self.memory_manager.update_memory(
            memory_id=memory_id,
            **update_data
        )
        
        if result:
            # Obtener la memoria actualizada
            memory = self.memory_manager.get_memory(memory_id)
            
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "id": memory_id,
                    "memory": memory.to_dict() if memory else {"id": memory_id},
                    "message": "Memoria actualizada correctamente"
                }
            )
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.RESOURCE_NOT_FOUND,
                message=f"No se pudo actualizar la memoria con ID: {memory_id}"
            )
    
    async def _handle_delete(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción DELETE para eliminar memorias.
        
        Args:
            message: Mensaje MCP con acción DELETE
            
        Returns:
            Respuesta con el resultado de la eliminación
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        
        # Solo soportamos eliminación de memorias
        if resource_type not in [MCPResource.MEMORY.value, "memory_item"]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para DELETE: {resource_type}"
            )
        
        # Extraer ID de la memoria
        memory_id = resource_path.strip("/")
        
        if not memory_id:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere un ID de memoria para eliminar"
            )
        
        # Eliminar la memoria usando el sistema de memoria base
        result = self.memory_manager.memory_system.delete_memory(memory_id)
        
        if result:
            return MCPResponse.success_response(
                message_id=message.id,
                data={
                    "id": memory_id,
                    "message": "Memoria eliminada correctamente"
                }
            )
        else:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.RESOURCE_NOT_FOUND,
                message=f"No se pudo eliminar la memoria con ID: {memory_id}"
            )
    
    async def _handle_query(self, message: MCPMessage) -> MCPResponse:
        """
        Maneja la acción QUERY para consultas avanzadas.
        
        Args:
            message: Mensaje MCP con acción QUERY
            
        Returns:
            Respuesta con los resultados de la consulta
        """
        resource_type = message.resource_type
        resource_path = message.resource_path
        data = message.data or {}
        
        # Solo soportamos consultas de memoria
        if resource_type not in [MCPResource.MEMORY.value, "memory_item"]:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.NOT_IMPLEMENTED,
                message=f"Tipo de recurso no soportado para QUERY: {resource_type}"
            )
        
        # Verificar datos requeridos
        if "query" not in data:
            return MCPResponse.error_response(
                message_id=message.id,
                code=MCPErrorCode.INVALID_REQUEST,
                message="Se requiere el campo 'query' para la consulta"
            )
        
        query = data["query"]
        limit = int(data.get("limit", 100))
        offset = int(data.get("offset", 0))
        
        # Determinar qué sistema de memoria usar
        memory_system_type = resource_path.strip("/")
        memory_system = None
        
        if memory_system_type and memory_system_type in self.memory_manager._specialized_memories:
            memory_system = self.memory_manager.get_memory_system(memory_system_type)
        else:
            memory_system = self.memory_manager.memory_system
        
        # Ejecutar la consulta
        memories = memory_system.storage.query(query, limit=limit, offset=offset)
        
        # Convertir a diccionarios para la respuesta
        memory_dicts = [memory.to_dict() for memory in memories]
        
        return MCPResponse.success_response(
            message_id=message.id,
            data={
                "results": memory_dicts,
                "count": len(memory_dicts),
                "query": query
            }
        ) 