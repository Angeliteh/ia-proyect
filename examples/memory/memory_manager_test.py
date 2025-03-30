#!/usr/bin/env python
"""
Memory Manager Test

Este script prueba las funcionalidades del nuevo MemoryManager, demostrando
su capacidad para coordinar diferentes tipos de memoria y proporcionar una
interfaz unificada.
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime, timedelta
import time
import random
from pathlib import Path
import shutil

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("memory_manager_test.log", mode="w")
    ]
)
logger = logging.getLogger("memory_manager_test")

# Añadir la ruta del proyecto al PATH
current_dir = os.path.dirname(os.path.abspath(__file__))  # examples/memory
example_dir = os.path.dirname(current_dir)  # examples
project_dir = os.path.dirname(example_dir)  # raíz del proyecto
sys.path.insert(0, project_dir)

try:
    # Importar módulos del sistema de memoria
    from memory.core.memory_manager import MemoryManager
    from memory.storage.in_memory_storage import InMemoryStorage
    from memory.processors.embedder import Embedder
    from memory.processors.summarizer import Summarizer
    
    logger.info("Módulos de memoria importados correctamente")
    USING_REAL_MODULES = True
except ImportError as e:
    logger.error(f"Error al importar módulos: {e}")
    logger.error("Verifica que el módulo memory.core.memory_manager existe")
    sys.exit(1)

# Crear directorio temporal para pruebas persistentes
def setup_temp_dir():
    """Crear un directorio temporal para las pruebas."""
    temp_dir = Path(current_dir) / "temp_memory_test"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    logger.info(f"Directorio temporal creado: {temp_dir}")
    return temp_dir

def cleanup_temp_dir(temp_dir, memory_manager=None):
    """
    Elimina el directorio temporal creado para las pruebas.
    
    Args:
        temp_dir: Ruta al directorio temporal
        memory_manager: Instancia de MemoryManager para cerrar sus conexiones (opcional)
    """
    try:
        # Cerrar todas las conexiones a bases de datos antes de eliminar
        if memory_manager is not None:
            # Cerrar conexiones de bases de datos especializadas
            for memory_type, memory_system in memory_manager._specialized_memories.items():
                if hasattr(memory_system, 'storage') and hasattr(memory_system.storage, 'conn'):
                    try:
                        memory_system.storage.conn.close()
                        logger.info(f"Conexión cerrada para {memory_type}")
                    except Exception as e:
                        logger.warning(f"Error al cerrar conexión para {memory_type}: {e}")
        
        # Esperar un momento para asegurar que los archivos se liberen
        time.sleep(1)
        
        # Borrar el directorio
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Directorio temporal eliminado: {temp_dir}")
    except Exception as e:
        logger.error(f"Error al eliminar directorio temporal: {e}")
        # Intentar listar los archivos que no se pudieron eliminar
        try:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    logger.error(f"  No se pudo eliminar: {os.path.join(root, file)}")
        except:
            pass

# Datos de muestra para pruebas
def generate_sample_memories(memory_manager):
    """Generar datos de muestra para las pruebas."""
    
    # Hechos (para memoria semántica)
    facts = [
        {
            "content": {
                "subject": "Python",
                "predicate": "is_a",
                "object": "programming language"
            },
            "memory_type": "fact",
            "importance": 0.8,
            "metadata": {
                "confidence": 1.0,
                "source": "official documentation"
            }
        },
        {
            "content": {
                "subject": "Python",
                "predicate": "created_by",
                "object": "Guido van Rossum"
            },
            "memory_type": "fact",
            "importance": 0.7,
            "metadata": {
                "confidence": 1.0,
                "source": "official documentation"
            }
        },
        {
            "content": {
                "subject": "Python",
                "predicate": "version",
                "object": "3.9"
            },
            "memory_type": "fact",
            "importance": 0.6,
            "metadata": {
                "confidence": 0.9,
                "source": "user input"
            }
        }
    ]
    
    # Eventos (para memoria episódica)
    events = [
        {
            "content": "User asked about Python's creator",
            "memory_type": "interaction",
            "importance": 0.5,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "episode_title": "Python Information Session"
            }
        },
        {
            "content": "System provided information about Python",
            "memory_type": "interaction",
            "importance": 0.5,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "episode_title": "Python Information Session"
            }
        },
        {
            "content": "User requested code example",
            "memory_type": "interaction",
            "importance": 0.6,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "episode_title": "Python Information Session"
            }
        }
    ]
    
    # Conceptos (para memoria a largo plazo)
    concepts = [
        {
            "content": "Python is known for its readability and simple syntax",
            "memory_type": "concept",
            "importance": 0.9,
            "metadata": {
                "category": "programming language",
                "tags": ["Python", "syntax", "readability"]
            }
        },
        {
            "content": "Python supports multiple programming paradigms",
            "memory_type": "concept",
            "importance": 0.8,
            "metadata": {
                "category": "programming language",
                "tags": ["Python", "paradigms", "OOP", "functional"]
            }
        }
    ]
    
    # Datos generales (para memoria a corto plazo)
    general_data = [
        {
            "content": "The weather today is sunny with a high of 75°F",
            "memory_type": "general",
            "importance": 0.2,
            "metadata": {
                "category": "weather",
                "timestamp": datetime.now().isoformat()
            }
        },
        {
            "content": "Remember to check the documentation for more information",
            "memory_type": "general",
            "importance": 0.3,
            "metadata": {
                "category": "reminder",
                "timestamp": datetime.now().isoformat()
            }
        }
    ]
    
    return facts + events + concepts + general_data

def run_basic_tests(memory_manager):
    """Ejecutar pruebas básicas del MemoryManager."""
    logger.info("=== INICIANDO PRUEBAS BÁSICAS ===")
    
    # Verificar inicialización correcta
    logger.info(f"MemoryManager inicializado con {len(memory_manager._specialized_memories)} subsistemas de memoria")
    
    # Generar datos de prueba
    sample_memories = generate_sample_memories(memory_manager)
    memory_ids = []
    
    # Añadir memorias al sistema
    logger.info("Añadiendo memorias al sistema...")
    for sample in sample_memories:
        memory_id = memory_manager.add_memory(
            content=sample["content"],
            memory_type=sample["memory_type"],
            importance=sample["importance"],
            metadata=sample["metadata"]
        )
        memory_ids.append(memory_id)
        logger.info(f"  Memoria añadida: {memory_id} (tipo: {sample['memory_type']})")
    
    # Verificar que se hayan guardado correctamente
    logger.info("Verificando almacenamiento de memorias...")
    for memory_id in memory_ids:
        memory = memory_manager.get_memory(memory_id)
        if memory:
            logger.info(f"  Memoria recuperada: {memory_id} (tipo: {memory.memory_type})")
        else:
            logger.error(f"  Error: No se pudo recuperar la memoria {memory_id}")
    
    # Probar consultas básicas
    logger.info("Probando consultas básicas...")
    
    # Consultar por tipo
    facts = memory_manager.query_memories(memory_type="fact")
    logger.info(f"  Consulta por tipo 'fact': {len(facts)} resultados")
    
    # Consultar por importancia
    important = memory_manager.query_memories(min_importance=0.7)
    logger.info(f"  Consulta por importancia ≥ 0.7: {len(important)} resultados")
    
    # Consultar por tipo de memoria especializada
    stm_memories = memory_manager.query_memories(target_memory_system="short_term")
    logger.info(f"  Consulta a memoria de corto plazo: {len(stm_memories)} resultados")
    
    # Probar vinculación de memorias
    if len(memory_ids) >= 2:
        logger.info("Probando vinculación de memorias...")
        source_id = memory_ids[0]
        target_id = memory_ids[1]
        
        result = memory_manager.link_memories(source_id, target_id, "related_to")
        logger.info(f"  Vinculación de {source_id} a {target_id}: {'Exitosa' if result else 'Fallida'}")
        
        related = memory_manager.get_related_memories(source_id)
        logger.info(f"  Memorias relacionadas con {source_id}: {len(related)} resultados")
    
    # Probar actualización de importancia
    if memory_ids:
        logger.info("Probando actualización de importancia...")
        test_id = memory_ids[0]
        old_importance = memory_manager.get_memory(test_id).importance
        new_importance = min(1.0, old_importance + 0.2)
        
        result = memory_manager.update_memory_importance(test_id, new_importance)
        logger.info(f"  Actualización de importancia para {test_id}: {'Exitosa' if result else 'Fallida'}")
        logger.info(f"  Importancia anterior: {old_importance}, Nueva: {memory_manager.get_memory(test_id).importance}")
    
    # Obtener estadísticas
    logger.info("Obteniendo estadísticas del sistema de memoria...")
    stats = memory_manager.get_statistics()
    logger.info(f"  Estadísticas: {json.dumps(stats, indent=2)}")
    
    logger.info("=== PRUEBAS BÁSICAS COMPLETADAS ===\n")
    return memory_ids

def run_advanced_tests(memory_manager, memory_ids):
    """Ejecutar pruebas avanzadas del MemoryManager."""
    logger.info("=== INICIANDO PRUEBAS AVANZADAS ===")
    
    # Probar consolidación de memoria
    logger.info("Probando consolidación de memoria...")
    # Incrementar el contador de acceso para simular actividad
    if memory_ids:
        for _ in range(5):
            random_id = random.choice(memory_ids)
            memory = memory_manager.get_memory(random_id)
            logger.info(f"  Accediendo a memoria {random_id} (accesos: {memory.access_count})")
    
    # Ejecutar consolidación
    memory_manager.consolidate_memories()
    logger.info("  Consolidación de memoria ejecutada")
    
    # Resumir memorias
    logger.info("Probando resumir memorias...")
    all_memories = memory_manager.query_memories(limit=10)
    summary = memory_manager.summarize_memories(all_memories, max_length=200)
    logger.info(f"  Resumen generado ({len(summary)} caracteres): {summary}")
    
    # Simular olvido
    if memory_ids:
        logger.info("Probando olvidar memoria...")
        forget_id = memory_ids.pop()
        result = memory_manager.forget_memory(forget_id)
        logger.info(f"  Olvido de memoria {forget_id}: {'Exitoso' if result else 'Fallido'}")
        
        # Verificar que se haya olvidado
        forgotten = memory_manager.get_memory(forget_id)
        if forgotten:
            logger.error(f"  Error: La memoria {forget_id} no se olvidó correctamente")
        else:
            logger.info(f"  La memoria {forget_id} se olvidó correctamente")
    
    # Probar limpieza de memoria a corto plazo
    logger.info("Probando limpieza de memoria a corto plazo...")
    memory_manager.clear_short_term_memory()
    stm_memories = memory_manager.query_memories(target_memory_system="short_term")
    logger.info(f"  Memoria a corto plazo después de limpieza: {len(stm_memories)} elementos")
    
    logger.info("=== PRUEBAS AVANZADAS COMPLETADAS ===\n")

def run_persistence_tests(memory_manager, temp_dir):
    """Ejecutar pruebas de persistencia del MemoryManager."""
    logger.info("=== INICIANDO PRUEBAS DE PERSISTENCIA ===")
    
    # Añadir algunas memorias para la prueba
    logger.info("Añadiendo memorias para prueba de persistencia...")
    persistence_memories = [
        {
            "content": "This is a test memory for persistence",
            "memory_type": "general",
            "importance": 0.9,
            "metadata": {"test": "persistence"}
        },
        {
            "content": {
                "subject": "MemoryManager",
                "predicate": "supports",
                "object": "persistence"
            },
            "memory_type": "fact",
            "importance": 0.8,
            "metadata": {"test": "persistence"}
        }
    ]
    
    persistence_ids = []
    for mem in persistence_memories:
        memory_id = memory_manager.add_memory(
            content=mem["content"],
            memory_type=mem["memory_type"],
            importance=mem["importance"],
            metadata=mem["metadata"]
        )
        persistence_ids.append(memory_id)
        logger.info(f"  Memoria añadida para persistencia: {memory_id}")
    
    # Guardar estado
    save_path = temp_dir / "test_memory_state.json"
    result = memory_manager.save_state(save_path)
    logger.info(f"  Guardado de estado: {'Exitoso' if result else 'Fallido'}")
    
    # Verificar que el archivo existe
    if save_path.exists():
        logger.info(f"  Archivo de estado creado: {save_path} ({save_path.stat().st_size} bytes)")
    else:
        logger.error(f"  Error: Archivo de estado no creado: {save_path}")
    
    # Crear nuevo memory manager y cargar estado
    logger.info("Creando nuevo MemoryManager y cargando estado guardado...")
    new_manager = MemoryManager(data_dir=temp_dir)
    load_result = new_manager.load_state(save_path)
    logger.info(f"  Carga de estado: {'Exitosa' if load_result else 'Fallida'}")
    
    # Verificar que las memorias se cargaron
    logger.info("Verificando memorias cargadas...")
    for memory_id in persistence_ids:
        memory = new_manager.get_memory(memory_id)
        if memory:
            logger.info(f"  Memoria recuperada: {memory_id} (tipo: {memory.memory_type})")
        else:
            logger.error(f"  Error: No se pudo recuperar la memoria {memory_id}")
    
    logger.info("=== PRUEBAS DE PERSISTENCIA COMPLETADAS ===\n")

def main():
    """Función principal de ejecución de pruebas."""
    # Configuración inicial
    parser = argparse.ArgumentParser(description="Pruebas del sistema de memoria")
    parser.add_argument("--skip-advanced", action="store_true", help="Omitir pruebas avanzadas")
    parser.add_argument("--skip-persistence", action="store_true", help="Omitir pruebas de persistencia")
    args = parser.parse_args()
    
    # Crear directorio temporal para tests
    temp_dir = setup_temp_dir()
    
    # Inicializar MemoryManager
    memory_manager = None
    try:
        memory_manager = MemoryManager(
            config={
                "use_long_term_memory": True,
                "use_episodic_memory": True,
                "use_semantic_memory": True,
                "short_term_memory": {
                    "retention_minutes": 5,
                    "capacity": 100
                }
            },
            data_dir=temp_dir
        )
        
        # Ejecutar pruebas básicas
        print("\n=== Pruebas Básicas ===")
        run_basic_tests(memory_manager)
        
        # Pruebas avanzadas (opcional)
        if not args.skip_advanced:
            print("\n=== Pruebas Avanzadas ===")
            memory_ids = generate_sample_memories(memory_manager)
            run_advanced_tests(memory_manager, memory_ids)
        
        # Pruebas de persistencia (opcional)
        if not args.skip_persistence:
            print("\n=== Pruebas de Persistencia ===")
            run_persistence_tests(memory_manager, temp_dir)
        
        print("\n✅ Todas las pruebas completadas con éxito!")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Limpiar directorio temporal
        cleanup_temp_dir(temp_dir, memory_manager)

if __name__ == "__main__":
    main() 