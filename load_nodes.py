"""
Load nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import torch
import folder_paths

from .utils import (
    BIGMAX, MAX_PATH_COUNT, MultiPathInfo, MultiImageBatch,
    strip_path, load_images_from_directory, 
    is_changed_load_images_multi, validate_load_images
)


class LoadImagesMultiPathUpload:
    """
    Load Images from multiple directories (Upload-based selection).
    Processes directories sequentially and combines all images.
    Use path_count to specify how many directory inputs you need (1-50).
    """
    
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        directories = [""]  # Allow empty selection
        for item in os.listdir(input_dir):
            if not os.path.isfile(os.path.join(input_dir, item)) and item != "clipspace":
                directories.append(item)
        
        inputs = {
            "required": {
                "path_count": ("INT", {"default": 1, "min": 1, "max": MAX_PATH_COUNT, "step": 1}),
                "directory_1": (directories,),
            },
            "optional": {
                "size_check": ("BOOLEAN", {"default": True, "tooltip": "If True, resize images to match first image in each folder. If False, all images must have same size."}),
                "image_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1, "tooltip": "0 = no limit"}),
                "skip_first_images": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX, "step": 1}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            },
        }
        
        # Add directory inputs 2-50 as optional
        for i in range(2, MAX_PATH_COUNT + 1):
            inputs["optional"][f"directory_{i}"] = (directories,)
        
        return inputs
    
    RETURN_TYPES = ("MULTI_IMAGE_BATCH", "INT")
    RETURN_NAMES = ("image_batches", "total_frames")
    FUNCTION = "load_images_multi"
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Load images from multiple directories. Each folder maintains its own dimensions. Connect to 'Save Images Multi-Path' node."

    def load_images_multi(self, path_count: int, **kwargs):
        """Load images from multiple directories sequentially, each folder separately"""
        
        size_check = kwargs.get('size_check', True)
        image_load_cap = kwargs.get('image_load_cap', 0)
        skip_first_images = kwargs.get('skip_first_images', 0)
        select_every_nth = kwargs.get('select_every_nth', 1)
        
        multi_batch = MultiImageBatch()
        total_frame_count = 0
        
        # Process each directory sequentially
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            
            if not directory or directory == "":
                print(f"[LoadImagesMultiPath] Directory {i} is empty, skipping...")
                continue
            
            # Get the full path
            full_path = folder_paths.get_annotated_filepath(strip_path(directory))
            
            if not os.path.isdir(full_path):
                print(f"[LoadImagesMultiPath] Directory '{full_path}' not found, skipping...")
                continue
            
            try:
                print(f"[LoadImagesMultiPath] Processing directory {i}/{path_count}: {full_path}")
                
                images, masks, frame_count, size, has_alpha = load_images_from_directory(
                    full_path, 
                    image_load_cap, 
                    skip_first_images, 
                    select_every_nth,
                    size_check
                )
                
                # Get just the directory name, not full path
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                
                # Add this batch to the multi-batch container
                multi_batch.add_batch(images, masks, dir_name, size)
                total_frame_count += frame_count
                
                print(f"[LoadImagesMultiPath] Loaded {frame_count} images ({size[0]}x{size[1]}) from directory {i}: {dir_name}")
                
            except FileNotFoundError as e:
                print(f"[LoadImagesMultiPath] Error loading directory {i}: {e}")
                continue
            except ValueError as e:
                print(f"[LoadImagesMultiPath] Validation error in directory {i}:")
                print(str(e))
                raise
            except Exception as e:
                print(f"[LoadImagesMultiPath] Unexpected error loading directory {i}: {e}")
                raise
        
        if len(multi_batch) == 0:
            raise FileNotFoundError("No images could be loaded from any of the specified directories.")
        
        print(f"[LoadImagesMultiPath] Total: {total_frame_count} images from {len(multi_batch)} directories")
        
        return (multi_batch, total_frame_count)
    
    @classmethod
    def IS_CHANGED(s, path_count: int, **kwargs):
        directories = []
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            if directory and directory != "":
                directory = folder_paths.get_annotated_filepath(strip_path(directory))
                directories.append(directory)
        
        return is_changed_load_images_multi(
            directories,
            kwargs.get('image_load_cap', 0),
            kwargs.get('skip_first_images', 0),
            kwargs.get('select_every_nth', 1)
        )

    @classmethod
    def VALIDATE_INPUTS(s, path_count: int, **kwargs):
        valid_dirs = 0
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            if directory and directory != "":
                directory = folder_paths.get_annotated_filepath(strip_path(directory))
                result = validate_load_images(directory)
                if result == True:
                    valid_dirs += 1
        
        if valid_dirs == 0:
            return "At least one valid directory must be specified."
        
        return True


class LoadImagesMultiPathPath:
    """
    Load Images from multiple directory paths (String-based input).
    Each folder is processed separately and maintains its own dimensions.
    Use path_count to specify how many directory inputs you need (1-50).
    """
    
    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "path_count": ("INT", {"default": 1, "min": 1, "max": MAX_PATH_COUNT, "step": 1}),
                "directory_1": ("STRING", {"placeholder": "X://path/to/images", "default": ""}),
            },
            "optional": {
                "size_check": ("BOOLEAN", {"default": True, "tooltip": "If True, resize images to match first image in each folder. If False, all images must have same size."}),
                "image_load_cap": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1, "tooltip": "0 = no limit"}),
                "skip_first_images": ("INT", {"default": 0, "min": 0, "max": BIGMAX, "step": 1}),
                "select_every_nth": ("INT", {"default": 1, "min": 1, "max": BIGMAX, "step": 1}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            },
        }
        
        # Add directory inputs 2-50 as optional
        for i in range(2, MAX_PATH_COUNT + 1):
            inputs["optional"][f"directory_{i}"] = ("STRING", {"placeholder": f"X://path/to/images", "default": ""})
        
        return inputs
    
    RETURN_TYPES = ("MULTI_IMAGE_BATCH", "INT")
    RETURN_NAMES = ("image_batches", "total_frames")
    FUNCTION = "load_images_multi"
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Load images from multiple directory paths. Each folder maintains its own dimensions. Connect to 'Save Images Multi-Path' node."

    def load_images_multi(self, path_count: int, **kwargs):
        """Load images from multiple directory paths sequentially, each folder separately"""
        
        size_check = kwargs.get('size_check', True)
        image_load_cap = kwargs.get('image_load_cap', 0)
        skip_first_images = kwargs.get('skip_first_images', 0)
        select_every_nth = kwargs.get('select_every_nth', 1)
        
        multi_batch = MultiImageBatch()
        total_frame_count = 0
        
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            
            if not directory or directory.strip() == "":
                print(f"[LoadImagesMultiPath] Directory {i} is empty, skipping...")
                continue
            
            full_path = strip_path(directory)
            
            if not os.path.isdir(full_path):
                print(f"[LoadImagesMultiPath] Directory '{full_path}' not found, skipping...")
                continue
            
            try:
                print(f"[LoadImagesMultiPath] Processing directory {i}/{path_count}: {full_path}")
                
                images, masks, frame_count, size, has_alpha = load_images_from_directory(
                    full_path, 
                    image_load_cap, 
                    skip_first_images, 
                    select_every_nth,
                    size_check
                )
                
                # Get just the directory name, not full path
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                
                # Add this batch to the multi-batch container
                multi_batch.add_batch(images, masks, dir_name, size)
                total_frame_count += frame_count
                
                print(f"[LoadImagesMultiPath] Loaded {frame_count} images ({size[0]}x{size[1]}) from directory {i}: {dir_name}")
                
            except FileNotFoundError as e:
                print(f"[LoadImagesMultiPath] Error loading directory {i}: {e}")
                continue
            except ValueError as e:
                print(f"[LoadImagesMultiPath] Validation error in directory {i}:")
                print(str(e))
                raise
            except Exception as e:
                print(f"[LoadImagesMultiPath] Unexpected error loading directory {i}: {e}")
                raise
        
        if len(multi_batch) == 0:
            raise FileNotFoundError("No images could be loaded from any of the specified directories.")
        
        print(f"[LoadImagesMultiPath] Total: {total_frame_count} images from {len(multi_batch)} directories")
        
        return (multi_batch, total_frame_count)
    
    @classmethod
    def IS_CHANGED(s, path_count: int, **kwargs):
        directories = []
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            if directory and directory.strip() != "":
                directory = strip_path(directory)
                directories.append(directory)
        
        return is_changed_load_images_multi(
            directories,
            kwargs.get('image_load_cap', 0),
            kwargs.get('skip_first_images', 0),
            kwargs.get('select_every_nth', 1)
        )

    @classmethod
    def VALIDATE_INPUTS(s, path_count: int, **kwargs):
        valid_dirs = 0
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            if directory and directory.strip() != "":
                directory = strip_path(directory)
                result = validate_load_images(directory)
                if result == True:
                    valid_dirs += 1
        
        if valid_dirs == 0:
            return "At least one valid directory must be specified."
        
        return True
