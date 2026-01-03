import requests
import json
import os
import folder_paths
from server import PromptServer
from aiohttp import web
import numpy as np
from PIL import Image
import io
import base64
import json
import csv
import time
from pathlib import Path
from datetime import datetime
try:
    from PIL import PngImagePlugin
except ImportError:
    pass

# Shared configuration - Simplified
# (No longer used for file mapping, but keeping folder name reference)

# Helper to fetch Ollama models
def get_ollama_models(url="http://127.0.0.1:11434"):
    try:
        # Use short timeout to not block UI load
        response = requests.get(f"{url}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            
            # Sort by modified_at descending (newest first)
            models.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            
            model_names = [m["name"] for m in models]
            
            return model_names
    except Exception:
        pass
        
    return ["gpt-oss:20b"]

class OllamaLLMNode:
    """
    A custom node for ComfyUI that interfaces with a local Ollama instance to generate text.
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        models = get_ollama_models()
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "model": (models,),
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
    
    # Map friendly names to UI input names
    ELEMENT_INPUTS = [
        "subject", "composition", "action", "location", "style", 
        "editing_instructions", "camera_lighting", "specific_text", 
        "factual_constraints"
    ]
    
    def __init__(self):
        self.elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        # Ensure elements dir exists
        if not os.path.exists(self.elements_dir):
            try:
                os.makedirs(self.elements_dir)
            except:
                pass

    @classmethod
    def INPUT_TYPES(s):
        # elements_dir logic moved/redundant but needed for CSV check
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        if not os.path.exists(elements_dir):
            try: 
                os.makedirs(elements_dir)
            except: 
                pass

        # Get models dynamically
        models = get_ollama_models()

        inputs = {
            "required": {
                "theme": ("STRING", {"multiline": True, "default": "Cyberpunk detective"}),
                "model": (models,),
                "url": ("STRING", {"default": "http://127.0.0.1:11434"}),
                "keep_alive": ("INT", {"default": 0, "min": 0, "max": 240, "step": 1}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            }
        }
        
        # Simple hardcoded options
        simple_options = ["Follow Theme", "Randomised", "Skip"]
        
        for key in s.ELEMENT_INPUTS:
            inputs["required"][f"{key}_input"] = (simple_options,)
            
        # Unified Save Toggle for CSV
        inputs["optional"]["save_to_csv"] = ("BOOLEAN", {"default": False, "label_on": "Save to CSV", "label_off": "Don't Save"})

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
                # Verbatim from file (Should not happen with new inputs, but kept for safety)
                final_elements[key] = input_val

        # 2. Call Ollama if needed
        generated_data = {}
        
        if to_generate_theme or to_generate_random:
            # Construct system prompt (Text based, robust to chatty models)
            system_instruction = (
                "You are an expert at creating detailed image generation prompts.\n"
                "Your task is to generate structured prompt elements with your best imagination based on a user Theme or Randomly.\n"
                "Describe the character’s clothing in rich and precise detail, either by following the provided Theme or by generating it randomly. The level of detail should adapt to the Composition: for close-up or portrait shots, focus only on upper-body attire and omit any lower-body descriptions; for medium or full-body compositions, ensure that lower-body clothing and footwear are clearly and thoroughly described.\n"
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
                "Composition: A photorealistic close-up portrait, framed from the chest to the top of the head.\n"
                "Subject: A young woman with pale skin and a very slender, skinny build with a small waist. She is wearing a black satin corset with mesh panels and subtle leather strapping details, accessorized with a simple black velvet choker.\n"
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
            }
            
            if seed is not None:
                payload["options"] = {"seed": seed}

            try:
                response = requests.post(api_url, json=payload)
                response.raise_for_status()
                result_json = response.json()
                content = result_json.get("response", "")
                
                print(f"Ollama Raw Output: {content}")

                # Robust Text Extraction using Regex / Line Logic
                # Check for each key we requested
                
                # Simple Line Parser Strategy
                lines = content.split('\n')
                current_key = None
                buffer = []
                
                def save_buffer(k, buf):
                    if k and buf:
                        generated_data[k] = " ".join(buf).strip()
                
                # Create a lookup for headers to keys
                header_map = {}
                for k, v in display_names.items():
                    header_map[v.lower()] = k
                    header_map[v.lower() + ":"] = k

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    is_header = False
                    line_lower = line.lower()
                    
                    for header_str, key_id in header_map.items():
                        if line_lower.startswith(header_str.lower()):
                            save_buffer(current_key, buffer)
                            current_key = key_id
                            buffer = []
                            
                            remainder = line[len(header_str):].strip()
                            if remainder.startswith(":"):
                                remainder = remainder[1:].strip()
                            
                            if remainder:
                                buffer.append(remainder)
                            is_header = True
                            break
                    
                    if not is_header:
                        if current_key:
                            buffer.append(line)
                            
                save_buffer(current_key, buffer)

            except Exception as e:
                print(f"Ollama API Error: {e}")
                
        # 3. Assemble Final Prompt & Generate Summary Tag
        for key in to_generate_theme + to_generate_random:
            if key in generated_data:
                final_elements[key] = generated_data[key]
            else:
                 final_elements[key] = ""

        prompt_parts = []
        for key in self.ELEMENT_INPUTS:
            if key in final_elements:
                val = str(final_elements[key])
                name = display_names[key]
                if val and val.strip():
                    prompt_parts.append(f"{name}: {val}")
        
        full_text = "\n".join(prompt_parts)
        
        # 4. Save to CSV Logic
        if kwargs.get("save_to_csv", False):
            try:
                # Generate Summary Tag using AI
                # Schema: thm-[2words]_sbj-[2words]_loc-[2words]_act-[2words]
                
                print("[OllamaNbpCharacter] Generating AI Summary Tag...")
                
                summary_prompt = (
                    "Analyze the following character description and extract 4 key elements: Theme, Subject, Location, and Action.\n"
                    "For each element, summarize it into exactly THREE words.\n"
                    "Format the output string EXACTLY like this: thm-word_word_word_sbj-word_word_word_loc-word_word_word_act-word_word_word\n"
                    "Use lowercase only. Use underscores between words in a pair. Use hyphens between the tag name and the words.\n"
                    "Do NOT output anything else. No intro, no explanation.\n\n"
                    f"Description:\n{full_text}\n"
                    f"Context Theme: {theme}\n"
                )
                
                summary_payload = {
                    "model": model,
                    "prompt": summary_prompt,
                    "stream": False,
                    "keep_alive": f"{keep_alive}m",
                    "options": {"temperature": 0.1} # Low temp for strict formatting
                }
                
                summary_tag = "thm-na_sbj-na_loc-na_act-na" # Default fallback
                
                try:
                    s_response = requests.post(api_url, json=summary_payload)
                    s_response.raise_for_status()
                    s_data = s_response.json()
                    s_content = s_data.get("response", "").strip().lower()
                    
                    # Basic validation: check if it looks roughly right
                    if "thm-" in s_content and "sbj-" in s_content:
                        # Clean up any extra whitespace or newlines
                        s_content = "".join(s_content.split())
                        summary_tag = s_content
                        print(f"[OllamaNbpCharacter] AI Summary: {summary_tag}")
                    else:
                        print(f"[OllamaNbpCharacter] AI Summary failed validation, text was: {s_content}")
                        # Fallback to regex if AI fails hard?
                        # For now, let's trust the AI or leave the error visible so user knows.
                        summary_tag = s_content if s_content else "error_generating_summary"
                        
                except Exception as e:
                    print(f"[OllamaNbpCharacter] AI Summary API Error: {e}")
                    # Fallback to simple construction if API fails
                    def get_tag_words(text):
                        if not text: return "na"
                        words = [w for w in re.findall(r'\w+', text.lower()) if len(w) > 2]
                        return "_".join(words[:2]) if words else "na"

                    sbj_t = get_tag_words(final_elements.get("subject", ""))
                    loc_t = get_tag_words(final_elements.get("location", ""))
                    thm_t = get_tag_words(theme)
                    act_t = get_tag_words(final_elements.get("action", ""))
                    summary_tag = f"thm-{thm_t}_sbj-{sbj_t}_loc-{loc_t}_act-{act_t}"

                csv_file_path = os.path.join(self.elements_dir, "prompts.csv")
                file_exists = os.path.exists(csv_file_path)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with open(csv_file_path, mode='a', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Timestamp', 'SummaryTag', 'FullPrompt']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    if not file_exists:
                        writer.writeheader()

                    writer.writerow({
                        'Timestamp': timestamp, 
                        'SummaryTag': summary_tag, 
                        'FullPrompt': full_text
                    })
                    
                print(f"[OllamaNbpCharacter] Saved to CSV: {summary_tag}")
                
                # Emit event to notify frontend
                try:
                    PromptServer.instance.send_sync("ollama.prompt_saved", {
                         "summary": summary_tag,
                         "timestamp": timestamp
                    })
                except Exception as e:
                    print(f"Error emitting event: {e}")
                
            except Exception as e:
                print(f"[OllamaNbpCharacter] Error saving CSV: {e}")

        print(f"Ollama NBP Character Final: {full_text}")
        
        return {"ui": {"text": [full_text]}, "result": (full_text,)}

class OllamaCharacterRestore:
    """
    Restores full character prompts saved in 'prompts.csv'.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        csv_file_path = os.path.join(elements_dir, "prompts.csv")
        
        saved_prompts = []
        
        if os.path.exists(csv_file_path):
            try:
                with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    # We expect columns: Timestamp, SummaryTag, FullPrompt
                    for row in reader:
                        ts = row.get("Timestamp", "Unknown Date")
                        tag = row.get("SummaryTag", "No Tag")
                        # We use a combined string for the dropdown
                        # Format: "YYYY-MM-DD HH:MM:SS - sbj-..."
                        label = f"{ts} - {tag}"
                        saved_prompts.append(label)
                    
                    # Reverse to show newest first
                    saved_prompts.reverse()
            except Exception as e:
                print(f"Error reading prompts.csv: {e}")
                saved_prompts = [f"Error reading CSV: {e}"]
        
        if not saved_prompts:
            saved_prompts = ["No saved prompts found"]

        return {
            "required": {
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

    def restore(self, saved_prompts):
        """
        Finds the full text corresponding to the selected label from the CSV.
        """
        if saved_prompts == "No saved prompts found" or saved_prompts.startswith("Error"):
             return {"ui": {"text": [""]}, "result": ("",)}

        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        csv_file_path = os.path.join(elements_dir, "prompts.csv")
        
        full_text = ""
        
        if not os.path.exists(csv_file_path):
             return {"ui": {"text": ["Error: prompts.csv not found"]}, "result": ("",)}
             
        try:
            with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ts = row.get("Timestamp", "Unknown Date")
                    tag = row.get("SummaryTag", "No Tag")
                    label = f"{ts} - {tag}"
                    
                    if label == saved_prompts:
                        full_text = row.get("FullPrompt", "")
                        break
        except Exception as e:
            print(f"Error restoring from CSV: {e}")
            full_text = f"Error: {e}"

        return {"ui": {"text": [full_text]}, "result": (full_text,)}

class OllamaImageSaver:
    """
    A custom node that saves images with filenames generated by Ollama's vision capabilities.
    """
    
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        # Show all models to avoid filtering issues
        models = get_ollama_models()
        
        # Get user's download directory as default
        try:
             default_path = str(Path.home() / "Downloads")
        except:
             default_path = "./output"

        return {
            "required": {
                "images": ("IMAGE",),
                "folder_path": ("STRING", {"default": default_path}),
                "model": (models,),
                "url": ("STRING", {"default": "http://127.0.0.1:11434"}),
            },
            "optional": {
                "filename_prefix": ("STRING", {"default": ""}),
                "add_metadata": ("BOOLEAN", {"default": True, "label_on": "Add Metadata (WxH, Date)", "label_off": "No Metadata"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "Ollama"

    def save_images(self, images, folder_path, model, url, filename_prefix="Ollama", add_metadata=True, prompt=None, extra_pnginfo=None, **kwargs):
        
        ollama_prompt = "Analyze the image and generate a filename part using EXACTLY this format: sbj-[subject_two_words]_loc-[location_two_words]_thm-[theme_two_words]_act-[action_two_words]. Replace brackets with 2 descriptive words separated by underscore. Use lowercase only. Example: sbj-young_girl_loc-floral_garden_thm-green_nature_act-sitting_ground. Do not output anything else."
        
        # Robust Argument Recovery for Stale Workflows
        # Scan 'url', 'filename_prefix', and 'kwargs' for the real URL.
        # The prompt is likely in 'url' due to positional shift.
        
        candidates = [url, filename_prefix] + list(kwargs.values())
        real_url = "http://127.0.0.1:11434" # Fallback default
        found_url = False
        
        # 1. Identify valid URL
        for c in candidates:
            if isinstance(c, str) and (c.startswith("http://") or c.startswith("https://")):
                real_url = c
                found_url = True
                break
        
        # 2. Logic to detect if we need to swap
        # If 'url' is NOT the real URL (e.g. it's the prompt text), we override it.
        # We only override if we found a better candidate OR if the current 'url' is clearly invalid (has spaces, long text).
        
        is_url_invalid = isinstance(url, str) and (" " in url or len(url) > 100 or not url.startswith("http"))
        
        if found_url:
            if is_url_invalid or url != real_url:
                print(f"OllamaImageSaver: Correcting argument mismatch. {url[:20]}... -> {real_url}")
                url = real_url
                
                # If we used filename_prefix as the source, reset filename_prefix to default
                if filename_prefix == real_url:
                    filename_prefix = "Ollama"
        else:
            # If no URL found at all, but current 'url' is bad, force default
            if is_url_invalid:
                 print(f"OllamaImageSaver: Invalid URL detected ('{url[:20]}...'). Reverting to default.")
                 url = "http://127.0.0.1:11434"
                 if filename_prefix == url: 
                    filename_prefix = "Ollama"

        results = []
        
        # Ensure output directory exists
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except Exception as e:
                print(f"Error creating directory {folder_path}: {e}")
                return {}

        for batch_number, image in enumerate(images):
            # 1. Convert Tensor to PIL
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # 2. Prepare for Ollama (Base64)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # 3. Call Ollama Vision
            keywords = "image"
            if model:
                try:
                    api_url = f"{url}/api/generate"
                    payload = {
                        "model": model,
                        "prompt": ollama_prompt,
                        "images": [img_base64],
                        "stream": False
                    }
                    print(f"Sending image to Ollama ({model})...")
                    response = requests.post(api_url, json=payload)
                    response.raise_for_status()
                    
                    response_data = response.json()
                    raw_text = response_data.get("response", "")
                    
                    # 4. Clean up keywords
                    # Apply simple cleaning but allow hyphens for the tag format (sbj-..., loc-...)
                    # We allow alphanumeric, underscores, and hyphens.
                    cleaned = "".join([c if c.isalnum() or c == "-" else "_" for c in raw_text])
                    # Remove duplicate underscores
                    while "__" in cleaned:
                        cleaned = cleaned.replace("__", "_")
                        
                    keywords = cleaned.strip("_")
                    # Limit length
                    if len(keywords) > 200:
                        keywords = keywords[:200]
                        
                except Exception as e:
                    print(f"Ollama Vision Error: {e}")
                    keywords = "ollama_error"
            
            # 5. Construct Filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            width, height = img.size
            
            filename_parts = []
            if filename_prefix:
                filename_parts.append(filename_prefix)
            
            filename_parts.append(keywords)
            
            if add_metadata:
                filename_parts.append(f"{width}x{height}")
                filename_parts.append(timestamp)
                
            filename = "_".join(filename_parts) + ".png"
            
            # 6. Save Image (Lossless PNG) with Metadata
            full_path = os.path.join(folder_path, filename)
            
            metadata = PngImagePlugin.PngInfo()
            
            # Helper: Recursive Masking of Sensitive Keys
            def sanitize_metadata(data):
                if isinstance(data, dict):
                    new_data = {}
                    for k, v in data.items():
                        # Check recursively
                        cleaned_v = sanitize_metadata(v)
                        
                        # Check key name for sensitive terms
                        k_lower = k.lower()
                        sensitive_terms = ["api_key", "apikey", "secret", "token", "password", "auth", "key"]
                        
                        # Special logic: "key" is very generic, so usually we look for exact "api_key" etc.
                        # But if the user says "API KEY value is also stored", let's be aggressive on specific known patterns.
                        # Pattern matching: specific keys usually found in AI nodes.
                        if any(term in k_lower for term in ["api_key", "apikey", "auth_token", "access_token"]):
                            new_data[k] = "***MASKED***"
                        # Also handle "google_api_key", "openai_key" etc.
                        elif "_key" in k_lower and "model" not in k_lower and "hotkey" not in k_lower: 
                            # heuristic to avoid masking 'hotkeys' or 'model_key' if that existed.
                            new_data[k] = "***MASKED***"
                        else:
                            new_data[k] = cleaned_v
                    return new_data
                    
                elif isinstance(data, list):
                    return [sanitize_metadata(item) for item in data]
                else:
                    return data

            if prompt is not None:
                # Sanitize the full prompt structure
                safe_prompt = sanitize_metadata(prompt)
                metadata.add_text("prompt", json.dumps(safe_prompt))
                
            if extra_pnginfo is not None:
                safe_extra = sanitize_metadata(extra_pnginfo)
                for x in safe_extra:
                    metadata.add_text(x, json.dumps(safe_extra[x]))

            try:
                img.save(full_path, format="PNG", pnginfo=metadata, optimize=False, compress_level=4)
                print(f"Saved image to: {full_path}")
            except Exception as e:
                print(f"Error saving image: {e}")

        return {"ui": {"images": results}}

# API Route to fetch CSV prompts list (for refresh)
@PromptServer.instance.routes.post("/ollama/get_csv_prompts")
async def get_csv_prompts(request):
    try:
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        csv_file_path = os.path.join(elements_dir, "prompts.csv")
        
        saved_prompts = []
        if os.path.exists(csv_file_path):
             with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ts = row.get("Timestamp", "Unknown Date")
                    tag = row.get("SummaryTag", "No Tag")
                    label = f"{ts} - {tag}"
                    saved_prompts.append(label)
                saved_prompts.reverse()
        
        if not saved_prompts:
            saved_prompts = ["No saved prompts found"]
            
        return web.json_response(saved_prompts)
    except Exception as e:
         return web.Response(status=500, text=str(e))

# API Route to fetch CSV content for preview
@PromptServer.instance.routes.post("/ollama/get_csv_content")
async def get_csv_content(request):
    try:
        data = await request.json()
        label_target = data.get("label")
        
        if not label_target:
             return web.Response(status=400, text="Missing label")
             
        elements_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "elements")
        csv_file_path = os.path.join(elements_dir, "prompts.csv")
        
        full_text = ""
        
        if os.path.exists(csv_file_path):
            try:
                with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        ts = row.get("Timestamp", "Unknown Date")
                        tag = row.get("SummaryTag", "No Tag")
                        label = f"{ts} - {tag}"
                        
                        if label == label_target:
                            full_text = row.get("FullPrompt", "")
                            break
            except Exception as e:
                print(f"Error reading CSV for preview: {e}")
                full_text = f"Error: {e}"
                
        return web.json_response({"content": full_text})
        
    except Exception as e:
        print(f"Error serving CSV content: {e}")
        return web.Response(status=500, text=str(e))

NODE_CLASS_MAPPINGS = {
    "OllamaLLMNode": OllamaLLMNode,
    "OllamaNbpCharacter": OllamaNbpCharacter,
    "OllamaCharacterRestore": OllamaCharacterRestore,
    "OllamaImageSaver": OllamaImageSaver
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaLLMNode": "Ollama LLM",
    "OllamaNbpCharacter": "Ollama NBP Character",
    "OllamaCharacterRestore": "Ollama Character Restore",
    "OllamaImageSaver": "Ollama Image Saver"
}