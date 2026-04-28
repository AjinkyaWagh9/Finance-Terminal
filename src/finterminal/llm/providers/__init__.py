"""Provider registry — maps the `provider:` key in models.yaml to a class.

To add a new provider: implement LLMProvider in a new module and add it here.
"""

from .anthropic import AnthropicProvider
from .null import NullProvider
from .ollama import OllamaProvider

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "null": NullProvider,
    # "xai": XAIProvider,                  # added in Phase 2.5
    # "openai_compat": OpenAICompatProvider,  # added when needed
}
