#!/usr/bin/env python3
"""
Event Merger - Combines analysis, objective, and procedure JSON files into a single timeline.
Processes timestamps and creates a unified event stream for HUD overlay.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Union, Any
from dataclasses import dataclass

# Add parent directory to path to import BaseModels
sys.path.append(str(Path(__file__).parent.parent))

from video_understanding.simple_models import (
    ProcedureExtraction,
    ObjectiveEventsList,
    AnalysisEventsResult,
    PipetteSettingChange,
    AspirationEvent,
    DispensingEvent,
    TipChangeEvent,
    WarningEvent,
    WellStateEvent
)

@dataclass
class TimelineEvent:
    """Unified event for timeline display"""
    start_time: float  # seconds from video start
    end_time: float    # seconds from video start
    event_type: str    # "warning", "well_state", "pipette_setting", "aspiration", "dispensing", "tip_change"
    title: str         # Short title for HUD
    description: str   # Detailed description
    priority: str      # "high", "medium", "low"
    event_model: Union[PipetteSettingChange, AspirationEvent, DispensingEvent, TipChangeEvent, WarningEvent, WellStateEvent]  # Typed event model


def parse_timestamp_range(timestamp_str: str) -> Tuple[float, float]:
    """Parse timestamp range string like '0:14 - 0:16' into start/end seconds"""
    # Handle single timestamps like '0:14' 
    if ' - ' not in timestamp_str:
        time_parts = timestamp_str.split(':')
        if len(time_parts) == 2:
            minutes, seconds = map(int, time_parts)
            total_seconds = minutes * 60 + seconds
            return total_seconds, total_seconds + 1  # Add 1 second duration
    
    # Handle ranges like '0:14 - 0:16'
    start_str, end_str = timestamp_str.split(' - ')
    
    def time_to_seconds(time_str: str) -> float:
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    
    return time_to_seconds(start_str), time_to_seconds(end_str)


def process_analysis_events(analysis_events: AnalysisEventsResult) -> List[TimelineEvent]:
    """Convert analysis events to timeline events using BaseModel instances"""
    events = []
    
    for event in analysis_events.events:
        start_time, end_time = parse_timestamp_range(event.timestamp_range)
        
        if isinstance(event, WarningEvent):
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="warning",
                title=event.warning_message,
                description=event.description,
                priority="high",
                event_model=event
            ))
        elif isinstance(event, WellStateEvent):
            status = "Complete" if event.is_complete else "Partial"
            reagents = [r.name for r in event.current_contents]
            title = f"Well {event.well_id}: {status}"
            description = f"Contains: {', '.join(reagents)}"
            
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="well_state",
                title=title,
                description=description,
                priority="medium",
                event_model=event
            ))
    
    return events


def process_objective_events(objective_events: ObjectiveEventsList) -> List[TimelineEvent]:
    """Convert objective events to timeline events using BaseModel instances"""
    events = []
    
    for event in objective_events.events:
        start_time, end_time = parse_timestamp_range(event.timestamp_range)
        
        if isinstance(event, PipetteSettingChange):
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="pipette_setting",
                title=f"Set to {event.new_setting_ul}μL",
                description=f"Pipette volume adjusted to {event.new_setting_ul} microliters",
                priority="low",
                event_model=event
            ))
        elif isinstance(event, AspirationEvent):
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="aspiration",
                title=f"Aspirate {event.reagent.name}",
                description=f"Drew {event.reagent.volume_ul}μL of {event.reagent.name}",
                priority="medium",
                event_model=event
            ))
        elif isinstance(event, DispensingEvent):
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="dispensing",
                title=f"Dispense {event.reagent.name}",
                description=f"Added {event.reagent.volume_ul}μL of {event.reagent.name}",
                priority="medium",
                event_model=event
            ))
        elif isinstance(event, TipChangeEvent):
            events.append(TimelineEvent(
                start_time=start_time,
                end_time=end_time,
                event_type="tip_change",
                title="Tip Change",
                description="Pipette tip attached/removed",
                priority="low",
                event_model=event
            ))
    
    return events


def merge_events_to_timeline(
    analysis_file: str,
    objective_file: str,
    procedure_file: str,
    output_file: str
) -> None:
    """Merge all event files into a single timeline JSON using BaseModel validation"""
    
    # Load and validate JSON files using BaseModels
    with open(analysis_file, 'r') as f:
        analysis_data = json.load(f)
    
    # Parse individual analysis events based on their structure
    parsed_analysis_events = []
    for event_data in analysis_data.get("events", []):
        if "warning_message" in event_data:
            parsed_analysis_events.append(WarningEvent(**event_data))
        elif "well_id" in event_data:
            parsed_analysis_events.append(WellStateEvent(**event_data))
    
    analysis_events = AnalysisEventsResult(
        thinking=analysis_data.get("thinking", "Analysis events extracted from video"),
        events=parsed_analysis_events
    )
    
    with open(objective_file, 'r') as f:
        objective_data = json.load(f)
    
    # Parse individual objective events based on their structure
    parsed_objective_events = []
    for event_data in objective_data.get("events", []):
        if "new_setting_ul" in event_data:
            parsed_objective_events.append(PipetteSettingChange(**event_data))
        elif "reagent" in event_data:
            # Determine if aspiration or dispensing based on thinking content
            thinking = event_data.get("thinking", "").lower()
            if "aspiration" in thinking or "aspirate" in thinking:
                parsed_objective_events.append(AspirationEvent(**event_data))
            else:
                parsed_objective_events.append(DispensingEvent(**event_data))
        else:
            # Tip change event
            parsed_objective_events.append(TipChangeEvent(**event_data))
    
    objective_events = ObjectiveEventsList(
        thinking=objective_data.get("thinking", "Objective events extracted from video"),
        events=parsed_objective_events
    )
    
    with open(procedure_file, 'r') as f:
        procedure_data = json.load(f)
    procedure = ProcedureExtraction(**procedure_data)
    
    # Process events using typed BaseModel instances
    timeline_events = []
    timeline_events.extend(process_analysis_events(analysis_events))
    timeline_events.extend(process_objective_events(objective_events))
    
    # Sort by start time
    timeline_events.sort(key=lambda x: x.start_time)
    
    # Convert to serializable format with typed event models
    timeline_data = {
        "procedure_context": procedure.model_dump(),
        "total_events": len(timeline_events),
        "timeline": [
            {
                "start_time": event.start_time,
                "end_time": event.end_time,
                "event_type": event.event_type,
                "title": event.title,
                "description": event.description,
                "priority": event.priority,
                "event_model": event.event_model.model_dump(),
                "event_model_type": type(event.event_model).__name__
            }
            for event in timeline_events
        ]
    }
    
    # Save merged timeline
    with open(output_file, 'w') as f:
        json.dump(timeline_data, f, indent=2)
    
    print(f"Merged {len(timeline_events)} events into timeline: {output_file}")
    
    # Print summary
    event_counts = {}
    for event in timeline_events:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
    
    print("Event breakdown:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")


if __name__ == "__main__":
    import sys
    
    # Default file paths
    base_dir = Path(__file__).parent.parent
    analysis_file = base_dir / "analysis_events_result.json"
    objective_file = base_dir / "objective_events_result.json"
    procedure_file = base_dir / "procedure_result.json"
    output_file = base_dir / "video_processing" / "merged_timeline.json"
    
    merge_events_to_timeline(
        str(analysis_file),
        str(objective_file),
        str(procedure_file),
        str(output_file)
    )