import requests
import json
import os
from server import PromptServer

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
        
        file_path = os.path.join(self.elements_dir, self.ELEMENT_FILES[element_key])
        
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
            
            # Emit event to frontend
            PromptServer.instance.send_sync("ollama.option_saved", {
                "element": element_key, 
                "content": content
            })

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
            
        # Add "Save Full Prompt" toggle
        inputs["optional"]["save_full_prompt"] = ("BOOLEAN", {"default": False, "label_on": "Save Full Prompt to all.txt", "label_off": "Don't Save Full Prompt"})

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
                "Your task is to generate structured prompt elements with your best imagination and description based on a user Theme or Randomly.\n"
                "Do NOT output conversational fillers like 'Here is the prompt'. Just output the fields.\n\n"
                "DEFINITIONS:\n"
                "• Subject: Who or what is in the image? Be specific. (e.g., a stoic robot barista with glowing blue optics; a fluffy calico cat wearing a tiny wizard hat).\n"
                "• Composition: How is the shot framed? (e.g., extreme close-up, wide shot, low angle shot, portrait).\n"
                "• Action: What is happening? (e.g., brewing a cup of coffee, casting a magical spell, mid-stride running through a field).\n"
                "• Location: Where does the scene take place? (e.g., a futuristic cafe on Mars, a cluttered alchemist's library, a sun-drenched meadow at golden hour).\n"
                "• Style: What is the overall aesthetic? (e.g., 3D animation, film noir, watercolor painting, photorealistic, 1990s product photography).\n"
                "• Editing Instructions: For modifying an existing image, be direct and specific. (e.g., change the man's tie to green, remove the car in the background)\n"
                "• Camera and lighting details: Direct the shot like a cinematographer. (e.g., \"A low-angle shot with a shallow depth of field (f/1.8),\" \"Golden hour backlighting creating long shadows,\" \"Cinematic color grading with muted teal tones.\")\n"
                "• Specific text integration: Clearly state what text should appear and how it should look. (e.g., \"The headline 'URBAN EXPLORER' rendered in bold, white, sans-serif font at the top.\")\n"
                "• Factual constraints (for diagrams): Specify the need for accuracy and ensure your inputs themselves are factual (e.g., \"A scientifically accurate cross-section diagram,\" \"Ensure historical accuracy for the Victorian era.\").\n"
                "\n"
                "Example:\n"
                "Subject: A young woman with pale skin and a very slender, skinny build with a small waist. She has grey hair with distinct pink and blue highlights. She is wearing a black satin corset with mesh panels and subtle leather strapping details, accessorized with a simple black velvet choker.\n"
                "Composition: A photorealistic close-up portrait, framed from the chest to the top of the head.\n"
                "Action: She is seated at a cluttered antique vanity table. Her body is turned away, but she turns her head over her shoulder to look directly into the camera with a sultry, confident gaze. One hand rests on the aged wooden table near a perfume bottle.\n"
                "Location: A dimly lit, bohemian bedroom in Paris. The background consists of a warm bokeh of tarnished silver hand-mirrors, vintage cosmetics, and heavy, dark tapestries.\n"
                "Style: Photorealistic, cinematic, and ultra-high resolution (8k). The aesthetic should mimic the look of Kodak Portra 400 film.\n"
                "Editing Instructions: N/A\n"
                "Camera and lighting details: Shot on Kodak Portra 400 film. The scene is lit by the warm, soft glow of a vintage desk lamp on the vanity, creating deep shadows and intimate highlights on her décolletage and the metallic hair highlights.\n"
                "Specific text integration: N/A\n"
                "Factual constraints (for diagrams): N/A\n"
                "\n"
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
        
        # 3b. Save Full Prompt Logic
        if kwargs.get("save_full_prompt", False):
            all_file_path = os.path.join(self.elements_dir, "all.txt")
            
            # Simple separator
            separator = "\n" + "="*60 + "\n"
            
            # Create if missing
            if not os.path.exists(all_file_path):
                with open(all_file_path, "w", encoding="utf-8") as f:
                    pass
            
            pass

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
        
        # 5. Save Full Prompt (Moved here to have access to full_text)
        if kwargs.get("save_full_prompt", False):
            all_file_path = os.path.join(self.elements_dir, "all.txt")
            separator = "\n" + "="*60 + "\n"
            
            try:
                with open(all_file_path, "a", encoding="utf-8") as f:
                    f.write(separator)
                    f.write(f"Theme: {theme}\n") # context
                    f.write(full_text)
                    f.write("\n")
                print(f"[OllamaNbpCharacter] Saved full prompt to all.txt")
            except Exception as e:
                print(f"[OllamaNbpCharacter] Error saving to all.txt: {e}")

        print(f"Ollama NBP Character Final: {full_text}")
        
        return {"ui": {"text": [full_text]}, "result": (full_text,)}

