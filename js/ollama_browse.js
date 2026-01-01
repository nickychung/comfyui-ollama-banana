import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "Comfy.OllamaImageSaver.Browse",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "OllamaImageSaver") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);

                const browseBtn = this.addWidget("button", "Select Folder (Local)", "Browse...", () => {
                    api.fetchApi("/ollama/browse", { method: "POST" })
                        .then(response => response.json())
                        .then(data => {
                            if (data.path) {
                                const folderWidget = this.widgets.find(w => w.name === "folder_path");
                                if (folderWidget) {
                                    folderWidget.value = data.path;
                                    this.setDirtyCanvas(true);
                                }
                            }
                        })
                        .catch(err => {
                            console.error("Error browsing folder:", err);
                        });
                });

                // 1. Move Button to be before 'folder_path' (Top of folder_path)
                const folderIdx = this.widgets.findIndex(w => w.name === "folder_path");
                if (folderIdx !== -1) {
                    // Remove button from end (it was just added)
                    const btnIdx = this.widgets.indexOf(browseBtn);
                    if (btnIdx !== -1) {
                        this.widgets.splice(btnIdx, 1);
                        // Insert AT folderIdx to perform "before" insertion
                        this.widgets.splice(folderIdx, 0, browseBtn);
                    }
                }

                // 2. Check Tkinter Status and dim/disable if needed
                api.fetchApi("/ollama/check_tkinter")
                    .then(response => response.json())
                    .then(data => {
                        if (!data.available) {
                            browseBtn.name = "Browse (Unavailable - Missing Tkinter)";
                            // ComfyUI buttons are functional via callback.
                            // We replace the callback to show alert.
                            browseBtn.callback = () => {
                                alert("Folder browsing is disabled because Tkinter is missing on the server (System Python Required).");
                            };
                            // No standard visual disabled state, but changing name indicates it.
                        }
                    })
                    .catch(() => { });
            };
        }
    },
});
