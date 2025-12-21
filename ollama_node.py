import requests
import json
import os

class OllamaLLMNode:
    """
    A custom node for ComfyUI that interfaces with a local Ollama instance to generate text.
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "model": ("STRING", {"default": "gpt-oss:20b"}),
                "url": ("STRING", {"default": "http://127.0.0.1:11434"}),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Prompt",)
    FUNCTION = "generate_text"
    CATEGORY = "Ollama"
    OUTPUT_NODE = True

    def generate_text(self, prompt, model, url, keep_alive, seed=None):
        """
        Generates text using the Ollama API.
        """
        api_url = f"{url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": f"{keep_alive}m"
        }
        
        if seed is not None:
             options = {
                 "seed": seed
             }
             payload["options"] = options

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "")
            
            print(f"Ollama Generated Text: {generated_text}")
            
            return {"ui": {"text": [generated_text]}, "result": (generated_text,)}
            
        except requests.exceptions.RequestException as e:
            return {"ui": {"text": [f"Error: {str(e)}"]}, "result": (f"Error: {str(e)}",)}
        except json.JSONDecodeError:
             return {"ui": {"text": ["Error: Failed to decode JSON response from Ollama."]}, "result": ("Error: Failed to decode JSON response from Ollama.",)}
        except Exception as e:
             return {"ui": {"text": [f"Error: An unexpected error occurred: {str(e)}"]}, "result": (f"Error: An unexpected error occurred: {str(e)}",)}

class OllamaNbpCharacter:
    """
    A custom node for ComfyUI that generates structured character prompts using Ollama.
    Supports 9 structured elements with persistence and dynamic generation.
    """
    
    # Map friendly names to file names
    ELEMENT_FILES = {
        "subject": "subject.txt",
        "composition": "composition.txt",
        "action": "action.txt",
        "location": "location.txt",
        "style": "style.txt",
        "editing_instructions": "editing_instructions.txt",
        "camera_lighting": "camera_lighting.txt",
        "specific_text": "specific_text.txt",
        "factual_constraints": "factual_constraints.txt"
    }

    # Map friendly names to UI input names
    ELEMENT_INPUTS = [
        "subject", "composition", "action", "location", "style", 
        "editing_instructions", "camera_lighting", "specific_text", 
        "factual_constraints"
    ]
    
    def __init__(self):
        self.elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        # Ensure files exists (method below)
        pass # Files kept by INPUT_TYPES mostly, but logic is shared

    def _save_option(self, element_key, content):
        """Appends a new option to the corresponding text file."""
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        file_path = os.path.join(elements_dir, self.ELEMENT_FILES[element_key])
        
        # Check for duplicates (simple check)
        existing = set()
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                existing = {line.strip() for line in f if line.strip()}
        
        # Avoid saving empty or duplicate
        if content and content.strip() and content not in existing:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{content}\n")
            print(f"[OllamaNbpCharacter] Saved new {element_key}: {content}")

    @classmethod
    def INPUT_TYPES(s):
        # Determine path
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        
        # Helper to ensure files and load opts
        if not os.path.exists(elements_dir):
            try:
                os.makedirs(elements_dir)
            except:
                pass # Already exists race condition
            
        element_map = {
            "subject": "subject.txt",
            "composition": "composition.txt",
            "action": "action.txt",
            "location": "location.txt",
            "style": "style.txt",
            "editing_instructions": "editing_instructions.txt",
            "camera_lighting": "camera_lighting.txt",
            "specific_text": "specific_text.txt",
            "factual_constraints": "factual_constraints.txt"
        }

        # Ensure all files exist so we can read them
        for fname in element_map.values():
            fpath = os.path.join(elements_dir, fname)
            if not os.path.exists(fpath):
                with open(fpath, "w", encoding="utf-8") as f:
                    pass

        def load_opts(fname):
            path = os.path.join(elements_dir, fname)
            opts = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    opts = [line.strip() for line in f if line.strip()]
            return opts

        inputs = {
            "required": {
                "theme": ("STRING", {"multiline": True, "default": "Cyberpunk detective"}),
                "model": ("STRING", {"default": "gpt-oss:20b"}),
                "url": ("STRING", {"default": "http://127.0.0.1:11434"}),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
        
        defaults = ["Follow Theme", "Randomised", "Skip"]
        
        for key, fname in element_map.items():
            opts = defaults + load_opts(fname)
            inputs["required"][f"{key}_input"] = (opts,)
        
        # Add granular Save toggles
        for key in element_map.keys():
            inputs["optional"][f"save_{key}"] = ("BOOLEAN", {"default": False, "label_on": f"Save {key}", "label_off": f"Don't Save {key}"})

        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Prompt",)
    FUNCTION = "generate_character_prompt"
    CATEGORY = "Ollama"
    OUTPUT_NODE = True

    def generate_character_prompt(self, theme, model, url, keep_alive, seed=None, **kwargs):
        """
        Generates a character prompt using the Ollama API with structured inputs.
        """
        import re # Import locally to avoid top-level dependency issues if re not standard (it is standard)

        api_url = f"{url}/api/generate"
        
        # 1. Parse Inputs & Identify Generation Needs
        final_elements = {}
        to_generate_theme = []
        to_generate_random = []
        
        # Map snake_case to Title Case
        display_names = {
            "subject": "Subject",
            "composition": "Composition",
            "action": "Action",
            "location": "Location",
            "style": "Style",
            "editing_instructions": "Editing Instructions",
            "camera_lighting": "Camera and lighting details",
            "specific_text": "Specific text integration",
            "factual_constraints": "Factual constraints"
        }
        
        for key in self.ELEMENT_INPUTS:
            input_val = kwargs.get(f"{key}_input", "Skip")
            
            if input_val == "Skip":
                continue
            elif input_val == "Follow Theme":
                to_generate_theme.append(key)
            elif input_val == "Randomised":
                to_generate_random.append(key)
            else:
                # Verbatim from file
                final_elements[key] = input_val

        # 2. Call Ollama if needed
        generated_data = {}
        
        if to_generate_theme or to_generate_random:
            # Construct system prompt with detailed definitions AND strict JSON requirement
            system_instruction = (
                "You are an expert at creating detailed image generation prompts.\n"
                "Your task is to generate structured prompt elements based on a user Theme or Randomly.\n\n"
                "DEFINITIONS:\n"
                "• Subject: Who or what is in the image? Be specific. (e.g., a stoic robot barista).\n"
                "• Composition: How is the shot framed? (e.g., extreme close-up, wide shot).\n"
                "• Action: What is happening? (e.g., brewing coffee, casting a spell).\n"
                "• Location: Where does the scene take place? (e.g., futuristic cafe).\n"
                "• Style: Aesthetic style? (e.g., 3D animation, film noir, photorealistic).\n"
                "• Editing Instructions: Specific changes (e.g., change tie to green).\n"
                "• Camera and lighting details: (e.g., low-angle shot, f/1.8, golden hour).\n"
                "• Specific text integration: Text to appear in image (e.g., 'URBAN EXPLORER' sign).\n"
                "• Factual constraints: Accuracy requirements (e.g., historically accurate).\n"
                "\n"
                "INSTRUCTIONS:\n"
                "1. Output valid JSON only.\n"
                "2. No markdown, no explanations, no conversational filler.\n"
                "3. Ensure strictly valid JSON format.\n"
            )
            
            user_instruction = f"Context Theme: {theme}\n\nREQUIRED ELEMENTS:\n"
            
            # Build the expected keys list for the model
            expected_keys_json = []
            if to_generate_theme:
                user_instruction += "Generate based on Theme:\n"
                for key in to_generate_theme:
                    user_instruction += f"- {key} ({display_names[key]})\n"
                    expected_keys_json.append(f'  "{key}": "generated content..."')
            
            if to_generate_random:
                user_instruction += "Generate Randomly (Ignore Theme):\n"
                for key in to_generate_random:
                    user_instruction += f"- {key} ({display_names[key]})\n"
                    expected_keys_json.append(f'  "{key}": "random content..."')
            
            # Add Example Structure to guide the model
            user_instruction += "\nOutput this EXACT JSON Structure (filled with content):\n{\n"
            user_instruction += ",\n".join(expected_keys_json)
            user_instruction += "\n}\n\nResponse:"

            payload = {
                "model": model,
                "prompt": system_instruction + user_instruction,
                "stream": False,
                "keep_alive": f"{keep_alive}m",
                "format": "json"
            }
            
            if seed is not None:
                payload["options"] = {"seed": seed}

            try:
                response = requests.post(api_url, json=payload)
                response.raise_for_status()
                result_json = response.json()
                content = result_json.get("response", "")
                
                # Robust JSON Extraction using Regex
                # Finds the first valid { ... } block
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        data = json.loads(json_str)
                        # Normalize keys helpers
                        def normalize(k): return k.lower().replace(" ", "_")
                        
                        for key, val in data.items():
                            norm_key = normalize(key)
                            # Try to match to our keys
                            matched = False
                            for real_key in self.ELEMENT_INPUTS:
                                if real_key == norm_key or normalize(display_names[real_key]) == norm_key:
                                    generated_data[real_key] = val
                                    matched = True
                                    break
                            # Fuzzy match
                            if not matched:
                                 for real_key in self.ELEMENT_INPUTS:
                                     if real_key in norm_key:
                                         generated_data[real_key] = val
                                         matched = True
                                         break
                    except json.JSONDecodeError:
                        print(f"Ollama JSON Decode Error. Content found but invalid: {json_str}")
                else:
                    print(f"Ollama JSON Error. No JSON object found in output: {content}")

            except Exception as e:
                print(f"Ollama API Error: {e}")
                
        # 3. Save Logic
        for key in self.ELEMENT_INPUTS:
            was_generated = (key in to_generate_theme) or (key in to_generate_random)
            
            if was_generated and key in generated_data:
                should_save = kwargs.get(f"save_{key}", False)
                if should_save:
                    self._save_option(key, generated_data[key])

        # 4. Assemble Final Prompt
        for key in to_generate_theme + to_generate_random:
            if key in generated_data:
                final_elements[key] = generated_data[key]
            else:
                 final_elements[key] = ""

        # Order matters
        prompt_parts = []
        for key in self.ELEMENT_INPUTS:
            if key in final_elements:
                val = str(final_elements[key])
                name = display_names[key]
                if val and val.strip():
                    prompt_parts.append(f"{name}: {val}")
        
        full_text = "\n".join(prompt_parts)
        
        print(f"Ollama NBP Character Final: {full_text}")
        
        return {"ui": {"text": [full_text]}, "result": (full_text,)}
