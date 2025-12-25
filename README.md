# ComfyUI-LoadImagesMultiPath

A ComfyUI custom node package for loading images from multiple directories and saving them back separately. **Each folder maintains its own image dimensions** - no cross-folder resizing.

## Features

- **Multiple Directory Support**: Load images from up to 50 different directories
- **Separate Folder Processing**: Each folder maintains its own dimensions - no cross-folder resizing
- **Optional Within-Folder Size Check**: When enabled, resizes images within each folder to match the first image
- **Alpha Channel Handling**: Properly handles RGBA images
- **Progress Bar**: Shows loading progress across all directories
- **Graceful Skipping**: Empty or invalid directories are skipped with warnings
- **Dynamic UI**: Directory input fields show/hide based on `path_count` value
- **Split Save**: Save outputs to separate files per folder with automatic naming
- **Multiple Export Formats**: Save as image sequences (PNG/JPG/WebP) or MP4 videos (H.264)

## Installation

1. Navigate to your ComfyUI custom nodes directory:
   ```bash
   cd ComfyUI/custom_nodes/
   ```

2. Clone or copy this repository:
   ```bash
   git clone https://github.com/yourusername/ComfyUI-LoadImagesMultiPath.git
   ```
   
   Or simply copy the `ComfyUI-LoadImagesMultiPath` folder into `custom_nodes/`

3. Install dependencies (most are already included with ComfyUI):
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ffmpeg** (required for MP4 export):
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use `choco install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)

5. Restart ComfyUI

## Nodes

### Load Images Multi-Path (Upload)
- Uses dropdown selection for directories from ComfyUI's input folder
- Each folder maintains its original image dimensions
- Outputs: MULTI_IMAGE_BATCH, total_frames

### Load Images Multi-Path (Path)
- Uses string input for full directory paths
- Each folder maintains its original image dimensions
- Outputs: MULTI_IMAGE_BATCH, total_frames

### Save Images Multi-Path
- Saves images/videos from MULTI_IMAGE_BATCH
- Each folder saved separately with original dimensions
- Automatically appends `_directoryname` suffix to filename

### Save Images/Video (Simple)
- Simple save node for standard IMAGE type
- Saves all images as a single output

## Load Node Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path_count` | INT | 1 | Number of directory inputs to use (1-50) |
| `directory_1` to `directory_50` | STRING/DROPDOWN | "" | Directory paths to load images from |
| `size_check` | BOOLEAN | True | If True, resize images within each folder to match first image. If False, all images in folder must have same size |
| `image_load_cap` | INT | 0 | Maximum images to load per directory (0 = no limit) |
| `skip_first_images` | INT | 0 | Number of images to skip at the start of each directory |
| `select_every_nth` | INT | 1 | Load every Nth image from each directory |

## Save Node Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_batches` | MULTI_IMAGE_BATCH | - | Input from load node |
| `output_format` | DROPDOWN | "images" | Export format: "images" or "mp4" |
| `filename_prefix` | STRING | "output" | Base filename (directory name is appended automatically) |
| `output_directory` | STRING | "" | Output folder (empty = ComfyUI output folder) |
| `frame_rate` | INT | 24 | Frame rate for MP4 export |
| `image_format` | DROPDOWN | "png" | Image format: "png", "jpg", or "webp" |
| `jpg_quality` | INT | 95 | Quality for JPG/WebP (1-100) |
| `video_quality` | INT | 23 | CRF value for MP4 (0=lossless, 23=default, 51=worst) |

## Workflow

```
┌─────────────────────────────┐
│  Load Images Multi-Path     │
├─────────────────────────────┤
│  path_count: 3              │
│  directory_1: scene_A (530x528)
│  directory_2: scene_B (1080x1920)
│  directory_3: scene_C (720x480)
└──────────┬──────────────────┘
           │
           │ MULTI_IMAGE_BATCH (each folder separate)
           ▼
┌─────────────────────────────┐
│  Save Images Multi-Path     │
├─────────────────────────────┤
│  output_format: mp4         │
│  filename_prefix: output    │
└─────────────────────────────┘
           │
           ▼
    Output Files (each with original dimensions):
    - output_scene_A.mp4 (530x528)
    - output_scene_B.mp4 (1080x1920)
    - output_scene_C.mp4 (720x480)
```

## Key Behavior

1. **No cross-folder resizing**: Each folder keeps its original dimensions
2. **Within-folder size_check**: When enabled, images within each folder are resized to match that folder's first image
3. **Direct save connection**: Connect Load node directly to Save node - no processing nodes between (they only accept standard IMAGE type)

## Notes

- This node package uses a custom `MULTI_IMAGE_BATCH` type to keep folders separate
- If you need to process images (filters, upscaling, etc.), you'll need to process each folder separately using standard ComfyUI nodes
- Empty directories or invalid paths are skipped automatically
- Supported image formats: PNG, JPG, JPEG, BMP, WEBP, and other common formats
- MP4 export uses H.264 codec with yuv420p pixel format for maximum compatibility

## License

MIT License - See [LICENSE](LICENSE) file for details.
