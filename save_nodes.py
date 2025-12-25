"""
Save nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import subprocess
import tempfile
import numpy as np
from PIL import Image
import folder_paths
from .utils import get_ffmpeg, sanitize_filename


def _save_images(images, base_name, out_dir, fmt, img_fmt, quality, fps, crf):
    """Save images as sequence or video"""
    if fmt == "images":
        subdir = os.path.join(out_dir, base_name)
        os.makedirs(subdir, exist_ok=True)
        
        for i, tensor in enumerate(images):
            img = Image.fromarray((tensor.cpu().numpy() * 255).astype(np.uint8))
            path = os.path.join(subdir, f"{base_name}_{i:05d}.{img_fmt}")
            img.save(path, quality=quality) if img_fmt in ["jpg", "webp"] else img.save(path)
        
        return subdir
    
    else:  # mp4
        ffmpeg = get_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found")
        
        output = os.path.join(out_dir, f"{base_name}.mp4")
        
        with tempfile.TemporaryDirectory() as tmp:
            for i, tensor in enumerate(images):
                img = Image.fromarray((tensor.cpu().numpy() * 255).astype(np.uint8))
                img.save(os.path.join(tmp, f"f_{i:05d}.png"))
            
            # scale filter ensures dimensions are divisible by 2 (required by h264)
            result = subprocess.run([
                ffmpeg, "-y", "-framerate", str(fps),
                "-i", os.path.join(tmp, "f_%05d.png"),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v", "libx264", "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-preset", "medium", output
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg error: {result.stderr}")
        
        return output


class SaveImagesMultiPath:
    """Save images split by original directories using path_info."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "path_info": ("PATH_INFO",),
                "filename_prefix": ("STRING", {"default": "output"}),
            },
            "optional": {
                "output_format": (["images", "mp4"], {"default": "images"}),
                "output_directory": ("STRING", {"default": ""}),
                "image_format": (["png", "jpg", "webp"], {"default": "png"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100}),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 120}),
                "video_crf": ("INT", {"default": 23, "min": 0, "max": 51}),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_paths",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "image/multi-path"

    def save(self, images, path_info, filename_prefix, output_format="images", output_directory="",
             image_format="png", quality=95, frame_rate=24, video_crf=23):
        
        out_dir = output_directory.strip() or folder_paths.get_output_directory()
        os.makedirs(out_dir, exist_ok=True)
        
        paths = []
        idx = 0
        
        for count, dir_name in zip(path_info.frame_counts, path_info.dir_names):
            batch = images[idx:idx + count]
            idx += count
            
            name = f"{filename_prefix}_{sanitize_filename(dir_name)}"
            print(f"[SaveMultiPath] {dir_name}: {count} frames → {name}")
            
            paths.append(_save_images(batch, name, out_dir, output_format, image_format, quality, frame_rate, video_crf))
        
        result = "\n".join(paths)
        return {"ui": {"text": [result]}, "result": (result,)}
    
    @classmethod
    def IS_CHANGED(s, **kw):
        return float("nan")


class SaveImagesSimple:
    """Save standard IMAGE batch as single output."""
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "output"}),
            },
            "optional": {
                "output_format": (["images", "mp4"], {"default": "images"}),
                "output_directory": ("STRING", {"default": ""}),
                "image_format": (["png", "jpg", "webp"], {"default": "png"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100}),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 120}),
                "video_crf": ("INT", {"default": 23, "min": 0, "max": 51}),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "image/multi-path"

    def save(self, images, filename_prefix, output_format="images", output_directory="",
             image_format="png", quality=95, frame_rate=24, video_crf=23):
        
        out_dir = output_directory.strip() or folder_paths.get_output_directory()
        os.makedirs(out_dir, exist_ok=True)
        
        name = sanitize_filename(filename_prefix)
        print(f"[SaveSimple] {images.shape[0]} frames → {name}")
        
        result = _save_images(images, name, out_dir, output_format, image_format, quality, frame_rate, video_crf)
        return {"ui": {"text": [result]}, "result": (result,)}
    
    @classmethod
    def IS_CHANGED(s, **kw):
        return float("nan")
