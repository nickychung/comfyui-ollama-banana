
import sys
import os
import io
import base64
from PIL import Image
import numpy as np
from unittest.mock import MagicMock, patch

# Mock ComfyUI dependencies
sys.modules['server'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()
sys.modules['folder_paths'] = MagicMock()
sys.modules['folder_paths'].get_output_directory.return_value = "./mock_output"

# Mock requests before importing node
sys.modules['requests'] = MagicMock()
mock_requests = sys.modules['requests']

import ollama_node

def test_manual():
    node = ollama_node.OllamaImageSaver()
    node.output_dir = "./mock_output"
    
    # Mock return
    params = {
        "model": "llava",
        "prompt": "describe",
        "url": "http://lo",
        "folder_path": "./test_dbg",
        "images": [MagicMock()] # Dummy
    }
    
    # Setup dummy image
    params['images'][0].cpu().numpy.return_value = np.zeros((64, 64, 3), dtype=np.float32)
    
    # Setup Requests Mock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "A_cute_cat"}
    
    # IMPORTANT: We need to make sure the requests used BY THE NODE is our mock
    # Since we mocked sys.modules['requests'], it should be.
    # But let's verify ollama_node.requests is our mock
    print(f"Node requests id: {id(ollama_node.requests)}")
    print(f"Mock requests id: {id(mock_requests)}")
    
    ollama_node.requests.post.return_value = mock_resp
    
    print("Running save_images...")
    node.save_images(**params)
    print("Done.")

if __name__ == "__main__":
    test_manual()
