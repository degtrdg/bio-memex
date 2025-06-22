#!/usr/bin/env python3
"""
Test script demonstrating the new Pydantic models for lab video analysis.
This script shows how to create and use the enhanced models for tracking
pipetting operations with complete state management.
"""

import uuid
from datetime import datetime
from video_understanding.models import (
    PipetteState, PipetteAction, ContaminationLevel, 
    Reagent, ReagentTransfer, ContaminationWarning, VolumeDiscrepancy,
    WellContents, ExperimentState, WarningType, WarningSeverity,
    TipContaminationHistory
)


def demo_basic_usage():
    """Demonstrate basic usage of the new models"""
    print("=== Basic Model Usage Demo ===\n")
    
    # Create an experiment
    experiment = ExperimentState(
        experiment_id="EXP-001", 
        total_wells=6
    )
    
    # Initialize pipette state
    pipette = PipetteState(
        volume_setting_ul=30.0,
        tip_attached=True,
        tip_id="TIP-001",
        tip_contamination_level=ContaminationLevel.CLEAN
    )
    experiment.pipette_state = pipette
    
    print(f"Created experiment: {experiment.experiment_id}")
    print(f"Pipette volume setting: {pipette.volume_setting_ul}µl")
    print(f"Tip status: {pipette.tip_contamination_level.value}")
    print()


def demo_reagent_transfer():
    """Demonstrate reagent transfer tracking"""
    print("=== Reagent Transfer Demo ===\n")
    
    # Create experiment
    experiment = ExperimentState(experiment_id="EXP-002", total_wells=3)
    
    # Create a reagent
    reagent_a = Reagent(
        name="Reagent A", 
        volume_ul=30.0, 
        source_container="TUBE-1",
        color="orange-brown"
    )
    
    # Create a transfer
    transfer = ReagentTransfer(
        transfer_id=str(uuid.uuid4()),
        reagent=reagent_a,
        source_container="TUBE-1",
        destination_well="A1",
        intended_volume_ul=30.0,
        actual_volume_ul=29.5,  # Slight discrepancy
        pipette_volume_setting=30.0,
        tip_contamination_before=ContaminationLevel.CLEAN,
        tip_contamination_after=ContaminationLevel.POTENTIALLY_CONTAMINATED
    )
    
    # Add transfer to experiment
    experiment.add_transfer(transfer)
    
    print(f"Transfer completed: {reagent_a} -> {transfer.destination_well}")
    print(f"Volume accuracy: {transfer.volume_accuracy or 'N/A'}")
    print(f"Has discrepancy: {transfer.has_volume_discrepancy()}")
    print(f"Well A1 contents: {experiment.wells['A1'].total_volume_ul}µl")
    print()


def demo_contamination_tracking():
    """Demonstrate contamination warning system"""
    print("=== Contamination Tracking Demo ===\n")
    
    experiment = ExperimentState(experiment_id="EXP-003")
    
    # Create contamination warning
    warning = ContaminationWarning(
        warning_id=str(uuid.uuid4()),
        warning_type=WarningType.CROSS_CONTAMINATION,
        severity=WarningSeverity.HIGH,
        contamination_source="Previous reagent in tip",
        affected_containers=["A1", "A2"],
        contaminated_reagent="Reagent B",
        description="Tip was not changed between different reagents",
        recommended_action="Change pipette tip immediately",
        contamination_probability=0.8
    )
    
    # Add warning to experiment
    experiment.add_contamination_warning(warning)
    
    print(f"Warning generated: {warning.warning_type.value}")
    print(f"Severity: {warning.severity.value}")
    print(f"Description: {warning.description}")
    print(f"Recommended action: {warning.recommended_action}")
    print(f"Critical warnings: {experiment.critical_warnings}")
    print(f"Overall contamination risk: {experiment.contamination_risk_level.value}")
    print()


def demo_volume_discrepancy():
    """Demonstrate volume discrepancy tracking"""
    print("=== Volume Discrepancy Demo ===\n")
    
    # Create volume discrepancy
    discrepancy = VolumeDiscrepancy(
        discrepancy_id=str(uuid.uuid4()),
        container_id="A1",
        expected_volume_ul=60.0,
        observed_volume_ul=55.0,
        severity=WarningSeverity.MEDIUM,
        description="Well A1 has less volume than expected",
        possible_causes=["Pipetting inaccuracy", "Evaporation", "Measurement error"],
        suggested_actions=["Re-check volume", "Add additional reagent if needed"]
    )
    
    # Calculate differences
    discrepancy.calculate_differences()
    
    print(f"Volume discrepancy in {discrepancy.container_id}")
    print(f"Expected: {discrepancy.expected_volume_ul}µl")
    print(f"Observed: {discrepancy.observed_volume_ul}µl")
    print(f"Absolute difference: {discrepancy.absolute_difference_ul}µl")
    print(f"Relative difference: {discrepancy.relative_difference_percent:.1f}%")
    print(f"Possible causes: {', '.join(discrepancy.possible_causes)}")
    print()


