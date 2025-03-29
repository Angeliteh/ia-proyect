#!/usr/bin/env python
"""
Memory System Examples

This module contains examples for demonstrating the memory system functionality.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import json
from uuid import uuid4
import sqlite3

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.core.memory_system import MemorySystem
from memory.core.memory_item import MemoryItem
from memory.storage.in_memory_storage import InMemoryStorage
from memory.types.episodic_memory import EpisodicMemory, Episode
from memory.types.semantic_memory import SemanticMemory, Fact

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_basic_demo():
    """Run a basic demonstration of the memory system."""
    logger.info("Running basic memory demonstration")
    
    # Create a memory system
    memory_system = MemorySystem(storage=InMemoryStorage())
    
    # Add some memories
    memory_id1 = memory_system.add_memory(
        content="This is a test memory about artificial intelligence",
        memory_type="fact",
        importance=0.8,
        metadata={"source": "user"}
    )
    
    memory_id2 = memory_system.add_memory(
        content="Remember to buy milk and eggs from the store",
        memory_type="reminder",
        importance=0.5,
        metadata={"source": "system", "due": "tomorrow"}
    )
    
    memory_id3 = memory_system.add_memory(
        content="Complete project report by Friday",
        memory_type="task",
        importance=0.9,
        metadata={
            "source": "user",
            "task": "Complete project report",
            "due_date": "2023-12-15",
            "priority": "high"
        }
    )
    
    # Print the memory IDs
    print(f"Created memory system and added three memories with IDs:")
    print(f"  - {memory_id1}")
    print(f"  - {memory_id2}")
    print(f"  - {memory_id3}")
    
    # Retrieve a memory
    memory = memory_system.get_memory(memory_id1)
    print(f"\nRetrieved memory content: '{memory.content}' (access count: {memory.access_count})")
    
    # Query memories by type
    memories = memory_system.query_memories(memory_type="reminder")
    print(f"\nFound {len(memories)} memories of type 'reminder':")
    for memory in memories:
        print(f"  - {memory.content}")
    
    # Query memories by importance
    memories = memory_system.query_memories(min_importance=0.7)
    print(f"\nFound {len(memories)} memories with importance >= 0.7:")
    for memory in memories:
        print(f"  - {memory.content} (importance: {memory.importance})")
        if memory.metadata:
            print(f"    Metadata: {memory.metadata}")
    
    # Link memories
    memory_system.link_memories(memory_id1, memory_id3, "related_to")
    
    # Find related memories
    related = memory_system.get_related_memories(memory_id1)
    print(f"\nLinked the AI memory to the project report task")
    print(f"Found {len(related)} related memories for memory '{memory.content}'")
    
    # Print some stats
    print("\nMemory system statistics:")
    print(f"  - Total memories: {len(memory_system.get_all_memories())}")
    
    sources = {}
    for memory in memory_system.get_all_memories():
        source = memory.metadata.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1
    
    print(f"  - Sources: {', '.join([f'{s} ({c})' for s, c in sources.items()])}")


def run_episodic_demo():
    """Run a demonstration of the episodic memory system."""
    logger.info("Running episodic memory demonstration")
    
    # Create a temporary database path
    db_path = "data/memory/episodic_demo.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove the database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create a memory system
    memory_system = MemorySystem(storage=InMemoryStorage())
    
    # Create an episodic memory system
    episodic_memory = EpisodicMemory(memory_system, db_path=db_path)
    
    print("Created episodic memory system")
    
    # Create a conversation episode
    print("\nCreating a conversation episode...")
    conversation_id = episodic_memory.create_episode(
        title="Conversation about AI project",
        description="Discussion about implementing a new AI agent",
        importance=0.8,
        metadata={"participants": ["user", "assistant"]}
    )
    
    # Add memories to the conversation episode
    memory_id1 = memory_system.add_memory(
        content="I'm thinking about creating a new AI agent for my project.",
        memory_type="message",
        importance=0.7,
        metadata={"speaker": "user", "timestamp": datetime.now().isoformat()}
    )
    
    memory_id2 = memory_system.add_memory(
        content="That sounds interesting! What kind of agent are you considering?",
        memory_type="message",
        importance=0.7,
        metadata={"speaker": "assistant", "timestamp": datetime.now().isoformat()}
    )
    
    memory_id3 = memory_system.add_memory(
        content="I'm considering a recommendation agent that can suggest music based on mood.",
        memory_type="message",
        importance=0.8,
        metadata={"speaker": "user", "timestamp": datetime.now().isoformat()}
    )
    
    # Add the memories to the episode
    episodic_memory.add_memory_to_episode(conversation_id, memory_id1)
    episodic_memory.add_memory_to_episode(conversation_id, memory_id2)
    episodic_memory.add_memory_to_episode(conversation_id, memory_id3)
    
    # Create a task episode
    print("Creating a task episode...")
    task_id = episodic_memory.create_episode(
        title="Implement music recommendation agent",
        description="Steps to implement the music recommendation AI agent",
        importance=0.9,
        metadata={"status": "in_progress", "due_date": "2023-12-30"}
    )
    
    # Add memories to the task episode
    memory_id4 = memory_system.add_memory(
        content="Research existing music recommendation algorithms",
        memory_type="task_item",
        importance=0.8,
        metadata={"status": "completed", "timestamp": datetime.now().isoformat()}
    )
    
    memory_id5 = memory_system.add_memory(
        content="Design data model for storing user preferences",
        memory_type="task_item",
        importance=0.8,
        metadata={"status": "in_progress", "timestamp": datetime.now().isoformat()}
    )
    
    memory_id6 = memory_system.add_memory(
        content="Implement API for accessing music service",
        memory_type="task_item",
        importance=0.9,
        metadata={"status": "not_started", "timestamp": datetime.now().isoformat()}
    )
    
    # Add the memories to the episode
    episodic_memory.add_memory_to_episode(task_id, memory_id4)
    episodic_memory.add_memory_to_episode(task_id, memory_id5)
    episodic_memory.add_memory_to_episode(task_id, memory_id6)
    
    # Create a reference link between the conversation and task episodes
    memory_id7 = memory_system.add_memory(
        content="Link between conversation and task implementation",
        memory_type="reference",
        importance=0.7,
        metadata={
            "source_episode": conversation_id,
            "target_episode": task_id,
            "relationship": "resulted_in"
        }
    )
    
    # Add the reference memory to both episodes
    episodic_memory.add_memory_to_episode(conversation_id, memory_id7)
    episodic_memory.add_memory_to_episode(task_id, memory_id7)
    
    # Print episode information
    print("\nEpisode information:")
    
    conversation = episodic_memory.get_episode(conversation_id)
    task = episodic_memory.get_episode(task_id)
    
    print(f"\nConversation episode: '{conversation.title}'")
    print(f"  Description: {conversation.description}")
    print(f"  Importance: {conversation.importance}")
    print(f"  Active: {conversation.is_active}")
    print(f"  Memory count: {len(conversation.memory_ids)}")
    
    print(f"\nTask episode: '{task.title}'")
    print(f"  Description: {task.description}")
    print(f"  Importance: {task.importance}")
    print(f"  Active: {task.is_active}")
    print(f"  Memory count: {len(task.memory_ids)}")
    
    # List all memories in the conversation episode
    print("\nConversation memories:")
    conversation_memories = episodic_memory.get_memories_for_episode(conversation_id)
    for memory in conversation_memories:
        speaker = memory.metadata.get("speaker", "system")
        print(f"  - [{speaker}] {memory.content}")
    
    # List all memories in the task episode
    print("\nTask memories:")
    task_memories = episodic_memory.get_memories_for_episode(task_id)
    for memory in task_memories:
        status = memory.metadata.get("status", "unknown")
        if status != "unknown":
            print(f"  - [{status}] {memory.content}")
        else:
            print(f"  - {memory.content}")
    
    # Demonstrate episode search
    print("\nSearching for episodes containing 'music':")
    search_results = episodic_memory.search_episodes("music")
    for episode in search_results:
        print(f"  - {episode.title}: {episode.description}")
    
    # Get summary of an episode
    print("\nEpisode summary:")
    summary = episodic_memory.get_episode_summary(task_id)
    for key, value in summary.items():
        if key != "first_memory" and key != "last_memory":
            print(f"  - {key}: {value}")
    
    # Clean up by closing the database connection
    episodic_memory.storage.clear()
    print("\nEpisodic memory demonstration completed")


def run_semantic_demo():
    """Run a demonstration of the semantic memory system."""
    logger.info("Running semantic memory demonstration")
    
    # Create a temporary database path
    db_path = "data/memory/semantic_demo.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove the database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create a memory system
    memory_system = MemorySystem(storage=InMemoryStorage())
    
    # Create a semantic memory system
    semantic_memory = SemanticMemory(memory_system, db_path=db_path)
    
    print("Created semantic memory system")
    
    # Add some facts about Paris
    print("\nAdding facts about Paris...")
    fact1_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="is_capital_of",
        object_="France",
        confidence=1.0,
        source="geography_knowledge"
    )
    
    fact2_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="population",
        object_=2.161,  # In millions
        confidence=0.9,
        source="statistics_2023"
    )
    
    fact3_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="has_landmark",
        object_="Eiffel Tower",
        confidence=1.0,
        source="tourism_data"
    )
    
    fact4_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="has_landmark",
        object_="Louvre Museum",
        confidence=1.0,
        source="tourism_data"
    )
    
    fact5_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="founded_year",
        object_=52,  # BCE
        confidence=0.7,  # Less confidence for historical data
        source="historical_records"
    )
    
    # Add structured data as an object
    fact6_id = semantic_memory.add_fact(
        subject="Paris",
        predicate="weather",
        object_={
            "seasons": {
                "summer": {"avg_high": 25, "avg_low": 16},
                "winter": {"avg_high": 8, "avg_low": 3}
            },
            "annual_rainfall": 637,  # mm
            "climate_type": "oceanic"
        },
        confidence=0.85,
        source="weather_data"
    )
    
    # Add facts about Eiffel Tower
    print("Adding facts about Eiffel Tower...")
    fact7_id = semantic_memory.add_fact(
        subject="Eiffel Tower",
        predicate="located_in",
        object_="Paris",
        confidence=1.0,
        source="geography_knowledge"
    )
    
    fact8_id = semantic_memory.add_fact(
        subject="Eiffel Tower",
        predicate="height",
        object_=330,  # meters
        confidence=1.0,
        source="architecture_data"
    )
    
    fact9_id = semantic_memory.add_fact(
        subject="Eiffel Tower",
        predicate="built_year",
        object_=1889,
        confidence=1.0,
        source="historical_records"
    )
    
    # Add facts with different confidence levels about the same subject-predicate
    print("Adding potentially conflicting facts with different confidence levels...")
    fact10_id = semantic_memory.add_fact(
        subject="Earth",
        predicate="age",
        object_=4.54,  # billion years
        confidence=0.95,
        source="geological_study_2020"
    )
    
    fact11_id = semantic_memory.add_fact(
        subject="Earth",
        predicate="age",
        object_=4.5,  # billion years (simplified)
        confidence=0.8,
        source="educational_material"
    )
    
    # Print all facts we've added
    print("\nAdded the following facts to semantic memory:")
    all_subjects = semantic_memory.get_all_subjects()
    
    for subject in all_subjects:
        facts = semantic_memory.get_facts_about(subject)
        print(f"\nFacts about {subject}:")
        
        for fact in facts:
            obj_str = str(fact.object)
            if isinstance(fact.object, dict):
                obj_str = "complex data"
            
            print(f"  - {fact.predicate}: {obj_str} (confidence: {fact.confidence:.2f}, source: {fact.source})")
    
    # Demonstrate queries
    print("\nQuerying facts about Paris...")
    paris_facts = semantic_memory.get_facts_about("Paris")
    print(f"Found {len(paris_facts)} facts about Paris")
    
    # Demonstrate getting a specific fact value
    capital_of = semantic_memory.get_fact_value("Paris", "is_capital_of")
    print(f"\nParis is the capital of: {capital_of}")
    
    # Demonstrate querying with minimum confidence
    print("\nFacts with confidence >= 0.9:")
    high_confidence_facts = semantic_memory.query_facts(min_confidence=0.9)
    for fact in high_confidence_facts:
        print(f"  - {fact.subject} {fact.predicate} {fact.object} (confidence: {fact.confidence:.2f})")
    
    # Demonstrate checking for conflicts
    print("\nChecking for conflicts in Earth's age...")
    conflicts = semantic_memory.check_conflicts("Earth", "age")
    if conflicts:
        print(f"Found {len(conflicts)} conflicting facts:")
        for fact1, fact2 in conflicts:
            print(f"  - Conflict: {fact1.object} (confidence: {fact1.confidence:.2f}) vs {fact2.object} (confidence: {fact2.confidence:.2f})")
    else:
        print("No conflicts found.")
    
    # Demonstrate fact summary
    print("\nGenerating fact summary for Paris:")
    summary = semantic_memory.get_fact_summary("Paris")
    print(summary)
    
    # Demonstrate accessing and updating a fact
    print("\nRetrieving and updating a fact...")
    fact = semantic_memory.get_fact(fact2_id)
    if fact:
        print(f"Original fact: {fact.subject} {fact.predicate} {fact.object} (confidence: {fact.confidence:.2f})")
        
        # Update confidence
        semantic_memory.update_fact_confidence(fact2_id, 0.95)
        
        # Retrieve the updated fact
        updated_fact = semantic_memory.get_fact(fact2_id)
        print(f"Updated fact: {updated_fact.subject} {updated_fact.predicate} {updated_fact.object} (confidence: {updated_fact.confidence:.2f})")
    
    # Clean up by closing the database connection
    semantic_memory.storage.clear()
    print("\nSemantic memory demonstration completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Memory System Examples")
    parser.add_argument("--demo", choices=["basic", "episodic", "semantic"], default="basic",
                        help="Which demo to run (default: basic)")
    
    args = parser.parse_args()
    
    if args.demo == "basic":
        run_basic_demo()
    elif args.demo == "episodic":
        run_episodic_demo()
    elif args.demo == "semantic":
        run_semantic_demo()
    else:
        print(f"Unknown demo: {args.demo}") 