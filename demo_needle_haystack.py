#!/usr/bin/env python3
"""
Demo script showing the needle-in-haystack video processor in action.
Simulates the processing of a full lab video with realistic events.
"""

from video_understanding.needle_haystack_processor import (
    NeedleHaystackProcessor, 
    VideoEvent, 
    generate_hud_data
)
import json


class MockNeedleHaystackProcessor(NeedleHaystackProcessor):
    """Mock processor that simulates realistic lab video events"""
    
    def _query_video_model(self, query: str) -> list:
        """Return realistic mock events based on query type"""
        
        if "pipette volume setting" in query:
            return [
                {'timestamp': '00:01:15', 'new_volume': '30µL', 'confidence': 0.95},
                {'timestamp': '00:03:42', 'new_volume': '20µL', 'confidence': 0.92},
                {'timestamp': '00:07:18', 'new_volume': '30µL', 'confidence': 0.98}
            ]
            
        elif "aspirated from containers" in query:
            return [
                {
                    'timestamp': '00:01:30', 
                    'container': 'eppendorf_tube_A', 
                    'reagent': 'Reagent A',
                    'volume': '30µL',
                    'label': 'A'
                },
                {
                    'timestamp': '00:04:15',
                    'container': 'eppendorf_tube_B',
                    'reagent': 'Reagent B', 
                    'volume': '20µL',
                    'label': 'B'
                },
                {
                    'timestamp': '00:07:45',
                    'container': 'eppendorf_tube_A',
                    'reagent': 'Reagent A',
                    'volume': '30µL', 
                    'label': 'A'
                }
            ]
            
        elif "dispensed from pipette into wells" in query:
            return [
                {
                    'timestamp': '00:01:50',
                    'well_id': 'A1',
                    'volume': '30µL',
                    'mixing': False
                },
                {
                    'timestamp': '00:04:35', 
                    'well_id': 'A2',
                    'volume': '20µL',
                    'mixing': False
                },
                {
                    'timestamp': '00:08:10',
                    'well_id': 'A1',  # Same well - potential contamination!
                    'volume': '30µL',
                    'mixing': True
                }
            ]
            
        elif "tips are changed" in query:
            return [
                {
                    'timestamp': '00:00:30',
                    'action': 'pickup',
                    'new_tip': True
                },
                {
                    'timestamp': '00:06:00',
                    'action': 'eject', 
                    'new_tip': False
                },
                {
                    'timestamp': '00:06:15',
                    'action': 'pickup',
                    'new_tip': True  
                }
            ]
            
        elif "experimental protocol" in query:
            return {
                'reagents': [
                    {'name': 'Reagent A', 'container': 'eppendorf_tube_A', 'volume': 500.0},
                    {'name': 'Reagent B', 'container': 'eppendorf_tube_B', 'volume': 500.0}
                ],
                'target_wells': ['A1', 'A2', 'B1', 'B2'],
                'protocol_name': 'Standard Mixing Assay'
            }
            
        return []


def run_demo():
    """Run a complete demonstration of the needle-in-haystack processor"""
    
    print("🎬 NEEDLE-IN-HAYSTACK VIDEO PROCESSOR DEMO")
    print("=" * 50)
    print()
    
    # Initialize processor with mock data
    video_frames = []  # Would contain actual video frames
    video_duration = 600.0  # 10 minutes
    
    processor = MockNeedleHaystackProcessor(video_frames, video_duration)
    
    print("📹 Processing entire video with targeted queries...")
    experiment_state = processor.process_video()
    
    print(f"✅ Processing complete! Experiment ID: {experiment_state.experiment_id}")
    print()
    
    # Show extracted events
    print("🎯 EXTRACTED EVENTS:")
    print("-" * 20)
    for i, event in enumerate(processor.events, 1):
        print(f"{i:2d}. [{event.timestamp}] {event.event_type.upper()}")
        for key, value in event.data.items():
            print(f"    {key}: {value}")
        print()
    
    # Show final experiment state
    print("🧪 FINAL EXPERIMENT STATE:")
    print("-" * 25)
    print(f"Pipette volume setting: {experiment_state.pipette_state.volume_setting_ul}µL")
    print(f"Last reagent: {experiment_state.pipette_state.last_reagent_aspirated.name if experiment_state.pipette_state.last_reagent_aspirated else 'None'}")
    print(f"Tip contamination: {experiment_state.pipette_state.tip_contamination_level.value}")
    print(f"Wells with reagents: {len(experiment_state.wells)}")
    print(f"Total transfers: {len(experiment_state.all_transfers)}")
    print(f"Contamination warnings: {len(experiment_state.contamination_warnings)}")
    print()
    
    # Show well contents
    if experiment_state.wells:
        print("🧬 WELL CONTENTS:")
        print("-" * 15)
        for well_id, well in experiment_state.wells.items():
            print(f"{well_id}: {well.total_volume_ul}µL total")
            for reagent in well.reagents:
                print(f"  • {reagent.name}: {reagent.volume_ul}µL")
        print()
    
    # Show warnings
    if experiment_state.contamination_warnings:
        print("⚠️  CONTAMINATION WARNINGS:")
        print("-" * 25)
        for warning in experiment_state.contamination_warnings:
            print(f"• {warning.severity.value.upper()}: {warning.description}")
            print(f"  Affected wells: {', '.join(warning.affected_containers)}")
            print(f"  Risk level: {warning.contamination_probability:.1%}")
            print()
    
    # Generate HUD data
    print("📊 HUD OVERLAY DATA:")
    print("-" * 18)
    hud_data = generate_hud_data(experiment_state)
    print(json.dumps(hud_data, indent=2))
    print()
    
    print("🎉 DEMO COMPLETE!")
    print("=" * 50)
    print("Key advantages over batch-by-batch processing:")
    print("• No error propagation (no more eppendorf hallucinations!)")
    print("• Complete video context for each query")
    print("• Accurate state reconstruction via event replay") 
    print("• Real-time HUD data for live demos")
    print("• Scalable to any video length")


if __name__ == "__main__":
    run_demo()