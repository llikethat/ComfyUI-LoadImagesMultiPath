"""
Load nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import torch
import folder_paths
from comfy.utils import common_upscale

from .utils import (
    BIGMAX, MAX_PATH_COUNT, MultiPathInfo,
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
    
    RETURN_TYPES = ("IMAGE", "MASK", "INT", "MULTIPATH_INFO")
    RETURN_NAMES = ("IMAGE", "MASK", "frame_count", "path_info")
    FUNCTION = "load_images_multi"
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Load images from multiple directories sequentially. Set path_count to show the number of directory inputs needed."

    def load_images_multi(self, path_count: int, **kwargs):
        """Load images from multiple directories sequentially"""
        
        image_load_cap = kwargs.get('image_load_cap', 0)
        skip_first_images = kwargs.get('skip_first_images', 0)
        select_every_nth = kwargs.get('select_every_nth', 1)
        
        all_images = []
        all_masks = []
        total_frame_count = 0
        
        # Track info for each directory
        frame_counts = []
        directory_names = []
        
        target_size = None
        target_has_alpha = None
        
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
                    select_every_nth
                )
                
                # Set target size from first valid directory
                if target_size is None:
                    target_size = size
                    target_has_alpha = has_alpha
                
                # Resize images if needed to match target size
                if size != target_size:
                    print(f"[LoadImagesMultiPath] Resizing images from {size} to {target_size}")
                    images = images.movedim(-1, 1)  # BHWC -> BCHW
                    images = common_upscale(images, target_size[0], target_size[1], "lanczos", "center")
                    images = images.movedim(1, -1)  # BCHW -> BHWC
                
                # Handle alpha channel mismatch
                if has_alpha and not target_has_alpha:
                    if images.shape[-1] == 4:
                        images = images[:, :, :, :3]
                
                all_images.append(images)
                all_masks.append(masks)
                total_frame_count += frame_count
                
                # Store info for this directory
                frame_counts.append(frame_count)
                # Get just the directory name, not full path
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                directory_names.append(dir_name)
                
                print(f"[LoadImagesMultiPath] Loaded {frame_count} images from directory {i}")
                
            except FileNotFoundError as e:
                print(f"[LoadImagesMultiPath] Error loading directory {i}: {e}")
                continue
            except Exception as e:
                print(f"[LoadImagesMultiPath] Unexpected error loading directory {i}: {e}")
                continue
        
        if len(all_images) == 0:
            raise FileNotFoundError("No images could be loaded from any of the specified directories.")
        
        # Concatenate all images and masks
        combined_images = torch.cat(all_images, dim=0)
        combined_masks = torch.cat(all_masks, dim=0)
        
        # Create path info object
        path_info = MultiPathInfo(frame_counts, directory_names)
        
        print(f"[LoadImagesMultiPath] Total images loaded: {total_frame_count} from {len(all_images)} directories")
        
        return (combined_images, combined_masks, total_frame_count, path_info)
    
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
    Processes directories sequentially and combines all images.
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
    
    RETURN_TYPES = ("IMAGE", "MASK", "INT", "MULTIPATH_INFO")
    RETURN_NAMES = ("IMAGE", "MASK", "frame_count", "path_info")
    FUNCTION = "load_images_multi"
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Load images from multiple directory paths sequentially. Set path_count to show the number of directory inputs needed."

    def load_images_multi(self, path_count: int, **kwargs):
        """Load images from multiple directory paths sequentially"""
        
        image_load_cap = kwargs.get('image_load_cap', 0)
        skip_first_images = kwargs.get('skip_first_images', 0)
        select_every_nth = kwargs.get('select_every_nth', 1)
        
        all_images = []
        all_masks = []
        total_frame_count = 0
        
        # Track info for each directory
        frame_counts = []
        directory_names = []
        
        target_size = None
        target_has_alpha = None
        
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
                    select_every_nth
                )
                
                if target_size is None:
                    target_size = size
                    target_has_alpha = has_alpha
                
                if size != target_size:
                    print(f"[LoadImagesMultiPath] Resizing images from {size} to {target_size}")
                    images = images.movedim(-1, 1)
                    images = common_upscale(images, target_size[0], target_size[1], "lanczos", "center")
                    images = images.movedim(1, -1)
                
                if has_alpha and not target_has_alpha:
                    if images.shape[-1] == 4:
                        images = images[:, :, :, :3]
                
                all_images.append(images)
                all_masks.append(masks)
                total_frame_count += frame_count
                
                # Store info for this directory
                frame_counts.append(frame_count)
                # Get just the directory name, not full path
                dir_name = os.path.basename(full_path.rstrip('/\\'))
                directory_names.append(dir_name)
                
                print(f"[LoadImagesMultiPath] Loaded {frame_count} images from directory {i}")
                
            except FileNotFoundError as e:
                print(f"[LoadImagesMultiPath] Error loading directory {i}: {e}")
                continue
            except Exception as e:
                print(f"[LoadImagesMultiPath] Unexpected error loading directory {i}: {e}")
                continue
        
        if len(all_images) == 0:
            raise FileNotFoundError("No images could be loaded from any of the specified directories.")
        
        combined_images = torch.cat(all_images, dim=0)
        combined_masks = torch.cat(all_masks, dim=0)
        
        # Create path info object
        path_info = MultiPathInfo(frame_counts, directory_names)
        
        print(f"[LoadImagesMultiPath] Total images loaded: {total_frame_count} from {len(all_images)} directories")
        
        return (combined_images, combined_masks, total_frame_count, path_info)
    
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
