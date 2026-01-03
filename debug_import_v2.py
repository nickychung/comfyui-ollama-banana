
import sys
import os

# Mock ComfyUI environment
sys.modules['folder_paths'] = type('obj', (object,), {'get_input_directory': lambda: '.'})
sys.modules['server'] = type('obj', (object,), {'PromptServer': type('obj', (object,), {'instance': type('obj', (object,), {'routes': type('obj', (object,), {'post': lambda x: lambda y: y})})})})
sys.modules['aiohttp'] = type('obj', (object,), {'web': type('obj', (object,), {'Response': lambda: None, 'json_response': lambda x: None})})

try:
    import ollama_node
    print("Import Successful")
except Exception as e:
    import traceback
    traceback.print_exc()
