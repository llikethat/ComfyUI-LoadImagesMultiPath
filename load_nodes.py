"""
Load nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import torch
import folder_paths
from .utils import BIGMAX, MAX_PATH_COUNT, PathInfo, strip_path, load_images, hash_directories, validate_directory


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
    
    RETURN_TYPES = ("IMAGE", "INT", "PATH_INFO")
    RETURN_NAMES = ("IMAGE", "frame_count", "path_info")
    FUNCTION = "load"
    CATEGORY = "image/multi-path"

    def load(self, path_count, **kw):
        size_check = kw.get('size_check', True)
        cap = kw.get('image_load_cap', 0)
        skip = kw.get('skip_first_images', 0)
        every_nth = kw.get('select_every_nth', 1)
        
        all_images = []
        frame_counts = []
        dir_names = []
        target_size = None
        
        for i in range(1, path_count + 1):
            directory = kw.get(f'directory_{i}', "")
            if not directory:
                continue
            
            full_path = folder_paths.get_annotated_filepath(strip_path(directory))
            if not os.path.isdir(full_path):
                print(f"[LoadImagesMultiPath] Not found: {full_path}")
                continue
            
            try:
                images, target_size = load_images(full_path, cap, skip, every_nth, target_size, size_check)
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                
                all_images.append(images)
                frame_counts.append(images.shape[0])
                dir_names.append(dir_name)
                
                print(f"[LoadImagesMultiPath] {dir_name}: {images.shape[0]} images ({target_size[0]}x{target_size[1]})")
            except Exception as e:
                print(f"[LoadImagesMultiPath] Error: {e}")
                raise
        
        if not all_images:
            raise FileNotFoundError("No images loaded from any directory.")
        
        combined = torch.cat(all_images, dim=0)
        path_info = PathInfo(frame_counts, dir_names)
        
        return (combined, combined.shape[0], path_info)
    
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
    
    RETURN_TYPES = ("IMAGE", "INT", "PATH_INFO")
    RETURN_NAMES = ("IMAGE", "frame_count", "path_info")
    FUNCTION = "load"
    CATEGORY = "image/multi-path"

    def load(self, path_count, **kw):
        size_check = kw.get('size_check', True)
        cap = kw.get('image_load_cap', 0)
        skip = kw.get('skip_first_images', 0)
        every_nth = kw.get('select_every_nth', 1)
        
        all_images = []
        frame_counts = []
        dir_names = []
        target_size = None
        
        for i in range(1, path_count + 1):
            directory = kw.get(f'directory_{i}', "").strip()
            if not directory:
                continue
            
            full_path = strip_path(directory)
            if not os.path.isdir(full_path):
                print(f"[LoadImagesMultiPath] Not found: {full_path}")
                continue
            
            try:
                images, target_size = load_images(full_path, cap, skip, every_nth, target_size, size_check)
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                
                all_images.append(images)
                frame_counts.append(images.shape[0])
                dir_names.append(dir_name)
                
                print(f"[LoadImagesMultiPath] {dir_name}: {images.shape[0]} images ({target_size[0]}x{target_size[1]})")
            except Exception as e:
                print(f"[LoadImagesMultiPath] Error: {e}")
                raise
        
        if not all_images:
            raise FileNotFoundError("No images loaded from any directory.")
        
        combined = torch.cat(all_images, dim=0)
        path_info = PathInfo(frame_counts, dir_names)
        
        return (combined, combined.shape[0], path_info)
    
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
