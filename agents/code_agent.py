"""
Code Agent module.

This agent specializes in code-related tasks, including:
- Code generation
- Code explanation
- Code review and improvement
- Bug fixing
- Answering programming questions
"""

import logging
import re
import os
import json
from typing import Dict, List, Any, Optional, Union

from .base import BaseAgent, AgentResponse
from models.core.model_manager import ModelManager

class CodeAgent(BaseAgent):
    """
    Agent specialized in code-related tasks.
    
    This agent can analyze, generate, explain, and improve code across
    various programming languages.
    
    Attributes:
        model_manager: The model manager for accessing AI models
        supported_languages: List of programming languages this agent supports
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the code agent.
        
        Args:
            agent_id: Unique identifier for the agent
            config: Configuration dictionary containing:
                - model_manager: Instance of ModelManager (optional)
                - default_model: Name of the default model to use (optional)
                - supported_languages: List of supported programming languages (optional)
        """
        super().__init__(agent_id, config)
        
        # Use the provided model manager or create a new one
        self.model_manager = config.get("model_manager")
        if not self.model_manager:
            self.model_manager = ModelManager()
            
        # Set the default model name - try to use models that are known to be available
        # Orden de preferencia: Gemini, modelos locales (Mistral, Phi), y luego otros
        preferred_model_order = [
            # Gemini primero
            "gemini-2.0-flash", "gemini-pro", "gemini-1.5-flash",
            # Modelos locales después
            "mistral-7b-instruct", "phi-2", "llama-2-7b-chat",
            # Otros modelos cloud como respaldo
            "claude-3-haiku-20240307", "gpt-3.5-turbo"
        ]
        
        # Usar el modelo especificado en la configuración, si existe
        self.model_name = config.get("model", None)
        
        # Si no se especificó un modelo, buscar uno disponible según la preferencia
        if not self.model_name:
            try:
                # Obtener la lista de modelos disponibles
                available_models = self.model_manager.list_available_models()
                available_model_names = [model["name"] for model in available_models]
                
                if available_model_names:
                    # Recorrer la lista de modelos preferidos y usar el primero que esté disponible
                    for model_name in preferred_model_order:
                        if model_name in available_model_names:
                            self.model_name = model_name
                            self.logger.info(f"Usando modelo preferido: {self.model_name}")
                            break
                    
                    # Si ningún modelo preferido está disponible, usar el primero de la lista
                    if not self.model_name:
                        self.model_name = available_model_names[0]
                        self.logger.info(f"Usando primer modelo disponible: {self.model_name}")
                else:
                    # Si no hay modelos disponibles, usar el primero de la lista de preferencias
                    self.model_name = preferred_model_order[0]
                    self.logger.warning(f"No se encontraron modelos disponibles, usando modelo por defecto: {self.model_name}")
                    
            except Exception as e:
                self.logger.warning(f"Error obteniendo modelos disponibles: {str(e)}")
                # Usar Gemini como fallback si hay error
                self.model_name = "gemini-2.0-flash"
                self.logger.warning(f"Usando modelo por defecto debido a error: {self.model_name}")
        
        self.logger.info(f"Code agent initialized with model: {self.model_name}")
        
        # Track supported languages
        self.supported_languages = config.get(
            "supported_languages", 
            ["python", "javascript", "typescript", "java", "c", "c++", "c#", "go", "rust", "sql"]
        )
        
        self.logger.info(f"Supported languages: {', '.join(self.supported_languages)}")
    
    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a code-related query.
        
        Args:
            query: The code-related query
            context: Optional context with:
                - code: Existing code to reference
                - language: Programming language 
                - task: Specific task (generate, explain, improve, fix)
                - use_memory: Boolean indicating if memory should be used (default: True)
                
        Returns:
            AgentResponse with the processed result
        """
        self.set_state("processing")
        context = context or {}
        
        # Debug logging if requested
        if context.get("debug_memory", False):
            self.logger.info(f"DEBUG: Procesando consulta con contexto: {context}")
            self.logger.info(f"DEBUG: ¿Tiene memoria configurada? {self.has_memory()}")
            if self.has_memory():
                memories = self.recall(query=query, limit=3)
                self.logger.info(f"DEBUG: Se encontraron {len(memories)} memorias relevantes para '{query}'")
        
        task = context.get("task", self._detect_task(query))
        language = context.get("language", self._detect_language(query, context.get("code", "")))
        code = context.get("code", "")
        
        self.logger.info(f"Processing code task: {task} (language: {language})")
        
        try:
            # Intentar cargar el modelo
            model = None
            model_info = None
            error_messages = []
            
            # Lista de modelos para intentar en orden de preferencia
            models_to_try = [self.model_name]
            
            # Si existe un modelo local Mistral, agregarlo como fallback
            mistral_path = "models/local/Mistral-7B-Instruct-v0.3.Q4_K_M.gguf"
            if os.path.exists(mistral_path):
                models_to_try.append("mistral-7b-instruct")
                self.logger.info("Se encontró modelo local Mistral, se usará como fallback")
            
            # Intentar modelos en orden
            for model_name in models_to_try:
                try:
                    self.logger.info(f"Intentando cargar modelo: {model_name}")
                    model, model_info = await self.model_manager.load_model(model_name)
                    self.logger.info(f"Modelo cargado correctamente: {model_name}")
                    # Actualizar el nombre del modelo utilizado
                    self.model_name = model_info.name
                    break
                except Exception as model_error:
                    error_message = f"No se pudo cargar el modelo {model_name}: {str(model_error)}"
                    self.logger.warning(error_message)
                    error_messages.append(error_message)
                    continue
            
            # Si no se pudo cargar ningún modelo
            if model is None:
                # Si estamos en modo orquestador o sistema, proporcionar una respuesta básica
                if context.get("from_orchestrator") or "system" in context.get("sender_id", ""):
                    return self._generate_basic_response(query, task, language, code)
                
                # Sino, propagar el error para que el usuario sepa qué pasó
                raise ValueError(f"No se pudo cargar ningún modelo. Errores: {'; '.join(error_messages)}")
            
            # Usar el método especializado para procesar con modelo y memoria
            # Explícitamente pasamos el flag use_memory del contexto
            use_memory = context.get("use_memory", True)
            memory_threshold = context.get("memory_threshold", 0.5)
            
            # Log para debugging
            if context.get("debug_memory", False):
                self.logger.info(f"DEBUG: use_memory={use_memory}, memory_threshold={memory_threshold}")
            
            result = await self._process_with_model(
                task=task, 
                language=language, 
                query=query, 
                context=context,
                use_memory=use_memory,
                memory_threshold=memory_threshold
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing code query: {str(e)}")
            self.set_state("error")
            
            # Intentar generar una respuesta básica si viene del orquestador
            if context.get("from_orchestrator") or "orchestrator" in context.get("sender_id", ""):
                try:
                    return self._generate_basic_response(query, task, language, code)
                except Exception as fallback_error:
                    self.logger.error(f"Error generando respuesta básica: {str(fallback_error)}")
            
            return AgentResponse(
                content=f"Error processing your code request: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "task": task,
                    "language": language
                }
            )
    
    def get_capabilities(self) -> List[str]:
        """
        Get a list of this agent's capabilities.
        
        Returns:
            List of capability strings
        """
        return [
            "code_generation",
            "code_explanation",
            "code_improvement",
            "bug_fixing",
            "code_review",
            "answer_programming_questions"
        ]
    
    def _detect_task(self, query: str) -> str:
        """
        Detect the type of code task from the query.
        
        Args:
            query: The query text
            
        Returns:
            Task type (generate, explain, improve, fix)
        """
        # Palabras clave que indican tipos de tarea
        task_keywords = {
            "generate": r"\bgenera\b|\bcrea\b|\bescribe\b|\bimplementa\b|\bprograma\b|\bescriba\b|\bhaz\b|\bhacer\b",
            "explain": r"\bexplica\b|\bcomenta\b|\bdocumenta\b|\bentender\b|\bentienda\b|\bque hace\b|\bcómo funciona\b",
            "improve": r"\bmejora\b|\boptimiza\b|\brefactoriza\b|\brefina\b|\benhance\b",
            "fix": r"\bcorrige\b|\barregla\b|\bsoluciona\b|\bfix\b|\bdebug\b|\berror\b|\bfalla\b|\bproblema\b"
        }
        
        # Comprobar si la consulta contiene palabras clave de tareas
        for task, pattern in task_keywords.items():
            if re.search(pattern, query, re.IGNORECASE):
                return task
                
        # Si contiene palabras clave relacionadas con código pero no con tareas específicas,
        # probablemente sea una solicitud de generación
        code_related = r"\bcódigo\b|\bprograma\b|\bfunción\b|\balgorithm\b|\bscript\b|\bprogramación\b"
        if re.search(code_related, query, re.IGNORECASE):
            return "generate"
            
        # Default a generación si no se detecta ninguna tarea específica
        return "generate"
    
    def _detect_language(self, query: str, code: str = "") -> str:
        """
        Detect the programming language from query or code.
        
        Args:
            query: The query text
            code: Existing code (if any)
            
        Returns:
            Detected language or default language
        """
        # Si hay código existente, intentar detectar el lenguaje de la sintaxis
        if code:
            # Verificar extensiones/sintaxis comunes
            if re.search(r"def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import|print\s*\(", code):
                return "python"
            elif re.search(r"function\s+\w+\s*\(|var\s+\w+\s*=|let\s+\w+\s*=|const\s+\w+\s*=", code):
                return "javascript"
            elif re.search(r"public\s+class|private\s+\w+|protected\s+\w+|import\s+java\.", code):
                return "java"
            # Más patrones para otros lenguajes...
        
        # Palabras clave que indican lenguajes de programación en la consulta
        language_keywords = {
            "python": r"\bpython\b|\bpy\b",
            "javascript": r"\bjavascript\b|\bjs\b",
            "typescript": r"\btypescript\b|\bts\b",
            "java": r"\bjava\b(?!\s*script)",
            "c#": r"\bc#\b|\.net\b|csharp\b",
            "c++": r"\bc\+\+\b|\bcpp\b",
            "c": r"\bc\s+code\b|\bc\s+program\b|\bin\s+c\b(?!\+)|\bc\b(?!\+|\#|\s*language)",
            "go": r"\bgo\b|\bgolang\b",
            "rust": r"\brust\b",
            "sql": r"\bsql\b"
        }
        
        # Palabras específicas que indican claramente un lenguaje
        if "script en Python" in query or "código Python" in query or "programa Python" in query:
            return "python"
        
        # Verificar palabras clave en la consulta
        for language, pattern in language_keywords.items():
            if re.search(pattern, query, re.IGNORECASE):
                return language
        
        # Verificar si la tarea menciona un lenguaje específico
        if "fibonacci" in query.lower() and "python" in query.lower():
            return "python"
            
        # Verificar si hay menciones específicas de bibliotecas o frameworks
        if any(lib in query.lower() for lib in ["pandas", "numpy", "matplotlib", "django", "flask"]):
            return "python"
        elif any(lib in query.lower() for lib in ["react", "vue", "angular", "node"]):
            return "javascript"
        
        # Default to Python para tareas de algoritmos básicos si no se especifica
        if any(word in query.lower() for word in ["algoritmo", "secuencia", "fibonacci", "factorial", "ordenamiento", "búsqueda"]):
            return "python"
        
        # Por defecto, devolver Python
        return "python"
    
    def _build_prompt(self, query: str, task: str, language: str, code: str = "") -> str:
        """
        Build a prompt for the code agent based on the task type.
        
        Args:
            query: The user query
            task: Type of task (generate, explain, improve, fix)
            language: Programming language to use
            code: Existing code (if any)
            
        Returns:
            Properly formatted prompt for the model
        """
        # Determinar si estamos usando un modelo local
        is_local_model = False
        try:
            model_info = self.model_manager.models_info.get(self.model_name)
            if model_info and model_info.local:
                is_local_model = True
                self.logger.info(f"Usando formato de prompt para modelo local: {self.model_name}")
        except Exception as e:
            self.logger.warning(f"Error al determinar si el modelo es local: {str(e)}")
        
        # Prompt base según el tipo de tarea
        if task == "generate":
            if is_local_model:
                # Prompt más simple y directo para modelos locales
                prompt = f"""<|im_start|>system
