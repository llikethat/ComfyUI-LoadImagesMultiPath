import os
import hashlib
import numpy as np
import torch
from PIL import Image, ImageOps
import folder_paths
from comfy.k_diffusion.utils import FolderOfImages
from comfy.utils import common_upscale, ProgressBar

# Constants
BIGMAX = (2**53-1)
MAX_PATH_COUNT = 50


def strip_path(path):
    """Strip and clean the path string"""
    if path is None:
        return None
    # Strip whitespace and quotes
    path = path.strip().strip('"').strip("'")
    return path if path else None


def get_sorted_dir_files_from_directory(directory, skip_first_files=0, select_every_nth=1, extensions=None):
    """Get sorted list of files from a directory with filtering options"""
    if extensions is None:
        extensions = FolderOfImages.IMG_EXTENSIONS
    
    dir_files = []
    for f in os.listdir(directory):
        filepath = os.path.join(directory, f)
        if os.path.isfile(filepath):
            ext = os.path.splitext(f)[1].lower()
            if ext in extensions:
                dir_files.append(filepath)
    
    # Sort files naturally
    dir_files.sort()
    
    # Apply skip and select_every_nth
    if skip_first_files > 0:
        dir_files = dir_files[skip_first_files:]
    
    if select_every_nth > 1:
        dir_files = dir_files[::select_every_nth]
    
    return dir_files


def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def is_changed_load_images_multi(directories: list, image_load_cap: int = 0, skip_first_images: int = 0, select_every_nth: int = 1, **kwargs):
    """Hash function for multiple directories to detect changes"""
    m = hashlib.sha256()
    for directory in directories:
        if directory and os.path.isdir(directory):
            dir_files = get_sorted_dir_files_from_directory(directory, skip_first_images, select_every_nth, FolderOfImages.IMG_EXTENSIONS)
            if image_load_cap != 0:
                dir_files = dir_files[:image_load_cap]
            for filepath in dir_files:
                m.update(calculate_file_hash(filepath).encode())
    return m.digest().hex()


def validate_load_images(directory: str):
    """Validate that a directory exists and contains files"""
    if not os.path.isdir(directory):
        return f"Directory '{directory}' cannot be found."
    dir_files = os.listdir(directory)
    if len(dir_files) == 0:
        return f"No files in directory '{directory}'."
    return True


def load_images_from_directory(directory: str, image_load_cap: int = 0, skip_first_images: int = 0, select_every_nth: int = 1):
    """Load images from a single directory and return tensors"""
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory '{directory}' cannot be found.")
    
    dir_files = get_sorted_dir_files_from_directory(directory, skip_first_images, select_every_nth, FolderOfImages.IMG_EXTENSIONS)
    
    if len(dir_files) == 0:
        raise FileNotFoundError(f"No files in directory '{directory}'.")
    
    if image_load_cap > 0:
        dir_files = dir_files[:image_load_cap]
    
    # Determine common size and alpha channel presence
    sizes = {}
    has_alpha = False
    for image_path in dir_files:
        i = Image.open(image_path)
        i = ImageOps.exif_transpose(i)
        has_alpha |= 'A' in i.getbands()
        count = sizes.get(i.size, 0)
        sizes[i.size] = count + 1
    
    size = max(sizes.items(), key=lambda x: x[1])[0]
    iformat = "RGBA" if has_alpha else "RGB"
    
    def load_image(file_path):
        i = Image.open(file_path)
        i = ImageOps.exif_transpose(i)
        i = i.convert(iformat)
        i = np.array(i, dtype=np.float32)
        i /= 255.0
        if i.shape[0] != size[1] or i.shape[1] != size[0]:
            i = torch.from_numpy(i).movedim(-1, 0).unsqueeze(0)
            i = common_upscale(i, size[0], size[1], "lanczos", "center")
            i = i.squeeze(0).movedim(0, -1).numpy()
        if has_alpha:
            i[:, :, -1] = 1 - i[:, :, -1]
        return i
    
    total_images = len(dir_files)
    pbar = ProgressBar(total_images)
    
    loaded_images = []
    for idx, file_path in enumerate(dir_files):
        loaded_images.append(load_image(file_path))
        pbar.update_absolute(idx + 1, total_images)
    
    images = torch.from_numpy(np.array(loaded_images, dtype=np.float32))
    
    if has_alpha:
        masks = images[:, :, :, 3]
        images = images[:, :, :, :3]
    else:
        masks = torch.zeros((images.size(0), 64, 64), dtype=torch.float32, device="cpu")
    
    return images, masks, images.size(0), size, has_alpha


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
    
    RETURN_TYPES = ("IMAGE", "MASK", "INT")
    RETURN_NAMES = ("IMAGE", "MASK", "frame_count")
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
            directory = folder_paths.get_annotated_filepath(strip_path(directory))
            
            if not os.path.isdir(directory):
                print(f"[LoadImagesMultiPath] Directory '{directory}' not found, skipping...")
                continue
            
            try:
                print(f"[LoadImagesMultiPath] Processing directory {i}/{path_count}: {directory}")
                
                images, masks, frame_count, size, has_alpha = load_images_from_directory(
                    directory, 
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
        
        print(f"[LoadImagesMultiPath] Total images loaded: {total_frame_count} from {len(all_images)} directories")
        
        return (combined_images, combined_masks, total_frame_count)
    
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
    
    RETURN_TYPES = ("IMAGE", "MASK", "INT")
    RETURN_NAMES = ("IMAGE", "MASK", "frame_count")
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
        
        target_size = None
        target_has_alpha = None
        
        for i in range(1, path_count + 1):
            dir_key = f"directory_{i}"
            directory = kwargs.get(dir_key, "")
            
            if not directory or directory.strip() == "":
                print(f"[LoadImagesMultiPath] Directory {i} is empty, skipping...")
                continue
            
            directory = strip_path(directory)
            
            if not os.path.isdir(directory):
                print(f"[LoadImagesMultiPath] Directory '{directory}' not found, skipping...")
                continue
            
            try:
                print(f"[LoadImagesMultiPath] Processing directory {i}/{path_count}: {directory}")
                
                images, masks, frame_count, size, has_alpha = load_images_from_directory(
                    directory, 
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
        
        print(f"[LoadImagesMultiPath] Total images loaded: {total_frame_count} from {len(all_images)} directories")
        
        return (combined_images, combined_masks, total_frame_count)
    
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
