import requests
import json
import os
from server import PromptServer
from aiohttp import web

# Shared configuration
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

# Helper functions for label generation
def parse_single_line(line):
    line = line.strip()
    if not line: return ""
    words = line.split()
    if len(words) > 10:
        return " ".join(words[:10]) + "..."
    return line

def parse_all_txt_chunk(chunk):
    chunk = chunk.strip()
    if not chunk: return ""
    
    lines = chunk.split('\n')
    short_map = {"Subject": "Sub", "Composition": "Com", "Action": "Act", "Location": "Loc", "Style": "Sty"}
    label_parts = []
    
    # Helper to pick 3 random words deterministically
    def get_random_3(text):
        words = text.split()
        if not words: return ""
        if len(words) <= 3: return " ".join(words)
        # Deterministic seed based on the text content
        import random
        rng = random.Random(text)
        chosen = rng.sample(words, 3)
        return " ".join(chosen)

    theme_line = next((l for l in lines if l.startswith("Theme:")), None)
    if theme_line:
        if ":" in theme_line:
            val = theme_line.split(":", 1)[1].strip()
            short_val = get_random_3(val)
            if short_val:
                label_parts.append(f"Thm: {short_val}")

    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            if k in short_map:
                short_val = get_random_3(v)
                if short_val:
                    label_parts.append(f"{short_map[k]}: {short_val}")
    
    if not label_parts:
        # Fallback if no structured parts found
        return " ".join(chunk.split()[:5]) + "..."
    
    return ", ".join(label_parts)

# Add API Route to fetch options dynamically
@PromptServer.instance.routes.post("/ollama/get_options")
async def get_options(request):
    try:
        data = await request.json()
        filename = data.get("filename")
        
        if not filename:
            return web.Response(status=400, text="Missing filename")
            
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        file_path = os.path.join(elements_dir, filename)
        
        options = []
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Special parsing for 'all.txt'
            if filename == "all.txt":
                separator = "="*60
                chunks = content.split(separator)
                for chunk in chunks:
                    label = parse_all_txt_chunk(chunk)
                    if label:
                        options.append(label)
                
                # Reverse to show newest first
                options.reverse()
                
            else:
                # Standard line-based files
                lines = content.split('\n')
                for line in lines:
                    label = parse_single_line(line)
                    if label:
                        options.append(label)
                
                # Reverse standard files too? Usually yes for "saved recently"
                options.reverse()
        
        if not options:
            options = ["No saved prompts found"]
            
        return web.json_response(options)
        
    except Exception as e:
        print(f"Error serving options: {e}")
        return web.Response(status=500, text=str(e))

@PromptServer.instance.routes.post("/ollama/get_content")
async def get_content(request):
    try:
        data = await request.json()
        filename = data.get("filename")
        label_target = data.get("label")
        
        if not filename or not label_target:
            return web.Response(status=400, text="Missing filename or label")
            
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        file_path = os.path.join(elements_dir, filename)
        
        full_text = ""
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if filename == "all.txt":
                separator = "="*60
                chunks = content.split(separator)
                valid_chunks = [c.strip() for c in chunks if c.strip()]
                
                # Re-do logic to match label
                for chunk in valid_chunks:
                    label = parse_all_txt_chunk(chunk)
                        
                    if label == label_target:
                        lines = chunk.split('\n')
                        lines_to_keep = [l for l in lines if not l.startswith("Theme:")]
                        full_text = "\n".join(lines_to_keep).strip()
                        break
            else:
                # Line based
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    label = parse_single_line(line)
                    
                    if label == label_target:
                        full_text = line
                        break
                        
        return web.json_response({"content": full_text})
        
    except Exception as e:
        print(f"Error serving content: {e}")
        return web.Response(status=500, text=str(e))


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
    
    # Use shared map
    ELEMENT_FILES_MAP = ELEMENT_FILES

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
        
        file_path = os.path.join(self.elements_dir, self.ELEMENT_FILES_MAP[element_key])
        
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
            
        # Use shared map
        element_map = ELEMENT_FILES

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
    Restores full character prompts saved in 'all.txt' or individual element files.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        # file_list: [all.txt, subject.txt, ...]
        file_list = ["all.txt"] + list(ELEMENT_FILES.values())
        
        # We start with the options from ALL (default)
        # Note: ComfyUI will execute this ONCE on load. Dynamic updates handled by JS.
        # We need to pre-populate 'saved_prompts' based on 'all.txt' defaults so it works on first load.
        
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        all_file_path = os.path.join(elements_dir, "all.txt")
        saved_prompts = []
        
        # --- LOGIC DUPLICATED FROM API FOR INITIAL LOAD ---
        # (Alternatively we could call a shared function)
        if os.path.exists(all_file_path):
             with open(all_file_path, "r", encoding="utf-8") as f:
                content = f.read()
                separator = "="*60
                chunks = content.split(separator)
                for chunk in chunks:
                    label = parse_all_txt_chunk(chunk)
                    if label:
                        saved_prompts.append(label)
        
        if not saved_prompts:
            saved_prompts = ["No saved prompts found"]
        saved_prompts.reverse()
        # ----------------------------------------------------

        return {
            "required": {
                "source_file": (file_list,),
                "saved_prompts": (saved_prompts,),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        return True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Prompt",)
    FUNCTION = "restore"
    CATEGORY = "Ollama"
    OUTPUT_NODE = True

    def restore(self, source_file, saved_prompts):
        """
        Finds the full text corresponding to the selected label from the selected file.
        """
        if saved_prompts == "No saved prompts found":
             return {"ui": {"text": [""]}, "result": ("",)}

        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        file_path = os.path.join(elements_dir, source_file)
        
        full_text = ""
        
        if not os.path.exists(file_path):
             return {"ui": {"text": [f"Error: File {source_file} not found"]}, "result": ("",)}
             
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # LOGIC BRANCH based on source_file
        if source_file == "all.txt":
            separator = "="*60
            chunks = content.split(separator)
            valid_chunks = [c.strip() for c in chunks if c.strip()]
            
            target_label = saved_prompts
            
            for chunk in valid_chunks:
                label = parse_all_txt_chunk(chunk)
                
                if label == target_label:
                    lines = chunk.split('\n')
                    lines_to_keep = [l for l in lines if not l.startswith("Theme:")]
                    full_text = "\n".join(lines_to_keep).strip()
                    break
        else:
            # Simple line-based matching for other files
            target_label = saved_prompts
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                
                label = parse_single_line(line)
                    
                if label == target_label:
                    full_text = line
                    break

        return {"ui": {"text": [full_text]}, "result": (full_text,)}