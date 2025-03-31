"""
Memory Embedder Module

This module provides functionality for generating vector embeddings for memories,
enabling semantic search and similarity-based retrieval.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Callable, Union, Tuple

# Importar Sentence Transformers para embeddings avanzados
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "sentence-transformers no está instalado. Se usará embedding simple. "
        "Para mejor rendimiento, instale con: pip install sentence-transformers"
    )

from ..core.memory_item import MemoryItem

logger = logging.getLogger(__name__)

# Singleton para el modelo (para no cargarlo cada vez)
_model_cache = {}


class MemoryEmbedder:
    """
    Memory embedder processor that generates vector embeddings for memories.
    
    This class provides functionality to create semantic embeddings for memories,
    enabling semantic search and similarity-based operations.
    """
    
    def __init__(
        self,
        embedding_function: Callable[[str], List[float]],
        embedding_dim: int = 768
    ):
        """
        Initialize a new memory embedder.
        
        Args:
            embedding_function: Function that takes a string and returns a vector embedding
            embedding_dim: Dimension of the embedding vectors
        """
        self.embedding_function = embedding_function
        self.embedding_dim = embedding_dim
        logger.info(f"Initialized memory embedder with embedding_dim={embedding_dim}")
    
    def get_text_for_embedding(self, memory: MemoryItem) -> str:
        """
        Extract text from a memory item for embedding.
        
        Args:
            memory: The memory item to extract text from
            
        Returns:
            A string representation suitable for embedding
        """
        # If content is already a string, use it directly
        if isinstance(memory.content, str):
            return memory.content
        
        # For dictionaries, combine key-value pairs
        if isinstance(memory.content, dict):
            parts = []
            for key, value in memory.content.items():
                parts.append(f"{key}: {value}")
            return "\n".join(parts)
        
        # For lists, join items
        if isinstance(memory.content, list):
            parts = []
            for item in memory.content:
                parts.append(str(item))
            return "\n".join(parts)
        
        # For other types, convert to string
        return str(memory.content)
    
    def generate_embedding(self, memory: MemoryItem) -> List[float]:
        """
        Generate a vector embedding for a memory item.
        
        Args:
            memory: The memory item to embed
            
        Returns:
            A vector embedding as a list of floats
        """
        text = self.get_text_for_embedding(memory)
        
        try:
            # Verificar si la función de embedding es asíncrona
            import inspect
            if inspect.iscoroutinefunction(self.embedding_function):
                logger.warning("La función de embedding es asíncrona, pero se está llamando sincrónicamente. Usando simple_embedding como alternativa.")
                return self._simple_embedding(text)
            
            # Función normal síncrona
            embedding = self.embedding_function(text)
            logger.debug(f"Generated embedding for memory {memory.id}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return a zero vector as fallback
            return [0.0] * self.embedding_dim
    
    def generate_embeddings(self, memories: List[MemoryItem]) -> Dict[str, List[float]]:
        """
        Generate embeddings for multiple memory items.
        
        Args:
            memories: List of memory items to embed
            
        Returns:
            Dictionary mapping memory IDs to embeddings
        """
        embeddings = {}
        
        for memory in memories:
            embedding = self.generate_embedding(memory)
            embeddings[memory.id] = embedding
        
        logger.debug(f"Generated embeddings for {len(embeddings)} memories")
        return embeddings
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings with improved precision.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        # Convert to numpy arrays for efficient computation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Check for zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # Handle zero vectors
        if norm1 < 1e-10 or norm2 < 1e-10:
            return 0.0
        
        # Normalize vectors before computing similarity (unit vectors)
        vec1_norm = vec1 / norm1
        vec2_norm = vec2 / norm2
        
        # Calculate cosine similarity with normalized vectors
        # This is more numerically stable
        dot_product = np.dot(vec1_norm, vec2_norm)
        
        # Apply slight non-linearity to emphasize higher similarity values
        # This helps distinguish between highly similar items
        if dot_product > 0:
            dot_product = dot_product ** 0.9  # Slight power transformation
        
        # Ensure the result is between 0 and 1
        similarity = max(0.0, min(1.0, float(dot_product)))
        
        return similarity
    
    def find_similar_memories(
        self,
        query: Union[str, MemoryItem, List[float]],
        memories: List[MemoryItem],
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[MemoryItem, float]]:
        """
        Find memories similar to a query.
        
        Args:
            query: Query string, memory item, or embedding vector
            memories: List of memory items to search through
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (memory, similarity) tuples, sorted by similarity
        """
        # Get the query embedding
        if isinstance(query, str):
            # Obtener el embedding dependiendo de si la función es asíncrona o no
            import inspect
            if inspect.iscoroutinefunction(self.embedding_function):
                logger.warning("La función de embedding es asíncrona, pero se está llamando sincrónicamente. Usando simple_embedding como alternativa.")
                # Usar una función de embedding simple en su lugar
                query_embedding = self._simple_embedding(query)
            else:
                query_embedding = self.embedding_function(query)
        elif isinstance(query, MemoryItem):
            query_embedding = self.generate_embedding(query)
        else:
            query_embedding = query
        
        # Calculate similarities
        results = []
        
        for memory in memories:
            # Generate embedding if not already present
            if not hasattr(memory, 'embedding') or memory.embedding is None:
                memory.embedding = self.generate_embedding(memory)
            
            # Calculate similarity
            similarity = self.calculate_similarity(query_embedding, memory.embedding)
            
            # Add to results if above threshold
            if similarity >= threshold:
                results.append((memory, similarity))
        
        # Sort by similarity (highest first) and limit to top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _simple_embedding(self, text: str) -> List[float]:
        """
        Genera embeddings utilizando Sentence Transformers o fallback a método simple.
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            Vector de embedding
        """
        # Intentar usar Sentence Transformers si está disponible
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Obtener o cargar el modelo
                if 'model' not in _model_cache:
                    logger.info("Cargando modelo Sentence Transformer...")
                    _model_cache['model'] = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
                    
                model = _model_cache['model']
                
                # Generar embedding
                embedding = model.encode(text)
                return embedding.tolist()  # Convertir a lista para serialización
            except Exception as e:
                logger.error(f"Error generando embedding con Sentence Transformers: {e}")
                # Fallback al embedding simple original si hay error
                logger.info("Usando embedding fallback por error")
                return self._fallback_embedding(text)
        else:
            # Si Sentence Transformers no está disponible, usar el método fallback
            logger.debug("Usando embedding fallback")
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Método de embedding fallback que no requiere dependencias externas.
        
        Esta función se usa como alternativa cuando Sentence Transformers no está disponible,
        o cuando hay un error en la generación del embedding principal.
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            Vector de embedding
        """
        import hashlib
        import re
        from collections import Counter
        
        # Limpiar y normalizar el texto
        text = text.lower()
        
        # Eliminar puntuación y caracteres especiales
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Eliminar números
        text = re.sub(r'\d+', ' ', text)
        
        # Eliminar espacios extras
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Lista de palabras vacías en español e inglés (stopwords)
        stopwords = {'a', 'al', 'algo', 'algunas', 'algunos', 'ante', 'antes', 'como', 'con', 'contra',
                     'cual', 'cuando', 'de', 'del', 'desde', 'donde', 'durante', 'e', 'el', 'ella',
                     'ellas', 'ellos', 'en', 'entre', 'era', 'erais', 'eran', 'eras', 'eres', 'es',
                     'and', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with'}
        
        # Dividir en palabras
        words = text.split()
        # Filtrar palabras vacías
        words = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Contar frecuencia de palabras
        word_counts = Counter(words)
        
        # Crear un vector con la dimensión correcta
        embedding = [0.0] * self.embedding_dim
        
        # Rellenar el vector con valores basados en las palabras
        for word, count in word_counts.items():
            # Crear un hash determinista para la palabra
            hash_obj = hashlib.md5(word.encode())
            hash_val = int(hash_obj.hexdigest(), 16)
            
            # Usar el hash para determinar qué dimensiones se afectan
            dim_index = hash_val % self.embedding_dim
            
            # Valor a asignar basado en frecuencia de la palabra
            value = min(1.0, count / 10)  # Limitar a 1.0
            
            # Aplicar una función de decaimiento para valores más distantes
            for i in range(10):  # Afectar 10 dimensiones cercanas
                pos = (dim_index + i) % self.embedding_dim
                decay = 0.8 ** i  # Función de decaimiento exponencial
                embedding[pos] += value * decay
        
        # Normalizar el vector (si no es vector cero)
        norm = np.linalg.norm(embedding)
        if norm > 1e-10:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def process_memories(self, memories: List[MemoryItem]) -> None:
        """
        Process a batch of memories, generating embeddings for those without them.
        
        Args:
            memories: List of memory items to process
        """
        for memory in memories:
            if not hasattr(memory, 'embedding') or memory.embedding is None:
                memory.embedding = self.generate_embedding(memory)
                logger.debug(f"Added embedding to memory {memory.id}")
    
    def create_memory_clusters(
        self,
        memories: List[MemoryItem],
        num_clusters: int = 5,
        min_similarity: float = 0.7
    ) -> Dict[int, List[MemoryItem]]:
        """
        Cluster memories based on their embeddings.
        
        Args:
            memories: List of memory items to cluster
            num_clusters: Target number of clusters
            min_similarity: Minimum similarity to assign to a cluster
            
        Returns:
            Dictionary mapping cluster IDs to lists of memory items
        """
        if not memories:
            return {}
            
        # Ensure all memories have embeddings
        self.process_memories(memories)
        
        # Simple clustering algorithm (could be replaced with k-means or other approaches)
        clusters = {}
        remaining = memories.copy()
        
        # Start with random centers
        import random
        random.shuffle(remaining)
        
        centers = []
        for i in range(min(num_clusters, len(remaining))):
            center = remaining.pop(0)
            centers.append(center)
            clusters[i] = [center]
        
        # Assign remaining memories to closest cluster
        for memory in remaining:
            best_cluster = -1
            best_similarity = min_similarity  # Must meet minimum similarity
            
            for i, center in enumerate(centers):
                similarity = self.calculate_similarity(memory.embedding, center.embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = i
            
            if best_cluster >= 0:
                clusters[best_cluster].append(memory)
            else:
                # Create a new cluster if no good match
                new_cluster_id = len(clusters)
                clusters[new_cluster_id] = [memory]
                centers.append(memory)
        
        logger.debug(f"Created {len(clusters)} memory clusters")
        return clusters


class Embedder:
    """
    Simplified interface for memory embedding functionality.
    
    This class provides a simpler entry point to the more comprehensive
    MemoryEmbedder class, using default settings suitable for most use cases.
    """
    
    def __init__(self, embedding_dim: int = 768):
        """
        Initialize a new embedder with a default embedding function.
        
        Args:
            embedding_dim: Dimension of the embedding vectors
        """
        # Create a simple default embedding function
        def default_embedding_function(text: str) -> List[float]:
            """Simple embedding function that creates a pseudo-random embedding based on text content."""
            import hashlib
            
            # Create a deterministic seed based on the text
            text_bytes = text.encode('utf-8')
            hash_obj = hashlib.md5(text_bytes)
            seed = int(hash_obj.hexdigest(), 16) % (2**32)
            
            # Set the random seed for reproducibility
            np.random.seed(seed)
            
            # Generate a random embedding
            embedding = np.random.randn(embedding_dim).tolist()
            
            # Normalize to unit length
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            return embedding
        
        # Initialize the full embedder with our default function
        self.embedder = MemoryEmbedder(
            embedding_function=default_embedding_function,
            embedding_dim=embedding_dim
        )
        
        logger.info("Initialized Embedder with default embedding function")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate an embedding for a text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Vector embedding as a list of floats
        """
        # Create a temporary memory item
        from ..core.memory_item import MemoryItem
        temp_memory = MemoryItem(content=text)
        
        # Generate and return the embedding
        return self.embedder.generate_embedding(temp_memory)
    
    def find_similar(self, query: str, memories: List[MemoryItem], top_k: int = 5) -> List[MemoryItem]:
        """
        Find memories similar to a query string.
        
        Args:
            query: Query string to find similar memories for
            memories: List of memory items to search through
            top_k: Number of top results to return
            
        Returns:
            List of similar memory items
        """
        results = self.embedder.find_similar_memories(query, memories, top_k=top_k)
        return [memory for memory, _ in results]
    
    def process_memories(self, memories: List[MemoryItem]) -> None:
        """
        Process memories by adding embeddings to them.
        
        Args:
            memories: List of memory items to process
        """
        self.embedder.process_memories(memories) 