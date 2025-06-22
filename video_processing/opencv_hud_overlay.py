#!/usr/bin/env python3
"""
OpenCV HUD Overlay - Much cleaner than FFmpeg approach!
Uses OpenCV to add text overlays directly to video frames.
"""

import cv2
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Add parent directory to path to import BaseModels
sys.path.append(str(Path(__file__).parent.parent))


def create_enhanced_event_text(event: Dict) -> Tuple[str, str]:
    """Create enhanced event text using BaseModel data
    Returns: (main_text, detail_text)
    """
    event_model_type = event.get("event_model_type")
    event_model = event.get("event_model", {})
    
    if event_model_type == "AspirationEvent":
        reagent = event_model.get("reagent", {})
        reagent_name = reagent.get('name', 'Unknown').replace('Reagent ', '')
        volume = reagent.get('volume_ul', 0)
        return f"ASPIRATING {reagent_name}", f"{volume}μL"
    
    elif event_model_type == "DispensingEvent":
        reagent = event_model.get("reagent", {})
        reagent_name = reagent.get('name', 'Unknown').replace('Reagent ', '')
        volume = reagent.get('volume_ul', 0)
        return f"DISPENSING {reagent_name}", f"{volume}μL"
    
    elif event_model_type == "WellStateEvent":
        well_id = event_model.get("well_id", "?")
        is_complete = event_model.get("is_complete", False)
        contents = event_model.get("current_contents", [])
        reagent_names = [r.get("name", "?").replace('Reagent ', '') for r in contents]
        
        if is_complete:
            return f"WELL {well_id} COMPLETE", f"Contains: {' + '.join(reagent_names)}"
        else:
            return f"WELL {well_id} PARTIAL", f"Added: {' + '.join(reagent_names)}"
    
    elif event_model_type == "PipetteSettingChange":
        volume = event_model.get("new_setting_ul", 0)
        return f"PIPETTE SET", f"{volume}μL"
    
    elif event_model_type == "WarningEvent":
        warning = event_model.get("warning_message", "Warning")
        description = event_model.get("description", "")
        return f"WARNING", description or warning[:40]
    
    elif event_model_type == "TipChangeEvent":
        return f"TIP CHANGE", "New tip attached"
    
    else:
        return event.get("title", "Event"), ""


def get_text_color(event_type: str) -> Tuple[int, int, int]:
    """Get BGR color for event type"""
    colors = {
        "warning": (0, 0, 255),      # Red
        "well_state": (0, 255, 0),   # Green  
        "pipette_setting": (0, 255, 255),  # Yellow
        "aspiration": (255, 255, 0),  # Cyan
        "dispensing": (0, 165, 255),  # Orange
        "tip_change": (255, 255, 255)  # White
    }
    return colors.get(event_type, (255, 255, 255))


def draw_text_with_background(frame, text, position, font_scale, color, thickness=2, bg_color=(0, 0, 0)):
    """Draw text with a background box for better visibility"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = position
    
    # Draw background rectangle
    padding = 10
    cv2.rectangle(frame, 
                 (x - padding, y - text_height - padding), 
                 (x + text_width + padding, y + baseline + padding), 
                 bg_color, -1)
    
    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    return text_width, text_height


def create_hud_video_opencv(input_video: str, timeline_file: str, output_video: str) -> None:
    """Create HUD overlay video using OpenCV - much cleaner than FFmpeg!"""
    
    # Load timeline
    with open(timeline_file, 'r') as f:
        timeline_data = json.load(f)
    
    timeline_events = timeline_data["timeline"]
    print(f"Processing {len(timeline_events)} events for HUD overlay...")
    
    # Open input video
    cap = cv2.VideoCapture(input_video)
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Video: {width}x{height} @ {fps}fps, {total_frames} frames")
    
    # Create video writer with better codec
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec, much more compatible
    out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Current time in seconds
        current_time = frame_count / fps
        
        # Find active events for current time
        active_events = []
        for event in timeline_events:
            start_time = event["start_time"]
            end_time = event["end_time"]
            
            # Extend duration for better readability
            original_duration = end_time - start_time
            extended_duration = max(3.0, original_duration + 2.0)
            end_time = start_time + extended_duration
            
            if start_time <= current_time <= end_time:
                active_events.append(event)
        
        # Sort by priority (warnings first)
        priority_order = {"warning": 4, "dispensing": 3, "aspiration": 3, "well_state": 2, "pipette_setting": 1, "tip_change": 0}
        active_events.sort(key=lambda x: -priority_order.get(x["event_type"], 0))
        
        # Take only the highest priority event to avoid overlaps
        if active_events:
            event = active_events[0]
            
            # Get event text and color
            main_text, detail_text = create_enhanced_event_text(event)
            color = get_text_color(event["event_type"])
            
            # Draw main action text at top center
            main_font_scale = 2.5  # Much bigger
            text_width, text_height = draw_text_with_background(
                frame, main_text, 
                (width//2 - len(main_text)*20, 80),  # Rough centering
                main_font_scale, color, thickness=3
            )
            
            # Draw detail text below main text
            if detail_text:
                detail_font_scale = 1.5
                draw_text_with_background(
                    frame, detail_text,
                    (width//2 - len(detail_text)*15, 150),  # Below main text
                    detail_font_scale, (255, 255, 255), thickness=2
                )
            
            # Draw thinking commentary at bottom center
            thinking_text = event.get("event_model", {}).get("thinking", "")
            if thinking_text:
                # Limit length to fit screen
                if len(thinking_text) > 80:
                    thinking_text = thinking_text[:77] + "..."
                
                commentary_font_scale = 0.8
                draw_text_with_background(
                    frame, thinking_text,
                    (width//2 - len(thinking_text)*8, height - 60),  # Bottom center
                    commentary_font_scale, (0, 255, 255), thickness=2  # Cyan
                )
        
        # Write frame
        out.write(frame)
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames ({frame_count/total_frames*100:.1f}%)")
    
    # Cleanup
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    print(f"✓ HUD video created: {output_video}")


def main():
    """Main function to create HUD overlay video using OpenCV"""
    base_dir = Path(__file__).parent.parent
    
    # Input files
    input_video = base_dir / "videos" / "output_long_again_2_timestamped.mp4"
    timeline_file = base_dir / "video_processing" / "merged_timeline.json"
    
    # Output file
    output_video = base_dir / "video_processing" / "hud_overlay_opencv.mp4"
    
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
    
    # Create HUD overlay using OpenCV
    create_hud_video_opencv(
        str(input_video),
        str(timeline_file), 
        str(output_video)
    )


if __name__ == "__main__":
    main()