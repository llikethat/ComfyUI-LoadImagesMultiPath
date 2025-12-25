"""
Utility functions for ComfyUI-LoadImagesMultiPath
"""

import os
import hashlib
import shutil
import numpy as np
import torch
from PIL import Image, ImageOps
from comfy.k_diffusion.utils import FolderOfImages
from comfy.utils import ProgressBar

BIGMAX = (2**53-1)
MAX_PATH_COUNT = 50


class MultiImageBatch:
    """Container for multiple image batches with different dimensions."""
    
    def __init__(self):
        self.batches = []
    
    def add(self, images, dir_name, size):
        self.batches.append({'images': images, 'dir_name': dir_name, 'size': size})
    
    def __len__(self):
        return len(self.batches)
    
    def __iter__(self):
        return iter(self.batches)


def strip_path(path):
    """Clean path string"""
    if not path:
        return None
    return path.strip().strip('"\'') or None


def get_image_files(directory, skip=0, every_nth=1):
    """Get sorted image files from directory"""
    extensions = FolderOfImages.IMG_EXTENSIONS
    files = sorted([
        os.path.join(directory, f) for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and os.path.splitext(f)[1].lower() in extensions
    ])
    
    if skip > 0:
        files = files[skip:]
    if every_nth > 1:
        files = files[::every_nth]
    return files


def hash_directories(directories, cap=0, skip=0, every_nth=1):
    """Hash directories for change detection"""
    m = hashlib.sha256()
    for d in directories:
        if d and os.path.isdir(d):
            files = get_image_files(d, skip, every_nth)
            if cap > 0:
                files = files[:cap]
            for f in files:
                with open(f, 'rb') as fp:
                    m.update(fp.read(8192))
    return m.hexdigest()


def validate_directory(directory):
    """Check if directory exists and has files"""
    if not os.path.isdir(directory):
        return f"Directory not found: {directory}"
    if not os.listdir(directory):
        return f"Empty directory: {directory}"
    return True


def load_images(directory, cap=0, skip=0, every_nth=1, size_check=True):
    """Load images from directory as tensor batch"""
    from comfy.utils import common_upscale
    
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    files = get_image_files(directory, skip, every_nth)
    if not files:
        raise FileNotFoundError(f"No images in: {directory}")
    
    if cap > 0:
        files = files[:cap]
    
    pbar = ProgressBar(len(files))
    tensors = []
    target_w, target_h = None, None
    
    for idx, path in enumerate(files):
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        
        w, h = img.size
        if target_w is None:
            target_w, target_h = w, h
        
        tensor = torch.from_numpy(np.array(img, dtype=np.float32) / 255.0)
        
        # Resize if needed
        if size_check and (w != target_w or h != target_h):
            tensor = tensor.unsqueeze(0).movedim(-1, 1)
            tensor = common_upscale(tensor, target_w, target_h, "lanczos", "center")
            tensor = tensor.movedim(1, -1).squeeze(0)
        
        tensors.append(tensor.unsqueeze(0))
        pbar.update_absolute(idx + 1, len(files))
    
    return torch.cat(tensors, dim=0), (target_w, target_h)


def get_ffmpeg():
    """Find ffmpeg executable"""
    path = shutil.which("ffmpeg")
    if path:
        return path
    for p in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", 
              "C:\\ffmpeg\\bin\\ffmpeg.exe", "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"]:
        if os.path.isfile(p):
            return p
    return None


def sanitize_filename(name):
    """Remove invalid filename characters"""
    for c in '<>:"/\\|?*':
        name = name.replace(c, '_')
    return name.strip(' .')
