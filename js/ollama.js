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

// Listener for Prompt Saved Event to trigger Auto-Refresh
api.addEventListener("ollama.prompt_saved", async (event) => {
    // We could use the data to optimize, but simplest is to just fetch the latest list
    const graph = app.graph;
    if (!graph) return;

    // Find all Restore Nodes
    const restoreNodes = graph.findNodesByType("OllamaCharacterRestore");
    if (restoreNodes.length === 0) return;

    try {
        const response = await api.fetchApi("/ollama/get_csv_prompts", { method: "POST" });
        if (response.ok) {
            const newOptions = await response.json();

            for (const node of restoreNodes) {
                const widget = node.widgets?.find((w) => w.name === "saved_prompts");
                if (widget) {
                    const currentVal = widget.value;
                    widget.options.values = newOptions;

                    // If existing value is not in new list (unlikely if strictly adding), valid check
                    // If "No saved prompts found" was selected, auto-select the new one
                    if (currentVal === "No saved prompts found" && newOptions.length > 0) {
                        widget.value = newOptions[0];
                        // Trigger callback to update preview
                        if (widget.callback) {
                            widget.callback(widget.value);
                        }
                    }

                    // If the user wants to jump to the NEWEST item automatically:
                    // newOptions[0] is the newest.
                    // Let's assume yes, if they are generating, they likely want to see the result.
                    if (newOptions.length > 0 && newOptions[0] !== currentVal) {
                        // Only switch if the top item is different (it should be)
                        // But maybe they are browsing an old one? 
                        // UX decision: Auto-Switching might be annoying if they are comparing.
                        // But users usually generate -> restore immediate.
                        // Let's Auto-Switch for now as per "refresh and get latest" request.
                        widget.value = newOptions[0];
                        if (widget.callback) widget.callback(widget.value);
                    }
                }
            }
        }
    } catch (e) {
        console.error("[Ollama] Failed to auto-refresh prompts", e);
    }
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
