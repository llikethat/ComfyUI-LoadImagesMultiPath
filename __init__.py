"""
ComfyUI-LoadImagesMultiPath

A custom node package for loading images from multiple directories sequentially
and saving them back split by directory.

Author: Custom Node
Version: 1.1.0
License: MIT
"""

from .load_nodes import (
    LoadImagesMultiPathUpload, 
    LoadImagesMultiPathPath
)

from .save_nodes import (
    SaveImagesMultiPath,
    SaveImagesMultiPathSimple
)

NODE_CLASS_MAPPINGS = {
    "LoadImagesMultiPath_Upload": LoadImagesMultiPathUpload,
    "LoadImagesMultiPath_Path": LoadImagesMultiPathPath,
    "SaveImagesMultiPath": SaveImagesMultiPath,
    "SaveImagesMultiPath_Simple": SaveImagesMultiPathSimple,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImagesMultiPath_Upload": "Load Images Multi-Path (Upload)",
    "LoadImagesMultiPath_Path": "Load Images Multi-Path (Path)",
    "SaveImagesMultiPath": "Save Images Multi-Path",
    "SaveImagesMultiPath_Simple": "Save Images/Video (Simple)",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print("\033[92m[ComfyUI-LoadImagesMultiPath] Loaded successfully!\033[0m")
