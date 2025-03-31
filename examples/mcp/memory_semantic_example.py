"""
Ejemplo de búsqueda semántica con el servidor de memoria MCP.

Este ejemplo demuestra:
1. Cómo configurar un servidor de memoria MCP con capacidades de búsqueda semántica
2. Cómo crear memorias y generar embeddings
3. Cómo realizar búsquedas semánticas basadas en vectores
4. Cómo comparar búsquedas por texto vs búsquedas semánticas

Para ejecutar el ejemplo:
    python examples/mcp/memory_semantic_example.py
    
Requisitos adicionales para embeddings avanzados:
    pip install sentence-transformers
"""

import asyncio
import logging
import sys
import os
import json
import uuid
import hashlib
import importlib.util
from typing import Dict, Any, Optional, List, Callable, Union

# Aseguramos que el directorio raíz del proyecto esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("memory_semantic_example")

# Importamos los componentes necesarios
try:
    from mcp.core import MCPMessage, MCPResponse, MCPAction, MCPResource, MCPRegistry
    from mcp_servers.memory import MemoryServer
    from mcp.clients import SimpleDirectClient
except ImportError as e:
    logger.error(f"Error importando módulos: {e}")
    sys.exit(1)


def print_section_header(title: str) -> None:
    """Imprime un encabezado de sección con formato."""
    separator = "=" * 80
    logger.info("\n" + separator)
    logger.info(f"  {title}")
    logger.info(separator)


def simple_embedding_function(text: str, embedding_dim: int = 768) -> List[float]:
    """
    Función de embedding simple basada en hash de palabras.
    
    Esta función es solo para demostración y no debe usarse en producción.
    En un entorno real se usaría un modelo como sentence-transformers.
    
    Args:
        text: Texto a convertir en embedding
        embedding_dim: Dimensión del vector resultante
        
    Returns:
        Vector de embedding como lista de floats
    """
    words = text.lower().split()
    vector = [0.0] * embedding_dim
    
    for i, word in enumerate(words):
        # Hash de la palabra para generar un valor pseudo-aleatorio
        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
        
        # Distribuir el valor en varias posiciones del vector
        for j in range(min(5, embedding_dim)):
            pos = (hash_val + j) % embedding_dim
            vector[pos] += (1.0 / (i + 1)) * (0.9 ** j)
    
    # Normalizar el vector
    norm = sum(v**2 for v in vector) ** 0.5
    if norm > 0:
        vector = [v / norm for v in vector]
    
    return vector


def get_embedding_function() -> tuple[Callable, int, str]:
    """
    Obtiene la mejor función de embedding disponible.
    
    Returns:
        Tupla con (función_embedding, dimensión, descripción)
    """
    # Intentar cargar sentence-transformers si está disponible
    if importlib.util.find_spec("sentence_transformers"):
        try:
            from sentence_transformers import SentenceTransformer
            
            # Usar un modelo pequeño para el ejemplo
            model_name = 'paraphrase-MiniLM-L3-v2'  # 384 dimensiones, rápido
            
            logger.info(f"Cargando modelo de embeddings: {model_name}")
            model = SentenceTransformer(model_name)
            
            # Obtener dimensión del modelo
            embedding_dim = model.get_sentence_embedding_dimension()
            
            # Función wrapper para el modelo
            def model_embedding_function(text: str, embedding_dim: int = embedding_dim) -> List[float]:
                embedding = model.encode(text)
                return embedding.tolist()
            
            return model_embedding_function, embedding_dim, f"SentenceTransformer ({model_name})"
        except Exception as e:
            logger.warning(f"Error al cargar sentence-transformers: {str(e)}")
            logger.warning("Se usará la función de embedding simple")
    else:
        logger.warning("Sentence-transformers no está instalado")
        logger.warning("Para mejores resultados, instale: pip install sentence-transformers")
    
    # Usar función simple como fallback
    return simple_embedding_function, 256, "Embedding simple (hash)"


