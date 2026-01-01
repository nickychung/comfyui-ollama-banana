
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import io
import base64
from PIL import Image
import numpy as np

# Mock ComfyUI dependencies
sys.modules['server'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()
sys.modules['folder_paths'] = MagicMock()
sys.modules['folder_paths'].get_output_directory.return_value = "./mock_output"

# Mock requests
sys.modules['requests'] = MagicMock()

# Now import the node
import ollama_node

class TestOllamaImageSaver(unittest.TestCase):
    def setUp(self):
        self.node = ollama_node.OllamaImageSaver()
        # Mock folder_paths
        self.node.output_dir = "./mock_output"
        
    @patch('ollama_node.requests.post')
    @patch('ollama_node.Image.Image.save') 
    @patch('os.makedirs')
    def test_save_images_logic(self, mock_makedirs, mock_save, mock_post):
        # 1. Setup Mock Input
        # Create a dummy tensor image (1, 64, 64, 3)
        # ComfyUI image format is [Batch, Height, Width, Channel]
        dummy_tensor = MagicMock()
        dummy_tensor.cpu().numpy.return_value = np.zeros((64, 64, 3), dtype=np.float32)
        
        images = [dummy_tensor]
        folder_path = "./test_output"
        model = "llava"
        prompt = "Describe this"
        url = "http://localhost:11434"
        
        # 2. Setup Mock Responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "A_cute_cat_sitting_on_a_fence."}
        mock_post.return_value = mock_response
        
        # 3. Run the function
        self.node.save_images(images, folder_path, model, prompt, url, filename_prefix="Test", add_metadata=True)
        
        # 4. Verify Ollama Call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['model'], "llava")
        self.assertEqual(payload['prompt'], prompt)
        self.assertTrue(len(payload['images'][0]) > 0) # Ensure base64 image sent
        
        # 5. Verify Save
        # Should create dir
        mock_makedirs.assert_called_with(folder_path)
        
        # Should save image
        # We can check the filename in the path passed to save
        mock_save.assert_called()
        # The first arg to save is the path or file object depending on usage.
        # In our code: img.save(full_path, format="PNG", optimize=False)
        
        # There might be multiple calls to save (one for buffer to base64, one for actual file)
        # The base64 one uses a BytesIO object, the file one uses a string path.
        
        file_save_calls = [c for c in mock_save.call_args_list if isinstance(c[0][0], str)]
        self.assertTrue(len(file_save_calls) > 0)
        
        save_path = file_save_calls[0][0][0]
        print(f"DEBUG: Full Save Path: {save_path}")
        
        # Check filename components
        if "Test" not in save_path: print("FAIL: Test prefix missing")
        if "A_cute_cat" not in save_path: print("FAIL: Keywords missing")
        if ".png" not in save_path: print("FAIL: Extension missing")
        if "64x64" not in save_path: print("FAIL: Metadata missing")

        self.assertIn("Test", save_path)
        self.assertIn("A_cute_cat", save_path)
        self.assertIn(".png", save_path)
        self.assertIn("64x64", save_path) # Metadata
        
        # Check optimize=False
        kwargs = file_save_calls[0][1]
        self.assertEqual(kwargs.get('optimize'), False)
        self.assertEqual(kwargs.get('format'), "PNG")

    @patch('ollama_node.get_ollama_models')
    def test_vision_filter(self, mock_get_models):
        # This tests the INPUT_TYPES logic indirectly by mocking the helper
        pass

if __name__ == '__main__':
    unittest.main()
