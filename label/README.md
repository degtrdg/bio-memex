# Label Directory

This directory contains a computer vision labeling system that uses Roboflow's inference API to detect and annotate objects in images. The system runs two different workflows to identify source and destination objects, then creates annotated images with bounding boxes.

## Overview

The labeling system performs the following tasks:
1. **Source Detection**: Identifies source objects using a custom workflow (`custom-workflow-2`)
2. **Destination Detection**: Identifies destination objects using another custom workflow (`custom-workflow-3`)
3. **Annotation**: Draws bounding boxes on images to visualize the detected objects
4. **Data Organization**: Saves results in a structured directory format

## Features

- **Dual Workflow Processing**: Runs two separate AI workflows for different object detection tasks
- **Automatic Data Organization**: Creates and maintains organized directory structure
- **Visual Annotations**: Generates annotated images with colored bounding boxes
- **JSON Export**: Saves raw API results for further analysis
- **Confidence Filtering**: Filters destination predictions based on confidence thresholds

## Directory Structure

The system automatically creates the following directory structure:

```
label/
├── data/
│   ├── json/           # Raw API results
│   ├── original/       # Original input images
│   └── annotated/      # Images with bounding box annotations
├── label.py           # Main labeling script
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Dependencies

- `opencv-python>=4.5.0`: For image processing and drawing bounding boxes
- `inference_sdk`: Roboflow's Python SDK for API interactions

## Usage

### Basic Usage

Run the labeling script with an image path:

```bash
python label.py <image_path>
```

### Example

```bash
python label.py ../videos/0.mov
```

## Workflow Details

### Source Workflow (`custom-workflow-2`)
- **Purpose**: Detects source objects in the image
- **Selection Criteria**: Finds the object with the smallest y-coordinate (highest in the image)
- **Filtering**: Excludes objects with height > 500 pixels
- **Output**: Single prediction with bounding box coordinates

### Destination Workflow (`custom-workflow-3`)
- **Purpose**: Detects destination objects in the image
- **Selection Criteria**: All objects above confidence threshold (default: 0.1)
- **Filtering**: Confidence-based filtering only
- **Output**: Multiple predictions with bounding box coordinates

## Output Files

For each processed image, the system generates:

1. **JSON Results** (`data/json/`):
   - `{basename}_source_results.json`: Raw source workflow results
   - `{basename}_destination_results.json`: Raw destination workflow results

2. **Annotated Images** (`data/annotated/`):
   - `{basename}_combined_annotated.jpg`: Image with both source (green) and destination (red) bounding boxes

## Bounding Box Format

The system handles two bounding box formats:
- **Center-based**: `[x, y, width, height]` where x,y are center coordinates
- **Separate fields**: Individual `x`, `y`, `width`, `height` fields

## Color Coding

- **Green bounding boxes**: Source objects (detected by workflow-2)
- **Red bounding boxes**: Destination objects (detected by workflow-3)

## Configuration

### API Configuration
The script uses the following Roboflow configuration:
- **Workspace**: `test-ymb2o`
- **API URL**: `https://serverless.roboflow.com`
- **API Key**: Configured in the script

### Confidence Thresholds
- **Source**: No confidence filtering (selects by position)
- **Destination**: Default threshold of 0.1 (configurable)

## Error Handling

The system includes error handling for:
- Missing or invalid image files
- API request failures
- JSON serialization errors
- Directory creation issues

## Troubleshooting

### Common Issues

1. **Image not found**: Ensure the image path is correct and the file exists
2. **API errors**: Check your internet connection and API key validity
3. **Permission errors**: Ensure write permissions for the data directories

### Debug Information

The script provides detailed console output including:
- Workflow execution status
- Prediction counts and confidence scores
- Bounding box coordinates
- File save locations

## API Requirements

- Valid Roboflow API key
- Access to the specified workspace (`test-ymb2o`)
- Access to the custom workflows (`custom-workflow-2` and `custom-workflow-3`)

## License

This labeling system is part of the bio-memex project. Please refer to the main project license for usage terms. 