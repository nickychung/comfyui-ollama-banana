from .ollama_node import OllamaLLMNode, OllamaNbpCharacter, OllamaCharacterRestore

NODE_CLASS_MAPPINGS = {
    "OllamaLLMNode": OllamaLLMNode,
    "OllamaNbpCharacter": OllamaNbpCharacter,
    "OllamaCharacterRestore": OllamaCharacterRestore
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaLLMNode": "Ollama LLM",
    "OllamaNbpCharacter": "Ollama NBP Character",
    "OllamaCharacterRestore": "Ollama Character Restore"
}

WEB_DIRECTORY = "js"