Eres un programador experto que genera código limpio, bien comentado y optimizado, siguiendo las mejores prácticas.
<|im_end|>
<|im_start|>user
Necesito que generes código en {language} para: {query}
<|im_end|>
<|im_start|>assistant
"""
            else:
                prompt = (
                    f"Eres un programador experto en {language}. "
                    f"Genera el código para: {query}\n\n"
                    f"Sé conciso y muestra solo el código con comentarios mínimos "
                    f"necesarios para entenderlo. Usa las mejores prácticas para {language}."
                )
        
        elif task == "explain":
            # El código a explicar debe estar presente
            if not code:
                code = "// No se proporcionó código para explicar"
            
            if is_local_model:
                prompt = f"""<|im_start|>system
Eres un programador experto que explica código de manera clara y concisa.
<|im_end|>
<|im_start|>user
Por favor explica el siguiente código en {language}:

```{language}
{code}
```

{query}
<|im_end|>
<|im_start|>assistant
"""
            else:
                prompt = (
                    f"Explica el siguiente código en {language}:\n\n"
                    f"```{language}\n{code}\n```\n\n"
                    f"Consulta adicional: {query}\n\n"
                    f"Proporciona una explicación clara y detallada de lo que hace el código."
                )
        
        elif task == "improve":
            if not code:
                code = f"// No se proporcionó código en {language} para mejorar"
            
            if is_local_model:
                prompt = f"""<|im_start|>system
