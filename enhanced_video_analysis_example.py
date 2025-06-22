#!/usr/bin/env python3
"""
Enhanced Video Analysis Integration Example

This script demonstrates how to integrate the new enhanced Pydantic models
with your existing video analysis workflow to create a comprehensive
lab monitoring system.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from video_understanding.models import (
    VideoAnalysis, ExperimentState, PipetteState, PipetteAction,
    ContaminationLevel, Reagent, ReagentTransfer, ContaminationWarning,
    VolumeDiscrepancy, WellContents, WarningType, WarningSeverity,
    TipContaminationHistory
)


class EnhancedVideoAnalyzer:
    """Enhanced video analyzer that maintains experiment state across batches"""
    
    def __init__(self, experiment_id: str):
        self.experiment_state = ExperimentState(experiment_id=experiment_id)
        self.batch_count = 0
    
    def process_batch_with_enhanced_tracking(
        self, 
        frame_batch: List[str], 
        ai_analysis_result: VideoAnalysis
    ) -> VideoAnalysis:
        """
        Process a video batch with enhanced state tracking.
        
        This method shows how to enhance the existing VideoAnalysis output
        with the new comprehensive tracking models.
        """
        
        self.batch_count += 1
        
        # Start with the original AI analysis
        enhanced_analysis = ai_analysis_result.model_copy()
        enhanced_analysis.frame_range = f"batch_{self.batch_count}"
        enhanced_analysis.analysis_confidence = 0.85  # Example confidence score
        
        # Enhanced tracking based on the thinking/analysis
        if ai_analysis_result.thinking:
            self._extract_enhanced_events_from_thinking(
                ai_analysis_result.thinking, 
                enhanced_analysis
            )
        
        # Update pipette state if needed
        if ai_analysis_result.protocol_log_triggered and ai_analysis_result.protocol_log:
            self._update_pipette_state_from_log(
                ai_analysis_result.protocol_log,
                enhanced_analysis
            )
        
        # Process any detected transfers
        if enhanced_analysis.transfers_detected:
            for transfer in enhanced_analysis.transfers_detected:
                self.experiment_state.add_transfer(transfer)
        
        # Process contamination warnings
        if enhanced_analysis.contamination_warnings_detected:
            for warning in enhanced_analysis.contamination_warnings_detected:
                self.experiment_state.add_contamination_warning(warning)
        
        # Process volume discrepancies
        if enhanced_analysis.volume_discrepancies_detected:
            for discrepancy in enhanced_analysis.volume_discrepancies_detected:
                self.experiment_state.add_volume_discrepancy(discrepancy)
        
        # Update the experiment state in the analysis
        enhanced_analysis.experiment_state_updated = True
        enhanced_analysis.experiment_state = self.experiment_state
        
        return enhanced_analysis
    
    def _extract_enhanced_events_from_thinking(
        self, 
        thinking: str, 
        analysis: VideoAnalysis
    ):
        """Extract specific events from the AI's thinking text"""
        
        thinking_lower = thinking.lower()
        
        # Detect key events
        key_events = []
        
        if "pipette" in thinking_lower and "volume" in thinking_lower:
            key_events.append("pipette_volume_change")
            
            # Try to extract volume setting
            if "30" in thinking:
                if not self.experiment_state.pipette_state:
                    self.experiment_state.pipette_state = PipetteState()
                self.experiment_state.pipette_state.volume_setting_ul = 30.0
                analysis.pipette_state_changed = True
                analysis.new_pipette_state = self.experiment_state.pipette_state
        
        if "aspirat" in thinking_lower:
            key_events.append("aspiration_detected")
            
            # Detect reagent aspiration
            if "orange" in thinking_lower or "reagent a" in thinking_lower:
                reagent = Reagent(
                    name="Reagent A",
                    volume_ul=30.0,
                    source_container="TUBE-A",
                    color="orange-brown"
                )
                
                if not self.experiment_state.pipette_state:
                    self.experiment_state.pipette_state = PipetteState()
                
                self.experiment_state.pipette_state.last_reagent_aspirated = reagent
                self.experiment_state.pipette_state.last_action = PipetteAction.ASPIRATE
                self.experiment_state.pipette_state.action_timestamp = datetime.now()
                
                analysis.pipette_state_changed = True
                analysis.new_pipette_state = self.experiment_state.pipette_state
        
        if "dispens" in thinking_lower:
            key_events.append("dispensing_detected")
            
            # Try to detect well dispense
            well_indicators = ["a1", "a2", "a3", "b1", "b2", "b3"]
            dispensed_well = None
            
            for well in well_indicators:
                if well in thinking_lower:
                    dispensed_well = well.upper()
                    break
            
            if dispensed_well and self.experiment_state.pipette_state:
                pipette = self.experiment_state.pipette_state
                if pipette.last_reagent_aspirated:
                    # Create transfer
                    transfer = ReagentTransfer(
                        transfer_id=str(uuid.uuid4()),
                        reagent=pipette.last_reagent_aspirated,
                        source_container=pipette.last_reagent_aspirated.source_container or "UNKNOWN",
                        destination_well=dispensed_well,
                        intended_volume_ul=pipette.volume_setting_ul,
                        actual_volume_ul=pipette.volume_setting_ul,  # Assume accurate for demo
                        pipette_volume_setting=pipette.volume_setting_ul,
                        tip_contamination_before=pipette.tip_contamination_level,
                        tip_contamination_after=ContaminationLevel.POTENTIALLY_CONTAMINATED
                    )
                    
                    analysis.transfers_detected.append(transfer)
                    
                    # Update pipette state
                    pipette.last_action = PipetteAction.DISPENSE
                    pipette.tip_contamination_level = ContaminationLevel.POTENTIALLY_CONTAMINATED
                    pipette.last_reagent_aspirated = None  # Tip now empty
        
        if "tip" in thinking_lower and ("change" in thinking_lower or "attach" in thinking_lower):
            key_events.append("tip_change_detected")
            
            if not self.experiment_state.pipette_state:
                self.experiment_state.pipette_state = PipetteState()
            
            self.experiment_state.pipette_state.tip_attached = True
            self.experiment_state.pipette_state.tip_contamination_level = ContaminationLevel.CLEAN
            self.experiment_state.pipette_state.tip_id = f"TIP-{self.batch_count:03d}"
            
            analysis.pipette_state_changed = True
            analysis.new_pipette_state = self.experiment_state.pipette_state
        
        # Check for contamination risks
        if any(word in thinking_lower for word in ["contamination", "cross", "dirty", "residue"]):
            warning = ContaminationWarning(
                warning_id=str(uuid.uuid4()),
                warning_type=WarningType.CROSS_CONTAMINATION,
                severity=WarningSeverity.MEDIUM,
                contamination_source="Detected during video analysis",
                affected_containers=["Unknown"],
                description="Potential contamination detected in video frames",
                recommended_action="Review pipetting technique and tip usage"
            )
            analysis.contamination_warnings_detected.append(warning)
        
        analysis.key_events_detected = key_events
    
    def _update_pipette_state_from_log(self, protocol_log: str, analysis: VideoAnalysis):
        """Update pipette state based on protocol log entries"""
        
        log_lower = protocol_log.lower()
        
        # Initialize pipette state if needed
        if not self.experiment_state.pipette_state:
            self.experiment_state.pipette_state = PipetteState()
        
        pipette = self.experiment_state.pipette_state
        
        # Extract volume changes
        if "volume" in log_lower and "set" in log_lower:
            # Try to extract volume number
            import re
            volume_match = re.search(r'(\d+)(?:\.\d+)?\s*[µu]?l', protocol_log, re.IGNORECASE)
            if volume_match:
                volume = float(volume_match.group(1))
                pipette.volume_setting_ul = volume
                analysis.pipette_state_changed = True
                analysis.new_pipette_state = pipette
        
        # Track reagent aspiration
        if "aspirat" in log_lower:
            # Simple reagent detection
            if "reagent a" in log_lower or "orange" in log_lower:
                reagent = Reagent(name="Reagent A", volume_ul=pipette.volume_setting_ul, color="orange")
                pipette.last_reagent_aspirated = reagent
                pipette.last_action = PipetteAction.ASPIRATE
                analysis.pipette_state_changed = True
    
    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get current experiment summary for monitoring"""
        return {
            "experiment_id": self.experiment_state.experiment_id,
            "batches_processed": self.batch_count,
            "total_transfers": len(self.experiment_state.all_transfers),
            "wells_with_content": len(self.experiment_state.wells),
            "contamination_warnings": len(self.experiment_state.contamination_warnings),
            "volume_discrepancies": len(self.experiment_state.volume_discrepancies),
            "current_pipette_state": {
                "volume_setting": self.experiment_state.pipette_state.volume_setting_ul if self.experiment_state.pipette_state else "N/A",
                "tip_attached": self.experiment_state.pipette_state.tip_attached if self.experiment_state.pipette_state else False,
                "contamination_level": self.experiment_state.pipette_state.tip_contamination_level.value if self.experiment_state.pipette_state else "unknown",
                "last_action": self.experiment_state.pipette_state.last_action.value if self.experiment_state.pipette_state else "idle"
            },
            "hud_data": self.experiment_state.get_hud_summary()
        }


def demonstrate_enhanced_integration():
    """Demonstrate integration with existing video analysis workflow"""
    
    print("=" * 70)
    print("ENHANCED VIDEO ANALYSIS INTEGRATION DEMO")
    print("=" * 70)
    print()
    
    # Initialize enhanced analyzer
    analyzer = EnhancedVideoAnalyzer("DEMO-EXP-001")
    
    # Simulate processing several batches (like your existing workflow)
    sample_batches = [
        {
            "frames": ["frame_00099.png", "frame_00104.png", "frame_00109.png"],
            "ai_result": VideoAnalysis(
                thinking="The user revealed a handwritten notebook containing a detailed plan for the experiment. This plan serves as the goal state, outlining which reagents ('A', 'B', 'L') and volumes (30µl) should be added to wells A1-A3 and B1-B3. After showing the plan, the user proceeded to pick up a pipette, attach a tip, and aspirate an orange-brown liquid from a microcentrifuge tube. The pipette volume dial briefly showed '30.0', which matches the volumes specified in the notebook.",
                goal_state_triggered=True,
                protocol_log_triggered=True,
                protocol_log="Procedure goal defined from handwritten notebook. Pipette volume set to 30µl. Aspirated 30µl of orange-brown liquid from a source tube."
            )
        },
        {
            "frames": ["frame_00114.png", "frame_00119.png", "frame_00124.png"],
            "ai_result": VideoAnalysis(
                thinking="The user is holding the pipette with the aspirated orange-brown liquid and positions it over well A1. They slowly dispense the liquid into the well, creating a small orange pool at the bottom. The dispensing appears controlled and complete.",
                current_state_triggered=True,
                protocol_log_triggered=True,
                protocol_log="Dispensed 30µl of Reagent A into well A1. Well A1 now contains orange liquid."
            )
        },
        {
            "frames": ["frame_00129.png", "frame_00134.png", "frame_00139.png"],
            "ai_result": VideoAnalysis(
                thinking="The user returns to the source tubes and aspirates a different reagent - this one appears blue in color. They did not change the pipette tip between reagents, which could lead to cross-contamination of Reagent B with residual Reagent A.",
                protocol_log_triggered=True,
                protocol_log="Aspirated blue reagent (Reagent B) without changing tip. Potential cross-contamination risk.",
                warnings_triggered=True,
                warnings=["Did not change tip between different reagents - cross-contamination risk"]
            )
        }
    ]
    
    # Process each batch
    for i, batch in enumerate(sample_batches, 1):
        print(f"📹 Processing Batch {i}:")
        print(f"   Frames: {len(batch['frames'])} frames")
        
        # Process with enhanced tracking
        enhanced_result = analyzer.process_batch_with_enhanced_tracking(
            batch["frames"], 
            batch["ai_result"]
        )
        
        # Show enhanced results
        print(f"   Key events detected: {enhanced_result.key_events_detected}")
        print(f"   Transfers detected: {len(enhanced_result.transfers_detected)}")
        print(f"   Contamination warnings: {len(enhanced_result.contamination_warnings_detected)}")
        print(f"   Pipette state changed: {enhanced_result.pipette_state_changed}")
        
        if enhanced_result.transfers_detected:
            for transfer in enhanced_result.transfers_detected:
                print(f"   → Transfer: {transfer.reagent.name} to {transfer.destination_well}")
        
        if enhanced_result.contamination_warnings_detected:
            for warning in enhanced_result.contamination_warnings_detected:
                print(f"   ⚠️  Warning: {warning.description}")
        
        print()
    
    # Show final experiment summary
    print("📊 FINAL EXPERIMENT SUMMARY:")
    summary = analyzer.get_experiment_summary()
    
    print(f"   Experiment ID: {summary['experiment_id']}")
    print(f"   Batches processed: {summary['batches_processed']}")
    print(f"   Total transfers: {summary['total_transfers']}")
    print(f"   Wells with content: {summary['wells_with_content']}")
    print(f"   Contamination warnings: {summary['contamination_warnings']}")
    print()
    
    print("🎛️  CURRENT PIPETTE STATE:")
    pipette_state = summary['current_pipette_state']
    for key, value in pipette_state.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    print()
    
    print("📺 HUD DATA FOR OVERLAY:")
    hud_data = summary['hud_data']
    for key, value in hud_data.items():
        print(f"   {key}: {value}")
    print()
    
    # Show how to query the data
    print("🔍 EXAMPLE QUERIES:")
    
    # Find all transfers
    all_transfers = analyzer.experiment_state.all_transfers
    print(f"   • All transfers: {len(all_transfers)}")
    
    # Find contamination warnings
    warnings = analyzer.experiment_state.contamination_warnings
    print(f"   • Contamination warnings: {len(warnings)}")
    
    # Check specific wells
    if "A1" in analyzer.experiment_state.wells:
        a1_volume = analyzer.experiment_state.wells["A1"].total_volume_ul
        print(f"   • A1 total volume: {a1_volume}µl")
    
    # Check current contamination risk
    risk_level = analyzer.experiment_state.contamination_risk_level
    print(f"   • Overall contamination risk: {risk_level.value}")
    
    print()
    print("=" * 70)
    print("INTEGRATION COMPLETE!")
    print("This shows how to enhance your existing VideoAnalysis")
    print("with comprehensive state tracking for HUD overlays and")
    print("advanced 'needle in the haystack' queries.")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_enhanced_integration()