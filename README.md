# ComfyUI-LoadImagesMultiPath

Load images from multiple directories into a single batch, process them, and save back split by original folders.

## Features

- Load from up to 50 directories
- Standard `IMAGE` output - works with any ComfyUI node
- `path_info` tracks folder boundaries for split saving
- Export as PNG/JPG/WebP sequences or MP4 video

## Important

**All images are resized to match the first image of the first folder** when `size_check=True` (default). This ensures a consistent batch size for processing.

If `size_check=False`, all images must already have the same dimensions or the node will fail.

## Installation

1. Copy to `ComfyUI/custom_nodes/`
2. Install ffmpeg for MP4 export (optional)
3. Restart ComfyUI

## Workflow

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Load Images         │     │ Processing       │     │ Save Images         │
│ Multi-Path          │────▶│ (any nodes)      │────▶│ Multi-Path          │
│                     │     │                  │     │                     │
│ IMAGE ─────────────────────────────────────────────▶ images              │
│ path_info ─────────────────────────────────────────▶ path_info           │
└─────────────────────┘     └──────────────────┘     └─────────────────────┘
```

**Output:**
- `output_folderA.mp4`
- `output_folderB.mp4`
- `output_folderC.mp4`

## Load Node Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| path_count | 1 | Number of directories (1-50) |
| directory_N | - | Directory path |
| size_check | True | Resize all images to first image size |
| image_load_cap | 0 | Max images per folder (0=unlimited) |
| skip_first_images | 0 | Skip N images at start |
| select_every_nth | 1 | Load every Nth image |

**Outputs:** `IMAGE`, `frame_count`, `path_info`

## Save Node Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| output_format | images | `images` or `mp4` |
| filename_prefix | output | Base filename (folder name appended) |
| output_directory | - | Output path (empty=ComfyUI output) |
| image_format | png | `png`, `jpg`, `webp` |
| quality | 95 | JPG/WebP quality (1-100) |
| frame_rate | 24 | FPS for MP4 |
| video_crf | 23 | MP4 quality (0=best, 51=worst) |

## License

MIT