Eres un programador experto que mejora código existente haciéndolo más eficiente, legible y siguiendo las mejores prácticas.
<|im_end|>
<|im_start|>user
Mejora el siguiente código en {language}:

```{language}
{code}
```

Instrucciones adicionales: {query}
<|im_end|>
<|im_start|>assistant
"""
            else:
                prompt = (
                    f"Mejora el siguiente código en {language}:\n\n"
                    f"```{language}\n{code}\n```\n\n"
                    f"Instrucciones para la mejora: {query}\n\n"
                    f"Proporciona el código mejorado y explica brevemente las mejoras realizadas."
                )
        
        elif task == "fix":
            if not code:
                code = f"// No se proporcionó código en {language} para arreglar"
            
            if is_local_model:
                prompt = f"""<|im_start|>system
Eres un programador experto que corrige errores en el código y resuelve problemas.
<|im_end|>
<|im_start|>user
Corrige el siguiente código en {language} que tiene errores:

```{language}
{code}
```

Descripción del problema: {query}
<|im_end|>
<|im_start|>assistant
"""
            else:
                prompt = (
                    f"Corrige el siguiente código en {language} que tiene errores:\n\n"
                    f"```{language}\n{code}\n```\n\n"
                    f"Descripción del problema: {query}\n\n"
                    f"Proporciona el código corregido y explica qué errores había y cómo los solucionaste."
                )
        
        else:  # general code question
            if is_local_model:
                prompt = f"""<|im_start|>system
