"""
Needle-in-haystack video processor for lab procedure analysis.
Processes entire videos with targeted queries to avoid error propagation.
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import uuid

from video_understanding.models import (
    PipetteState,
    ReagentTransfer,
    ContaminationWarning,
    ExperimentState,
    WellContents,
    Reagent,
    ContaminationLevel,
    PipetteAction,
    WarningType,
    WarningSeverity,
    TipContaminationHistory
)


@dataclass
class VideoEvent:
    """Single event extracted from video with timestamp"""
    timestamp: str
    event_type: str  # "volume_change", "aspiration", "dispensing", "tip_change"
    data: Dict[str, Any]
    confidence: float = 1.0


class NeedleHaystackProcessor:
    """
    Processes entire lab videos using targeted queries to extract specific events.
    Avoids error propagation by maintaining complete video context.
    """

    def __init__(self, video_frames: List[Any], video_duration: float):
        self.video_frames = video_frames
        self.video_duration = video_duration
        self.events: List[VideoEvent] = []

    def process_video(self) -> ExperimentState:
        """
        Main processing pipeline using needle-in-haystack approach.
        Returns complete experiment state for HUD overlay.
        """

        # Step 1: Extract all event types in parallel
        self._extract_pipette_volume_changes()
        self._extract_aspiration_events()
        self._extract_dispensing_events()
        self._extract_tip_changes()
        self._extract_protocol_context()

        # Step 2: Sort events chronologically
        self.events.sort(key=lambda e: self._timestamp_to_seconds(e.timestamp))

        # Step 3: Build complete state by replaying events
        return self._build_experiment_state()

    def _extract_pipette_volume_changes(self):
        """Find all times pipette volume setting changed"""

        query = """
        Find all moments in this lab video where the pipette volume setting is changed.
        Look for:
        - Hand adjusting the volume dial/wheel on the pipette
        - Close-up shots of the pipette display showing volume numbers
        - Any visible volume setting changes (e.g., 10µL → 30µL)

        For each event, extract:
        - Timestamp when change occurred
        - New volume setting (with units)
        - Previous setting if visible

        Return as list of events with timestamps.
        """

        # This would call the video model with the full video + query
        results = self._query_video_model(query)

        for result in results:
            event = VideoEvent(
                timestamp=result['timestamp'],
                event_type='volume_change',
                data={
                    'new_setting': result['new_volume'],
                    'previous_setting': result.get('previous_volume'),
                    'confidence': result.get('confidence', 0.8)
                }
            )
            self.events.append(event)

    def _extract_aspiration_events(self):
        """Find all aspiration events with source containers"""

        query = """
        Find all moments where liquid is aspirated from containers into the pipette.
        Look for:
        - Pipette tip entering tubes/containers
        - Liquid level dropping in source container
        - Pipette plunger being pulled up
        - Liquid entering the pipette tip

        For each aspiration, identify:
        - Timestamp of aspiration
        - Source container (eppendorf tube, beaker, etc.)
        - Reagent being aspirated (from container labels if visible)
        - Approximate volume (based on liquid level change)

        Return chronological list of aspiration events.
        """

        results = self._query_video_model(query)

        for result in results:
            event = VideoEvent(
                timestamp=result['timestamp'],
                event_type='aspiration',
                data={
                    'source_container': result['container'],
                    'reagent': result['reagent'],
                    'volume': result.get('volume'),
                    'container_label': result.get('label')
                }
            )
            self.events.append(event)

    def _extract_dispensing_events(self):
        """Find all dispensing events into wells"""

        query = """
        Find all moments where liquid is dispensed from pipette into wells.
        Look for:
        - Pipette tip entering wells in the 96-well plate
        - Liquid being expelled from tip
        - Pipette plunger being pushed down
        - Well contents increasing

        For each dispensing event, identify:
        - Timestamp
        - Target well position (A1, B2, etc.)
        - Approximate volume dispensed
        - Any mixing or multiple dispenses into same well

        Return chronological list of dispensing events.
        """

        results = self._query_video_model(query)

        for result in results:
            event = VideoEvent(
                timestamp=result['timestamp'],
                event_type='dispensing',
                data={
                    'target_well': result['well_id'],
                    'volume': result.get('volume'),
                    'is_mixing': result.get('mixing', False)
                }
            )
            self.events.append(event)

    def _extract_tip_changes(self):
        """Find all tip change/ejection events"""

        query = """
        Find all moments where pipette tips are changed or ejected.
        Look for:
        - Tips being ejected into tip waste
        - New tips being picked up from tip boxes
        - Tip ejector button being pressed
        - Tips falling/being discarded

        For each tip change:
        - Timestamp of tip ejection/change
        - Whether new tip was immediately picked up
        - Any contamination concerns (tip touching surfaces)

        Return chronological list of tip change events.
        """

        results = self._query_video_model(query)

        for result in results:
            event = VideoEvent(
                timestamp=result['timestamp'],
                event_type='tip_change',
                data={
                    'action': result['action'],  # 'eject' or 'pickup'
                    'new_tip_picked_up': result.get('new_tip', False)
                }
            )
            self.events.append(event)

    def _extract_protocol_context(self):
        """Extract protocol information from notebook/setup"""

        query = """
        Find the experimental protocol being followed in this video.
        Look for:
        - Written notebook/protocol being reviewed at start
        - Container labels indicating reagent types
        - Any visible procedure steps or goals
        - Target well configurations

        Extract:
        - Reagent types and their container assignments
        - Target wells for each reagent
        - Expected volumes for each transfer
        - Overall experimental goal

        Return protocol structure.
        """

        results = self._query_video_model(query)

        # Store protocol context for state building
        self.protocol_context = results if isinstance(results, dict) else {}

    def _build_experiment_state(self) -> ExperimentState:
        """
        Build complete experiment state by replaying all events chronologically.
        This avoids error propagation by processing events in correct order.
        """

        # Initialize state
        pipette_state = PipetteState(
            volume_setting_ul=10.0,  # Default 10µL
            actual_aspirated_volume_ul=None,
            last_reagent_aspirated=None,
            source_container_id=None,
            aspiration_timestamp=None,
            tip_contamination_level=ContaminationLevel.CLEAN,
            tip_contamination_history=[],
            tip_attached=False,
            tip_id=None,
            current_position=None,
            last_action=PipetteAction.IDLE,
            action_timestamp=None,
            accuracy_score=None
        )

        wells: Dict[str, WellContents] = {}
        containers: Dict[str, Dict] = {}
        warnings: List[ContaminationWarning] = []
        transfers: List[ReagentTransfer] = []

        # Initialize from protocol context
        if hasattr(self, 'protocol_context'):
            for reagent_info in self.protocol_context.get('reagents', []):
                containers[reagent_info['container']] = {
                    'reagent': reagent_info['name'],
                    'initial_volume': reagent_info.get('volume', 500.0),
                    'remaining_volume': reagent_info.get('volume', 500.0)
                }

        # Replay events to build state
        for event in self.events:
            self._apply_event_to_state(
                event, pipette_state, wells, containers, warnings, transfers
            )

        return ExperimentState(
            experiment_id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            pipette_state=pipette_state,
            wells=wells,
            source_containers=containers,
            goal_wells={},
            protocol_steps=[],
            all_transfers=transfers,
            contamination_warnings=warnings,
            volume_discrepancies=[],
            completion_percentage=self._calculate_completion(wells),
            wells_completed=len([w for w in wells.values() if w.is_complete()]),
            total_wells=len(wells) if wells else 0,
            overall_accuracy=None,
            contamination_risk_level=ContaminationLevel.CLEAN,
            critical_warnings=len([w for w in warnings if w.is_critical()])
        )

    def _apply_event_to_state(self, event: VideoEvent, pipette_state: PipetteState,
                             wells: Dict, containers: Dict, warnings: List, transfers: List):
        """Apply single event to update state"""

        if event.event_type == 'volume_change':
            # Convert volume string to float (e.g., "30µL" -> 30.0)
            volume_str = event.data['new_setting']
            volume_value = float(volume_str.replace('µL', '').replace('µl', '').replace('uL', ''))
            pipette_state.volume_setting_ul = volume_value

        elif event.event_type == 'aspiration':
            # Create reagent object
            reagent = Reagent(
                name=event.data['reagent'],
                volume_ul=pipette_state.volume_setting_ul,
                source_container=event.data['source_container'],
                color=None,
                density=None
            )

            # Update pipette state
            pipette_state.last_reagent_aspirated = reagent
            pipette_state.actual_aspirated_volume_ul = pipette_state.volume_setting_ul
            pipette_state.source_container_id = event.data['source_container']
            pipette_state.aspiration_timestamp = datetime.now()

            # Add to contamination history
            contamination_event = TipContaminationHistory(
                timestamp=datetime.now(),
                frame_number=None,
                contamination_source=event.data['reagent'],
                contamination_level=ContaminationLevel.POTENTIALLY_CONTAMINATED,
                action_taken=None
            )
            pipette_state.tip_contamination_history.append(contamination_event)
            pipette_state.tip_contamination_level = ContaminationLevel.POTENTIALLY_CONTAMINATED

            # Update container volume
            if event.data['source_container'] in containers:
                # Convert volume strings to calculate remaining
                # This is simplified - would need proper volume parsing
                pass

        elif event.event_type == 'dispensing':
            well_id = event.data['target_well']

            # Create transfer record (only if we have a reagent)
            if pipette_state.last_reagent_aspirated:
                transfer = ReagentTransfer(
                    transfer_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    frame_number=None,
                    reagent=pipette_state.last_reagent_aspirated,
                    source_container=pipette_state.source_container_id or "unknown",
                    destination_well=well_id,
                    intended_volume_ul=pipette_state.actual_aspirated_volume_ul or 0.0,
                    actual_volume_ul=pipette_state.actual_aspirated_volume_ul,
                    volume_accuracy=1.0,
                    pipette_volume_setting=pipette_state.volume_setting_ul,
                    tip_contamination_before=ContaminationLevel.CLEAN,
                    tip_contamination_after=pipette_state.tip_contamination_level,
                    transfer_quality_score=1.0,
                    observed_issues=[]
                )
                transfers.append(transfer)
                
                # Update well contents
                if well_id not in wells:
                    wells[well_id] = WellContents(
                        well_id=well_id,
                        reagents=[],
                        total_volume_ul=0.0,
                        expected_volume_ul=None,
                        transfer_history=[],
                        last_modified=None,
                        contamination_risk=ContaminationLevel.CLEAN,
                        contamination_sources=[],
                        observed_color=None,
                        homogeneous=None
                    )
                
                wells[well_id].add_reagent(transfer)

            # Check for contamination warnings
            self._check_contamination_warnings(pipette_state, well_id, warnings)

            # Reset pipette aspiration
            pipette_state.actual_aspirated_volume_ul = 0.0
            pipette_state.last_action = PipetteAction.DISPENSE
            pipette_state.action_timestamp = datetime.now()

        elif event.event_type == 'tip_change':
            if event.data['action'] == 'eject':
                # Reset contamination state
                pipette_state.tip_contamination_history = []
                pipette_state.tip_contamination_level = ContaminationLevel.CLEAN
                pipette_state.tip_attached = False
                pipette_state.tip_id = None
                pipette_state.last_reagent_aspirated = None
                pipette_state.actual_aspirated_volume_ul = 0.0
                pipette_state.last_action = PipetteAction.CHANGE_TIP
                pipette_state.action_timestamp = datetime.now()
            elif event.data['action'] == 'pickup':
                pipette_state.tip_attached = True
                pipette_state.tip_id = str(uuid.uuid4())
                pipette_state.last_action = PipetteAction.CHANGE_TIP

    def _check_contamination_warnings(self, pipette_state: PipetteState,
                                    target_well: str, warnings: List):
        """Check for cross-contamination issues"""

        if len(pipette_state.tip_contamination_history) > 1:
            # Multiple reagents in tip history
            reagents = [h.contamination_source for h in pipette_state.tip_contamination_history]
            if len(set(reagents)) > 1:
                warning = ContaminationWarning(
                    warning_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    frame_number=None,
                    warning_type=WarningType.CROSS_CONTAMINATION,
                    severity=WarningSeverity.HIGH,
                    contamination_source=reagents[0],
                    affected_containers=[target_well],
                    contaminated_reagent=reagents[-1],
                    description=(f"Cross-contamination risk: tip used with "
                               f"{len(set(reagents))} different reagents"),
                    recommended_action="Change pipette tip before dispensing",
                    contamination_probability=0.9,
                    impact_severity=0.8
                )
                warnings.append(warning)

    def _calculate_completion(self, wells: Dict) -> float:
        """Calculate experiment completion percentage"""
        if not hasattr(self, 'protocol_context'):
            return 0.0

        expected_wells = len(self.protocol_context.get('target_wells', []))
        completed_wells = len([w for w in wells.values() if w.reagents])

        return (completed_wells / expected_wells * 100) if expected_wells > 0 else 0.0

    def _query_video_model(self, query: str) -> List[Dict]:
        """
        Query the video model with full video context.
        In real implementation, this would call the actual video model API.
        """
        # Placeholder - would integrate with actual video model
        # Returns mock results for now
        return []

    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp string to seconds for sorting"""
        # Parse timestamp format like "00:05:23"
        parts = timestamp.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        if len(parts) == 2:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        return float(parts[0])


