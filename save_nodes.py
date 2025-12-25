"""
Save nodes for ComfyUI-LoadImagesMultiPath
"""

import os
import subprocess
import tempfile
import numpy as np
from PIL import Image
import folder_paths

from .utils import get_ffmpeg_path, sanitize_filename


class SaveImagesMultiPath:
    """
    Save images/videos split by the original directories they were loaded from.
    Works with the path_info output from LoadImagesMultiPath nodes.
    Automatically appends directory name as suffix to filename.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "path_info": ("MULTIPATH_INFO",),
                "output_format": (["images", "mp4"],),
                "filename_prefix": ("STRING", {"default": "output"}),
                "output_directory": ("STRING", {"default": "", "placeholder": "Leave empty for ComfyUI output folder"}),
            },
            "optional": {
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "image_format": (["png", "jpg", "webp"],),
                "jpg_quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "video_quality": ("INT", {"default": 23, "min": 0, "max": 51, "step": 1, "tooltip": "CRF value: 0=lossless, 23=default, 51=worst"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_paths",)
    FUNCTION = "save_images_multi"
    OUTPUT_NODE = True
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Save images or videos split by original directories. Filename gets '_directoryname' suffix automatically."

    def save_images_multi(self, images, path_info, output_format, filename_prefix, 
                          output_directory="", frame_rate=24, image_format="png", 
                          jpg_quality=95, video_quality=23, prompt=None, extra_pnginfo=None):
        """Save images split by their original directories"""
        
        # Determine output directory
        if output_directory and output_directory.strip():
            out_dir = output_directory.strip()
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
        else:
            out_dir = folder_paths.get_output_directory()
        
        # Get frame counts and directory names from path_info
        frame_counts = path_info.frame_counts
        directory_names = path_info.directory_names
        
        # Verify total frames match
        total_expected = sum(frame_counts)
        total_actual = images.shape[0]
        
        if total_expected != total_actual:
            print(f"[SaveImagesMultiPath] Warning: Expected {total_expected} frames but got {total_actual}")
        
        output_paths = []
        current_idx = 0
        
        # Process each directory's worth of images
        for i, (frame_count, dir_name) in enumerate(zip(frame_counts, directory_names)):
            # Get the slice of images for this directory
            end_idx = current_idx + frame_count
            dir_images = images[current_idx:end_idx]
            current_idx = end_idx
            
            # Create filename with directory suffix
            safe_dir_name = sanitize_filename(dir_name)
            base_filename = f"{filename_prefix}_{safe_dir_name}"
            
            print(f"[SaveImagesMultiPath] Saving {frame_count} frames for '{dir_name}' as '{base_filename}'")
            
            if output_format == "images":
                # Save as image sequence
                output_subdir = os.path.join(out_dir, base_filename)
                os.makedirs(output_subdir, exist_ok=True)
                
                for j, img_tensor in enumerate(dir_images):
                    # Convert tensor to PIL Image
                    img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
                    img = Image.fromarray(img_np)
                    
                    # Determine file extension and save
                    frame_filename = f"{base_filename}_{j:05d}.{image_format}"
                    frame_path = os.path.join(output_subdir, frame_filename)
                    
                    if image_format == "jpg":
                        img.save(frame_path, quality=jpg_quality)
                    elif image_format == "webp":
                        img.save(frame_path, quality=jpg_quality)
                    else:
                        img.save(frame_path)
                
                output_paths.append(output_subdir)
                print(f"[SaveImagesMultiPath] Saved {frame_count} images to: {output_subdir}")
                
            elif output_format == "mp4":
                # Save as MP4 video
                ffmpeg_path = get_ffmpeg_path()
                if not ffmpeg_path:
                    raise RuntimeError("ffmpeg not found. Please install ffmpeg to export MP4 videos.")
                
                output_file = os.path.join(out_dir, f"{base_filename}.mp4")
                
                # Create temporary directory for frames
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save frames as temporary PNGs
                    for j, img_tensor in enumerate(dir_images):
                        img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
                        img = Image.fromarray(img_np)
                        temp_frame = os.path.join(temp_dir, f"frame_{j:05d}.png")
                        img.save(temp_frame)
                    
                    # Build ffmpeg command
                    cmd = [
                        ffmpeg_path,
                        "-y",  # Overwrite output
                        "-framerate", str(frame_rate),
                        "-i", os.path.join(temp_dir, "frame_%05d.png"),
                        "-c:v", "libx264",
                        "-crf", str(video_quality),
                        "-pix_fmt", "yuv420p",
                        "-preset", "medium",
                        output_file
                    ]
                    
                    print(f"[SaveImagesMultiPath] Running ffmpeg: {' '.join(cmd)}")
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"[SaveImagesMultiPath] ffmpeg error: {result.stderr}")
                        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
                
                output_paths.append(output_file)
                print(f"[SaveImagesMultiPath] Saved video to: {output_file}")
        
        # Return paths as newline-separated string
        paths_str = "\n".join(output_paths)
        
        return {"ui": {"text": [paths_str]}, "result": (paths_str,)}
    
    @classmethod
    def IS_CHANGED(s, **kwargs):
        return float("nan")  # Always re-execute


class SaveImagesMultiPathSimple:
    """
    Simplified save node that saves all images to a single output.
    Does not require path_info - just saves all images as one sequence/video.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "output_format": (["images", "mp4"],),
                "filename_prefix": ("STRING", {"default": "output"}),
                "output_directory": ("STRING", {"default": "", "placeholder": "Leave empty for ComfyUI output folder"}),
            },
            "optional": {
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "image_format": (["png", "jpg", "webp"],),
                "jpg_quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "video_quality": ("INT", {"default": 23, "min": 0, "max": 51, "step": 1, "tooltip": "CRF value: 0=lossless, 23=default, 51=worst"}),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image/multi-path"
    DESCRIPTION = "Simple save node - saves all images as one sequence or video."

    def save_images(self, images, output_format, filename_prefix, 
                    output_directory="", frame_rate=24, image_format="png", 
                    jpg_quality=95, video_quality=23):
        """Save all images as single output"""
        
        # Determine output directory
        if output_directory and output_directory.strip():
            out_dir = output_directory.strip()
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
        else:
            out_dir = folder_paths.get_output_directory()
        
        base_filename = sanitize_filename(filename_prefix)
        frame_count = images.shape[0]
        
        print(f"[SaveImagesMultiPath] Saving {frame_count} frames as '{base_filename}'")
        
        if output_format == "images":
            # Save as image sequence
            output_subdir = os.path.join(out_dir, base_filename)
            os.makedirs(output_subdir, exist_ok=True)
            
            for j, img_tensor in enumerate(images):
                img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
                img = Image.fromarray(img_np)
                
                frame_filename = f"{base_filename}_{j:05d}.{image_format}"
                frame_path = os.path.join(output_subdir, frame_filename)
                
                if image_format == "jpg":
                    img.save(frame_path, quality=jpg_quality)
                elif image_format == "webp":
                    img.save(frame_path, quality=jpg_quality)
                else:
                    img.save(frame_path)
            
            output_path = output_subdir
            print(f"[SaveImagesMultiPath] Saved {frame_count} images to: {output_subdir}")
            
        elif output_format == "mp4":
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                raise RuntimeError("ffmpeg not found. Please install ffmpeg to export MP4 videos.")
            
            output_file = os.path.join(out_dir, f"{base_filename}.mp4")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                for j, img_tensor in enumerate(images):
                    img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
                    img = Image.fromarray(img_np)
                    temp_frame = os.path.join(temp_dir, f"frame_{j:05d}.png")
                    img.save(temp_frame)
                
                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-framerate", str(frame_rate),
                    "-i", os.path.join(temp_dir, "frame_%05d.png"),
                    "-c:v", "libx264",
                    "-crf", str(video_quality),
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    output_file
                ]
                
                print(f"[SaveImagesMultiPath] Running ffmpeg: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"[SaveImagesMultiPath] ffmpeg error: {result.stderr}")
                    raise RuntimeError(f"ffmpeg failed: {result.stderr}")
            
            output_path = output_file
            print(f"[SaveImagesMultiPath] Saved video to: {output_file}")
        
        return {"ui": {"text": [output_path]}, "result": (output_path,)}
    
    @classmethod
    def IS_CHANGED(s, **kwargs):
        return float("nan")
