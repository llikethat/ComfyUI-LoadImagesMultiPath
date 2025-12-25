"""
Load nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import folder_paths
from .utils import BIGMAX, MAX_PATH_COUNT, MultiImageBatch, strip_path, load_images, hash_directories, validate_directory


def _load_from_directories(directories, cap, skip, every_nth, size_check):
    """Common loading logic for both node types"""
    batch = MultiImageBatch()
    total = 0
    
    for path in directories:
        if not path or not os.path.isdir(path):
            continue
        
        try:
            images, size = load_images(path, cap, skip, every_nth, size_check)
            name = os.path.basename(path.rstrip('/\\'))
            batch.add(images, name, size)
            total += images.shape[0]
            print(f"[LoadImagesMultiPath] {name}: {images.shape[0]} images ({size[0]}x{size[1]})")
        except Exception as e:
            print(f"[LoadImagesMultiPath] Error loading {path}: {e}")
            raise
    
    if len(batch) == 0:
        raise FileNotFoundError("No images loaded from any directory.")
    
    return batch, total


class LoadImagesMultiPathUpload:
    """Load images from multiple directories (dropdown selection)."""
    
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        dirs = [""] + [d for d in os.listdir(input_dir) 
                       if os.path.isdir(os.path.join(input_dir, d)) and d != "clipspace"]
        
        inputs = {
            "required": {
                "path_count": ("INT", {"default": 1, "min": 1, "max": MAX_PATH_COUNT}),
                "directory_1": (dirs,),
            },
            "optional": {
                "size_check": ("BOOLEAN", {"default": True}),
                "image_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX}),
                "skip_first_images": ("INT", {"default": 0, "min": 0, "max": BIGMAX}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX}),
            },
        }
        for i in range(2, MAX_PATH_COUNT + 1):
            inputs["optional"][f"directory_{i}"] = (dirs,)
        return inputs
    
    RETURN_TYPES = ("MULTI_IMAGE_BATCH", "INT")
    RETURN_NAMES = ("image_batches", "total_frames")
    FUNCTION = "load"
    CATEGORY = "image/multi-path"

    def load(self, path_count, **kw):
        dirs = [folder_paths.get_annotated_filepath(strip_path(kw.get(f'directory_{i}', "")))
                for i in range(1, path_count + 1) if kw.get(f'directory_{i}')]
        return _load_from_directories(
            dirs, kw.get('image_load_cap', 0), kw.get('skip_first_images', 0),
            kw.get('select_every_nth', 1), kw.get('size_check', True)
        )
    
    @classmethod
    def IS_CHANGED(s, path_count, **kw):
        dirs = [folder_paths.get_annotated_filepath(strip_path(kw.get(f'directory_{i}', "")))
                for i in range(1, path_count + 1) if kw.get(f'directory_{i}')]
        return hash_directories(dirs, kw.get('image_load_cap', 0), 
                                kw.get('skip_first_images', 0), kw.get('select_every_nth', 1))

    @classmethod
    def VALIDATE_INPUTS(s, path_count, **kw):
        for i in range(1, path_count + 1):
            d = kw.get(f'directory_{i}')
            if d and validate_directory(folder_paths.get_annotated_filepath(strip_path(d))) == True:
                return True
        return "At least one valid directory required."


class LoadImagesMultiPathPath:
    """Load images from multiple directory paths (string input)."""
    
    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "path_count": ("INT", {"default": 1, "min": 1, "max": MAX_PATH_COUNT}),
                "directory_1": ("STRING", {"default": ""}),
            },
            "optional": {
                "size_check": ("BOOLEAN", {"default": True}),
                "image_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX}),
                "skip_first_images": ("INT", {"default": 0, "min": 0, "max": BIGMAX}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX}),
            },
        }
        for i in range(2, MAX_PATH_COUNT + 1):
            inputs["optional"][f"directory_{i}"] = ("STRING", {"default": ""})
        return inputs
    
    RETURN_TYPES = ("MULTI_IMAGE_BATCH", "INT")
    RETURN_NAMES = ("image_batches", "total_frames")
    FUNCTION = "load"
    CATEGORY = "image/multi-path"

    def load(self, path_count, **kw):
        dirs = [strip_path(kw.get(f'directory_{i}', ""))
                for i in range(1, path_count + 1) if kw.get(f'directory_{i}', "").strip()]
        return _load_from_directories(
            dirs, kw.get('image_load_cap', 0), kw.get('skip_first_images', 0),
            kw.get('select_every_nth', 1), kw.get('size_check', True)
        )
    
    @classmethod
    def IS_CHANGED(s, path_count, **kw):
        dirs = [strip_path(kw.get(f'directory_{i}', ""))
                for i in range(1, path_count + 1) if kw.get(f'directory_{i}', "").strip()]
        return hash_directories(dirs, kw.get('image_load_cap', 0),
                                kw.get('skip_first_images', 0), kw.get('select_every_nth', 1))

    @classmethod
    def VALIDATE_INPUTS(s, path_count, **kw):
        for i in range(1, path_count + 1):
            d = kw.get(f'directory_{i}', "").strip()
            if d and validate_directory(strip_path(d)) == True:
                return True
        return "At least one valid directory required."
