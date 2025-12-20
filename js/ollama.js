import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "Comfy.OllamaLLMNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaLLMNode") {
            // 1. Add the widget immediately when the node is created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Create the widget if it doesn't exist
                if (!this.widgets || !this.widgets.find(w => w.name === "generated_text")) {
                    // Use ComfyWidgets to create a DOM-based text widget (like the prompt box)
                    // Signature: STRING(node, inputName, inputData, app)
                    const w = ComfyWidgets.STRING(this, "generated_text", ["STRING", { multiline: true }], app).widget;

                    // Now inputEl should be available because it's a DOM widget
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.6;
                }

                // Resize node to be tall enough for output
                this.setSize([this.size[0], Math.max(this.size[1], 300)]);
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
