"""
Modelos en la nube.

Este paquete contiene implementaciones de la interfaz ModelInterface
para modelos en la nube como OpenAI, Anthropic, Gemini, etc.
"""

from .openai_model import OpenAIModel
from .anthropic_model import AnthropicModel

__all__ = ["OpenAIModel", "AnthropicModel"] 