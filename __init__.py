"""
ComfyUI-LoadImagesMultiPath

Load images from multiple directories, process them, and save back split by folder.
All images resized to first image size for consistent batch processing.

Version: 2.0.0
License: MIT
"""

from .load_nodes import LoadImagesMultiPathUpload, LoadImagesMultiPathPath
from .save_nodes import SaveImagesMultiPath, SaveImagesSimple

NODE_CLASS_MAPPINGS = {
    "LoadImagesMultiPath_Upload": LoadImagesMultiPathUpload,
    "LoadImagesMultiPath_Path": LoadImagesMultiPathPath,
    "SaveImagesMultiPath": SaveImagesMultiPath,
    "SaveImagesSimple": SaveImagesSimple,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImagesMultiPath_Upload": "Load Images Multi-Path (Upload)",
    "LoadImagesMultiPath_Path": "Load Images Multi-Path (Path)",
    "SaveImagesMultiPath": "Save Images Multi-Path",
    "SaveImagesSimple": "Save Images/Video (Simple)",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print("\033[92m[ComfyUI-LoadImagesMultiPath] Loaded!\033[0m")
