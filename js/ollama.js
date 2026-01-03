import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { api } from "../../scripts/api.js";

// Extension for OllamaNbpCharacter (Auto-refresh dropdowns if we add back saving?)
// Currently we don't have dynamic saving to the CSV via API, only via execution. 
// So the "ollama.option_saved" event is not emitted/handled in the same way.
// We can leave NBP alone or implement a mechanism later.

app.registerExtension({
    name: "Comfy.OllamaCharacterRestore",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaCharacterRestore") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                const promptsWidget = this.widgets.find((w) => w.name === "saved_prompts");

                // Helper to update preview text
                const updatePreview = async () => {
                    const labelVal = promptsWidget?.value;

                    if (!labelVal) return;
                    if (labelVal === "No saved prompts found") return;

                    // Find or create preview widget
                    let previewWidget = this.widgets.find(w => w.name === "preview_text");
                    if (!previewWidget) {
                        const w = ComfyWidgets.STRING(this, "preview_text", ["STRING", { multiline: true }], app).widget;
                        w.inputEl.readOnly = true;
                        w.inputEl.style.opacity = 0.6;
                        previewWidget = w;
                    }

                    try {
                        const response = await api.fetchApi("/ollama/get_csv_content", {
                            method: "POST",
                            body: JSON.stringify({ label: labelVal }),
                        });

                        if (response.ok) {
                            const data = await response.json();
                            if (previewWidget) {
                                previewWidget.value = data.content;
                            }
                        }
                    } catch (e) {
                        console.error("[Ollama] Failed to fetch content preview", e);
                    }
                };

                if (promptsWidget) {
                    promptsWidget.callback = async (value) => {
                        await updatePreview();
                        this.setDirtyCanvas(true);
                    };
                    
                    // Trigger once on load if value exists
                    setTimeout(() => {
                        if (promptsWidget.value) {
                            updatePreview();
                        }
                    }, 100);
                }

                // Initialize preview widget on load
                if (!this.widgets.find(w => w.name === "preview_text")) {
                    const w = ComfyWidgets.STRING(this, "preview_text", ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.6;
                }

                this.setSize([this.size[0], Math.max(this.size[1], 400)]);
            };
            
            // Standard onExecuted to update preview if it runs (backend also returns text)
             const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                if (message && message.text && message.text.length > 0) {
                    const widget = this.widgets?.find((w) => w.name === "preview_text");
                    if (widget) {
                        widget.value = message.text[0];
                    }
                    this.onResize?.(this.size);
                }
            };
        }
    },
});

app.registerExtension({
    name: "Comfy.OllamaLLMNode",
     async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaLLMNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);
                if (!this.widgets || !this.widgets.find(w => w.name === "generated_text")) {
                    const w = ComfyWidgets.STRING(this, "generated_text", ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.6;
                }
                this.setSize([this.size[0], Math.max(this.size[1], 300)]);
            };
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                if (message && message.text && message.text.length > 0) {
                    const text = message.text[0];
                    const widget = this.widgets?.find((w) => w.name === "generated_text");
                    if (widget) { widget.value = text; }
                    this.onResize?.(this.size);
                }
            };
        }
    },
});
