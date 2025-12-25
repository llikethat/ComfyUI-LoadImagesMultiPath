"""
Utility functions and classes for ComfyUI-LoadImagesMultiPath
"""

import os
import hashlib
import shutil
import numpy as np
import torch
from PIL import Image, ImageOps
from comfy.k_diffusion.utils import FolderOfImages
from comfy.utils import ProgressBar

# Constants
BIGMAX = (2**53-1)
MAX_PATH_COUNT = 50


class MultiPathInfo:
    """
    Container class to hold information about loaded directories.
    This is passed to the save node to know how to split the images.
    """
    def __init__(self, frame_counts: list, directory_names: list):
        self.frame_counts = frame_counts  # List of frame counts per directory
        self.directory_names = directory_names  # List of directory names (just the folder name, not full path)
    
    def to_dict(self):
        return {
            "frame_counts": self.frame_counts,
            "directory_names": self.directory_names
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(data["frame_counts"], data["directory_names"])


class MultiImageBatch:
    """
    Container class to hold multiple image batches, each with potentially different dimensions.
    Each batch corresponds to one folder.
    """
    def __init__(self):
        self.batches = []  # List of (images_tensor, masks_tensor, dir_name, size) tuples
    
    def add_batch(self, images, masks, dir_name, size):
        """Add a batch of images from a directory"""
        self.batches.append({
            'images': images,
            'masks': masks,
            'dir_name': dir_name,
            'size': size,
            'frame_count': images.shape[0]
        })
    
    def __len__(self):
        return len(self.batches)
    
    def __iter__(self):
        return iter(self.batches)
    
    def get_total_frames(self):
        return sum(b['frame_count'] for b in self.batches)
    
    def get_directory_names(self):
        return [b['dir_name'] for b in self.batches]
    
    def get_frame_counts(self):
        return [b['frame_count'] for b in self.batches]


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


def load_images_from_directory(directory: str, image_load_cap: int = 0, skip_first_images: int = 0, select_every_nth: int = 1, size_check: bool = True):
    """
    Load images from a single directory and return tensors.
    
    Args:
        directory: Path to the directory
        image_load_cap: Maximum number of images to load (0 = no limit)
        skip_first_images: Number of images to skip from start
        select_every_nth: Load every Nth image
        size_check: If True, resize images that don't match first image's size.
                   If False, load as-is (will error if sizes differ)
    """
    from comfy.utils import common_upscale
    
    # Ensure size_check is boolean
    size_check = bool(size_check)
    
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory '{directory}' cannot be found.")
    
    dir_files = get_sorted_dir_files_from_directory(directory, skip_first_images, select_every_nth, FolderOfImages.IMG_EXTENSIONS)
    
    if len(dir_files) == 0:
        raise FileNotFoundError(f"No files in directory '{directory}'.")
    
    if image_load_cap > 0:
        dir_files = dir_files[:image_load_cap]
    
    total_images = len(dir_files)
    pbar = ProgressBar(total_images)
    
    loaded_tensors = []
    loaded_masks = []
    target_size = None  # Will be set from first image (width, height)
    target_height = None
    target_width = None
    
    print(f"[LoadImagesMultiPath] size_check={size_check}, loading {total_images} images from {directory}")
    
    for idx, file_path in enumerate(dir_files):
        # Load and process each image
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        
        has_alpha = 'A' in img.getbands()
        iformat = "RGBA" if has_alpha else "RGB"
        img = img.convert(iformat)
        
        current_size = img.size  # (width, height)
        current_width, current_height = current_size
        
        # Set target size from first image
        if target_size is None:
            target_size = current_size
            target_width, target_height = current_size
            print(f"[LoadImagesMultiPath] Target size set to {target_width}x{target_height} from first image")
        
        # Convert to numpy then tensor
        img_np = np.array(img, dtype=np.float32)
        img_np /= 255.0
        
        if has_alpha:
            img_np[:, :, -1] = 1 - img_np[:, :, -1]
        
        # Convert to tensor (H, W, C)
        img_tensor = torch.from_numpy(img_np)
        
        # Handle alpha/mask
        if has_alpha:
            mask = img_tensor[:, :, 3]
            img_tensor = img_tensor[:, :, :3]
        else:
            mask = torch.zeros((img_tensor.shape[0], img_tensor.shape[1]), dtype=torch.float32)
        
        # Resize if size_check is enabled and size doesn't match
        if size_check and (current_width != target_width or current_height != target_height):
            print(f"[LoadImagesMultiPath] Resizing image {idx+1} from {current_width}x{current_height} to {target_width}x{target_height}")
            
            # Resize image tensor: (H, W, C) -> (1, C, H, W) for common_upscale
            img_tensor = img_tensor.unsqueeze(0).movedim(-1, 1)  # (1, C, H, W)
            img_tensor = common_upscale(img_tensor, target_width, target_height, "lanczos", "center")
            img_tensor = img_tensor.movedim(1, -1).squeeze(0)  # Back to (H, W, C)
            
            # Resize mask: (H, W) -> (1, 1, H, W) -> resize -> (H, W)
            mask = mask.unsqueeze(0).unsqueeze(0)  # (1, 1, H, W)
            mask = torch.nn.functional.interpolate(mask, size=(target_height, target_width), mode='nearest')
            mask = mask.squeeze(0).squeeze(0)  # Back to (H, W)
        
        # Add batch dimension (1, H, W, C) for image, (1, H, W) for mask
        img_tensor = img_tensor.unsqueeze(0)
        mask = mask.unsqueeze(0)
        
        loaded_tensors.append(img_tensor)
        loaded_masks.append(mask)
        
        pbar.update_absolute(idx + 1, total_images)
    
    # Concatenate all tensors
    try:
        images = torch.cat(loaded_tensors, dim=0)
        masks = torch.cat(loaded_masks, dim=0)
    except RuntimeError as e:
        if "Sizes of tensors must match" in str(e):
            sizes = set()
            for t in loaded_tensors:
                sizes.add((t.shape[2], t.shape[1]))  # (W, H)
            raise ValueError(
                f"Images in directory '{directory}' have different sizes: {sizes}. "
                f"size_check was {size_check}. If True, there may be a bug - please report."
            )
        raise
    
    return images, masks, images.size(0), target_size, False


def get_ffmpeg_path():
    """Find ffmpeg executable"""
    # Check if ffmpeg is in PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    
    # Common locations
    common_paths = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
    
    return None


def sanitize_filename(name):
    """Remove or replace invalid characters from filename"""
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Remove leading/trailing spaces and dots
    name = name.strip(' .')
    return name
