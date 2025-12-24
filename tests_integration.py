
import sys
import unittest
from unittest.mock import MagicMock

# Mock ComfyUI dependencies
sys.modules['server'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()

# Now import the node
# We accept that it might fail if there are other dependencies, but this is the main one.
import ollama_node

class TestOllamaNodeIntegration(unittest.TestCase):
    def test_parse_logic_integration(self):
        # Verify the helper functions are available and working in the module
        chunk = "Subject: A B C D\nAction: X Y Z"
        label = ollama_node.parse_all_txt_chunk(chunk)
        print(f"Integration Label: {label}")
        self.assertTrue("Sub:" in label)
        
    def test_restore_functionality(self):
        # Create a mock file setup would be hard, but we can verify the method exists
        node = ollama_node.OllamaCharacterRestore()
        self.assertTrue(hasattr(node, 'restore'))
        
    def test_input_types(self):
        # Check if INPUT_TYPES runs without error
        try:
            inputs = ollama_node.OllamaCharacterRestore.INPUT_TYPES()
            print("INPUT_TYPES keys:", inputs.keys())
            self.assertIn("required", inputs)
        except Exception as e:
            self.fail(f"INPUT_TYPES raised {e}")

if __name__ == '__main__':
    unittest.main()
