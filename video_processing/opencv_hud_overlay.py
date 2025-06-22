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
        return f"ASPIRATING {reagent_name}", f"{volume}uL"  # Use 'uL' instead of 'μL'
    
    elif event_model_type == "DispensingEvent":
        reagent = event_model.get("reagent", {})
        reagent_name = reagent.get('name', 'Unknown').replace('Reagent ', '')
        volume = reagent.get('volume_ul', 0)
        return f"DISPENSING {reagent_name}", f"{volume}uL"  # Use 'uL' instead of 'μL'
    
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
        return f"PIPETTE SET", f"{volume}uL"  # Use 'uL' instead of 'μL'
    
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


def draw_hud_text(frame, text, position, font_scale, color, thickness=2, center=False):
    """Draw text with proper HUD styling - no ugly black boxes!"""
    font = cv2.FONT_HERSHEY_COMPLEX  # More technical/HUD-like font
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = position
    
    # Center the text if requested
    if center:
        x = x - text_width // 2
    
    # Draw subtle glow effect (multiple layers)
    glow_color = (20, 20, 20)  # Dark glow
    for offset in [4, 3, 2, 1]:
        cv2.putText(frame, text, (x, y), font, font_scale, glow_color, thickness + offset, cv2.LINE_AA)
    
    # Draw main text with bright color
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    return text_width, text_height


def draw_hud_panel(frame, text, x, y, max_width, font_scale, color):
    """Draw text in a proper HUD panel with hexagonal styling"""
    font = cv2.FONT_HERSHEY_COMPLEX
    thickness = 2
    line_height = int(32 * font_scale)
    
    # Split text into words and wrap
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        (test_width, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        
        if test_width <= max_width - 40:  # Leave padding
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Limit to 5 lines max for cleaner look
    if len(lines) > 5:
        lines = lines[:5]
        lines[-1] = lines[-1][:35] + "..."
    
    # Calculate panel dimensions
    panel_height = len(lines) * line_height + 40
    panel_width = max_width + 40
    
    # Create hexagonal/angled panel shape
    points = np.array([
        [x, y + 15],  # Top left with angle
        [x + 15, y],  # Top left corner
        [x + panel_width - 15, y],  # Top right
        [x + panel_width, y + 15],  # Top right with angle
        [x + panel_width, y + panel_height - 15],  # Bottom right
        [x + panel_width - 15, y + panel_height],  # Bottom right corner
        [x + 15, y + panel_height],  # Bottom left
        [x, y + panel_height - 15]  # Bottom left with angle
    ], np.int32)
    
    # Draw semi-transparent panel background
    overlay = frame.copy()
    cv2.fillPoly(overlay, [points], (10, 25, 40))  # Dark blue-gray
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
    
    # Draw panel border with gradient effect
    cv2.polylines(frame, [points], True, (0, 150, 255), 2)  # Bright cyan border
    cv2.polylines(frame, [points], True, (0, 80, 150), 1)   # Inner glow
    
    # Add corner accent lights
    corner_size = 8
    for point in [points[1], points[3], points[5], points[7]]:
        cv2.circle(frame, tuple(point), corner_size, (0, 255, 255), -1)
        cv2.circle(frame, tuple(point), corner_size-2, (0, 150, 255), -1)
    
    # Draw each line with subtle glow
    for i, line in enumerate(lines):
        line_y = y + 25 + (i + 1) * line_height
        # Glow effect
        cv2.putText(frame, line, (x + 20, line_y), font, font_scale, (10, 10, 10), thickness + 2, cv2.LINE_AA)
        # Main text
        cv2.putText(frame, line, (x + 20, line_y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    return panel_height


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
            
            # Draw main action text with HUD glow effect
            main_font_scale = 3.0  # Massive for impact
            draw_hud_text(
                frame, main_text, 
                (width//2, 90),
                main_font_scale, color, thickness=3, center=True
            )
            
            # Draw detail text with glow
            if detail_text:
                detail_font_scale = 1.6
                draw_hud_text(
                    frame, detail_text,
                    (width//2, 170),
                    detail_font_scale, (255, 255, 255), thickness=2, center=True
                )
            
            # Draw thinking commentary as sci-fi HUD panel
            thinking_text = event.get("event_model", {}).get("thinking", "")
            if thinking_text:
                # Left panel parameters
                panel_x = 25
                panel_y = 250  # Start below main text
                panel_width = 380
                commentary_font_scale = 0.6
                
                # Draw hexagonal HUD panel on left side
                draw_hud_panel(
                    frame, thinking_text,
                    panel_x, panel_y, panel_width,
                    commentary_font_scale, (100, 255, 255)  # Light cyan
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