async def run_example():
    """Ejecuta el ejemplo de búsqueda semántica."""
    # Crear un directorio temporal para los datos de memoria
    data_dir = os.path.join(project_root, "examples/mcp/data/memory")
    os.makedirs(data_dir, exist_ok=True)
    
    # Obtener la mejor función de embedding disponible
    embedding_function, embedding_dim, embedding_type = get_embedding_function()
    logger.info(f"Usando: {embedding_type} con dimensión {embedding_dim}")
    
    # Crear un servidor de memoria con capacidad para búsqueda semántica
    server = MemoryServer(
        name="semantic_memory_example",
        description="Servidor de memoria con búsqueda semántica",
        data_dir=data_dir,
        embedding_function=embedding_function,
        embedding_dim=embedding_dim
    )
    
    logger.info(f"Servidor de memoria semántica creado: {server.name}")
    
    # Crear un cliente directo que se conecte al servidor
    client = SimpleDirectClient(server)
    
    try:
        # Conectar al servidor
        client.connect()
        logger.info("Cliente conectado al servidor de memoria")
        
        # 1. Verificar capacidades de vectorización
        print_section_header("CAPACIDADES DE VECTORIZACIÓN")
        
        info_message = MCPMessage(
            action=MCPAction.GET,
            resource_type=MCPResource.SYSTEM,
            resource_path="/info"
        )
        
        info_response = await client.send_message_async(info_message)
        if info_response.success:
            vector_search = info_response.data.get('vector_search', False)
            embedding_dim = info_response.data.get('embedding_dim')
            
            if vector_search:
                logger.info(f"✓ Búsqueda vectorial disponible con dimensión: {embedding_dim}")
            else:
                logger.error("✗ Búsqueda vectorial no disponible")
                return
        else:
            logger.error(f"✗ Error: {info_response.error.message if hasattr(info_response, 'error') else 'Error desconocido'}")
            return
        
        # 2. Crear memorias para el ejemplo
        print_section_header("CREAR MEMORIAS PARA EJEMPLO")
        
        # Lista de contenidos de memoria para el ejemplo (ampliada para mejor cobertura)
        test_memories = [
            {
                "content": "Python es un lenguaje de programación interpretado cuya filosofía hace hincapié en una sintaxis que favorezca un código legible",
                "memory_type": "fact",
                "importance": 0.8,
                "metadata": {"category": "programming", "tags": ["python", "language"]}
            },
            {
                "content": "Los gatos son animales domésticos que pertenecen a la familia de los félidos",
                "memory_type": "fact",
                "importance": 0.7,
                "metadata": {"category": "animals", "tags": ["cats", "pets"]}
            },
            {
                "content": "El aprendizaje automático es una rama de la inteligencia artificial que permite que las máquinas aprendan sin ser programadas explícitamente",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["machine learning", "ai"]}
            },
            {
                "content": "JavaScript es un lenguaje de programación interpretado, dialecto del estándar ECMAScript. Se define como orientado a objetos, basado en prototipos, imperativo, débilmente tipado y dinámico",
                "memory_type": "fact",
                "importance": 0.8,
                "metadata": {"category": "programming", "tags": ["javascript", "language"]}
            },
            {
                "content": "Los perros son mamíferos carnívoros de la familia de los cánidos que se caracterizan por su lealtad",
                "memory_type": "fact",
                "importance": 0.7,
                "metadata": {"category": "animals", "tags": ["dogs", "pets"]}
            },
            {
                "content": "La inteligencia artificial es la simulación de procesos de inteligencia humana por sistemas informáticos",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["artificial intelligence", "ai"]}
            },
            {
                "content": "Un vector de embedding es una representación numérica de un texto que captura su significado semántico",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["embeddings", "nlp"]}
            },
            {
                "content": "Las redes neuronales convolucionales (CNN) son especialmente efectivas para el procesamiento de imágenes y visión por computadora",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["neural networks", "deep learning", "computer vision"]}
            },
            {
                "content": "PHP y JavaScript son lenguajes muy utilizados en el desarrollo web, donde PHP se ejecuta en el servidor y JavaScript en el navegador",
                "memory_type": "fact",
                "importance": 0.8,
                "metadata": {"category": "programming", "tags": ["php", "javascript", "web development"]}
            },
            {
                "content": "Los transformers son arquitecturas de redes neuronales diseñadas para procesar datos secuenciales como texto, utilizando mecanismos de atención",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["transformers", "nlp", "attention"]}
            },
            {
                "content": "Para representar texto en modelos de IA, primero se tokeniza el texto y luego se convierte en vectores numéricos llamados embeddings",
                "memory_type": "fact",
                "importance": 0.9,
                "metadata": {"category": "ai", "tags": ["embeddings", "tokenization", "nlp"]}
            }
        ]
        
        memory_ids = []
        
        # Crear memorias con embeddings
        for memory_data in test_memories:
            create_memory_message = MCPMessage(
                action=MCPAction.CREATE,
                resource_type=MCPResource.MEMORY,
                resource_path="/",
                data={
                    "content": memory_data["content"],
                    "memory_type": memory_data["memory_type"],
                    "importance": memory_data["importance"],
                    "metadata": memory_data["metadata"],
                    "generate_embedding": True  # Generar embedding automáticamente
                }
            )
            
            create_response = await client.send_message_async(create_memory_message)
            
            if create_response.success:
                memory_id = create_response.data.get('id')
                memory_ids.append(memory_id)
                embedding_status = "✓ Con embedding" if create_response.data.get('embedding_generated') else "✗ Sin embedding"
                logger.info(f"Memoria creada: {memory_id} - {embedding_status}")
                logger.info(f"  Contenido: {memory_data['content'][:50]}...")
            else:
                logger.error(f"✗ Error: {create_response.error.message}")
        
        # 3. Obtener un embedding para un texto específico
        print_section_header("GENERAR EMBEDDING")
        
        text_to_embed = "Cómo funciona el aprendizaje profundo en la IA"
        
        embedding_message = MCPMessage(
            action=MCPAction.GET,
            resource_type="vector",
            resource_path="/",
            data={"text": text_to_embed}
        )
        
        embedding_response = await client.send_message_async(embedding_message)
        
        if embedding_response.success:
            embedding = embedding_response.data.get('embedding')
            dimensions = embedding_response.data.get('dimensions')
            logger.info(f"Embedding generado para: '{text_to_embed}'")
            logger.info(f"Dimensiones: {dimensions}")
            logger.info(f"Primeros 5 valores: {embedding[:5]}")
        else:
            logger.error(f"✗ Error: {embedding_response.error.message}")
        
        # 4. Realizar una búsqueda estándar (por palabras clave)
        print_section_header("BÚSQUEDA ESTÁNDAR")
        
        keyword_search_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "query": "inteligencia",
                "limit": 5
            }
        )
        
        keyword_response = await client.send_message_async(keyword_search_message)
        
        if keyword_response.success:
            results = keyword_response.data.get('results', [])
            count = keyword_response.data.get('count', 0)
            logger.info(f"Resultados de búsqueda por palabra clave 'inteligencia': {count}")
            
            for i, memory in enumerate(results):
                logger.info(f"  {i+1}. {memory['content'][:80]}...")
        else:
            logger.error(f"✗ Error: {keyword_response.error.message}")
        
        # 5. Realizar una búsqueda semántica 
        print_section_header("BÚSQUEDA SEMÁNTICA")
        
        semantic_search_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type=MCPResource.MEMORY,
            resource_path="/",
            data={
                "query": "inteligencia",
                "limit": 5,
                "semantic": True,
                "threshold": 0.2
            }
        )
        
        semantic_response = await client.send_message_async(semantic_search_message)
        
        if semantic_response.success:
            results = semantic_response.data.get('results', [])
            count = semantic_response.data.get('count', 0)
            semantic = semantic_response.data.get('semantic', False)
            logger.info(f"Resultados de búsqueda semántica por 'inteligencia': {count}")
            logger.info(f"Modo semántico: {'✓ Activo' if semantic else '✗ Inactivo'}")
            
            for i, memory in enumerate(results):
                relevance = memory.get('relevance', 0)
                logger.info(f"  {i+1}. Relevancia: {relevance:.2f} - {memory['content'][:80]}...")
        else:
            logger.error(f"✗ Error: {semantic_response.error.message}")
        
        # 6. Realizar búsqueda vectorial directa (más precisa)
        print_section_header("BÚSQUEDA VECTORIAL DIRECTA")
        
        vector_search_message = MCPMessage(
            action=MCPAction.SEARCH,
            resource_type="vector",
            resource_path="/",
            data={
                "query": "Cómo funcionan las redes neuronales para procesar información",
                "limit": 5,
                "threshold": 0.15
            }
        )
        
        vector_response = await client.send_message_async(vector_search_message)
        
        if vector_response.success:
            results = vector_response.data.get('results', [])
            count = vector_response.data.get('count', 0)
            logger.info(f"Resultados de búsqueda vectorial: {count}")
            
            for i, memory in enumerate(results):
                similarity = memory.get('similarity', 0)
                logger.info(f"  {i+1}. Similitud: {similarity:.2f} - {memory['content'][:80]}...")
        else:
            logger.error(f"✗ Error: {vector_response.error.message}")
        
        # 7. Demostrar la diferencia entre búsqueda por palabras clave y semántica
        print_section_header("COMPARACIÓN: PALABRAS CLAVE VS SEMÁNTICA")
        
        comparison_queries = [
            "lenguajes para desarrollo web",
            "mascotas populares",
            "tecnologías de aprendizaje de máquina",
            "representación de datos para IA"
        ]
        
        for query in comparison_queries:
            logger.info(f"\nConsulta de prueba: '{query}'")
            
            # Búsqueda por palabras clave
            keyword_message = MCPMessage(
                action=MCPAction.SEARCH,
                resource_type=MCPResource.MEMORY,
                resource_path="/",
                data={"query": query, "limit": 3}
            )
            
            # Búsqueda semántica
            semantic_message = MCPMessage(
                action=MCPAction.SEARCH,
                resource_type="vector",
                resource_path="/",
                data={"query": query, "limit": 3, "threshold": 0.15}
            )
            
            keyword_response = await client.send_message_async(keyword_message)
            semantic_response = await client.send_message_async(semantic_message)
            
            # Mostrar resultados de búsqueda por palabras clave
            if keyword_response.success:
                results = keyword_response.data.get('results', [])
                logger.info(f"  Resultados por palabras clave ({len(results)}):")
                if results:
                    for i, memory in enumerate(results):
                        logger.info(f"    {i+1}. {memory['content'][:80]}...")
                else:
                    logger.info("    No se encontraron coincidencias exactas")
            
            # Mostrar resultados de búsqueda semántica
            if semantic_response.success:
                results = semantic_response.data.get('results', [])
                logger.info(f"  Resultados semánticos ({len(results)}):")
                if results:
                    for i, memory in enumerate(results):
                        similarity = memory.get('similarity', 0)
                        logger.info(f"    {i+1}. Similitud: {similarity:.2f} - {memory['content'][:80]}...")
                else:
                    logger.info("    No se encontraron memorias semánticamente similares")
        
        # 8. Ejemplo de uso práctico con un agente
        print_section_header("EJEMPLO PRÁCTICO CON AGENTE")
        
        class SemanticMemoryAgent:
            def __init__(self, memory_client):
                self.memory_client = memory_client
                self.name = "SemanticMemoryAgent"
                
            async def remember(self, content, memory_type="observation", importance=0.5, metadata=None):
                """Almacena una nueva memoria con embedding."""
                metadata = metadata or {}
                metadata["agent"] = self.name
                
                create_message = MCPMessage(
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
                
                response = await self.memory_client.send_message_async(create_message)
                if response.success:
                    return response.data.get('id')
                return None
                
            async def recall_semantic(self, query, limit=3, threshold=0.25):
                """Realiza una búsqueda semántica."""
                search_message = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type="vector",
                    resource_path="/",
                    data={
                        "query": query,
                        "limit": limit,
                        "threshold": threshold
                    }
                )
                
                response = await self.memory_client.send_message_async(search_message)
                if response.success:
                    return response.data.get('results', [])
                return []
            
            async def recall_by_keyword(self, query, limit=3):
                """Realiza una búsqueda por palabras clave."""
                search_message = MCPMessage(
                    action=MCPAction.SEARCH,
                    resource_type=MCPResource.MEMORY,
                    resource_path="/",
                    data={
                        "query": query,
                        "limit": limit
                    }
                )
                
                response = await self.memory_client.send_message_async(search_message)
                if response.success:
                    return response.data.get('results', [])
                return []
            
            async def answer_question(self, question):
                """Responde a una pregunta usando memoria semántica y por palabras clave."""
                logger.info(f"Pregunta: {question}")
                
                # Estrategia combinada: primero semántica, luego keywords si no hay resultados
                memories = await self.recall_semantic(question, limit=3, threshold=0.2)
                
                # Si no hay resultados semánticos, probar con palabras clave
                if not memories:
                    logger.info("  No se encontraron resultados semánticos. Probando con palabras clave...")
                    memories = await self.recall_by_keyword(question, limit=3)
                
                if not memories:
                    return "No tengo información suficiente para responder a esa pregunta."
                
                # Construcción simple de respuesta basada en memorias recuperadas
                response = "Basado en lo que recuerdo:\n"
                
                for i, memory in enumerate(memories):
                    relevance = memory.get('relevance', memory.get('similarity', 0))
                    content = memory.get('content', '')
                    response += f"\n{i+1}. {content}"
                
                return response
        
        # Crear y usar un agente de memoria semántica
        agent = SemanticMemoryAgent(client)
        
        # El agente almacena un nuevo conocimiento
        new_fact = "Las redes neuronales convolucionales son especialmente efectivas para el procesamiento de imágenes en visión por computadora"
        
        memory_id = await agent.remember(
            content=new_fact,
            memory_type="fact",
            importance=0.9,
            metadata={"category": "ai", "tags": ["neural networks", "computer vision"]}
        )
        
        if memory_id:
            logger.info(f"✓ Agente almacenó un nuevo hecho: {memory_id}")
            
            # Realizar preguntas al agente
            questions = [
                "¿Qué tipo de redes neuronales se usan para visión por computadora?",
                "¿Cómo representamos datos para modelos de IA?",
                "¿Cuáles son algunos lenguajes de programación populares?"
            ]
            
            for question in questions:
                answer = await agent.answer_question(question)
                logger.info(f"\nRespuesta: {answer}")
        
        print_section_header("EJEMPLO COMPLETADO")
        logger.info("El ejemplo de búsqueda semántica se ha completado correctamente")
        
    except Exception as e:
        logger.error(f"Error en el ejemplo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Cerrar cliente
        client.disconnect()
        logger.info("Cliente desconectado")


if __name__ == "__main__":
    asyncio.run(run_example()) 