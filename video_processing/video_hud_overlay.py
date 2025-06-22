#!/usr/bin/env python3
"""
Video HUD Overlay - Creates a HUD overlay on the timestamped video showing events.
Takes the merged timeline JSON with BaseModel event data and overlays events as text on the video.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import tempfile

# Add parent directory to path to import BaseModels
sys.path.append(str(Path(__file__).parent.parent))

from video_understanding.simple_models import (
    PipetteSettingChange,
    AspirationEvent,
    DispensingEvent,
    TipChangeEvent,
    WarningEvent,
    WellStateEvent,
    Reagent
)


def create_enhanced_event_text(event: Dict) -> str:
    """Create enhanced event text using BaseModel data"""
    event_model_type = event.get("event_model_type")
    event_model = event.get("event_model", {})
    
    if event_model_type == "AspirationEvent":
        reagent = event_model.get("reagent", {})
        return f"↑ {reagent.get('name', 'Unknown')} ({reagent.get('volume_ul', 0)}μL)"
    
    elif event_model_type == "DispensingEvent":
        reagent = event_model.get("reagent", {})
        return f"↓ {reagent.get('name', 'Unknown')} ({reagent.get('volume_ul', 0)}μL)"
    
    elif event_model_type == "WellStateEvent":
        well_id = event_model.get("well_id", "?")
        is_complete = event_model.get("is_complete", False)
        contents = event_model.get("current_contents", [])
        reagent_names = [r.get("name", "?") for r in contents]
        status = "✓" if is_complete else "..."
        return f"{well_id}: {'+'.join(reagent_names)} {status}"
    
    elif event_model_type == "PipetteSettingChange":
        volume = event_model.get("new_setting_ul", 0)
        return f"⚙ {volume}μL"
    
    elif event_model_type == "WarningEvent":
        warning = event_model.get("warning_message", "Warning")
        return f"⚠ {warning}"
    
    elif event_model_type == "TipChangeEvent":
        return "🔄 Tip"
    
    else:
        return event.get("title", "Event")


def create_hud_video(
    input_video: str,
    timeline_file: str,
    output_video: str,
    temp_dir: str = None
) -> None:
    """Create HUD overlay video using FFmpeg"""
    
    # Load timeline
    with open(timeline_file, 'r') as f:
        timeline_data = json.load(f)
    
    timeline_events = timeline_data["timeline"]
    
    print(f"Processing {len(timeline_events)} events for HUD overlay...")
    
    # Get video duration
    duration_cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", input_video
    ]
    
    try:
        result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
        video_duration = float(result.stdout.strip())
        print(f"Video duration: {video_duration:.2f} seconds")
    except subprocess.CalledProcessError as e:
        print(f"Error getting video duration: {e}")
        video_duration = 120.0  # Default fallback
    
    # Create drawtext filter
    if not timeline_events:
        print("No events to overlay")
        return
    
    # Build complex filter with multiple drawtext overlays
    video_filters = []
    
    # Add timestamp preservation (if needed)
    base_filter = "[0:v]"
    
    # Add each event as a separate drawtext filter
    for i, event in enumerate(timeline_events):
        start_time = event["start_time"]
        end_time = event["end_time"]
        event_type = event["event_type"]
        title = event["title"].replace("'", "").replace(":", " ").replace(";", " ")  # Clean text
        
        # Color scheme
        colors = {
            "warning": "red",
            "well_state": "lime",
            "pipette_setting": "yellow",
            "aspiration": "cyan",
            "dispensing": "orange", 
            "tip_change": "white"
        }
        color = colors.get(event_type, "white")
        
        # Y position based on event type with better spacing
        y_positions = {
            "warning": 50,
            "pipette_setting": 90,
            "well_state": 130,
            "aspiration": 170,
            "dispensing": 210,
            "tip_change": 250
        }
        y_pos = y_positions.get(event_type, 290)
        
        # Add background box for better readability
        box_alpha = "0.7"
        
        if i == 0:
            filter_input = "[0:v]"
        else:
            filter_input = f"[v{i}]"
        
        if i == len(timeline_events) - 1:
            filter_output = "[out]"
        else:
            filter_output = f"[v{i+1}]"
        
        # Use enhanced event text from BaseModel data
        enhanced_text = create_enhanced_event_text(event)
        # Clean text for FFmpeg (remove special chars that cause issues)
        clean_text = enhanced_text.replace("'", "").replace(":", " ").replace(";", " ").replace("μ", "u")
        
        # Create drawtext filter with background box
        drawtext_filter = (
            f"{filter_input}drawtext=text='{clean_text}'"
            f":fontcolor={color}:fontsize=20:box=1:boxcolor=black@{box_alpha}"
            f":x=15:y={y_pos}:enable='between(t,{start_time},{end_time})'{filter_output}"
        )
        
        video_filters.append(drawtext_filter)
    
    # Combine all filters
    complex_filter = ";".join(video_filters)
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", "-y",  # Overwrite output
        "-i", input_video,
        "-filter_complex", complex_filter,
        "-map", "[out]",
        "-map", "0:a?",  # Include audio if present
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "copy",  # Copy audio without re-encoding
        output_video
    ]
    
    print("Running FFmpeg command...")
    print(" ".join(ffmpeg_cmd))
    
    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"✓ HUD video created: {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        raise


def main():
    """Main function to create HUD overlay video"""
    base_dir = Path(__file__).parent.parent
    
    # Input files
    input_video = base_dir / "videos" / "output_long_again_2_timestamped.mp4"
    timeline_file = base_dir / "video_processing" / "merged_timeline.json"
    
    # Output file
    output_video = base_dir / "video_processing" / "hud_overlay_video.mp4"
    
    # Check if input files exist
    if not input_video.exists():
        print(f"Error: Input video not found: {input_video}")
        return
    
    if not timeline_file.exists():
        print(f"Error: Timeline file not found: {timeline_file}")
        return
    
    print(f"Input video: {input_video}")
    print(f"Timeline file: {timeline_file}")
    print(f"Output video: {output_video}")
    
    # Create HUD overlay
    create_hud_video(
        str(input_video),
        str(timeline_file), 
        str(output_video)
    )


if __name__ == "__main__":
    main()