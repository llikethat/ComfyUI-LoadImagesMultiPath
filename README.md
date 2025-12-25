# ComfyUI-LoadImagesMultiPath

A ComfyUI custom node package for loading images from multiple directories sequentially and saving them back split by directory.

## Features

- **Multiple Directory Support**: Load images from up to 50 different directories
- **Sequential Processing**: Directories are processed in order (directory_1, directory_2, etc.)
- **Optional Size Check**: When enabled, automatically resizes images within each folder to match the first image's size
- **Alpha Channel Handling**: Properly handles RGBA images
- **Progress Bar**: Shows loading progress across all directories
- **Graceful Skipping**: Empty or invalid directories are skipped with warnings
- **Dynamic UI**: Directory input fields show/hide based on `path_count` value
- **Split Save**: Save outputs split by original directories with automatic naming
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

## File Structure

```
ComfyUI-LoadImagesMultiPath/
├── __init__.py          # Node registration
├── utils.py             # Common utilities and helper functions
├── load_nodes.py        # Load node classes
├── save_nodes.py        # Save node classes
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
├── README.md            # This file
└── web/
    └── js/
        └── multipath_widgets.js  # Dynamic widget visibility
```

## Nodes

### Load Images Multi-Path (Upload)
- Uses dropdown selection for directories from ComfyUI's input folder
- Best for directories already uploaded to ComfyUI
- Outputs: IMAGE, MASK, frame_count, path_info

### Load Images Multi-Path (Path)
- Uses string input for full directory paths
- Best for accessing directories anywhere on your system
- Outputs: IMAGE, MASK, frame_count, path_info

### Save Images Multi-Path
- Saves images/videos split by original directories
- Requires `path_info` from load nodes to know how to split
- Automatically appends `_directoryname` suffix to filename
- Example: If you load from folders "scene1" and "scene2" with filename "output":
  - Creates: `output_scene1.mp4` and `output_scene2.mp4` (or image folders)

### Save Images/Video (Simple)
- Simple save node that saves all images as a single output
- Does not require path_info
- Good for saving processed results without splitting

## Load Node Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path_count` | INT | 1 | Number of directory inputs to use (1-50) |
| `directory_1` to `directory_50` | STRING/DROPDOWN | "" | Directory paths to load images from |
| `size_check` | BOOLEAN | True | If True, resize images to match first image in each folder. If False, all images must have same size |
| `image_load_cap` | INT | 0 | Maximum images to load per directory (0 = no limit) |
| `skip_first_images` | INT | 0 | Number of images to skip at the start of each directory |
| `select_every_nth` | INT | 1 | Load every Nth image from each directory |

## Save Node Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | - | Input images to save |
| `path_info` | MULTIPATH_INFO | - | Path info from load node (only for SaveImagesMultiPath) |
| `output_format` | DROPDOWN | "images" | Export format: "images" or "mp4" |
| `filename_prefix` | STRING | "output" | Base filename (directory name is appended automatically) |
| `output_directory` | STRING | "" | Output folder (empty = ComfyUI output folder) |
| `frame_rate` | INT | 24 | Frame rate for MP4 export |
| `image_format` | DROPDOWN | "png" | Image format: "png", "jpg", or "webp" |
| `jpg_quality` | INT | 95 | Quality for JPG/WebP (1-100) |
| `video_quality` | INT | 23 | CRF value for MP4 (0=lossless, 23=default, 51=worst) |

## Outputs

### Load Nodes

| Output | Type | Description |
|--------|------|-------------|
| `IMAGE` | IMAGE | Combined batch of all loaded images |
| `MASK` | MASK | Combined masks (alpha channels or empty masks) |
| `frame_count` | INT | Total number of images loaded |
| `path_info` | MULTIPATH_INFO | Directory info for the save node |

### Save Nodes

| Output | Type | Description |
|--------|------|-------------|
| `output_paths` | STRING | Newline-separated list of output paths |

## Usage Example

1. Add **Load Images Multi-Path (Upload)** or **(Path)** node
2. Set `path_count` to the number of directories (e.g., 3)
3. Select or enter directory paths
4. Connect IMAGE output to your processing nodes
5. Connect all outputs to **Save Images Multi-Path** node
6. Set filename_prefix (e.g., "processed")
7. Choose output_format: "images" or "mp4"
8. Run the workflow

If your directories were named "scene_A", "scene_B", "scene_C", you'll get:
- `processed_scene_A.mp4` (or folder with images)
- `processed_scene_B.mp4`
- `processed_scene_C.mp4`

## Workflow Diagram

```
┌─────────────────────────────┐
│  Load Images Multi-Path     │
│  (Upload or Path)           │
├─────────────────────────────┤
│  path_count: 3              │
│  directory_1: scene_A       │
│  directory_2: scene_B       │
│  directory_3: scene_C       │
└──────────┬──────────────────┘
           │
           │ IMAGE, MASK, frame_count, path_info
           ▼
┌─────────────────────────────┐
│  Your Processing Nodes      │
│  (effects, upscaling, etc.) │
└──────────┬──────────────────┘
           │
           │ IMAGE
           ▼
┌─────────────────────────────┐
│  Save Images Multi-Path     │
├─────────────────────────────┤
│  images: ←─────────────────────── (from processing)
│  path_info: ←──────────────────── (from load node)
│  output_format: mp4         │
│  filename_prefix: processed │
└─────────────────────────────┘
           │
           ▼
    Output Files:
    - processed_scene_A.mp4
    - processed_scene_B.mp4
    - processed_scene_C.mp4
```

## Example Use Cases

- **Animation Sequences**: Combine multiple animation folders, process them, then save back separately
- **Batch Video Processing**: Load frames from multiple videos, apply effects, export as separate videos
- **Dataset Processing**: Process images from different source folders and maintain organization
- **Multi-angle Rendering**: Process renders from different camera angles in sequence

## Requirements

- Python 3.8+
- ComfyUI (latest version recommended)
- **ffmpeg** (required for MP4 export) - See installation instructions above

## Notes

- **size_check option**: When enabled (default), images within each folder are resized to match the first image's dimensions. When disabled, all images must have identical dimensions.
- **Per-folder resizing**: Each folder uses its own first image as the target size - folders can have different sizes from each other
- **Cross-directory consistency**: All directories must output the same final image dimensions (use resize nodes in workflow if needed)
- Empty directories or invalid paths are skipped automatically
- The node processes directories in numerical order (1, 2, 3, etc.)
- Supported image formats: PNG, JPG, JPEG, BMP, WEBP, and other common formats
- MP4 export uses H.264 codec with yuv420p pixel format for maximum compatibility

## License

MIT License - See [LICENSE](LICENSE) file for details.
