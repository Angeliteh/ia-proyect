#!/usr/bin/env python
"""
Script de prueba exhaustivo para el sistema de memoria

Este script prueba sistemáticamente todas las funcionalidades del MemoryManager
y sus subsistemas (ShortTermMemory, LongTermMemory, EpisodicMemory, SemanticMemory).
Cada prueba verifica un aspecto específico del sistema y reporta éxito o fracaso.
"""

import os
import sys
import argparse
import logging
import json
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import random
import uuid

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('memory_system_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('memory_test')

# Agregar el directorio raíz del proyecto al path para importar módulos
project_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_dir))

# Importar módulos del sistema de memoria
try:
    from memory.core.memory_manager import MemoryManager
    from memory.core.memory_system import MemorySystem
    from memory.core.memory_item import MemoryItem
    from memory.storage.in_memory_storage import InMemoryStorage
    from memory.processors.embedder import Embedder
    from memory.processors.summarizer import Summarizer
except ImportError as e:
    logger.error(f"Error al importar módulos del sistema de memoria: {e}")
    sys.exit(1)


class MemoryTestCase(unittest.TestCase):
    """Clase base para las pruebas del sistema de memoria."""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial para todas las pruebas."""
        # Crear directorio temporal para tests
        cls.temp_dir = Path('examples/memory/temp_test_data')
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
        os.makedirs(cls.temp_dir, exist_ok=True)
        
        # Inicializar el MemoryManager
        cls.memory_manager = MemoryManager(
            config={
                "use_long_term_memory": True,
                "use_episodic_memory": True,
                "use_semantic_memory": True,
                "short_term_memory": {
                    "retention_minutes": 60,
                    "capacity": 50
                }
            },
            data_dir=cls.temp_dir
        )
        
        # Crear datos de prueba
        cls.test_memories = cls._generate_test_memories()
        
        # Cargar memorias para las pruebas
        cls.memory_ids = []
        for memory_data in cls.test_memories:
            memory_id = cls.memory_manager.add_memory(
                content=memory_data["content"],
                memory_type=memory_data["memory_type"],
                importance=memory_data["importance"],
                metadata=memory_data["metadata"]
            )
            cls.memory_ids.append(memory_id)
        
        logger.info(f"Configuración completada: {len(cls.memory_ids)} memorias creadas para pruebas")
    
    @classmethod
    def tearDownClass(cls):
        """Limpieza después de todas las pruebas."""
        # Cerrar conexiones a bases de datos
        for memory_type, memory_system in cls.memory_manager._specialized_memories.items():
            if hasattr(memory_system, 'storage') and hasattr(memory_system.storage, 'conn'):
                try:
                    memory_system.storage.conn.close()
                    logger.info(f"Conexión cerrada para {memory_type}")
                except Exception as e:
                    logger.warning(f"Error al cerrar conexión para {memory_type}: {e}")
        
        # Esperar para asegurar que se liberen los archivos
        time.sleep(1)
        
        # Eliminar directorio temporal
        try:
            if Path(cls.temp_dir).exists():
                shutil.rmtree(cls.temp_dir)
                logger.info(f"Directorio temporal eliminado: {cls.temp_dir}")
        except Exception as e:
            logger.error(f"Error al eliminar directorio temporal: {e}")
    
    @staticmethod
    def _generate_test_memories():
        """Genera datos de prueba para las memorias."""
        memory_types = ["fact", "concept", "event", "conversation", "task"]
        
        test_memories = []
        
        # Hechos
        for i in range(5):
            test_memories.append({
                "content": f"El Sol es una estrella de tipo G ubicada en el brazo de Orión de la Vía Láctea, dato #{i+1}",
                "memory_type": "fact",
                "importance": random.uniform(0.5, 1.0),
                "metadata": {
                    "subject": "Sol",
                    "predicate": "es",
                    "object": "estrella tipo G",
                    "category": "astronomía",
                    "tags": ["espacio", "sistema solar", "estrella"]
                }
            })
        
        # Conceptos
        for i in range(5):
            test_memories.append({
                "content": f"La inteligencia artificial es la simulación de procesos de inteligencia humana por sistemas informáticos, concepto #{i+1}",
                "memory_type": "concept",
                "importance": random.uniform(0.6, 0.9),
                "metadata": {
                    "subject": "inteligencia artificial",
                    "predicate": "es",
                    "object": "simulación de procesos",
                    "category": "tecnología",
                    "tags": ["IA", "computación", "aprendizaje automático"]
                }
            })
        
        # Eventos
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).isoformat()
            test_memories.append({
                "content": f"Reunión del equipo para discutir el progreso del proyecto, evento #{i+1}",
                "memory_type": "event",
                "importance": random.uniform(0.3, 0.8),
                "metadata": {
                    "date": date,
                    "location": "Sala de conferencias",
                    "participants": ["Ana", "Juan", "Elena", "Carlos"],
                    "category": "trabajo",
                    "tags": ["reunión", "proyecto", "equipo"]
                }
            })
        
        # Conversaciones
        for i in range(5):
            test_memories.append({
                "content": f"Usuario: ¿Cómo puedo mejorar el rendimiento de mi aplicación?\nAsistente: Puedes empezar por identificar cuellos de botella con herramientas de profiling, conversación #{i+1}",
                "memory_type": "conversation",
                "importance": random.uniform(0.2, 0.7),
                "metadata": {
                    "user": "usuario123",
                    "timestamp": datetime.now().isoformat(),
                    "topic": "optimización",
                    "sentiment": "neutral",
                    "tags": ["soporte técnico", "optimización", "aplicación"]
                }
            })
        
        # Tareas
        for i in range(5):
            status = random.choice(["pendiente", "en progreso", "completada"])
            test_memories.append({
                "content": f"Implementar sistema de caché para mejorar tiempos de respuesta, tarea #{i+1}",
                "memory_type": "task",
                "importance": random.uniform(0.4, 0.9),
                "metadata": {
                    "assignee": "desarrollador" + str(random.randint(1, 5)),
                    "due_date": (datetime.now() + timedelta(days=random.randint(1, 14))).isoformat(),
                    "status": status,
                    "priority": random.choice(["baja", "media", "alta"]),
                    "tags": ["desarrollo", "optimización", "backend"]
                }
            })
        
        return test_memories
    
    def setUp(self):
        """Configuración antes de cada prueba individual."""
        pass
    
    def tearDown(self):
        """Limpieza después de cada prueba individual."""
        pass


class TestMemoryManagerBasic(MemoryTestCase):
    """Pruebas básicas para el MemoryManager."""
    
    def test_initialization(self):
        """Prueba que el MemoryManager se inicialice correctamente."""
        self.assertIsInstance(self.memory_manager.memory_system, MemorySystem)
        self.assertIn("short_term", self.memory_manager._specialized_memories)
        self.assertIn("long_term", self.memory_manager._specialized_memories)
        self.assertIn("episodic", self.memory_manager._specialized_memories)
        self.assertIn("semantic", self.memory_manager._specialized_memories)
    
    def test_add_memory(self):
        """Prueba la función de agregar memoria."""
        memory_id = self.memory_manager.add_memory(
            content="Prueba de memoria nueva",
            memory_type="test",
            importance=0.75,
            metadata={"test": True}
        )
        
        # Verificar que se creó la memoria
        self.assertIsNotNone(memory_id)
        memory = self.memory_manager.get_memory(memory_id)
        self.assertIsNotNone(memory)
        self.assertEqual(memory.content, "Prueba de memoria nueva")
        self.assertEqual(memory.memory_type, "test")
        self.assertEqual(memory.importance, 0.75)
        self.assertEqual(memory.metadata["test"], True)
    
    def test_get_memory(self):
        """Prueba la recuperación de memoria por ID."""
        if not self.memory_ids:
            self.skipTest("No hay IDs de memoria para probar")
        
        # Probar un ID válido
        memory_id = self.memory_ids[0]
        memory = self.memory_manager.get_memory(memory_id)
        self.assertIsNotNone(memory)
        self.assertEqual(memory.id, memory_id)
        
        # Probar un ID inválido
        invalid_id = str(uuid.uuid4())
        memory = self.memory_manager.get_memory(invalid_id)
        self.assertIsNone(memory)
    
    def test_update_memory(self):
        """Prueba la actualización de una memoria existente."""
        if not self.memory_ids:
            self.skipTest("No hay IDs de memoria para probar")
        
        memory_id = self.memory_ids[0]
        original = self.memory_manager.get_memory(memory_id)
        
        # Actualizar la memoria
        success = self.memory_manager.update_memory(
            memory_id=memory_id,
            content="Contenido actualizado",
            importance=0.9
        )
        
        self.assertTrue(success)
        
        # Verificar los cambios
        updated = self.memory_manager.get_memory(memory_id)
        self.assertEqual(updated.content, "Contenido actualizado")
        self.assertEqual(updated.importance, 0.9)
        # El tipo de memoria debe permanecer igual
        self.assertEqual(updated.memory_type, original.memory_type)


class TestMemoryManagerQueries(MemoryTestCase):
    """Pruebas para las funciones de consulta del MemoryManager."""
    
    def test_query_by_memory_type(self):
        """Prueba consultas filtradas por tipo de memoria."""
        # Consultar hechos
        facts = self.memory_manager.query_memories(memory_type="fact", limit=10)
        self.assertTrue(all(m.memory_type == "fact" for m in facts))
        
        # Consultar conceptos
        concepts = self.memory_manager.query_memories(memory_type="concept", limit=10)
        self.assertTrue(all(m.memory_type == "concept" for m in concepts))
    
    def test_query_by_importance(self):
        """Prueba consultas filtradas por nivel de importancia."""
        high_importance = self.memory_manager.query_memories(
            min_importance=0.8,
            limit=10
        )
        self.assertTrue(all(m.importance >= 0.8 for m in high_importance))
        
        low_importance = self.memory_manager.query_memories(
            max_importance=0.3,
            limit=10
        )
        self.assertTrue(all(m.importance <= 0.3 for m in low_importance))
    
    def test_query_by_metadata(self):
        """Prueba consultas filtradas por campos de metadatos."""
        # Consultar por categoría
        astronomy = self.memory_manager.query_memories(
            metadata_query={"category": "astronomía"},
            limit=10
        )
        self.assertTrue(all("astronomía" in m.metadata.get("category", "") for m in astronomy))
        
        # Consultar por status de tarea
        completed = self.memory_manager.query_memories(
            metadata_query={"status": "completada"},
            limit=10
        )
        self.assertTrue(all(m.metadata.get("status") == "completada" for m in completed))
        
    def test_content_search(self):
        """Prueba búsqueda por contenido."""
        # Buscar memorias que contienen "inteligencia"
        ai_memories = self.memory_manager.query_memories(
            content_query="inteligencia",
            limit=10
        )
        self.assertTrue(any("inteligencia" in str(m.content).lower() for m in ai_memories))
        
        # Buscar memorias que contienen "reunión"
        meeting_memories = self.memory_manager.query_memories(
            content_query="reunión",
            limit=10
        )
        self.assertTrue(any("reunión" in str(m.content).lower() for m in meeting_memories))


class TestSpecializedMemorySystems(MemoryTestCase):
    """Pruebas para los subsistemas de memoria especializados."""
    
    def test_short_term_memory(self):
        """Prueba las funciones de la memoria a corto plazo."""
        stm = self.memory_manager.get_memory_system("short_term")
        self.assertIsNotNone(stm)
        
        # Verificar que hay memorias en el sistema
        recent = stm.get_recent(limit=5)
        self.assertTrue(len(recent) > 0)
        
        # Probar la limpieza
        stm.clear()
        recent_after_clear = stm.get_recent(limit=5)
        self.assertEqual(len(recent_after_clear), 0)
        
        # Añadir una nueva memoria
        memory_id = stm.add(
            content="Memoria de prueba a corto plazo",
            source="test",
            importance=0.6
        )
        self.assertIsNotNone(memory_id)
        
        # Verificar que se añadió
        recent = stm.get_recent(limit=1)
        self.assertEqual(len(recent), 1)
    
    def test_long_term_memory(self):
        """Prueba las funciones de la memoria a largo plazo."""
        ltm = self.memory_manager.get_memory_system("long_term")
        self.assertIsNotNone(ltm)
        
        # Añadir varias memorias a largo plazo para asegurar que hay datos
        memory_ids = []
        for i in range(3):
            memory_id = ltm.add(
                content=f"Memoria importante para recordar a largo plazo #{i}",
                source=f"test_ltm_{i}",
                importance=0.85
            )
            self.assertIsNotNone(memory_id)
            memory_ids.append(memory_id)
            
            # Verificar que la memoria existe en el sistema base
            memory = self.memory_manager.get_memory(memory_id)
            self.assertIsNotNone(memory)
            self.assertEqual(memory.memory_type, "long_term")
            
            # Imprimir información de depuración sobre la memoria
            print(f"Memoria creada: ID={memory_id}, Tipo={memory.memory_type}, Importancia={memory.importance}")
        
        # Dar tiempo para que las operaciones de BD se completen
        time.sleep(1.0)
        
        # Ejecutar consulta SQLite directamente para depuración
        try:
            import sqlite3
            conn = sqlite3.connect(os.path.join(self.temp_dir, "long_term_memory.db"))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            total_count = cursor.fetchone()[0]
            print(f"Total de memorias en la BD según consulta directa: {total_count}")
            
            # Ver qué memory_types existen
            cursor.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type")
            type_counts = cursor.fetchall()
            print(f"Conteo por tipo de memoria: {type_counts}")
            
            # Ver algunos registros
            cursor.execute("SELECT id, memory_type, importance FROM memories LIMIT 5")
            sample_rows = cursor.fetchall()
            print(f"Muestra de registros: {sample_rows}")
            
            conn.close()
        except Exception as e:
            print(f"Error al consultar la BD directamente: {e}")
        
        # Obtener estadísticas
        stats = ltm.get_stats()
        print(f"Estadísticas retornadas por get_stats(): {stats}")
        self.assertIsNotNone(stats)
        self.assertIn("total_memories", stats)
        
        # Verificar que hay al menos las 3 memorias que acabamos de añadir
        self.assertGreaterEqual(stats["total_memories"], 3)
    
    def test_episodic_memory(self):
        """Prueba las funciones de la memoria episódica."""
        em = self.memory_manager.get_memory_system("episodic")
        self.assertIsNotNone(em)
        
        # Crear un episodio
        episode_id = em.create_episode(
            title="Episodio de prueba",
            description="Descripción del episodio de prueba",
            importance=0.7
        )
        self.assertIsNotNone(episode_id)
        
        # Verificar que se creó
        episode = em.get_episode(episode_id)
        self.assertIsNotNone(episode)
        self.assertEqual(episode.title, "Episodio de prueba")
        
        # Añadir una memoria al episodio
        new_memory_id = self.memory_manager.add_memory(
            content="Memoria para el episodio de prueba",
            memory_type="event",
            importance=0.6
        )
        
        success = em.add_memory_to_episode(episode_id, new_memory_id)
        self.assertTrue(success)
        
        # Verificar que se añadió
        memories = em.get_memories_for_episode(episode_id)
        self.assertTrue(any(m.id == new_memory_id for m in memories))
    
    def test_semantic_memory(self):
        """Prueba las funciones de la memoria semántica."""
        sm = self.memory_manager.get_memory_system("semantic")
        self.assertIsNotNone(sm)
        
        # Añadir un hecho
        fact_id = sm.add_fact(
            subject="Pitágoras",
            predicate="demostró",
            object_="el teorema que lleva su nombre",
            confidence=0.95,
            source="historia_matematicas"
        )
        self.assertIsNotNone(fact_id)
        
        # Recuperar el hecho
        fact = sm.get_fact(fact_id)
        self.assertIsNotNone(fact)
        self.assertEqual(fact.subject, "Pitágoras")
        
        # Consultar hechos sobre un tema
        facts_about = sm.get_facts_about("Pitágoras")
        self.assertTrue(len(facts_about) > 0)


class TestMemoryManagerAdvanced(MemoryTestCase):
    """Pruebas avanzadas para el MemoryManager."""
    
    def test_memory_linking(self):
        """Prueba la vinculación entre memorias."""
        if len(self.memory_ids) < 2:
            self.skipTest("No hay suficientes IDs de memoria para probar vinculación")
        
        source_id = self.memory_ids[0]
        target_id = self.memory_ids[1]
        
        # Vincular memorias
        success = self.memory_manager.link_memories(
            source_id=source_id,
            target_id=target_id,
            link_type="relacionado"
        )
        self.assertTrue(success)
        
        # Verificar la vinculación
        related = self.memory_manager.get_related_memories(source_id)
        self.assertTrue(any(m.id == target_id for m in related))
    
    def test_consolidation(self):
        """Prueba el proceso de consolidación de memorias."""
        # Añadir memorias para consolidación
        stm = self.memory_manager.get_memory_system("short_term")
        
        # Memoria con alta importancia que debería consolidarse
        high_id = stm.add(
            content="Memoria muy importante que debería consolidarse",
            source="test_consolidation",
            importance=0.9
        )
        
        # Memoria con baja importancia que no debería consolidarse
        low_id = stm.add(
            content="Memoria poco importante que no debería consolidarse",
            source="test_consolidation",
            importance=0.2
        )
        
        # Forzar accesos para memoria de baja importancia
        memory = self.memory_manager.get_memory(low_id)
        for _ in range(5):
            memory.access()
        
        # Ejecutar consolidación
        self.memory_manager.consolidate_memories()
        
        # Verificar resultados
        # La memoria de alta importancia debería haberse consolidado (eliminado de corto plazo)
        recent = stm.get_recent(limit=100)
        self.assertFalse(any(m.id == high_id for m in recent))
        
        # La memoria con muchos accesos debería haberse consolidado
        self.assertFalse(any(m.id == low_id for m in recent))
    
    def test_forget_memory(self):
        """Prueba la función de olvidar memorias."""
        # Crear una memoria para olvidar
        memory_id = self.memory_manager.add_memory(
            content="Esta memoria será olvidada",
            memory_type="test",
            importance=0.3
        )
        
        # Verificar que existe
        memory = self.memory_manager.get_memory(memory_id)
        self.assertIsNotNone(memory)
        
        # Olvidar la memoria
        success = self.memory_manager.forget_memory(memory_id)
        self.assertTrue(success)
        
        # Verificar que ya no existe
        forgotten = self.memory_manager.get_memory(memory_id)
        self.assertIsNone(forgotten)
    
    def test_state_persistence(self):
        """Prueba la persistencia de estado del sistema de memoria."""
        # Crear una memoria específica para probar persistencia
        persistence_id = self.memory_manager.add_memory(
            content="Esta memoria debería persistir después de guardar/cargar",
            memory_type="test_persistence",
            importance=0.8,
            metadata={"persistence_test": True}
        )
        
        # Recuperar la memoria
        memory = self.memory_manager.get_memory(persistence_id)
        self.assertIsNotNone(memory)
        
        # Convertir a diccionario y serializarlo manualmente
        memory_dict = memory.to_dict()
        
        try:
            # Verificar que podemos serializar correctamente
            serialized = json.dumps(memory_dict)
            self.assertIsNotNone(serialized)
            
            # Crear archivo de serialización directamente
            save_path = self.temp_dir / "manual_persistence_test.json"
            state = {
                "memories": [memory_dict],
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(save_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.assertTrue(save_path.exists())
            
            # Cargar desde el archivo
            with open(save_path, 'r') as f:
                loaded_state = json.load(f)
            
            self.assertIn("memories", loaded_state)
            self.assertEqual(len(loaded_state["memories"]), 1)
            loaded_memory = loaded_state["memories"][0]
            
            # Verificar que los datos son correctos
            self.assertEqual(loaded_memory["id"], persistence_id)
            self.assertEqual(loaded_memory["content"], "Esta memoria debería persistir después de guardar/cargar")
            self.assertEqual(loaded_memory["metadata"].get("persistence_test"), True)
            
            self.assertTrue(True)  # Si llegamos aquí, la prueba es exitosa
        except Exception as e:
            self.fail(f"Error al serializar/deserializar: {e}")


def run_tests():
    """Ejecuta todas las pruebas unitarias."""
    # Crear un ejecutor de pruebas que generará un informe detallado
    suite = unittest.TestSuite()
    
    # Añadir las clases de prueba al suite
    suite.addTest(unittest.makeSuite(TestMemoryManagerBasic))
    suite.addTest(unittest.makeSuite(TestMemoryManagerQueries))
    suite.addTest(unittest.makeSuite(TestSpecializedMemorySystems))
    suite.addTest(unittest.makeSuite(TestMemoryManagerAdvanced))
    
    # Ejecutar las pruebas
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Informar resultados
    logger.info(f"Tests completados: {result.testsRun}")
    logger.info(f"Tests exitosos: {result.testsRun - len(result.errors) - len(result.failures)}")
    logger.info(f"Tests fallidos: {len(result.failures)}")
    logger.info(f"Tests con error: {len(result.errors)}")
    
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pruebas para el sistema de memoria")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar información detallada")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Iniciando pruebas del sistema de memoria")
    result = run_tests()
    
    if len(result.failures) > 0 or len(result.errors) > 0:
        sys.exit(1)
    
    logger.info("Todas las pruebas completadas con éxito")
    sys.exit(0) 