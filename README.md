# ComfyUI Ollama Banana

A suite of ComfyUI nodes integrating **Ollama** for Nana Banana Pro - intelligent prompting, character generation, and image management. Specifically designed for local LLM workflows ensuring privacy and no API costs.

## Features

- **Local LLM Integration**: Works with any model running on [Ollama](https://ollama.com) (Llama 3, Mistral, Llava, etc.).
- **Ollama NBP Character**: A powerful node for generating structured, consistent character prompts based on Nana Banana Pro structure (Subject, Costume, Location, Action) with **CSV Logging**.
- **Smart History**: Auto-saves prompts to a CSV file. The **Character Restore** node instantly syncs with this history, allowing you to browse and restore previous prompts with a live preview.
- **Vision-Aware Saving**: The **Ollama Image Saver** uses vision models (like LLaVA) to analyze your image and automatically generate descriptive filenames (e.g., `sbj-robot_loc-mars_act-running.png`).

## Nodes

### 1. Ollama NBP Character
Generates highly detailed prompts based on a "Theme" or purely random inspiration.
- **Inputs**: Theme, Model, URL.
- **Modes**: "Follow Theme", "Randomised", "Skip" for each category (Subject, Action, etc.).
- **CSV Logging**: Saves generated prompts to `elements/prompts.csv`.
- **AI Auto-Tagging**: Uses a secondary AI pass to generate concise 3-word summary tags for each prompt (e.g., `sbj-red_hoodie_boy_loc-dark_forest_night`).

### 2. Ollama Character Restore
Pairs with the NBP node to manage your prompt history.
- **Auto-Refresh**: Automatically updates its list when a new prompt is generated.
- **Instant Preview**: Selecting a prompt instantly displays the full text.
- **Restore**: Outputs the full prompt string for use in your workflow.

### 3. Ollama Image Saver
Saves images with intelligent metadata.
- **Vision Analysis**: Uses a vision model to "see" the image and name the file based on its content.
- **Metadata**: Embeds full ComfyUI workflow metadata (drag-and-drop compatible).
- **Format**: Lossless PNG (Level 4 compression).

### 4. Ollama LLM
A simple, general-purpose node for chatting with Ollama.

## Installation

1.  **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2.  **Pull Models**:
    *   For Text: `ollama run llama3` (or any other text model).
    *   For Vision (Image Saver): `ollama run llava` (or `moondream`, `llama3.2-vision`).
3.  **Install Node**:
    ```bash
    cd ComfyUI/custom_nodes
    git clone https://github.com/nickychung/comfyui-ollama-banana
    cd comfyui-ollama-banana
    pip install -r requirements.txt
    ```
    **NOTE**: if you are using portable verison of ComfyUI, you need to run `pip install -r requirements.txt` in the ComfyUI folder - ComfyUI/python_embeded
    
    
4.  **Restart ComfyUI**.

## Usage Tips

- **Vision Models**: For the Image Saver to work, you **must** have a vision-capable model selected (e.g., `Qwen3-vl:8b`). If you pick a text-only model, it will fail to describe the image.
- **Ollama URL**: Defaults to `http://127.0.0.1:11434`. Ensure Ollama is running in the background.

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**. 
You are free to use, modify, and distribute this software for personal, non-commercial purposes. Commercial use is strictly prohibited without prior permission.
