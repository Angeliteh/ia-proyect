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
            
        # Set the default model name
        self.model_name = config.get("default_model", "gemini-2.0-flash")
        
        # Track supported languages
        self.supported_languages = config.get(
            "supported_languages", 
            ["python", "javascript", "typescript", "java", "c", "c++", "c#", "go", "rust", "sql"]
        )
        
        self.logger.info(f"Code agent initialized with model: {self.model_name}")
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
                
        Returns:
            AgentResponse with the processed result
        """
        self.set_state("processing")
        context = context or {}
        
        task = context.get("task", self._detect_task(query))
        language = context.get("language", self._detect_language(query, context.get("code", "")))
        code = context.get("code", "")
        
        self.logger.info(f"Processing code task: {task} (language: {language})")
        
        try:
            # Load the model
            model, model_info = await self.model_manager.load_model(self.model_name)
            
            # Build prompt based on the task
            prompt = self._build_prompt(query, task, language, code)
            
            # Generate response
            model_response = await model.generate(prompt)
            
            # Extract code from response if needed
            processed_response = self._process_response(model_response.text, task)
            
            response = AgentResponse(
                content=processed_response,
                metadata={
                    "task": task,
                    "language": language,
                    "model_used": self.model_name
                }
            )
            
            self.set_state("idle")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing code query: {str(e)}")
            self.set_state("error")
            return AgentResponse(
                content=f"Error processing your code request: {str(e)}",
                status="error",
                metadata={"error": str(e)}
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
        Detect the type of coding task from the query.
        
        Args:
            query: The user query
            
        Returns:
            Task type string
        """
        query = query.lower()
        
        if any(x in query for x in ["generate", "create", "write", "implement"]):
            return "generate"
        elif any(x in query for x in ["explain", "understand", "what does", "how does"]):
            return "explain"
        elif any(x in query for x in ["improve", "optimize", "refactor", "better"]):
            return "improve"
        elif any(x in query for x in ["fix", "debug", "error", "wrong", "issue", "problem"]):
            return "fix"
        elif any(x in query for x in ["review", "analyze", "check"]):
            return "review"
        else:
            return "generate"  # Default task
    
    def _detect_language(self, query: str, code: str) -> str:
        """
        Detect the programming language from the query or code.
        
        Args:
            query: The user query
            code: Any provided code
            
        Returns:
            Language identifier string
        """
        # First check if language is explicitly mentioned in query
        query = query.lower()
        
        for lang in self.supported_languages:
            if lang in query:
                return lang
        
        # If code is provided, try to guess from code
        if code:
            # Check for common language markers
            if re.search(r'^\s*(import|from|def|class|if __name__)', code, re.MULTILINE):
                return "python"
            elif re.search(r'^\s*(function|const|let|var|import\s+{|export)', code, re.MULTILINE):
                # Could be JavaScript or TypeScript
                return "typescript" if ".ts" in query or ": " in code else "javascript"
            elif re.search(r'^\s*(public class|private|protected|import java)', code, re.MULTILINE):
                return "java"
            elif re.search(r'^\s*(#include)', code, re.MULTILINE):
                return "c++" if re.search(r'(class|namespace|template|std::)', code) else "c"
            elif re.search(r'^\s*(using System|namespace|public class)', code, re.MULTILINE):
                return "c#"
            elif re.search(r'^\s*(package main|import ")', code, re.MULTILINE):
                return "go"
            elif re.search(r'^\s*(use std|fn main|pub struct)', code, re.MULTILINE):
                return "rust"
            elif re.search(r'^\s*(SELECT|CREATE TABLE|INSERT INTO)', code, re.MULTILINE, re.IGNORECASE):
                return "sql"
        
        # Default to Python if we can't detect
        return "python"
    
    def _build_prompt(self, query: str, task: str, language: str, code: str) -> str:
        """
        Build a prompt for the code model based on the task.
        
        Args:
            query: User query
            task: The type of task
            language: Programming language
            code: Existing code if any
            
        Returns:
            Prompt string for the model
        """
        prompts = {
            "generate": f"""
You are an expert programmer. Generate {language} code based on this request:

{query}

Write well-structured, commented, and efficient code.
            """,
            
            "explain": f"""
You are an expert programmer. Explain this {language} code in detail:

```{language}
{code}
```

{query}

Break down the explanation by sections and highlight important concepts.
            """,
            
            "improve": f"""
You are an expert programmer. Improve this {language} code:

```{language}
{code}
```

{query}

Explain what improvements you made and why.
            """,
            
            "fix": f"""
You are an expert programmer. Fix this {language} code that has issues:

```{language}
{code}
```

{query}

Explain what was wrong and how you fixed it.
            """,
            
            "review": f"""
You are an expert programmer. Review this {language} code:

```{language}
{code}
```

{query}

Point out strengths, weaknesses, bugs, and suggest improvements.
            """
        }
        
        # Use the appropriate prompt template or fall back to a generic one
        prompt_template = prompts.get(task, f"""
You are an expert programmer. Help with this {language} programming request:

{query}

{f"Here is the relevant code:\n\n```{language}\n{code}\n```" if code else ""}

Provide a clear and detailed response.
        """)
        
        return prompt_template.strip()
    
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