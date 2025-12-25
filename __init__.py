"""
ComfyUI-LoadImagesMultiPath
A custom node for loading images from multiple directories sequentially.

Author: Custom Node
Version: 1.0.0
"""

from .load_images_multipath import LoadImagesMultiPathUpload, LoadImagesMultiPathPath

NODE_CLASS_MAPPINGS = {
    "LoadImagesMultiPath_Upload": LoadImagesMultiPathUpload,
    "LoadImagesMultiPath_Path": LoadImagesMultiPathPath,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImagesMultiPath_Upload": "Load Images Multi-Path (Upload)",
    "LoadImagesMultiPath_Path": "Load Images Multi-Path (Path)",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

print("\033[92m[LoadImagesMultiPath] Loaded successfully!\033[0m")
