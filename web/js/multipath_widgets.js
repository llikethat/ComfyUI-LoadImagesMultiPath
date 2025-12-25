import { app } from "../../../scripts/app.js";

/**
 * LoadImagesMultiPath Widget Controller
 * 
 * This extension handles the dynamic visibility of directory widgets
 * based on the path_count value.
 */

const MULTI_PATH_NODE_TYPES = [
    "LoadImagesMultiPath_Upload",
    "LoadImagesMultiPath_Path"
];

const MAX_PATH_COUNT = 50;

/**
 * Updates the visibility of directory widgets based on path_count
 */
function updateDirectoryWidgetsVisibility(node) {
    if (!node.widgets) return;
    
    // Find the path_count widget
    const pathCountWidget = node.widgets.find(w => w.name === "path_count");
    if (!pathCountWidget) return;
    
    const pathCount = parseInt(pathCountWidget.value) || 1;
    
    let visibleCount = 0;
    
    // Update visibility of each directory widget
    for (let i = 1; i <= MAX_PATH_COUNT; i++) {
        const dirWidgetName = `directory_${i}`;
        const dirWidget = node.widgets.find(w => w.name === dirWidgetName);
        
        if (dirWidget) {
            if (i <= pathCount) {
                // Show widget
                dirWidget.hidden = false;
                dirWidget.type = dirWidget.origType || dirWidget.type;
                visibleCount++;
            } else {
                // Hide widget
                dirWidget.hidden = true;
                dirWidget.origType = dirWidget.origType || dirWidget.type;
                dirWidget.type = "hidden";
            }
        }
    }
    
    // Recalculate node size
    node.setSize(node.computeSize());
    
    // Mark the graph as dirty to trigger redraw
    if (app.graph) {
        app.graph.setDirtyCanvas(true, true);
    }
}

app.registerExtension({
    name: "LoadImagesMultiPath.WidgetController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Only apply to multi-path nodes
        if (!MULTI_PATH_NODE_TYPES.includes(nodeData.name)) {
            return;
        }
        
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = onNodeCreated?.apply(this, arguments);
            
            const node = this;
            
            // Find the path_count widget and add a callback
            const pathCountWidget = node.widgets?.find(w => w.name === "path_count");
            if (pathCountWidget) {
                const originalCallback = pathCountWidget.callback;
                pathCountWidget.callback = function(value) {
                    // Call original callback if it exists
                    if (originalCallback) {
                        originalCallback.call(this, value);
                    }
                    
                    // Update directory widget visibility
                    updateDirectoryWidgetsVisibility(node);
                };
            }
            
            // Initial visibility update after a short delay to ensure widgets are ready
            setTimeout(() => {
                updateDirectoryWidgetsVisibility(node);
            }, 100);
            
            return result;
        };
        
        // Handle configuration restore (when loading saved workflows)
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function(info) {
            const result = onConfigure?.apply(this, arguments);
            
            // Restore widget visibility after configuration
            setTimeout(() => {
                updateDirectoryWidgetsVisibility(this);
            }, 100);
            
            return result;
        };
    },
    
    /**
     * Called when a node is created in the graph
     */
    async nodeCreated(node) {
        if (!MULTI_PATH_NODE_TYPES.includes(node.type)) {
            return;
        }
        
        // Additional delayed update to ensure proper initialization
        setTimeout(() => {
            updateDirectoryWidgetsVisibility(node);
        }, 200);
    }
});

console.log("\x1b[32m[LoadImagesMultiPath] Widget controller loaded\x1b[0m");
