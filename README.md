# ComfyUI-LoadImagesMultiPath

A ComfyUI custom node for loading images from multiple directories sequentially. This node allows you to specify multiple folder paths and processes them in order, combining all images into a single batch.

## Features

- **Multiple Directory Support**: Load images from up to 50 different directories
- **Sequential Processing**: Directories are processed in order (directory_1, directory_2, etc.)
- **Automatic Resizing**: Images from different directories are automatically resized to match the first directory's dimensions
- **Alpha Channel Handling**: Properly handles mixed RGBA/RGB images
- **Progress Bar**: Shows loading progress across all directories
- **Graceful Skipping**: Empty or invalid directories are skipped with warnings
- **Dynamic UI**: Directory input fields show/hide based on `path_count` value

## Installation

Navigate to your ComfyUI custom nodes directory:
   ```
   cd ComfyUI/custom_nodes/
   ```

Restart ComfyUI

## Nodes

### Load Images Multi-Path (Upload)
- Uses dropdown selection for directories from ComfyUI's input folder
- Best for directories already uploaded to ComfyUI

### Load Images Multi-Path (Path)
- Uses string input for full directory paths
- Best for accessing directories anywhere on your system

## Usage

1. Add the node to your workflow
2. Set `path_count` to the number of directories you want to use
3. Select or enter the directory paths
4. Connect the outputs to your workflow

## License

MIT License
