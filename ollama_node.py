import requests
import json

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
    """
    
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "theme": ("STRING", {"multiline": True}),
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
    FUNCTION = "generate_character_prompt"
    CATEGORY = "Ollama"
    OUTPUT_NODE = True

    def generate_character_prompt(self, theme, model, url, keep_alive, seed=None):
        """
        Generates a character prompt using the Ollama API based on the provided theme.
        """
        api_url = f"{url}/api/generate"
        
        system_instruction = (
            "You are an expert at creating detailed image generation prompts. "
            "Create a character prompt based on the user's theme using the following structure:\\n"
            "• Subject: Who or what is in the image? Be specific. (e.g., a stoic robot barista with glowing blue optics; a fluffy calico cat wearing a tiny wizard hat).\\n"
            "• Composition: How is the shot framed? (e.g., extreme close-up, wide shot, low angle shot, portrait).\\n"
            "• Action: What is happening? (e.g., brewing a cup of coffee, casting a magical spell, mid-stride running through a field).\\n"
            "• Location: Where does the scene take place? (e.g., a futuristic cafe on Mars, a cluttered alchemist's library, a sun-drenched meadow at golden hour).\\n"
            "• Style: What is the overall aesthetic? (e.g., 3D animation, film noir, watercolor painting, photorealistic, 1990s product photography).\\n"
            "• Editing Instructions: For modifying an existing image, be direct and specific. (e.g., change the man's tie to green, remove the car in the background)\\n"
            "• Camera and lighting details: Direct the shot like a cinematographer. (e.g., \"A low-angle shot with a shallow depth of field (f/1.8),\" \"Golden hour backlighting creating long shadows,\" \"Cinematic color grading with muted teal tones.\")\\n"
            "• Specific text integration: Clearly state what text should appear and how it should look. (e.g., \"The headline 'URBAN EXPLORER' rendered in bold, white, sans-serif font at the top.\")\\n"
            "• Factual constraints (for diagrams): Specify the need for accuracy and ensure your inputs themselves are factual (e.g., \"A scientifically accurate cross-section diagram,\" \"Ensure historical accuracy for the Victorian era.\").\\n"
            "• Reference inputs: When using uploaded images, clearly define the role of each. (e.g., \"Use Image A for the character's pose, Image B for the art style, and Image C for the background environment.\")\\n"
            "\\n"
            "Example of the generated result:\\n"
            "Subject: A young woman with pale skin and a very slender, skinny build with a small waist. She has grey hair with distinct pink and blue highlights. She is wearing a black satin corset with mesh panels and subtle leather strapping details, accessorized with a simple black velvet choker.\\n"
            "Composition: A photorealistic close-up portrait, framed from the chest to the top of the head.\\n"
            "Action: She is seated at a cluttered antique vanity table. Her body is turned away, but she turns her head over her shoulder to look directly into the camera with a sultry, confident gaze. One hand rests on the aged wooden table near a perfume bottle.\\n"
            "Location: A dimly lit, bohemian bedroom in Paris. The background consists of a warm bokeh of tarnished silver hand-mirrors, vintage cosmetics, and heavy, dark tapestries.\\n"
            "Style: Photorealistic, cinematic, and ultra-high resolution (8k). The aesthetic should mimic the look of Kodak Portra 400 film.\\n"
            "Editing Instructions: N/A\\n"
            "Camera and lighting details: Shot on Kodak Portra 400 film. The scene is lit by the warm, soft glow of a vintage desk lamp on the vanity, creating deep shadows and intimate highlights on her décolletage and the metallic hair highlights.\\n"
            "Specific text integration: N/A\\n"
            "Factual constraints (for diagrams): N/A\\n"
            "Reference inputs: Use the uploaded picture for face consistency: KEEP all facial features EXACTLY the SAME as the uploaded picture. Do not alter identity, age, face shape, or expression.\\n"
        )
        
        full_prompt = f"{system_instruction}\\n\\nTheme: {theme}\\nGenerate the character prompt:"
        
        payload = {
            "model": model,
            "prompt": full_prompt,
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
            
            print(f"Ollama NBP Character Generated Text: {generated_text}")
            
            return {"ui": {"text": [generated_text]}, "result": (generated_text,)}
            
        except requests.exceptions.RequestException as e:
            return {"ui": {"text": [f"Error: {str(e)}"]}, "result": (f"Error: {str(e)}",)}
        except json.JSONDecodeError:
             return {"ui": {"text": ["Error: Failed to decode JSON response from Ollama."]}, "result": ("Error: Failed to decode JSON response from Ollama.",)}
        except Exception as e:
             return {"ui": {"text": [f"Error: An unexpected error occurred: {str(e)}"]}, "result": (f"Error: An unexpected error occurred: {str(e)}",)}
