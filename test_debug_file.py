
import sys
import os
import io
import base64
from PIL import Image
import numpy as np
from unittest.mock import MagicMock

# Redirect stdout to file
sys.stdout = open("debug_output.txt", "w")
sys.stderr = sys.stdout

# Mock ComfyUI dependencies
sys.modules['server'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()
sys.modules['folder_paths'] = MagicMock()
sys.modules['folder_paths'].get_output_directory.return_value = "./mock_output"
sys.modules['requests'] = MagicMock()

import ollama_node

def test_manual():
    print("Starting Test...")
    node = ollama_node.OllamaImageSaver()
    
    # Setup Params
    params = {
        "model": "llava",
        "prompt": "describe",
        "url": "http://lo",
        "folder_path": "./test_dbg",
        "images": [MagicMock()],
        "filename_prefix": "PREFIX"
    }
    params['images'][0].cpu().numpy.return_value = np.zeros((64, 64, 3), dtype=np.float32)
    
    # Setup Response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "KEYWORD1_KEYWORD2"}
    ollama_node.requests.post.return_value = mock_resp
    
    # Execute
    try:
        node.save_images(**params)
    except Exception as e:
        print(f"Exception: {e}")
        
    print("Test Finished.")

if __name__ == "__main__":
    test_manual()
    sys.stdout.close()