Eres un programador experto que responde preguntas de programación de manera clara y concisa.
<|im_end|>
<|im_start|>user
Pregunta de programación relacionada con {language}: {query}

{f"Código de referencia:\n```{language}\n{code}\n```" if code else ""}
<|im_end|>
<|im_start|>assistant
"""
            else:
                # Consulta general de programación
                prompt = (
                    f"Responde la siguiente pregunta sobre programación en {language}:\n\n"
                    f"{query}\n\n"
                )
                
                if code:
                    prompt += f"Código de referencia:\n```{language}\n{code}\n```\n\n"
                    
                prompt += "Proporciona una respuesta clara y concisa, con ejemplos de código si es necesario."
        
        return prompt
    
    def _process_response(self, response: str, task: str) -> str:
        """
        Process the model response based on the task.
        
        Args:
            response: The raw model response
            task: The type of task
            
        Returns:
            Processed response string
        """
        # For most tasks, just return the full response
        if task in ["explain", "review"]:
            return response
        
        # For code generation, try to extract just the code if it seems wrapped in explanation
        if task in ["generate", "improve", "fix"]:
            # If response has code blocks, try to extract them
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', response, re.DOTALL)
            
            if len(code_blocks) == 1:
                # If there's just one code block, return it
                return code_blocks[0]
            elif len(code_blocks) > 1:
                # If there are multiple code blocks, combine them with explanations
                return response
        
        # Default: return the full response
        return response

    def _generate_basic_response(self, query: str, task: str, language: str, code: str) -> AgentResponse:
        """
        Genera una respuesta básica sin utilizar un modelo de IA.
        Es útil como respuesta de fallback cuando no hay un modelo disponible.
        
        Args:
            query: La consulta original
            task: El tipo de tarea
            language: El lenguaje de programación
            code: Código existente, si lo hay
            
        Returns:
            AgentResponse con una respuesta básica
        """
        self.logger.info(f"Generando respuesta básica para tarea: {task} en {language}")
        
        response_content = ""
        
        if task == "generate" and language == "python":
            if "fibonacci" in query.lower():
                response_content = """
