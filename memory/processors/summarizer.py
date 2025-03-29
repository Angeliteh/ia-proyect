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
                source_info = f" (from {memory.source})"
                importance_info = f" [importance: {memory.importance:.2f}]"
                memory_summary += source_info + importance_info
            
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
        Generate a summary focused on a specific topic from a collection of memories.
        
        Args:
            memories: List of memory items to summarize
            topic: The topic to focus on
            max_length: Maximum length of the summary
            
        Returns:
            A string summary focused on the specified topic
        """
        if not memories:
            return f"No memories found related to '{topic}'."
        
        # If we have an external summarizer, use it with a prompt
        if self.external_summarizer:
            # Prepare combined content with a focus on the topic
            combined_content = f"Topic: {topic}\n\nContent:\n"
            for memory in memories:
                if isinstance(memory.content, str):
                    combined_content += memory.content + "\n\n"
                else:
                    combined_content += str(memory.content) + "\n\n"
            
            try:
                # Ask the external summarizer to focus on the topic
                prompt = f"Please provide a concise summary of the following content, focusing specifically on information related to '{topic}':\n\n{combined_content}"
                summary = self.external_summarizer(prompt)
                
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                
                return summary
            except Exception as e:
                logger.error(f"Error using external summarizer for topic summary: {e}")
                # Fall back to basic topic summarization
        
        # Basic topic summarization - look for memories that might contain the topic
        relevant_memories = []
        
        for memory in memories:
            content_str = str(memory.content)
            # Check if the topic appears in the content
            if topic.lower() in content_str.lower():
                relevant_memories.append(memory)
        
        if not relevant_memories:
            return f"Found {len(memories)} memories, but none seem specifically related to '{topic}'."
        
        # Summarize the relevant memories
        return self.summarize_memories(
            relevant_memories,
            max_total_length=max_length,
            include_metadata=True
        ) 