def process_lab_video_full_context(video_path: str) -> ExperimentState:
    """
    Main entry point for processing lab videos with full context.
    Returns complete experiment state for HUD overlay.
    """

    # Load video frames (would use actual video loading library)
    video_frames: List[Any] = []  # Placeholder
    video_duration = 600.0  # 10 minutes example

    processor = NeedleHaystackProcessor(video_frames, video_duration)
    experiment_state = processor.process_video()

    return experiment_state


# Example usage for HUD overlay
def generate_hud_data(experiment_state: ExperimentState) -> Dict[str, Any]:
    """Generate data structure for real-time HUD overlay"""

    if experiment_state.pipette_state:
        pipette_volume = f"{experiment_state.pipette_state.volume_setting_ul}µl"
        pipette_reagent = (experiment_state.pipette_state.last_reagent_aspirated.name
                          if experiment_state.pipette_state.last_reagent_aspirated else "None")
        tip_status = experiment_state.pipette_state.tip_contamination_level.value
        aspiration_volume = f"{experiment_state.pipette_state.actual_aspirated_volume_ul or 0}µl"
    else:
        pipette_volume = "N/A"
        pipette_reagent = "None"
        tip_status = "unknown"
        aspiration_volume = "0µl"

    return {
        "pipette": {
            "current_setting": pipette_volume,
            "last_reagent": pipette_reagent,
            "tip_status": tip_status,
            "aspiration_volume": aspiration_volume
        },
        "wells": {
            well.well_id: {
                "reagents": [{"name": r.name, "volume": f"{r.volume_ul}µl"} for r in well.reagents],
                "total_volume": well.total_volume_ul,
                "is_target": well.well_id in experiment_state.goal_wells
            }
            for well in experiment_state.wells.values()
        },
        "warnings": [
            {
                "type": w.warning_type.value,
                "severity": w.severity.value,
                "message": (f"Risk: {w.contamination_probability:.1%}"
                           if w.contamination_probability else w.description),
                "wells": w.affected_containers
            }
            for w in experiment_state.get_active_warnings()
        ],
        "progress": {
            "completion": f"{experiment_state.completion_percentage:.1f}%",
            "transfers_completed": len(experiment_state.all_transfers),
            "wells_used": len(experiment_state.wells)
        }
    }