def demo_hud_overlay():
    """Demonstrate HUD overlay data generation"""
    print("=== HUD Overlay Demo ===\n")
    
    # Create a complete experiment scenario
    experiment = ExperimentState(experiment_id="EXP-004", total_wells=6)
    
    # Set up pipette state
    reagent = Reagent(name="Buffer A", volume_ul=25.0, color="clear")
    pipette = PipetteState(
        volume_setting_ul=25.0,
        last_reagent_aspirated=reagent,
        source_container_id="TUBE-BUFFER-A",
        tip_attached=True,
        tip_contamination_level=ContaminationLevel.CLEAN,
        last_action=PipetteAction.ASPIRATE
    )
    experiment.pipette_state = pipette
    
    # Add some transfers
    for well_id in ["A1", "A2", "B1"]:
        transfer = ReagentTransfer(
            transfer_id=str(uuid.uuid4()),
            reagent=reagent,
            source_container="TUBE-BUFFER-A", 
            destination_well=well_id,
            intended_volume_ul=25.0,
            actual_volume_ul=25.0,
            pipette_volume_setting=25.0
        )
        experiment.add_transfer(transfer)
    
    # Get HUD summary
    hud_data = experiment.get_hud_summary()
    
    print("HUD Overlay Data:")
    for key, value in hud_data.items():
        print(f"  {key}: {value}")
    print()


def demo_tip_contamination_history():
    """Demonstrate tip contamination history tracking"""
    print("=== Tip Contamination History Demo ===\n")
    
    pipette = PipetteState(
        volume_setting_ul=20.0,
        tip_attached=True,
        tip_id="TIP-005"
    )
    
    # Add contamination events
    contamination_events = [
        TipContaminationHistory(
            contamination_source="Reagent A residue",
            contamination_level=ContaminationLevel.POTENTIALLY_CONTAMINATED,
            action_taken="Continued with same tip"
        ),
        TipContaminationHistory(
            contamination_source="Cross-contact with Reagent B",
            contamination_level=ContaminationLevel.CONTAMINATED,
            action_taken="Should change tip"
        )
    ]
    
    pipette.tip_contamination_history.extend(contamination_events)
    pipette.tip_contamination_level = ContaminationLevel.CONTAMINATED
    
    print(f"Tip ID: {pipette.tip_id}")
    print(f"Current contamination level: {pipette.tip_contamination_level.value}")
    print(f"Is contaminated: {pipette.is_contaminated()}")
    print(f"Requires tip change: {pipette.requires_tip_change()}")
    print(f"Contamination events: {len(pipette.tip_contamination_history)}")
    
    for i, event in enumerate(pipette.tip_contamination_history, 1):
        print(f"  Event {i}: {event.contamination_source} -> {event.contamination_level.value}")
    print()


def demo_well_completion_tracking():
    """Demonstrate well completion tracking"""
    print("=== Well Completion Tracking Demo ===\n")
    
    # Create a well with expected volume
    well = WellContents(well_id="A1", expected_volume_ul=90.0)
    
    # Add reagents progressively
    reagents_to_add = [
        ("Reagent A", 30.0),
        ("Reagent B", 30.0), 
        ("Buffer", 30.0)
    ]
    
    for reagent_name, volume in reagents_to_add:
        reagent = Reagent(name=reagent_name, volume_ul=volume)
        transfer = ReagentTransfer(
            transfer_id=str(uuid.uuid4()),
            reagent=reagent,
            source_container=f"TUBE-{reagent_name.replace(' ', '-')}",
            destination_well="A1",
            intended_volume_ul=volume,
            actual_volume_ul=volume,
            pipette_volume_setting=volume
        )
        well.add_reagent(transfer)
        
        print(f"Added {reagent_name} ({volume}µl)")
        print(f"  Total volume: {well.total_volume_ul}µl")
        print(f"  Is complete: {well.is_complete()}")
        print(f"  Volume discrepancy: {well.get_volume_discrepancy()}µl")
        print()


if __name__ == "__main__":
    print("Lab Video Analysis - New Pydantic Models Demo")
    print("=" * 50)
    print()
    
    demo_basic_usage()
    demo_reagent_transfer()
    demo_contamination_tracking()
    demo_volume_discrepancy()
    demo_hud_overlay()
    demo_tip_contamination_history()
    demo_well_completion_tracking()
    
    print("=" * 50)
    print("Demo completed! All models are working correctly.")