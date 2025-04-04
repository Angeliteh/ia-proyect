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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/memory
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

# Intentar importar los módulos reales
try:
    # Importar directamente desde los módulos de memoria
    from memory import MemorySystem, MemoryItem
    from memory import InMemoryStorage
    from memory import EpisodicMemory, Episode
    from memory import SemanticMemory, Fact
    
    logger.info("Módulos de memoria importados correctamente")
    USING_REAL_MODULES = True
except ImportError as e:
    logger.warning(f"No se pudieron importar los módulos de memoria: {e}")
    logger.info("Usando implementaciones simuladas para demostración")
    USING_REAL_MODULES = False
    
    # Implementaciones mínimas para demostración
    class MemoryItem:
        def __init__(self, id, content, memory_type="general", importance=0.5, metadata=None):
            self.id = id
            self.content = content
            self.memory_type = memory_type
            self.importance = importance
            self.metadata = metadata or {}
            self.created_at = datetime.now()
            self.last_accessed = datetime.now()
            self.access_count = 0
    
    class InMemoryStorage:
        def __init__(self):
            self.memories = {}
            self.links = {}
        
        def clear(self):
            self.memories = {}
            self.links = {}
    
    class MemorySystem:
        def __init__(self, storage=None):
            self.storage = storage or InMemoryStorage()
            logger.info("Memoria simulada inicializada")
            
        def add_memory(self, content, memory_type="general", importance=0.5, metadata=None):
            memory_id = str(uuid4())
            memory = MemoryItem(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                metadata=metadata
            )
            self.storage.memories[memory_id] = memory
            return memory_id
            
        def get_memory(self, memory_id):
            memory = self.storage.memories.get(memory_id)
            if memory:
                memory.access_count += 1
                memory.last_accessed = datetime.now()
            return memory
            
        def query_memories(self, memory_type=None, min_importance=None):
            results = []
            for memory in self.storage.memories.values():
                if memory_type and memory.memory_type != memory_type:
                    continue
                if min_importance is not None and memory.importance < min_importance:
                    continue
                results.append(memory)
            return results
            
        def get_all_memories(self):
            return list(self.storage.memories.values())
            
        def link_memories(self, from_id, to_id, link_type="related"):
            if from_id not in self.storage.links:
                self.storage.links[from_id] = {}
            self.storage.links[from_id][to_id] = link_type
            
        def get_related_memories(self, memory_id):
            if memory_id not in self.storage.links:
                return []
            
            related = []
            for related_id, _ in self.storage.links[memory_id].items():
                memory = self.get_memory(related_id)
                if memory:
                    related.append(memory)
            return related
    
    class Episode:
        def __init__(self, id, title, description="", importance=0.5, metadata=None):
            self.id = id
            self.title = title
            self.description = description
            self.importance = importance
            self.metadata = metadata or {}
            self.memory_ids = []
            self.is_active = True
            self.created_at = datetime.now()
    
    class EpisodicMemory:
        def __init__(self, memory_system, db_path=None):
            self.memory_system = memory_system
            self.db_path = db_path
            self.episodes = {}
            self.storage = InMemoryStorage()
            logger.info("Memoria episódica simulada inicializada")
            
        def create_episode(self, title, description="", importance=0.5, metadata=None):
            episode_id = str(uuid4())
            episode = Episode(
                id=episode_id,
                title=title,
                description=description,
                importance=importance,
                metadata=metadata
            )
            self.episodes[episode_id] = episode
            return episode_id
            
        def get_episode(self, episode_id):
            return self.episodes.get(episode_id)
            
        def add_memory_to_episode(self, episode_id, memory_id):
            episode = self.get_episode(episode_id)
            if episode:
                if memory_id not in episode.memory_ids:
                    episode.memory_ids.append(memory_id)
                return True
            return False
            
        def get_memories_for_episode(self, episode_id):
            episode = self.get_episode(episode_id)
            if not episode:
                return []
                
            memories = []
            for memory_id in episode.memory_ids:
                memory = self.memory_system.get_memory(memory_id)
                if memory:
                    memories.append(memory)
            return memories
            
        def search_episodes(self, query):
            results = []
            query = query.lower()
            for episode in self.episodes.values():
                if (query in episode.title.lower() or 
                    query in episode.description.lower()):
                    results.append(episode)
            return results
            
        def get_episode_summary(self, episode_id):
            episode = self.get_episode(episode_id)
            if not episode:
                return {}
                
            memories = self.get_memories_for_episode(episode_id)
            
            return {
                "id": episode.id,
                "title": episode.title,
                "description": episode.description,
                "memory_count": len(memories),
                "created_at": episode.created_at.isoformat(),
                "is_active": episode.is_active
            }
    
    class Fact:
        def __init__(self, id, subject, predicate, object_, confidence=1.0, source=None):
            self.id = id
            self.subject = subject
            self.predicate = predicate
            self.object = object_
            self.confidence = confidence
            self.source = source
            self.created_at = datetime.now()
    
    class SemanticMemory:
        def __init__(self, memory_system, db_path=None):
            self.memory_system = memory_system
            self.db_path = db_path
            self.facts = {}
            self.storage = InMemoryStorage()
            logger.info("Memoria semántica simulada inicializada")
            
        def add_fact(self, subject, predicate, object_, confidence=1.0, source=None):
            fact_id = str(uuid4())
            fact = Fact(
                id=fact_id,
                subject=subject,
                predicate=predicate,
                object_=object_,
                confidence=confidence,
                source=source
            )
            self.facts[fact_id] = fact
            return fact_id
            
        def get_fact(self, fact_id):
            return self.facts.get(fact_id)
            
        def get_facts_about(self, subject):
            return [fact for fact in self.facts.values() if fact.subject == subject]
            
        def get_fact_value(self, subject, predicate):
            for fact in self.facts.values():
                if fact.subject == subject and fact.predicate == predicate:
                    return fact.object
            return None
            
        def query_facts(self, min_confidence=None):
            if min_confidence is None:
                return list(self.facts.values())
            return [fact for fact in self.facts.values() if fact.confidence >= min_confidence]
            
        def check_conflicts(self, subject, predicate):
            facts = [f for f in self.facts.values() 
                    if f.subject == subject and f.predicate == predicate]
            
            conflicts = []
            for i in range(len(facts)):
                for j in range(i+1, len(facts)):
                    if facts[i].object != facts[j].object:
                        conflicts.append((facts[i], facts[j]))
            return conflicts
            
        def get_fact_summary(self, subject):
            facts = self.get_facts_about(subject)
            if not facts:
                return f"No information about {subject}"
                
            summary = f"Summary of {subject}:\n"
            for fact in facts:
                summary += f"- {fact.predicate}: {fact.object}"
                if fact.confidence < 1.0:
                    summary += f" (confidence: {fact.confidence:.2f})"
                summary += "\n"
            return summary
            
        def update_fact_confidence(self, fact_id, new_confidence):
            fact = self.get_fact(fact_id)
            if fact:
                fact.confidence = new_confidence
                return True
            return False
            
        def get_all_subjects(self):
            subjects = set()
            for fact in self.facts.values():
                subjects.add(fact.subject)
            return list(subjects)


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
    parser.add_argument("--check-real-modules", action="store_true",
                        help="Check if using real modules")
    
    args = parser.parse_args()
    
    # Check if we're using real modules
    if args.check_real_modules:
        print(f"USING_REAL_MODULES = {USING_REAL_MODULES}")
        sys.exit(0)
    
    if args.demo == "basic":
        run_basic_demo()
    elif args.demo == "episodic":
        run_episodic_demo()
    elif args.demo == "semantic":
        run_semantic_demo()
    else:
        print(f"Unknown demo: {args.demo}") 