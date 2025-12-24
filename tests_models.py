
import unittest
from unittest.mock import patch, MagicMock
import requests
import json

# Logic to be tested (copied from plan to be implemented)
def get_ollama_models(url="http://127.0.0.1:11434"):
    try:
        response = requests.get(f"{url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            # Sort by modified_at descending (newest first)
            # handle cases where modified_at might be missing
            models.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            
            model_names = [m["name"] for m in models]
            
            # Default logic: prefer gpt-oss:20b
            default_model = "gpt-oss:20b"
            if default_model in model_names:
                model_names.remove(default_model)
                model_names.insert(0, default_model)
                
            return model_names
    except Exception as e:
        print(f"Error fetching models: {e}")
        pass
        
    return ["gpt-oss:20b"]

class TestOllamaModels(unittest.TestCase):
    @patch('requests.get')
    def test_fetch_success_with_default(self, mock_get):
        # Mock response with gpt-oss:20b and others
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama2", "modified_at": "2023-01-01"},
                {"name": "gpt-oss:20b", "modified_at": "2023-01-02"}, # newer
                {"name": "mistral", "modified_at": "2023-01-03"} # newest
            ]
        }
        mock_get.return_value = mock_resp
        
        models = get_ollama_models()
        # Expect mistral first by date, BUT gpt-oss:20b moved to top
        print(f"Models: {models}")
        self.assertEqual(models[0], "gpt-oss:20b")
        self.assertIn("mistral", models)
        self.assertIn("llama2", models)

    @patch('requests.get')
    def test_fetch_success_no_default(self, mock_get):
        # Mock response WITHOUT gpt-oss:20b
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama2", "modified_at": "2023-01-01"},
                {"name": "mistral", "modified_at": "2023-01-05"}
            ]
        }
        mock_get.return_value = mock_resp
        
        models = get_ollama_models()
        # Expect mistral (newest) at top
        print(f"Models (no default): {models}")
        self.assertEqual(models[0], "mistral")
        
    @patch('requests.get')
    def test_fetch_failure(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        
        models = get_ollama_models()
        print(f"Models (failure): {models}")
        self.assertEqual(models, ["gpt-oss:20b"])

if __name__ == '__main__':
    unittest.main()
