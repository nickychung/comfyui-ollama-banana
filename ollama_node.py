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
        import re 

        api_url = f"{url}/api/generate"
        
        # 1. Parse Inputs & Identify Generation Needs
        final_elements = {}
        to_generate_theme = []
        to_generate_random = []
        
        # Map snake_case to Title Case (Used for Prompting and Parsing)
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
        
        # Reverse map for parsing (Title -> snake_case)
        title_to_key = {v.lower(): k for k, v in display_names.items()}

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
            # Construct system prompt (Text based, robust to chatty models)
            system_instruction = (
                "You are an expert at creating detailed image generation prompts.\n"
                "Your task is to generate structured prompt elements based on a user Theme or Randomly.\n"
                "Do NOT output conversational fillers like 'Here is the prompt'. Just output the fields.\n\n"
                "DEFINITIONS:\n"
                "• Subject: Who or what is in the image? Be specific.\n"
                "• Composition: How is the shot framed? (e.g., extreme close-up, wide shot).\n"
                "• Action: What is happening?\n"
                "• Location: Where does the scene take place?\n"
                "• Style: Aesthetic style? (e.g., 3D animation, film noir).\n"
                "• Editing Instructions: Specific changes.\n"
                "• Camera and lighting details: (e.g., f/1.8, golden hour).\n"
                "• Specific text integration: Text to appear in image.\n"
                "• Factual constraints: Accuracy requirements.\n\n"
            )
            
            user_instruction = f"Context Theme: {theme}\n\nREQUIRED OUTPUT FORMAT:\n"
            
            # Build the request list
            if to_generate_theme:
                user_instruction += "Generate based on Theme:\n"
                for key in to_generate_theme:
                    user_instruction += f"{display_names[key]}:\n"
            
            if to_generate_random:
                user_instruction += "Generate Randomly (Ignore Theme):\n"
                for key in to_generate_random:
                    user_instruction += f"{display_names[key]}:\n"
            
            user_instruction += "\nResponse:"

            payload = {
                "model": model,
                "prompt": system_instruction + user_instruction,
                "stream": False,
                "keep_alive": f"{keep_alive}m"
                # Removed "format": "json" to allow natural text generation
            }
            
            if seed is not None:
                payload["options"] = {"seed": seed}

            try:
                response = requests.post(api_url, json=payload)
                response.raise_for_status()
                result_json = response.json()
                content = result_json.get("response", "")
                
                print(f"Ollama Raw Output: {content}")

                # Robust Text Extraction using Regex
                # We look for "Key: Value" or "Key:\nValue" patterns
                
                # Check for each key we requested
                all_requested = to_generate_theme + to_generate_random
                
                for key in all_requested:
                    display_name = display_names[key]
                    # Regex explanation:
                    # 1. match the Display Name literally
                    # 2. match optional colon and whitespace
                    # 3. capture everything until the next newline that looks like a new header OR end of string
                    # Note: We assume headers are at start of lines.
                    
                    # Pattern: header followed by content, until next header or end
                    # We iterate lines to be safer against regex complexity
                    pass 
                
                # Simple Line Parser Strategy
                # Split by newlines, identify lines that start with a known header
                lines = content.split('\n')
                current_key = None
                buffer = []
                
                def save_buffer(k, buf):
                    if k and buf:
                        generated_data[k] = " ".join(buf).strip()
                
                # Create a lookup for headers to keys
                # e.g. "Subject" -> "subject", "Subject:" -> "subject"
                header_map = {}
                for k, v in display_names.items():
                    header_map[v.lower()] = k
                    header_map[v.lower() + ":"] = k

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this line starts with a known header
                    # Sort headers by length descending to match longest first ("Camera..." vs "Camera")
                    is_header = False
                    line_lower = line.lower()
                    
                    for header_str, key_id in header_map.items():
                        # We check if line STARTS with header_str (case insensitive match logic)
                        # clean check:
                        if line_lower.startswith(header_str.lower()):
                            # It's a header line. Save previous buffer.
                            save_buffer(current_key, buffer)
                            current_key = key_id
                            buffer = []
                            
                            # Content might be on the same line "Subject: Robot"
                            # Strip the header part
                            remainder = line[len(header_str):].strip()
                            # remove leading colon if header_str didn't have it (fuzzy match)
                            if remainder.startswith(":"):
                                remainder = remainder[1:].strip()
                            
                            if remainder:
                                buffer.append(remainder)
                            is_header = True
                            break
                    
                    if not is_header:
                        # Append to current buffer if we have a key
                        if current_key:
                            buffer.append(line)
                            
                # Save the last one
                save_buffer(current_key, buffer)

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
