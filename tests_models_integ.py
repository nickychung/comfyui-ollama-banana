
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies again
sys.modules['server'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()

import ollama_node

class TestModelIntegration(unittest.TestCase):
    def test_helper_exists(self):
        self.assertTrue(hasattr(ollama_node, 'get_ollama_models'))
        
    @patch('requests.get')
    def test_input_types_call(self, mock_get):
        # Ensure INPUT_TYPES class method calls the helper
        try:
             # Just mock a failure so it returns default quickly
            mock_get.side_effect = Exception("Fast fail")
            
            inputs = ollama_node.OllamaLLMNode.INPUT_TYPES()
            model_input = inputs['required']['model']
            print(f"Model Input Type: {model_input}")
            # It should be a tuple (list of strings)
            self.assertIsInstance(model_input[0], list)
            self.assertEqual(model_input[0], ["gpt-oss:20b"])
            
        except Exception as e:
            self.fail(f"INPUT_TYPES raised {e}")

if __name__ == '__main__':
    unittest.main()
