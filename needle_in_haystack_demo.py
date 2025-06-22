#!/usr/bin/env python3
"""
Needle in the Haystack Demo: Advanced queries on lab video analysis data.

This script demonstrates how the new Pydantic models enable sophisticated
queries across entire video analysis sessions to find specific events,
track contamination risks, and analyze experiment quality.
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from video_understanding.models import (
    ExperimentState, PipetteState, PipetteAction, ContaminationLevel,
    Reagent, ReagentTransfer, ContaminationWarning, VolumeDiscrepancy,
    WellContents, WarningType, WarningSeverity, TipContaminationHistory
)


class LabVideoAnalyzer:
    """Analyzer for performing complex queries on lab video data"""
    
    def __init__(self, experiment_state: ExperimentState):
        self.experiment = experiment_state
    
    def find_contamination_events(self, severity_threshold: WarningSeverity = WarningSeverity.MEDIUM) -> List[ContaminationWarning]:
        """Find all contamination events above a certain severity"""
        severity_order = {
            WarningSeverity.LOW: 1,
            WarningSeverity.MEDIUM: 2,
            WarningSeverity.HIGH: 3,
            WarningSeverity.CRITICAL: 4
        }
        
        threshold_level = severity_order[severity_threshold]
        return [
            warning for warning in self.experiment.contamination_warnings
            if severity_order[warning.severity] >= threshold_level
        ]
    
    def find_volume_discrepancies_by_well(self, well_id: str) -> List[VolumeDiscrepancy]:
        """Find all volume discrepancies for a specific well"""
        return [
            disc for disc in self.experiment.volume_discrepancies
            if disc.container_id == well_id
        ]
    
    def find_transfers_by_reagent(self, reagent_name: str) -> List[ReagentTransfer]:
        """Find all transfers involving a specific reagent"""
        return [
            transfer for transfer in self.experiment.all_transfers
            if transfer.reagent.name == reagent_name
        ]
    
    def find_cross_contamination_chain(self, reagent_name: str) -> Dict[str, Any]:
        """Trace potential cross-contamination chains for a reagent"""
        contaminated_wells = set()
        transfer_chain = []
        
        # Find all transfers of this reagent
        reagent_transfers = self.find_transfers_by_reagent(reagent_name)
        
        for transfer in reagent_transfers:
            # Check if tip was contaminated before or after transfer
            if (transfer.tip_contamination_before != ContaminationLevel.CLEAN or 
                transfer.tip_contamination_after != ContaminationLevel.CLEAN):
                contaminated_wells.add(transfer.destination_well)
                transfer_chain.append({
                    "transfer_id": transfer.transfer_id,
                    "destination": transfer.destination_well,
                    "contamination_before": transfer.tip_contamination_before.value,
                    "contamination_after": transfer.tip_contamination_after.value,
                    "timestamp": transfer.timestamp.isoformat()
                })
        
        return {
            "reagent": reagent_name,
            "potentially_contaminated_wells": list(contaminated_wells),
            "contamination_chain": transfer_chain,
            "risk_level": "high" if len(contaminated_wells) > 1 else "low"
        }
    
    def find_tip_changes_needed(self) -> List[Dict[str, Any]]:
        """Identify when tip changes should have occurred"""
        tip_change_events = []
        
        # Analyze tip contamination history
        pipette = self.experiment.pipette_state
        if pipette and pipette.requires_tip_change():
            tip_change_events.append({
                "current_tip_id": pipette.tip_id,
                "contamination_level": pipette.tip_contamination_level.value,
                "contamination_events": len(pipette.tip_contamination_history),
                "recommendation": "Change tip immediately"
            })
        
        # Analyze transfers for potential contamination
        tip_usage = {}  # tip_id -> list of transfers
        
        for transfer in self.experiment.all_transfers:
            # Simulate tip tracking (in real implementation, this would come from video analysis)
            tip_id = f"tip_{transfer.transfer_id[:8]}"  # Simplified tip tracking
            if tip_id not in tip_usage:
                tip_usage[tip_id] = []
            tip_usage[tip_id].append(transfer)
        
        # Check for tips used across different reagents
        for tip_id, transfers in tip_usage.items():
            reagents_used = set(t.reagent.name for t in transfers)
            if len(reagents_used) > 1:
                tip_change_events.append({
                    "tip_id": tip_id,
                    "reagents_contacted": list(reagents_used),
                    "transfers": len(transfers),
                    "recommendation": f"Should have changed tip between {reagents_used}"
                })
        
        return tip_change_events
    
    def analyze_pipetting_accuracy(self) -> Dict[str, Any]:
        """Analyze overall pipetting accuracy across the experiment"""
        accurate_transfers = 0
        total_transfers = len(self.experiment.all_transfers)
        volume_discrepancies = []
        
        for transfer in self.experiment.all_transfers:
            if transfer.actual_volume_ul is not None:
                discrepancy = abs(transfer.intended_volume_ul - transfer.actual_volume_ul)
                relative_error = discrepancy / transfer.intended_volume_ul
                
                volume_discrepancies.append(relative_error)
                
                # Consider transfer accurate if within 5% of intended volume
                if relative_error <= 0.05:
                    accurate_transfers += 1
        
        accuracy_rate = accurate_transfers / total_transfers if total_transfers > 0 else 0
        avg_error = sum(volume_discrepancies) / len(volume_discrepancies) if volume_discrepancies else 0
        
        return {
            "total_transfers": total_transfers,
            "accurate_transfers": accurate_transfers,
            "accuracy_rate": accuracy_rate,
            "average_volume_error": avg_error,
            "quality_grade": self._get_quality_grade(accuracy_rate)
        }
    
    def _get_quality_grade(self, accuracy_rate: float) -> str:
        """Convert accuracy rate to quality grade"""
        if accuracy_rate >= 0.95:
            return "Excellent"
        elif accuracy_rate >= 0.90:
            return "Good"
        elif accuracy_rate >= 0.80:
            return "Fair"
        else:
            return "Poor"
    
    def find_protocol_deviations(self) -> List[Dict[str, Any]]:
        """Find deviations from expected protocol"""
        deviations = []
        
        # Check for incomplete wells
        for well_id, well in self.experiment.wells.items():
            if well.expected_volume_ul and not well.is_complete():
                deviations.append({
                    "type": "incomplete_well",
                    "well_id": well_id,
                    "expected_volume": well.expected_volume_ul,
                    "actual_volume": well.total_volume_ul,
                    "deviation": well.get_volume_discrepancy()
                })
        
        # Check for volume discrepancies above threshold
        for discrepancy in self.experiment.volume_discrepancies:
            if discrepancy.relative_difference_percent and discrepancy.relative_difference_percent > 10:
                deviations.append({
                    "type": "volume_discrepancy",
                    "container": discrepancy.container_id,
                    "relative_error": discrepancy.relative_difference_percent,
                    "severity": discrepancy.severity.value
                })
        
        return deviations
    
    def generate_experiment_report(self) -> Dict[str, Any]:
        """Generate comprehensive experiment analysis report"""
        return {
            "experiment_id": self.experiment.experiment_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "experiment_duration": (self.experiment.last_updated - self.experiment.start_time).total_seconds() / 60,  # minutes
            "completion_status": {
                "percentage": self.experiment.completion_percentage,
                "wells_completed": self.experiment.wells_completed,
                "total_wells": self.experiment.total_wells
            },
            "quality_metrics": self.analyze_pipetting_accuracy(),
            "contamination_analysis": {
                "risk_level": self.experiment.contamination_risk_level.value,
                "total_warnings": len(self.experiment.contamination_warnings),
                "critical_warnings": self.experiment.critical_warnings,
                "contamination_events": [
                    {
                        "type": w.warning_type.value,
                        "severity": w.severity.value,
                        "source": w.contamination_source,
                        "affected_containers": w.affected_containers
                    }
                    for w in self.find_contamination_events(WarningSeverity.MEDIUM)
                ]
            },
            "protocol_deviations": self.find_protocol_deviations(),
            "tip_management": self.find_tip_changes_needed(),
            "hud_summary": self.experiment.get_hud_summary()
        }


def create_sample_experiment() -> ExperimentState:
    """Create a sample experiment with realistic data for demonstration"""
    
    # Create experiment
    experiment = ExperimentState(
        experiment_id="LAB-2024-001",
        total_wells=6
    )
    
    # Initialize pipette
    pipette = PipetteState(
        volume_setting_ul=30.0,
        tip_attached=True,
        tip_id="TIP-001",
        tip_contamination_level=ContaminationLevel.CLEAN
    )
    experiment.pipette_state = pipette
    
    # Set up goal wells
    for well_id in ["A1", "A2", "A3", "B1", "B2", "B3"]:
        goal_well = WellContents(
            well_id=well_id,
            expected_volume_ul=90.0  # Each well should get 3x 30µl reagents
        )
        experiment.goal_wells[well_id] = goal_well
    
    # Define reagents
    reagents = {
        "Reagent A": Reagent(name="Reagent A", volume_ul=30.0, source_container="TUBE-A", color="orange"),
        "Reagent B": Reagent(name="Reagent B", volume_ul=30.0, source_container="TUBE-B", color="blue"),
        "Buffer L": Reagent(name="Buffer L", volume_ul=30.0, source_container="TUBE-L", color="clear")
    }
    
    # Create realistic transfer sequence with some issues
    transfers = [
        # Good transfers to A1
        ReagentTransfer(
            transfer_id=str(uuid.uuid4()),
            reagent=reagents["Reagent A"],
            source_container="TUBE-A",
            destination_well="A1",
            intended_volume_ul=30.0,
            actual_volume_ul=30.0,
            pipette_volume_setting=30.0,
            tip_contamination_before=ContaminationLevel.CLEAN,
            tip_contamination_after=ContaminationLevel.POTENTIALLY_CONTAMINATED
        ),
        
        # Transfer to A2 without tip change (contamination issue)
        ReagentTransfer(
            transfer_id=str(uuid.uuid4()),
            reagent=reagents["Reagent B"],
            source_container="TUBE-B",
            destination_well="A2",
            intended_volume_ul=30.0,
            actual_volume_ul=28.5,  # Volume discrepancy
            pipette_volume_setting=30.0,
            tip_contamination_before=ContaminationLevel.POTENTIALLY_CONTAMINATED,
            tip_contamination_after=ContaminationLevel.CONTAMINATED
        ),
        
        # Continue with contaminated tip (more contamination)
        ReagentTransfer(
            transfer_id=str(uuid.uuid4()),
            reagent=reagents["Buffer L"],
            source_container="TUBE-L",
            destination_well="A3",
            intended_volume_ul=30.0,
            actual_volume_ul=29.0,  # Another slight discrepancy
            pipette_volume_setting=30.0,
            tip_contamination_before=ContaminationLevel.CONTAMINATED,
            tip_contamination_after=ContaminationLevel.CONTAMINATED
        )
    ]
    
    # Add transfers to experiment
    for transfer in transfers:
        experiment.add_transfer(transfer)
    
    # Add contamination warnings
    warning1 = ContaminationWarning(
        warning_id=str(uuid.uuid4()),
        warning_type=WarningType.CROSS_CONTAMINATION,
        severity=WarningSeverity.HIGH,
        contamination_source="Tip not changed between reagents",
        affected_containers=["A1", "A2"],
        description="Reagent A residue may contaminate Reagent B",
        recommended_action="Change pipette tip between different reagents"
    )
    experiment.add_contamination_warning(warning1)
    
    warning2 = ContaminationWarning(
        warning_id=str(uuid.uuid4()),
        warning_type=WarningType.CROSS_CONTAMINATION,
        severity=WarningSeverity.CRITICAL,
        contamination_source="Continued use of contaminated tip",
        affected_containers=["A2", "A3"],
        description="Multiple reagents contaminated due to tip reuse",
        recommended_action="Discard affected samples and restart with clean tip"
    )
    experiment.add_contamination_warning(warning2)
    
    # Add volume discrepancies
    discrepancy = VolumeDiscrepancy(
        discrepancy_id=str(uuid.uuid4()),
        container_id="A2",
        expected_volume_ul=30.0,
        observed_volume_ul=28.5,
        severity=WarningSeverity.MEDIUM,
        description="Volume in A2 is 1.5µl less than expected",
        possible_causes=["Pipetting inaccuracy", "Air bubble", "Tip leakage"]
    )
    discrepancy.calculate_differences()
    experiment.add_volume_discrepancy(discrepancy)
    
    return experiment


def run_needle_in_haystack_demo():
    """Run comprehensive needle-in-haystack analysis demo"""
    
    print("=" * 60)
    print("NEEDLE IN THE HAYSTACK: Lab Video Analysis Demo")
    print("=" * 60)
    print()
    
    # Create sample experiment
    experiment = create_sample_experiment()
    analyzer = LabVideoAnalyzer(experiment)
    
    print("🔬 Experiment Created:")
    print(f"   ID: {experiment.experiment_id}")
    print(f"   Total Transfers: {len(experiment.all_transfers)}")
    print(f"   Wells: {list(experiment.wells.keys())}")
    print(f"   Warnings: {len(experiment.contamination_warnings)}")
    print()
    
    # 1. Find contamination events
    print("🚨 CONTAMINATION ANALYSIS:")
    contamination_events = analyzer.find_contamination_events(WarningSeverity.MEDIUM)
    for event in contamination_events:
        print(f"   • {event.warning_type.value.title()} ({event.severity.value})")
        print(f"     Source: {event.contamination_source}")
        print(f"     Affected: {', '.join(event.affected_containers)}")
        print(f"     Action: {event.recommended_action}")
        print()
    
    # 2. Cross-contamination chain analysis
    print("🔗 CROSS-CONTAMINATION CHAIN ANALYSIS:")
    for reagent_name in ["Reagent A", "Reagent B", "Buffer L"]:
        chain = analyzer.find_cross_contamination_chain(reagent_name)
        if chain["contamination_chain"]:
            print(f"   • {reagent_name} ({chain['risk_level']} risk):")
            print(f"     Contaminated wells: {chain['potentially_contaminated_wells']}")
            for event in chain["contamination_chain"]:
                print(f"     → {event['destination']}: {event['contamination_before']} → {event['contamination_after']}")
            print()
    
    # 3. Tip management analysis
    print("💡 TIP MANAGEMENT ANALYSIS:")
    tip_changes = analyzer.find_tip_changes_needed()
    for tip_issue in tip_changes:
        print(f"   • Tip Issue: {tip_issue.get('tip_id', 'Current tip')}")
        if 'reagents_contacted' in tip_issue:
            print(f"     Reagents contacted: {tip_issue['reagents_contacted']}")
        print(f"     Recommendation: {tip_issue['recommendation']}")
        print()
    
    # 4. Volume accuracy analysis
    print("📊 PIPETTING ACCURACY ANALYSIS:")
    accuracy = analyzer.analyze_pipetting_accuracy()
    print(f"   • Total transfers: {accuracy['total_transfers']}")
    print(f"   • Accurate transfers: {accuracy['accurate_transfers']}")
    print(f"   • Accuracy rate: {accuracy['accuracy_rate']:.1%}")
    print(f"   • Average error: {accuracy['average_volume_error']:.1%}")
    print(f"   • Quality grade: {accuracy['quality_grade']}")
    print()
    
    # 5. Protocol deviations
    print("⚠️  PROTOCOL DEVIATIONS:")
    deviations = analyzer.find_protocol_deviations()
    for deviation in deviations:
        print(f"   • {deviation['type'].title()}: {deviation.get('well_id', deviation.get('container'))}")
        if 'expected_volume' in deviation:
            print(f"     Expected: {deviation['expected_volume']}µl, Got: {deviation['actual_volume']}µl")
        if 'relative_error' in deviation:
            print(f"     Error: {deviation['relative_error']:.1f}%")
        print()
    
    # 6. Advanced queries
    print("🔍 ADVANCED QUERIES:")
    
    # Find all Reagent A transfers
    reagent_a_transfers = analyzer.find_transfers_by_reagent("Reagent A")
    print(f"   • Reagent A transfers: {len(reagent_a_transfers)}")
    
    # Find volume discrepancies for A2
    a2_discrepancies = analyzer.find_volume_discrepancies_by_well("A2")
    print(f"   • A2 volume discrepancies: {len(a2_discrepancies)}")
    
    # Check HUD summary
    hud = experiment.get_hud_summary()
    print(f"   • Current contamination risk: {hud['contamination_risk']}")
    print(f"   • Active warnings: {hud['active_warnings']}")
    print()
    
    # 7. Generate comprehensive report
    print("📋 GENERATING COMPREHENSIVE REPORT...")
    report = analyzer.generate_experiment_report()
    
    print("\n" + "=" * 60)
    print("EXPERIMENT ANALYSIS REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2, default=str))
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("This demonstrates how the new models enable sophisticated")
    print("'needle in the haystack' queries across entire video sessions.")
    print("=" * 60)


if __name__ == "__main__":
    run_needle_in_haystack_demo()