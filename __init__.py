from .ollama_node import OllamaLLMNode, OllamaNbpCharacter

NODE_CLASS_MAPPINGS = {
    "OllamaLLMNode": OllamaLLMNode,
    "OllamaNbpCharacter": OllamaNbpCharacter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaLLMNode": "Ollama LLM",
    "OllamaNbpCharacter": "Ollama NBP Character"
}

WEB_DIRECTORY = "js"
