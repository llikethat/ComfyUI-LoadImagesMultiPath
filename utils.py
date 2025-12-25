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
from comfy.utils import common_upscale, ProgressBar

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
