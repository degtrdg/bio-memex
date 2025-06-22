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


def create_enhanced_event_text(event: Dict) -> Tuple[str, str, int]:
    """Create enhanced event text using BaseModel data
    Returns: (main_text, detail_text, font_size)
    """
    event_model_type = event.get("event_model_type")
    event_model = event.get("event_model", {})
    
    if event_model_type == "AspirationEvent":
        reagent = event_model.get("reagent", {})
        reagent_name = reagent.get('name', 'Unknown').replace('Reagent ', '')
        volume = reagent.get('volume_ul', 0)
        return f"ASPIRATING {reagent_name}", f"{volume}μL", 48
    
    elif event_model_type == "DispensingEvent":
        reagent = event_model.get("reagent", {})
        reagent_name = reagent.get('name', 'Unknown').replace('Reagent ', '')
        volume = reagent.get('volume_ul', 0)
        return f"DISPENSING {reagent_name}", f"{volume}μL", 48
    
    elif event_model_type == "WellStateEvent":
        well_id = event_model.get("well_id", "?")
        is_complete = event_model.get("is_complete", False)
        contents = event_model.get("current_contents", [])
        reagent_names = [r.get("name", "?").replace('Reagent ', '') for r in contents]
        
        if is_complete:
            return f"WELL {well_id} COMPLETE", f"Contains: {' + '.join(reagent_names)}", 42
        else:
            return f"WELL {well_id} PARTIAL", f"Added: {' + '.join(reagent_names)}", 42
    
    elif event_model_type == "PipetteSettingChange":
        volume = event_model.get("new_setting_ul", 0)
        return f"PIPETTE SET", f"{volume}μL", 36
    
    elif event_model_type == "WarningEvent":
        warning = event_model.get("warning_message", "Warning")
        description = event_model.get("description", "")
        return f"WARNING", description or warning[:40], 44
    
    elif event_model_type == "TipChangeEvent":
        return f"TIP CHANGE", "New tip attached", 36
    
    else:
        return event.get("title", "Event"), "", 36


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
    
    # Filter and prioritize events to prevent overlaps
    # Group events by priority and deduplicate overlapping timeframes
    priority_order = {"warning": 4, "dispensing": 3, "aspiration": 3, "well_state": 2, "pipette_setting": 1, "tip_change": 0}
    
    # Sort events by priority, then by start time
    sorted_events = sorted(timeline_events, key=lambda x: (x["start_time"], -priority_order.get(x["event_type"], 0)))
    
    # Remove overlapping events - keep highest priority event for each time period
    filtered_events = []
    for event in sorted_events:
        start_time = event["start_time"]
        end_time = event["end_time"]
        
        # Check for overlap with existing events
        has_overlap = False
        for existing in filtered_events:
            existing_start = existing["start_time"]
            existing_end = existing["end_time"]
            
            # Check if events overlap
            if not (end_time <= existing_start or start_time >= existing_end):
                # Events overlap - keep the higher priority one
                existing_priority = priority_order.get(existing["event_type"], 0)
                current_priority = priority_order.get(event["event_type"], 0)
                
                if current_priority > existing_priority:
                    # Remove the existing lower priority event
                    filtered_events.remove(existing)
                else:
                    # Skip this event
                    has_overlap = True
                    break
        
        if not has_overlap:
            filtered_events.append(event)
    
    # Sort filtered events by start time
    filtered_events.sort(key=lambda x: x["start_time"])
    
    print(f"Filtered to {len(filtered_events)} non-overlapping events from {len(timeline_events)} total")
    
    # Build HUD overlays - positioned at top of screen
    video_filters = []
    current_input = "[0:v]"
    
    for i, event in enumerate(filtered_events):
        start_time = event["start_time"]
        end_time = event["end_time"]
        event_type = event["event_type"]
        
        # Get enhanced text with different sizes for different event types
        main_text, detail_text, font_size = create_enhanced_event_text(event)
        
        # Color scheme - bright and bold for visibility
        colors = {
            "warning": "red",
            "well_state": "lime", 
            "pipette_setting": "yellow",
            "aspiration": "cyan",
            "dispensing": "orange",
            "tip_change": "white"
        }
        color = colors.get(event_type, "white")
        
        # Clean text for FFmpeg
        main_clean = main_text.replace("'", "").replace(":", " ").replace(";", " ").replace("μ", "u")
        detail_clean = detail_text.replace("'", "").replace(":", " ").replace(";", " ").replace("μ", "u")
        
        # Determine output label
        if i == len(filtered_events) - 1:
            output_label = "[out]"
        else:
            output_label = f"[v{i+1}]"
        
        # Get thinking commentary for left side
        thinking_text = event.get("event_model", {}).get("thinking", "")
        thinking_clean = thinking_text.replace("'", "").replace(":", " ").replace(";", " ").replace("μ", "u")
        # Limit length for sidebar display
        if len(thinking_clean) > 150:
            thinking_clean = thinking_clean[:147] + "..."
        
        # Create main HUD text (no manual newlines - use separate filters)
        main_text_only = main_clean
        
        # Position at top of screen, centered horizontally
        y_position = "50"  # 50 pixels from top
        
        # Increase font sizes
        main_font_size = font_size + 8  # Make main text even bigger
        detail_font_size = max(28, font_size - 8)  # Bigger detail text
        
        # Create main drawtext filter with sci-fi style font
        main_filter = (
            f"{current_input}drawtext=text='{main_text_only}'"
            f":fontcolor={color}:fontsize={main_font_size}:fontfile=/System/Library/Fonts/Menlo.ttc"
            f":box=1:boxcolor=black@0.9:boxborderw=8"
            f":x=(w-text_w)/2:y={y_position}"
            f":enable='between(t,{start_time},{end_time})'"
        )
        
        # Add detail text below if it exists
        detail_y = str(int(y_position) + main_font_size + 15)
        if detail_clean and detail_clean.strip():
            main_filter += f"[temp{i}];[temp{i}]drawtext=text='{detail_clean}'"
            main_filter += f":fontcolor=white:fontsize={detail_font_size}:fontfile=/System/Library/Fonts/Menlo.ttc"
            main_filter += f":box=1:boxcolor=black@0.9:boxborderw=6"
            main_filter += f":x=(w-text_w)/2:y={detail_y}"
            main_filter += f":enable='between(t,{start_time},{end_time})'"
        
        # Add thinking commentary on left side if it exists
        if thinking_clean and thinking_clean.strip():
            # Position the commentary box on left side
            commentary_y = 200  # Start position from top
            
            if detail_clean:
                main_filter += f"[temp{i}b];[temp{i}b]"
            else:
                main_filter += f"[temp{i}];[temp{i}]"
            
            main_filter += f"drawtext=text='{thinking_clean}'"
            main_filter += f":fontcolor=gray:fontsize=18:fontfile=/System/Library/Fonts/Menlo.ttc"
            main_filter += f":box=1:boxcolor=black@0.85:boxborderw=4"
            main_filter += f":x=30:y={commentary_y}"  # Left side position
            main_filter += f":enable='between(t,{start_time},{end_time})'"
        
        main_filter += output_label
        drawtext_filter = main_filter
        
        video_filters.append(drawtext_filter)
        current_input = output_label
    
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