"""
Memory Summarizer Module

This module provides functionality for summarizing memories, especially useful
for condensing large amounts of information into concise representations.
"""

import logging
from typing import List, Dict, Any, Optional, Callable

from ..core.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """
    Memory summarizer processor that generates concise summaries of memories.
    
    This class provides functionality to summarize individual memories or
    collections of memories, either using built-in rules or an external
    summarization model.
    """
    
    def __init__(self, external_summarizer: Optional[Callable] = None):
        """
        Initialize a new memory summarizer.
        
        Args:
            external_summarizer: Optional external summarization function that takes text
                                and returns a summary
        """
        self.external_summarizer = external_summarizer
        logger.info(f"Initialized memory summarizer with external_summarizer={external_summarizer is not None}")
    
    def summarize_memory(self, memory: MemoryItem, max_length: int = 100) -> str:
        """
        Generate a summary for a single memory item.
        
        Args:
            memory: The memory item to summarize
            max_length: Maximum length of the summary in characters
            
        Returns:
            A string summary of the memory
        """
        # If the memory content is already a string and short enough, use it directly
        if isinstance(memory.content, str) and len(memory.content) <= max_length:
            return memory.content
        
        # If we have an external summarizer, use it
        if self.external_summarizer and isinstance(memory.content, str):
            try:
                summary = self.external_summarizer(memory.content)
                # Ensure the summary isn't too long
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                return summary
            except Exception as e:
                logger.error(f"Error using external summarizer: {e}")
                # Fall back to basic summarization
        
        # Basic summarization logic
        if isinstance(memory.content, str):
            # For string content, take the first part
            if len(memory.content) > max_length:
                return memory.content[:max_length-3] + "..."
            return memory.content
        elif isinstance(memory.content, dict):
            # For dictionary content, create a summary of keys and values
            items = list(memory.content.items())
            summary_parts = []
            remaining_length = max_length - 3  # Reserve space for "..."
            
            for key, value in items:
                if isinstance(value, str) and len(value) > 30:
                    value_str = value[:30] + "..."
                else:
                    value_str = str(value)
                
                part = f"{key}: {value_str}"
                if len(part) > remaining_length:
                    if summary_parts:
                        summary_parts.append("...")
                    break
                
                summary_parts.append(part)
                remaining_length -= len(part) + 2  # 2 for ", " separator
                
                if remaining_length <= 0:
                    break
            
            return ", ".join(summary_parts)
        elif isinstance(memory.content, list):
            # For list content, summarize the first few items
            if not memory.content:
                return "[]"
                
            item_summaries = []
            remaining_length = max_length - 5  # Reserve space for "[...]"
            
            for item in memory.content:
                if isinstance(item, str) and len(item) > 20:
                    item_str = item[:20] + "..."
                else:
                    item_str = str(item)
                    if len(item_str) > 20:
                        item_str = item_str[:20] + "..."
                
                if len(item_str) > remaining_length:
                    if item_summaries:
                        item_summaries.append("...")
                    break
                
                item_summaries.append(item_str)
                remaining_length -= len(item_str) + 2  # 2 for ", " separator
                
                if remaining_length <= 0:
                    break
            
            return "[" + ", ".join(item_summaries) + "]"
        else:
            # For other types, just convert to string and truncate
            content_str = str(memory.content)
            if len(content_str) > max_length:
                return content_str[:max_length-3] + "..."
            return content_str
    
    def summarize_memories(
        self,
        memories: List[MemoryItem],
        max_total_length: int = 500,
        include_metadata: bool = False
    ) -> str:
        """
        Generate a summary for a collection of memory items.
        
        Args:
            memories: List of memory items to summarize
            max_total_length: Maximum total length of the summary
            include_metadata: Whether to include metadata in the summary
            
        Returns:
            A string summary of the memories
        """
        if not memories:
            return "No memories to summarize."
        
        # If we have an external summarizer and just one memory with string content,
        # use it directly for better quality
        if (
            len(memories) == 1 and
            self.external_summarizer and 
            isinstance(memories[0].content, str)
        ):
            try:
                summary = self.external_summarizer(memories[0].content)
                if len(summary) > max_total_length:
                    summary = summary[:max_total_length-3] + "..."
                return summary
            except Exception as e:
                logger.error(f"Error using external summarizer: {e}")
                # Fall back to basic summarization
        
        # For multiple memories, summarize each one briefly and combine
        memory_summaries = []
        remaining_length = max_total_length - 50  # Reserve space for intro and connector text
        
        # Sort memories by importance (highest first)
        sorted_memories = sorted(memories, key=lambda m: m.importance, reverse=True)
        
        for memory in sorted_memories:
            # Generate a brief summary for this memory
            memory_summary = self.summarize_memory(memory, max_length=100)
            
            # Add metadata if requested
            if include_metadata:
                if hasattr(memory, 'source') and memory.source:
                    source_info = f" (from {memory.source})"
                    memory_summary += source_info
                importance_info = f" [importance: {memory.importance:.2f}]"
                memory_summary += importance_info
            
            # Check if we can add this summary
            if len(memory_summary) > remaining_length:
                if memory_summaries:
                    memory_summaries.append("...")
                break
            
            memory_summaries.append(memory_summary)
            remaining_length -= len(memory_summary) + 2  # 2 for newline separator
            
            if remaining_length <= 0:
                break
        
        # Combine the summaries
        if len(memory_summaries) == len(memories):
            intro = f"Summary of {len(memories)} memories:\n"
        else:
            intro = f"Summary of {len(memory_summaries)} out of {len(memories)} memories:\n"
        
        return intro + "\n".join(memory_summaries)
    
    def generate_topic_summary(self, memories: List[MemoryItem], topic: str, max_length: int = 200) -> str:
        """
        Generate a summary of memories related to a specific topic.
        
        Args:
            memories: List of memory items to summarize
            topic: The topic to focus on
            max_length: Maximum length of the summary
            
        Returns:
            A summary focused on the specified topic
        """
        if not memories:
            return f"No memories found related to '{topic}'."
        
        # Filter memories that might be related to the topic
        topic_keywords = topic.lower().split()
        relevant_memories = []
        
        for memory in memories:
            memory_text = self.summarize_memory(memory, max_length=200).lower()
            relevance_score = 0
            
            # Simple keyword matching for relevance
            for keyword in topic_keywords:
                if keyword in memory_text:
                    relevance_score += 1
            
            # If memory has metadata with tags or categories, check those too
            if hasattr(memory, 'metadata') and memory.metadata:
                if isinstance(memory.metadata.get('tags'), list):
                    for tag in memory.metadata['tags']:
                        if any(keyword in str(tag).lower() for keyword in topic_keywords):
                            relevance_score += 2
                
                if isinstance(memory.metadata.get('category'), str):
                    if any(keyword in memory.metadata['category'].lower() for keyword in topic_keywords):
                        relevance_score += 2
            
            # If the memory seems relevant, include it
            if relevance_score > 0:
                relevant_memories.append((memory, relevance_score))
        
        # If no relevant memories found, return a message
        if not relevant_memories:
            return f"No memories found related to '{topic}'."
        
        # Sort by relevance score (highest first)
        relevant_memories.sort(key=lambda x: x[1], reverse=True)
        relevant_memories = [m for m, _ in relevant_memories]
        
        # Generate a summary focusing on the topic
        summary = self.summarize_memories(
            memories=relevant_memories[:5],  # Take the top 5 most relevant
            max_total_length=max_length,
            include_metadata=False
        )
        
        # Replace the generic intro with a topic-focused one
        summary_lines = summary.split('\n')
        topic_intro = f"Summary of information related to '{topic}':\n"
        summary = topic_intro + '\n'.join(summary_lines[1:])
        
        return summary


