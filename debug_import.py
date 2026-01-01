
import sys
import traceback
from unittest.mock import MagicMock

# Mock ComfyUI modules
sys.modules['folder_paths'] = MagicMock()
sys.modules['server'] = MagicMock()
sys.modules['server'].PromptServer = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()

print("Attempting to import ollama_node...")

try:
    import ollama_node
    print("Import Successful")
except ImportError as e:
    print(f"ImportError: {e}")
    traceback.print_exc()
except Exception:
    traceback.print_exc()
