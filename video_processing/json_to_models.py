#!/usr/bin/env python3
"""
JSON to BaseModel converter - Loads JSON files and converts them to proper BaseModel instances.
This allows for better type checking and validation of the event data.
"""

import json
import sys
from pathlib import Path
from typing import List, Union

# Add the parent directory to the path to import from video_understanding
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


def load_procedure_from_json(json_path: str) -> ProcedureExtraction:
    """Load and validate procedure extraction from JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return ProcedureExtraction(**data)


def load_objective_events_from_json(json_path: str) -> ObjectiveEventsList:
    """Load and validate objective events from JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Parse individual events based on their structure
    parsed_events = []
    for event_data in data.get("events", []):
        if "new_setting_ul" in event_data:
            parsed_events.append(PipetteSettingChange(**event_data))
        elif "reagent" in event_data:
            # Check if it's aspiration or dispensing based on thinking content
            thinking = event_data.get("thinking", "").lower()
            if "aspiration" in thinking or "aspirate" in thinking:
                parsed_events.append(AspirationEvent(**event_data))
            else:
                parsed_events.append(DispensingEvent(**event_data))
        else:
            # Tip change event
            parsed_events.append(TipChangeEvent(**event_data))
    
    return ObjectiveEventsList(events=parsed_events)


def load_analysis_events_from_json(json_path: str) -> AnalysisEventsResult:
    """Load and validate analysis events from JSON"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Parse individual events based on their structure
    parsed_events = []
    for event_data in data.get("events", []):
        if "warning_message" in event_data:
            parsed_events.append(WarningEvent(**event_data))
        elif "well_id" in event_data:
            parsed_events.append(WellStateEvent(**event_data))
    
    return AnalysisEventsResult(events=parsed_events)


def save_validated_models(
    procedure: ProcedureExtraction,
    objective_events: ObjectiveEventsList,
    analysis_events: AnalysisEventsResult,
    output_dir: str
) -> None:
    """Save validated BaseModel instances as JSON files"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save as validated JSON files
    with open(output_path / "validated_procedure.json", 'w') as f:
        json.dump(procedure.model_dump(), f, indent=2)
    
    with open(output_path / "validated_objective_events.json", 'w') as f:
        json.dump(objective_events.model_dump(), f, indent=2)
    
    with open(output_path / "validated_analysis_events.json", 'w') as f:
        json.dump(analysis_events.model_dump(), f, indent=2)
    
    print(f"Validated models saved to {output_path}")


def main():
    """Main function to convert JSON files to validated BaseModel instances"""
    base_dir = Path(__file__).parent.parent
    
    # Input files
    procedure_file = base_dir / "procedure_result.json"
    objective_file = base_dir / "objective_events_result.json"
    analysis_file = base_dir / "analysis_events_result.json"
    
    # Output directory
    output_dir = base_dir / "video_processing"
    
    try:
        # Load and validate
        print("Loading and validating procedure extraction...")
        procedure = load_procedure_from_json(str(procedure_file))
        print(f"✓ Procedure loaded: {len(procedure.goal_wells)} wells, {len(procedure.reagent_sources)} reagents")
        
        print("Loading and validating objective events...")
        objective_events = load_objective_events_from_json(str(objective_file))
        print(f"✓ Objective events loaded: {len(objective_events.events)} events")
        
        print("Loading and validating analysis events...")
        analysis_events = load_analysis_events_from_json(str(analysis_file))
        print(f"✓ Analysis events loaded: {len(analysis_events.events)} events")
        
        # Save validated models
        save_validated_models(procedure, objective_events, analysis_events, str(output_dir))
        
        # Print event type breakdown
        print("\nObjective Events Breakdown:")
        obj_types = {}
        for event in objective_events.events:
            event_type = type(event).__name__
            obj_types[event_type] = obj_types.get(event_type, 0) + 1
        
        for event_type, count in sorted(obj_types.items()):
            print(f"  {event_type}: {count}")
        
        print("\nAnalysis Events Breakdown:")
        analysis_types = {}
        for event in analysis_events.events:
            event_type = type(event).__name__
            analysis_types[event_type] = analysis_types.get(event_type, 0) + 1
        
        for event_type, count in sorted(analysis_types.items()):
            print(f"  {event_type}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()