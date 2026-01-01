import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "Comfy.OllamaImageSaver.Browse",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaImageSaver") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                // Add Browse Button
                // We add it as a widget.
                // addWidget(type, name, value, callback, options)

                const browseBtn = this.addWidget("button", "Select Folder (Local)", "Browse...", () => {
                    // Disable button to prevent double clicks?

                    api.fetchApi("/ollama/browse", { method: "POST" })
                        .then(response => response.json())
                        .then(data => {
                            if (data.path) {
                                // Update folder_path widget
                                const folderWidget = this.widgets.find(w => w.name === "folder_path");
                                if (folderWidget) {
                                    folderWidget.value = data.path;
                                    // Trigger redraw
                                    this.setDirtyCanvas(true);
                                }
                            }
                        })
                        .catch(err => {
                            console.error("Error browsing folder:", err);
                            alert("Error opening folder picker on server. Check server console.");
                        });
                });

                // Optional: Move button to be near folder_path?
                // Default adds to bottom. That is fine.
            };
        }
    },
});
