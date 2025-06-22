# Video HUD Processing Pipeline

This folder contains the complete BaseModel-powered pipeline for processing laboratory video analysis results into a HUD (Heads-Up Display) overlay video.

## Overview

The pipeline leverages Pydantic BaseModel classes to validate and process the three JSON analysis files (`analysis_events_result.json`, `objective_events_result.json`, `procedure_result.json`) into a single video with typed event overlays synchronized to the timeline.

## Files

### Scripts

- **`event_merger.py`** - Merges the three JSON files into a single timeline with unified event format
- **`json_to_models.py`** - Converts JSON files to validated BaseModel instances for type checking
- **`video_hud_overlay.py`** - Creates the final HUD overlay video using FFmpeg
- **`hud_processing.ipynb`** - Jupyter notebook for interactive testing and visualization

### Generated Files

- **`merged_timeline.json`** - Combined timeline of all events sorted by time
- **`validated_*.json`** - Type-validated versions of the original JSON files
- **`hud_overlay_video.mp4`** - Final output video with HUD overlays

## Usage

### Quick Start

Run the complete pipeline:

```bash
# Merge events into timeline
uv run video_processing/event_merger.py

# Validate JSON files (optional)
uv run video_processing/json_to_models.py

# Create HUD overlay video
uv run video_processing/video_hud_overlay.py
```

### Using the Notebook

For interactive exploration and visualization:

```bash
jupyter lab video_processing/hud_processing.ipynb
```

## BaseModel-Enhanced HUD Events

The HUD displays typed events with enhanced BaseModel-powered formatting:

- **⚠ Warning Events** (Red) - `⚠ Workspace Clutter and Contamination Risk`
- **Well State Events** (Lime) - `A1: A+B ✓` (complete) or `A2: A ...` (partial)
- **Pipette Settings** (Yellow) - `⚙ 30μL`
- **Aspiration Events** (Cyan) - `↑ Reagent A (30.0μL)`
- **Dispensing Events** (Orange) - `↓ Reagent B (30.0μL)`
- **Tip Changes** (White) - `🔄 Tip`

## BaseModel Event Timeline Structure

Each event in the merged timeline contains validated BaseModel data:

```json
{
  "start_time": 14.0,
  "end_time": 16.0,
  "event_type": "well_state",
  "title": "Well A1: Partial",
  "description": "Contains: A",
  "priority": "medium",
  "event_model": {
    "thinking": "The user dispenses...",
    "timestamp_range": "0:14 - 0:16",
    "well_id": "A1",
    "is_complete": false,
    "current_contents": [{"name": "A", "volume_ul": 30.0}],
    "missing_reagents": [{"name": "B", "volume_ul": 30.0}]
  },
  "event_model_type": "WellStateEvent"
}
```

## Processing Statistics

Based on the current analysis:

- **Total Events**: 26
- **Event Breakdown**:
  - Aspiration: 9 events
  - Well State: 6 events  
  - Tip Change: 6 events
  - Dispensing: 3 events
  - Pipette Setting: 1 event
  - Warning: 1 event

## Requirements

- Python with `uv` package manager
- FFmpeg for video processing
- Jupyter Lab for notebook usage (optional)

## Input/Output

**Input**: 
- `videos/output_long_again_2_timestamped.mp4` (timestamped source video)
- `analysis_events_result.json` (warning and well state events)
- `objective_events_result.json` (pipetting action events)  
- `procedure_result.json` (experimental protocol context)

**Output**:
- `video_processing/hud_overlay_video.mp4` (final HUD video)

## Notes

- Events are positioned vertically by type to avoid overlap
- Background boxes improve text readability
- Timeline synchronization uses precise timestamp ranges
- The pipeline preserves all original video quality and audio