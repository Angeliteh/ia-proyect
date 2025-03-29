"""
Memory Embedder Module

This module provides functionality for generating vector embeddings for memories,
enabling semantic search and similarity-based retrieval.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Callable, Union, Tuple

from ..core.memory_item import MemoryItem

logger = logging.getLogger(__name__)


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
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        # Convert to numpy arrays for efficient computation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        # Handle zero vectors
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure the result is between 0 and 1
        similarity = max(0.0, min(1.0, float(similarity)))
        
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
            query_embedding = self.embedding_function(query)
        elif isinstance(query, MemoryItem):
            query_embedding = self.generate_embedding(query)
        else:
            query_embedding = query
        
        # Calculate similarities
        results = []
        
        for memory in memories:
            # Generate embedding if not already present
            if not memory.embedding:
                memory.embedding = self.generate_embedding(memory)
            
            # Calculate similarity
            similarity = self.calculate_similarity(query_embedding, memory.embedding)
            
            # Add to results if above threshold
            if similarity >= threshold:
                results.append((memory, similarity))
        
        # Sort by similarity (highest first) and limit to top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def process_memories(self, memories: List[MemoryItem]) -> None:
        """
        Process a batch of memories, generating embeddings for those without them.
        
        Args:
            memories: List of memory items to process
        """
        for memory in memories:
            if not memory.embedding:
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
            best_similarity = -1
            
            for i, center in enumerate(centers):
                similarity = self.calculate_similarity(memory.embedding, center.embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = i
            
            # Only assign if similarity is above threshold
            if best_similarity >= min_similarity:
                clusters[best_cluster].append(memory)
            else:
                # Create a new cluster if we have room
                if len(clusters) < num_clusters:
                    cluster_id = len(clusters)
                    clusters[cluster_id] = [memory]
                    centers.append(memory)
                else:
                    # Otherwise, assign to best cluster anyway
                    clusters[best_cluster].append(memory)
        
        logger.info(f"Created {len(clusters)} memory clusters")
        return clusters 