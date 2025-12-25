# ComfyUI-LoadImagesMultiPath

Load images from multiple directories and save them separately. Each folder maintains its own dimensions.

## Features

- Load from up to 50 directories
- Each folder keeps its original image dimensions
- Optional within-folder size normalization
- Export as PNG/JPG/WebP sequences or MP4 video
- Automatic filename suffix from folder names

## Installation

1. Copy to `ComfyUI/custom_nodes/`
2. Install ffmpeg for MP4 export (optional)
3. Restart ComfyUI

## Nodes

### Load Images Multi-Path (Upload/Path)

| Parameter | Default | Description |
|-----------|---------|-------------|
| path_count | 1 | Number of directories (1-50) |
| directory_N | - | Directory path |
| size_check | True | Resize images within folder to match first image |
| image_load_cap | 0 | Max images per folder (0=unlimited) |
| skip_first_images | 0 | Skip N images at start |
| select_every_nth | 1 | Load every Nth image |

**Output:** `MULTI_IMAGE_BATCH`, `total_frames`

### Save Images Multi-Path

| Parameter | Default | Description |
|-----------|---------|-------------|
| output_format | images | `images` or `mp4` |
| filename_prefix | output | Base filename |
| output_directory | - | Output path (empty=ComfyUI output) |
| frame_rate | 24 | FPS for MP4 |
| image_format | png | `png`, `jpg`, `webp` |
| quality | 95 | JPG/WebP quality |
| video_crf | 23 | MP4 quality (0=best, 51=worst) |

## Usage

```
[Load Multi-Path] → [Save Multi-Path]
     ↓                    ↓
  folder_A (800x600)   output_folder_A.mp4 (800x600)
  folder_B (1920x1080) output_folder_B.mp4 (1920x1080)
```

## Notes

- Folders are processed separately - no cross-folder resizing
- `size_check` only affects images within the same folder
- Connect load node directly to save node (no processing in between)

## License

MIT
