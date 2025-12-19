app.registerExtension({
	name: "Comfy.OllamaLLMNode",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "OllamaLLMNode") {
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
                
                // message is what we return in "ui" from python
                // python returns: {"ui": {"text": [text]}, ...}
                
				if (message && message.text && message.text.length > 0) {
					const text = message.text[0];
                    
                    // Try to find a widget named "generated_text"
                    const widget = this.widgets?.find((w) => w.name === "generated_text");
                    
                    if (widget) {
                        widget.value = text;
                    } else {
                        // If it doesn't exist, create it.
                        // We use a custom widget or standard string widget.
                        // Note: ComfyUI widgets created dynamically might not save properly, but for display it's fine.
                        // Ideally, we define it in Python, but Python can't easily define 'output' widgets.
                        
                         const w = this.addWidget("text", "generated_text", text, (v) => {}, { multiline: true });
                         w.inputEl.readOnly = true;
                         w.inputEl.style.opacity = 0.6;
                    }
                    
                    // Force a redraw
                    this.setDirtyCanvas(true, true);
				}
			};
		}
	},
});