class OllamaCharacterRestore:
    """
    Restores full character prompts saved in 'all.txt'.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        all_file_path = os.path.join(elements_dir, "all.txt")
        saved_prompts = []
        
        separator = "="*60
        
        if os.path.exists(all_file_path):
            with open(all_file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split by separator
            chunks = content.split(separator)
            
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                    
                # Parse chunk to create a label
                # We want "Sub: <3 words>, Com: <3 words>..."
                lines = chunk.split('\n')
                
                # key mapping for label generation (short keys)
                short_map = {
                    "Subject": "Sub",
                    "Composition": "Com",
                    "Action": "Act",
                    "Location": "Loc",
                    "Style": "Sty"
                }
                
                label_parts = []
                
                # Check for Theme first
                theme_line = next((l for l in lines if l.startswith("Theme:")), None)
                if theme_line:
                    val = theme_line.split(":", 1)[1].strip()
                    words = val.split()[:3]
                    label_parts.append(f"Thm: {' '.join(words)}")

                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if k in short_map:
                            words = v.split()[:3]
                            short_val = " ".join(words)
                            if short_val:
                                label_parts.append(f"{short_map[k]}: {short_val}")
                
                if not label_parts:
                    words = chunk.split()[:5]
                    label = " ".join(words) + "..."
                else:
                    label = ", ".join(label_parts)
                
                saved_prompts.append(label)

        if not saved_prompts:
            saved_prompts = ["No saved prompts found"]

        # Reverse to show newest first
        saved_prompts.reverse()

        return {
            "required": {
                "saved_prompts": (saved_prompts,),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Prompt",)
    FUNCTION = "restore"
    CATEGORY = "Ollama"
    OUTPUT_NODE = True

    def restore(self, saved_prompts):
        """
        Finds the full text corresponding to the selected label.
        """
        if saved_prompts == "No saved prompts found":
            return {"ui": {"text": [""]}, "result": ("",)}

        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        all_file_path = os.path.join(elements_dir, "all.txt")
        separator = "="*60
        
        full_text = ""
        
        # Re-parse to find match
        if os.path.exists(all_file_path):
            with open(all_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            chunks = content.split(separator)
            valid_chunks = [c.strip() for c in chunks if c.strip()]
            
            target_label = saved_prompts
            
            for chunk in valid_chunks:
                # REPLICATE LABEL LOGIC
                lines = chunk.split('\n')
                short_map = {
                    "Subject": "Sub",
                    "Composition": "Com",
                    "Action": "Act",
                    "Location": "Loc",
                    "Style": "Sty"
                }
                label_parts = []
                theme_line = next((l for l in lines if l.startswith("Theme:")), None)
                if theme_line:
                    val = theme_line.split(":", 1)[1].strip()
                    words = val.split()[:3]
                    label_parts.append(f"Thm: {' '.join(words)}")

                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if k in short_map:
                            words = v.split()[:3]
                            short_val = " ".join(words)
                            if short_val:
                                label_parts.append(f"{short_map[k]}: {short_val}")
                
                if not label_parts:
                    words = chunk.split()[:5]
                    label = " ".join(words) + "..."
                else:
                    label = ", ".join(label_parts)
                
                if label == target_label:
                    lines_to_keep = []
                    for line in lines:
                        if not line.startswith("Theme:"):
                            lines_to_keep.append(line)
                    
                    full_text = "\n".join(lines_to_keep).strip()
                    break
        
        return {"ui": {"text": [full_text]}, "result": (full_text,)}