class Summarizer:
    """
    Simplified interface for memory summarization functionality.
    
    This class provides a simpler entry point to the more comprehensive
    MemorySummarizer class, using default settings suitable for most use cases.
    """
    
    def __init__(self):
        """Initialize a new summarizer with default settings."""
        # Create a simple default summarization function
        def default_summarizer(text: str) -> str:
            """Simple summarization function that extracts the first few sentences."""
            # Split text into sentences (simple approach)
            sentences = []
            for part in text.split('. '):
                # Handle abbreviations like "Dr." or "U.S.A."
                if part and part[-1].isalpha():
                    sentences.append(part + '.')
                elif part:
                    sentences.append(part)
            
            # Calculate summary length based on text size
            if len(text) < 500:
                summary_sentences = min(2, len(sentences))
            elif len(text) < 1000:
                summary_sentences = min(3, len(sentences))
            else:
                summary_sentences = min(4, len(sentences))
                
            # Create summary
            if sentences:
                summary = ' '.join(sentences[:summary_sentences])
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                return summary
            else:
                return text[:200] + "..." if len(text) > 200 else text
        
        # Initialize the full summarizer with our default function
        self.summarizer = MemorySummarizer(
            external_summarizer=default_summarizer
        )
        
        logger.info("Initialized Summarizer with default summarization function")
    
    def summarize(self, texts: List[str], max_length: int = 200) -> str:
        """
        Generate a summary for a collection of texts.
        
        Args:
            texts: List of text strings to summarize
            max_length: Maximum length of the summary
            
        Returns:
            A summarized string
        """
        # Convert texts to memory items
        from ..core.memory_item import MemoryItem
        memories = []
        
        for i, text in enumerate(texts):
            # Create a temporary memory item
            memory = MemoryItem(
                content=text,
                memory_type="text",
                importance=0.5
            )
            memories.append(memory)
        
        # Generate and return the summary
        summary = self.summarizer.summarize_memories(
            memories=memories,
            max_total_length=max_length,
            include_metadata=False
        )
        
        # Remove the generic intro line
        summary_lines = summary.split('\n', 1)
        if len(summary_lines) > 1:
            return summary_lines[1]
        return summary
    
    def summarize_memory(self, memory: MemoryItem, max_length: int = 100) -> str:
        """
        Generate a summary for a single memory item.
        
        Args:
            memory: The memory item to summarize
            max_length: Maximum length of the summary
            
        Returns:
            A string summary of the memory
        """
        return self.summarizer.summarize_memory(memory, max_length=max_length)
    
    def summarize_memories(self, memories: List[MemoryItem], max_length: int = 200) -> str:
        """
        Generate a summary for multiple memory items.
        
        Args:
            memories: List of memory items to summarize
            max_length: Maximum length of the summary
            
        Returns:
            A string summary of the memories
        """
        summary = self.summarizer.summarize_memories(
            memories=memories,
            max_total_length=max_length,
            include_metadata=False
        )
        
        # Remove the generic intro line
        summary_lines = summary.split('\n', 1)
        if len(summary_lines) > 1:
            return summary_lines[1]
        return summary 