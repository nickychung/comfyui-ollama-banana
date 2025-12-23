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

import { api } from "../../scripts/api.js";

api.addEventListener("ollama.option_saved", (event) => {
    const { element, content } = event.detail;
    if (!element || !content) return;

    // Map element key to input name (e.g., "subject" -> "subject_input")
    const widgetName = `${element}_input`;

    // Find all OllamaNbpCharacter nodes
    const graph = app.graph;
    if (!graph) return;

    graph.findNodesByType("OllamaNbpCharacter").forEach((node) => {
        const widget = node.widgets?.find((w) => w.name === widgetName);
        if (widget) {
            // Check if it's a combo/dropdown widget
            if (widget.type === "combo" || Array.isArray(widget.options?.values)) {
                const values = widget.options.values;
                // Add if not exists
                if (!values.includes(content)) {
                    values.push(content);
                    // Optionally set it as current value?
                    // user might prefer it stays on what it was, or switches.
                    // For now, just adding it to the list is safer.
                    console.log(`[Ollama] Updated ${widgetName} with new option:`, content);
                }
            }
        }
    });
});

app.registerExtension({
    name: "Comfy.OllamaCharacterRestore",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaCharacterRestore") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                const sourceWidget = this.widgets.find((w) => w.name === "source_file");
                const promptsWidget = this.widgets.find((w) => w.name === "saved_prompts");

                // Helper to update preview text
                const updatePreview = async () => {
                    const fileVal = sourceWidget?.value;
                    const labelVal = promptsWidget?.value;

                    if (!fileVal || !labelVal) return;

                    // Find or create preview widget
                    let previewWidget = this.widgets.find(w => w.name === "preview_text");
                    if (!previewWidget) {
                        const w = ComfyWidgets.STRING(this, "preview_text", ["STRING", { multiline: true }], app).widget;
                        w.inputEl.readOnly = true;
                        w.inputEl.style.opacity = 0.6;
                        previewWidget = w;
                    }

                    try {
                        const response = await api.fetchApi("/ollama/get_content", {
                            method: "POST",
                            body: JSON.stringify({ filename: fileVal, label: labelVal }),
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

                if (sourceWidget && promptsWidget) {
                    // 1. Callback when source file changes
                    sourceWidget.callback = async (value) => {
                        if (!value) return;

                        try {
                            const response = await api.fetchApi("/ollama/get_options", {
                                method: "POST",
                                body: JSON.stringify({ filename: value }),
                            });

                            if (response.ok) {
                                const options = await response.json();
                                promptsWidget.options.values = options;

                                // Reset to first option by default
                                if (options.length > 0) {
                                    promptsWidget.value = options[0];
                                } else {
                                    promptsWidget.value = "";
                                }

                                // Trigger preview update immediately
                                await updatePreview();

                                // Force redraw
                                this.setDirtyCanvas(true);
                            }
                        } catch (error) {
                            console.error("[Ollama] Failed to fetch options:", error);
                        }
                    };

                    // 2. Callback when specific prompt is selected
                    promptsWidget.callback = async (value) => {
                        await updatePreview();
                        this.setDirtyCanvas(true);
                    };
                }

                // Initialize preview widget on load
                if (!this.widgets.find(w => w.name === "preview_text")) {
                    const w = ComfyWidgets.STRING(this, "preview_text", ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.6;
                }

                this.setSize([this.size[0], Math.max(this.size[1], 400)]);

                // Trigger initial preview load after slight delay to ensure widgets ready
                setTimeout(() => {
                    if (sourceWidget && promptsWidget && sourceWidget.value && promptsWidget.value) {
                        updatePreview();
                    }
                }, 100);
            };

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