# Programa Python para calcular los primeros 10 números de Fibonacci
def fibonacci(n):
    fib_sequence = [0, 1]
    while len(fib_sequence) < n:
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence

# Generar y mostrar los primeros 10 números
fib_numbers = fibonacci(10)
print("Los primeros 10 números de Fibonacci son:")
print(fib_numbers)
"""
            elif "factorial" in query.lower():
                response_content = """
# Programa Python para calcular el factorial de un número
def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n-1)

# Probar con algunos números
for i in range(5):
    print(f"{i}! = {factorial(i)}")
"""
            else:
                response_content = """
# Programa Python básico
def main():
    print("Hola, mundo!")
    # Aquí iría el código específico para tu tarea
    # Pero sin un modelo de IA, no puedo generar código personalizado
    
if __name__ == "__main__":
    main()
"""
        elif task == "explain":
            response_content = f"""
# Explicación básica del código
'''
Para explicar este código en detalle, necesitaría acceso a un modelo de IA.
Sin embargo, puedo decirte que este es código en {language}.

Puntos generales a considerar cuando analices código:
1. Revisar la estructura general y flujo del programa
2. Identificar funciones y sus propósitos
3. Entender las estructuras de datos utilizadas
4. Revisar manejo de excepciones y casos de borde

Para un análisis detallado, considera agregar una API key válida para el modelo {self.model_name}.
'''
"""
        else:
            response_content = f"""
