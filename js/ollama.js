app.registerExtension({
    name: "Comfy.OllamaLLMNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        console.log("Loading Ollama Node Extension...");
        if (nodeData.name === "OllamaLLMNode") {
            // 1. Add the widget immediately when the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Create the widget if it doesn't exist
                if (!this.widgets || !this.widgets.find(w => w.name === "generated_text")) {
                    const w = this.addWidget("text", "generated_text", "", (v) => { }, { multiline: true });
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.6;
                }

                // Make sure it's resized specifically for multiline
                this.setSize([this.size[0], Math.max(this.size[1], 150)]);
            };

            // 2. Update the widget when the node executes
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                if (message && message.text && message.text.length > 0) {
                    const text = message.text[0];
                    const widget = this.widgets?.find((w) => w.name === "generated_text");

                    if (widget) {
                        widget.value = text;
                    }

                    this.onResize?.(this.size);
                }
            };
        }
    },
});
