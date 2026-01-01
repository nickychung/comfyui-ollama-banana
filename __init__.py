from .ollama_node import OllamaLLMNode, OllamaNbpCharacter, OllamaCharacterRestore, OllamaImageSaver

NODE_CLASS_MAPPINGS = {
    "OllamaLLMNode": OllamaLLMNode,
    "OllamaNbpCharacter": OllamaNbpCharacter,
    "OllamaCharacterRestore": OllamaCharacterRestore,
    "OllamaImageSaver": OllamaImageSaver
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaLLMNode": "Ollama LLM",
    "OllamaNbpCharacter": "Ollama NBP Character",
    "OllamaCharacterRestore": "Ollama Character Restore",
    "OllamaImageSaver": "Ollama Image Saver"
}

WEB_DIRECTORY = "js"