# Respuesta para solicitud de código
'''
He recibido tu solicitud para {task} código en {language}.
Sin embargo, no tengo acceso a un modelo de IA en este momento para generar una respuesta personalizada.

Para obtener mejores resultados:
1. Asegúrate de configurar una API key válida para {self.model_name}
2. Proporciona más detalles sobre tu solicitud específica
3. Incluye código existente si es relevante

Alternativamente, puedes usar el EchoAgent o SystemAgent para tareas que no requieran generación de código.
'''
"""

        return AgentResponse(
            content=response_content,
            metadata={
                "task": task,
                "language": language,
                "fallback": True,
                "model_used": "none"
            }
        )

    async def _process_with_model(self, task, language, query, context=None, use_memory=True, memory_threshold=0.5):
        """
        Process a code task using the configured language model.
        
        Args:
            task: The code task (generate, explain, etc.)
            language: The programming language
            query: The user query
            context: Optional additional context
            use_memory: Boolean indicating if memory should be used
            memory_threshold: Threshold for memory usage
            
        Returns:
            Generated code or explanation
        """
        context = context or {}
        debug = context.get("debug_memory", False)
        
        # Inicializar el objeto para memoria
        memory_context = {
            "memory_used": False,
            "memories_found": 0
        }
        
        relevant_memories = []
        if self.has_memory() and use_memory:
            # Búsqueda de memorias relevantes
            if debug:
                self.logger.info(f"DEBUG: Buscando memorias relevantes para: {query} (use_memory=True)")
            else:
                self.logger.info(f"Buscando memorias relevantes para: {query}")
            
            # Para tareas de código, es importante buscar memorias del mismo tipo y lenguaje
            # Primero extraemos palabras clave relevantes de la consulta
            import re
            
            # Patrones para detectar palabras clave específicas de algoritmos/conceptos
            algo_patterns = {
                "factorial": r"factorial",
                "fibonacci": r"fibonacci|fib",
                "ordenamiento": r"sort|ordenar|ordenamiento|bubble|quick|merge",
                "búsqueda": r"search|búsqueda|buscar|binary|lineal"
            }
            
            # Intentar encontrar palabras clave específicas en la consulta
            keywords = []
            for algo, pattern in algo_patterns.items():
                if re.search(pattern, query.lower()):
                    keywords.append(algo)
                    if debug:
                        self.logger.info(f"DEBUG: Detectada palabra clave especial: {algo}")
            
            # Inicializar memories como vacío
            memories = []
            
            # Si encontramos palabras clave, hacer una búsqueda específica primero
            if keywords:
                for keyword in keywords:
                    if debug:
                        self.logger.info(f"DEBUG: Buscando memorias con palabra clave: {keyword}")
                    keyword_memories = self.recall(
                        query=keyword,
                        memory_type="code_interaction",
                        limit=5
                    )
                    if keyword_memories:
                        if debug:
                            self.logger.info(f"DEBUG: Encontradas {len(keyword_memories)} memorias con palabra clave '{keyword}'")
                        memories = keyword_memories
                        break
            
            # Si no encontramos con palabras clave o no hay palabras clave, hacer la búsqueda normal
            if not keywords or not memories:
                if debug:
                    self.logger.info(f"DEBUG: Realizando búsqueda estándar por '{query}'")
                memories = self.recall(
                    query=query,
                    memory_type="code_interaction",
                    limit=5
                )
            
            if memories:
                if debug:
                    self.logger.info(f"DEBUG: Encontradas {len(memories)} memorias relevantes")
                    for i, mem in enumerate(memories):
                        if isinstance(mem.content, dict):
                            query_content = mem.content.get("query", "")
                            self.logger.info(f"DEBUG: Memoria {i+1} - Query: {query_content}")
                
                memory_context["memory_used"] = True
                memory_context["memories_found"] = len(memories)
                memory_context["memory_content"] = []
                
                # Filtrar memorias por lenguaje si es relevante
                language_memories = []
                if language and language != "any":
                    for mem in memories:
                        # Verificar lenguaje en metadata o content
                        mem_language = None
                        if isinstance(mem.content, dict):
                            mem_language = mem.content.get("language")
                        
                        if not mem_language and isinstance(mem.metadata, dict):
                            mem_language = mem.metadata.get("language")
                        
                        if mem_language and mem_language.lower() == language.lower():
                            language_memories.append(mem)
                    
                    if language_memories:
                        if debug:
                            self.logger.info(f"DEBUG: Filtradas a {len(language_memories)} memorias en lenguaje {language}")
                        memories = language_memories
                
                relevant_memories = memories
                
                # Extraer contenido para prompt
                for mem in memories:
                    if isinstance(mem.content, dict):
                        # Para contenido estructurado
                        if "response" in mem.content:
                            memory_context["memory_content"].append(mem.content["response"])
                        elif "code" in mem.content:
                            memory_context["memory_content"].append(mem.content["code"])
                        else:
                            memory_context["memory_content"].append(json.dumps(mem.content))
                    else:
                        # Para contenido simple (texto)
                        memory_context["memory_content"].append(str(mem.content))
            else:
                if debug:
                    self.logger.info("DEBUG: No se encontraron memorias relevantes en primera búsqueda")
                
                # Si se solicitó explícitamente usar memoria pero no se encontró ninguna,
                # buscar más ampliamente sin filtrar por tipo
                if use_memory:
                    if debug:
                        self.logger.info("DEBUG: Realizando búsqueda ampliada por memorias")
                    
                    broader_memories = self.recall(
                        query=query,
                        limit=3
                    )
                    if broader_memories:
                        if debug:
                            self.logger.info(f"DEBUG: Encontradas {len(broader_memories)} memorias en búsqueda ampliada")
                        memory_context["memory_used"] = True
                        memory_context["memories_found"] = len(broader_memories)
                        memory_context["memory_content"] = [str(mem.content) for mem in broader_memories]
                        relevant_memories = broader_memories
        elif not use_memory and debug:
            self.logger.info("DEBUG: Uso de memoria desactivado explícitamente")
        elif not self.has_memory() and debug:
            self.logger.info("DEBUG: Agente no tiene memoria configurada")
        
        # Enhance the prompt with memory information if available
        enhanced_query = query
        if relevant_memories and "memory_content" in memory_context:
            # Extract all relevant code examples from memory
            code_examples = []
            similar_queries = []
            
            for memory in relevant_memories:
                # Check if this is a stored code interaction
                if isinstance(memory.content, dict) and 'response' in memory.content:
                    response = memory.content.get('response', '')
                    original_query = memory.content.get('query', '')
                    
                    # Extract code blocks from response
                    import re
                    code_blocks = re.findall(r'```(?:python|javascript|java|cpp|c\+\+|c#|csharp|go|rust|sql)?(.+?)```', 
                                           response, re.DOTALL)
                    
                    if code_blocks:
                        # Found code blocks, add them as examples
                        for i, block in enumerate(code_blocks):
                            code_examples.append(f"Previous code example for '{original_query}':\n```\n{block.strip()}\n```")
                    
                    # Add the original query as a similar query
                    if original_query and original_query != query:
                        similar_queries.append(f"- You previously answered: '{original_query}'")
                
                # Also check if the memory content is a direct string with code
                elif isinstance(memory.content, str) and "```" in memory.content:
                    code_examples.append(f"Previous code:\n{memory.content}")
            
            # Build enhanced query with memory context
            memory_context_text = ""
            if code_examples:
                memory_context_text += "\n\nMemory context:\n"
                memory_context_text += "\n".join(code_examples)
            
            if similar_queries:
                memory_context_text += "\n\nSimilar queries:\n"
                memory_context_text += "\n".join(similar_queries)
            
            enhanced_query += memory_context_text
        
        # Build prompt based on the task and enhanced query
        prompt = self._build_prompt(enhanced_query, task, language, "")
        
        # Generate response - corrigiendo el error de coroutine
        model, model_info = await self.model_manager.load_model(self.model_name)
        model_response = await model.generate(prompt)
        
        # Extract code from response if needed
        processed_response = self._process_response(model_response.text, task)
        
        # Store the interaction in memory for future reference
        if self.has_memory():
            memory_content = {
                "query": query,
                "task": task,
                "language": language,
                "code": "",
                "response": processed_response
            }
            
            # More important for tasks that generate new code
            importance = 0.8 if task == "generate" else 0.6
            
            memory_id = self.remember(
                content=memory_content,
                importance=importance,
                memory_type="code_interaction",
                metadata={
                    "language": language,
                    "task": task,
                    "model_used": self.model_name,
                    "contains_code": "```" in processed_response
                }
            )
            self.logger.debug(f"Stored code interaction in memory: {memory_id}")
        
        response = AgentResponse(
            content=processed_response,
            metadata={
                "task": task,
                "language": language,
                "model_used": self.model_name,
                **memory_context
            }
        )
        
        self.set_state("idle")
        return response
