from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Enums for better type safety
class PipetteAction(str, Enum):
    ASPIRATE = "aspirate"
    DISPENSE = "dispense"
    MIX = "mix"
    BLOW_OUT = "blow_out"
    TOUCH_TIP = "touch_tip"
    CHANGE_TIP = "change_tip"
    IDLE = "idle"


class ContaminationLevel(str, Enum):
    CLEAN = "clean"
    POTENTIALLY_CONTAMINATED = "potentially_contaminated"
    CONTAMINATED = "contaminated"
    UNKNOWN = "unknown"


class WarningType(str, Enum):
    CROSS_CONTAMINATION = "cross_contamination"
    VOLUME_DISCREPANCY = "volume_discrepancy"
    TECHNIQUE_ERROR = "technique_error"
    EQUIPMENT_ISSUE = "equipment_issue"
    PROTOCOL_DEVIATION = "protocol_deviation"


class WarningSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Core data models
class Reagent(BaseModel):
    """Enhanced reagent with tracking capabilities"""

    name: str = Field(
        ..., description="Name of the reagent (e.g., 'Reagent A', 'Buffer')"
    )
    volume_ul: float = Field(..., description="Volume in microliters")

    def __str__(self) -> str:
        return f"{self.name} ({self.volume_ul}µl)"


class TipContaminationHistory(BaseModel):
    """History of tip contamination events"""

    frame_number: Optional[int] = Field(None, description="Video frame number")
    contamination_source: str = Field(..., description="What contaminated the tip")
    contamination_level: ContaminationLevel = Field(default=ContaminationLevel.UNKNOWN)
    action_taken: Optional[str] = Field(
        None, description="Action taken to address contamination"
    )


class PipetteState(BaseModel):
    """Complete state tracking for pipette operations"""

    volume_setting_ul: float = Field(
        default=0.0, description="Current volume setting in microliters"
    )
    actual_aspirated_volume_ul: Optional[float] = Field(
        None, description="Actually aspirated volume if different from setting"
    )

    # Reagent tracking
    last_reagent_aspirated: Optional[Reagent] = Field(
        None, description="Last reagent aspirated into tip"
    )
    source_container_id: Optional[str] = Field(
        None, description="Container where last reagent was aspirated from"
    )
    aspiration_timestamp: Optional[datetime] = Field(
        None, description="When the reagent was aspirated"
    )

    # Tip state
    tip_contamination_level: ContaminationLevel = Field(
        default=ContaminationLevel.CLEAN
    )
    tip_contamination_history: List[TipContaminationHistory] = Field(
        default_factory=list
    )
    tip_attached: bool = Field(
        default=False, description="Whether a tip is currently attached"
    )
    tip_id: Optional[str] = Field(None, description="Unique identifier for current tip")

    # Position tracking
    current_position: Optional[str] = Field(
        None, description="Current position (well ID, tube ID, or general location)"
    )
    last_action: PipetteAction = Field(default=PipetteAction.IDLE)
    action_timestamp: Optional[datetime] = Field(None)

    # Performance metrics
    accuracy_score: Optional[float] = Field(
        None, description="Estimated accuracy of last operation (0-1)"
    )

    def is_contaminated(self) -> bool:
        """Check if tip is potentially contaminated"""
        return self.tip_contamination_level in [
            ContaminationLevel.POTENTIALLY_CONTAMINATED,
            ContaminationLevel.CONTAMINATED,
        ]

    def requires_tip_change(self) -> bool:
        """Determine if tip should be changed"""
        return (
            self.tip_contamination_level == ContaminationLevel.CONTAMINATED
            or len(self.tip_contamination_history) > 3  # Multiple contamination events
        )


class ReagentTransfer(BaseModel):
    """Detailed tracking of reagent transfers between containers"""

    transfer_id: str = Field(..., description="Unique identifier for this transfer")
    timestamp: datetime = Field(default_factory=datetime.now)
    frame_number: Optional[int] = Field(
        None, description="Video frame number where transfer occurred"
    )

    # Transfer details
    reagent: Reagent = Field(..., description="Reagent being transferred")
    source_container: str = Field(..., description="Source container ID")
    destination_well: str = Field(..., description="Destination well ID")

    # Volume tracking
    intended_volume_ul: float = Field(..., description="Intended transfer volume")
    actual_volume_ul: Optional[float] = Field(
        None, description="Actual transferred volume if measurable"
    )
    volume_accuracy: Optional[float] = Field(None, description="Accuracy score (0-1)")

    # Pipette state during transfer
    pipette_volume_setting: float = Field(
        ..., description="Pipette volume setting used"
    )
    tip_contamination_before: ContaminationLevel = Field(
        default=ContaminationLevel.UNKNOWN
    )
    tip_contamination_after: ContaminationLevel = Field(
        default=ContaminationLevel.UNKNOWN
    )

    # Quality metrics
    transfer_quality_score: Optional[float] = Field(
        None, description="Overall transfer quality (0-1)"
    )
    observed_issues: List[str] = Field(
        default_factory=list, description="Issues observed during transfer"
    )

    def has_volume_discrepancy(self, threshold: float = 0.1) -> bool:
        """Check if there's a significant volume discrepancy"""
        if self.actual_volume_ul is None:
            return False
        discrepancy = abs(self.intended_volume_ul - self.actual_volume_ul)
        return discrepancy > (self.intended_volume_ul * threshold)


class ContaminationWarning(BaseModel):
    """Cross-contamination and tip contamination warnings"""

    warning_id: str = Field(..., description="Unique warning identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    frame_number: Optional[int] = Field(
        None, description="Video frame where issue was detected"
    )

    warning_type: WarningType = Field(..., description="Type of contamination warning")
    severity: WarningSeverity = Field(..., description="Severity level")

    # Contamination details
    contamination_source: str = Field(..., description="Source of contamination")
    affected_containers: List[str] = Field(
        ..., description="Containers potentially affected"
    )
    contaminated_reagent: Optional[str] = Field(
        None, description="Reagent that may be contaminated"
    )

    # Context
    description: str = Field(
        ..., description="Human-readable description of the contamination risk"
    )
    recommended_action: str = Field(
        ..., description="Recommended action to mitigate risk"
    )

    # Risk assessment
    contamination_probability: Optional[float] = Field(
        None, description="Probability of contamination (0-1)"
    )
    impact_severity: Optional[float] = Field(
        None, description="Potential impact severity (0-1)"
    )

    def is_critical(self) -> bool:
        """Check if this is a critical contamination warning"""
        return self.severity == WarningSeverity.CRITICAL


class VolumeDiscrepancy(BaseModel):
    """Volume measurement discrepancies and inaccuracies"""

    discrepancy_id: str = Field(..., description="Unique discrepancy identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    frame_number: Optional[int] = Field(
        None, description="Video frame where discrepancy was detected"
    )

    # Volume details
    container_id: str = Field(..., description="Container where discrepancy occurred")
    expected_volume_ul: float = Field(
        ..., description="Expected volume based on protocol"
    )
    observed_volume_ul: Optional[float] = Field(
        None, description="Visually observed volume"
    )
    calculated_volume_ul: Optional[float] = Field(
        None, description="Volume calculated from transfers"
    )

    # Discrepancy analysis
    absolute_difference_ul: Optional[float] = Field(
        None, description="Absolute volume difference"
    )
    relative_difference_percent: Optional[float] = Field(
        None, description="Relative difference as percentage"
    )

    # Context
    possible_causes: List[str] = Field(
        default_factory=list, description="Possible causes of discrepancy"
    )
    severity: WarningSeverity = Field(..., description="Severity of the discrepancy")
    description: str = Field(..., description="Human-readable description")

    # Recommendations
    suggested_actions: List[str] = Field(
        default_factory=list, description="Suggested corrective actions"
    )
    requires_protocol_adjustment: bool = Field(
        default=False, description="Whether protocol needs adjustment"
    )

    def calculate_differences(self):
        """Calculate absolute and relative differences"""
        if self.observed_volume_ul is not None:
            self.absolute_difference_ul = abs(
                self.expected_volume_ul - self.observed_volume_ul
            )
            if self.expected_volume_ul > 0:
                self.relative_difference_percent = (
                    self.absolute_difference_ul / self.expected_volume_ul
                ) * 100


class WellContents(BaseModel):
    """Enhanced well tracking with cumulative reagent history"""

    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B2')")
    reagents: List[Reagent] = Field(
        default_factory=list, description="Current reagents in well"
    )

    # Volume tracking
    total_volume_ul: float = Field(default=0.0, description="Total volume in well")
    expected_volume_ul: Optional[float] = Field(
        None, description="Expected volume based on protocol"
    )

    # Transfer history
    transfer_history: List[ReagentTransfer] = Field(
        default_factory=list, description="All transfers into this well"
    )
    last_modified: Optional[datetime] = Field(
        None, description="Last time well contents changed"
    )

    # Quality tracking
    contamination_risk: ContaminationLevel = Field(default=ContaminationLevel.CLEAN)
    contamination_sources: List[str] = Field(
        default_factory=list, description="Potential contamination sources"
    )

    # Visual properties
    observed_color: Optional[str] = Field(None, description="Current visual color")
    homogeneous: Optional[bool] = Field(
        None, description="Whether contents appear well-mixed"
    )

    def add_reagent(self, transfer: ReagentTransfer):
        """Add a reagent transfer to this well"""
        # Add to transfer history
        self.transfer_history.append(transfer)

        # Update reagent list
        existing_reagent = next(
            (r for r in self.reagents if r.name == transfer.reagent.name), None
        )

        if existing_reagent:
            existing_reagent.volume_ul += (
                transfer.actual_volume_ul or transfer.intended_volume_ul
            )
        else:
            new_reagent = transfer.reagent.model_copy()
            new_reagent.volume_ul = (
                transfer.actual_volume_ul or transfer.intended_volume_ul
            )
            self.reagents.append(new_reagent)

        # Update total volume
        self.total_volume_ul += transfer.actual_volume_ul or transfer.intended_volume_ul
        self.last_modified = transfer.timestamp

        # Update contamination risk
        if transfer.tip_contamination_after != ContaminationLevel.CLEAN:
            self.contamination_risk = max(
                self.contamination_risk, transfer.tip_contamination_after
            )

    def get_volume_discrepancy(self) -> Optional[float]:
        """Calculate volume discrepancy if expected volume is set"""
        if self.expected_volume_ul is None:
            return None
        return abs(self.total_volume_ul - self.expected_volume_ul)

    def is_complete(self) -> bool:
        """Check if well has reached expected volume"""
        if self.expected_volume_ul is None:
            return False
        return (
            abs(self.total_volume_ul - self.expected_volume_ul) < 0.5
        )  # 0.5µl tolerance


class ExperimentState(BaseModel):
    """Complete experiment state for HUD overlay and analysis"""

    experiment_id: str = Field(..., description="Unique experiment identifier")
    start_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    # Equipment state
    pipette_state: Optional[PipetteState] = Field(default=None)

    # Container states
    wells: Dict[str, WellContents] = Field(
        default_factory=dict, description="All wells in the experiment"
    )
    source_containers: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Source container information and remaining volumes",
    )

    # Goal tracking
    goal_wells: Dict[str, WellContents] = Field(
        default_factory=dict, description="Target end state for each well"
    )
    protocol_steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="Protocol steps and completion status"
    )

    # Event tracking
    all_transfers: List[ReagentTransfer] = Field(default_factory=list)
    contamination_warnings: List[ContaminationWarning] = Field(default_factory=list)
    volume_discrepancies: List[VolumeDiscrepancy] = Field(default_factory=list)

    # Progress metrics
    completion_percentage: float = Field(
        default=0.0, description="Overall experiment completion (0-100)"
    )
    wells_completed: int = Field(default=0, description="Number of wells completed")
    total_wells: int = Field(default=0, description="Total wells in experiment")

    # Quality metrics
    overall_accuracy: Optional[float] = Field(
        None, description="Overall volume accuracy score (0-1)"
    )
    contamination_risk_level: ContaminationLevel = Field(
        default=ContaminationLevel.CLEAN
    )
    critical_warnings: int = Field(default=0, description="Number of critical warnings")

    def add_transfer(self, transfer: ReagentTransfer):
        """Add a new reagent transfer to the experiment"""
        self.all_transfers.append(transfer)

        # Update destination well
        if transfer.destination_well not in self.wells:
            self.wells[transfer.destination_well] = WellContents(
                well_id=transfer.destination_well,
                expected_volume_ul=None,
                last_modified=None,
                observed_color=None,
                homogeneous=None,
            )

        self.wells[transfer.destination_well].add_reagent(transfer)
        self.last_updated = datetime.now()

        # Update completion metrics
        self.update_completion_metrics()

    def add_contamination_warning(self, warning: ContaminationWarning):
        """Add a contamination warning"""
        self.contamination_warnings.append(warning)
        if warning.is_critical():
            self.critical_warnings += 1

        # Update overall contamination risk
        if warning.severity in [WarningSeverity.HIGH, WarningSeverity.CRITICAL]:
            self.contamination_risk_level = ContaminationLevel.CONTAMINATED
        elif (
            warning.severity == WarningSeverity.MEDIUM
            and self.contamination_risk_level == ContaminationLevel.CLEAN
        ):
            self.contamination_risk_level = ContaminationLevel.POTENTIALLY_CONTAMINATED

    def add_volume_discrepancy(self, discrepancy: VolumeDiscrepancy):
        """Add a volume discrepancy"""
        self.volume_discrepancies.append(discrepancy)

    def update_completion_metrics(self):
        """Update experiment completion metrics"""
        if self.total_wells > 0:
            completed_wells = sum(
                1 for well in self.wells.values() if well.is_complete()
            )
            self.wells_completed = completed_wells
            self.completion_percentage = (completed_wells / self.total_wells) * 100

    def get_active_warnings(self) -> List[ContaminationWarning]:
        """Get currently active warnings"""
        # For now, return all warnings. In future, could add resolution tracking
        return [
            w
            for w in self.contamination_warnings
            if w.severity in [WarningSeverity.HIGH, WarningSeverity.CRITICAL]
        ]

    def get_hud_summary(self) -> Dict[str, Any]:
        """Get summary information for HUD overlay"""
        if self.pipette_state:
            pipette_volume = f"{self.pipette_state.volume_setting_ul}µl"
            pipette_reagent = (
                self.pipette_state.last_reagent_aspirated.name
                if self.pipette_state.last_reagent_aspirated
                else "None"
            )
            tip_status = self.pipette_state.tip_contamination_level.value
            last_action = self.pipette_state.last_action.value
        else:
            pipette_volume = "N/A"
            pipette_reagent = "None"
            tip_status = "unknown"
            last_action = "idle"

        return {
            "experiment_id": self.experiment_id,
            "completion_percentage": self.completion_percentage,
            "wells_completed": f"{self.wells_completed}/{self.total_wells}",
            "pipette_volume": pipette_volume,
            "pipette_reagent": pipette_reagent,
            "tip_status": tip_status,
            "active_warnings": len(self.get_active_warnings()),
            "contamination_risk": self.contamination_risk_level.value,
            "last_action": last_action,
            "total_transfers": len(self.all_transfers),
        }


# Legacy models for backward compatibility
class Well(BaseModel):
    """Simple well model for backward compatibility"""

    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B1')")
    reagents: List[Reagent] = Field(
        default_factory=list, description="List of reagents in this well"
    )


class VideoAnalysis(BaseModel):
    """Enhanced video analysis with new tracking capabilities"""

    thinking: str = Field(
        ...,
        description="Your reasoning about what you observed happening in this frame sequence. Explain what pipetting operations occurred and how they relate to the procedure.",
    )

    # Legacy triggered flags for backward compatibility
    goal_state_triggered: bool = Field(default=False)
    goal_state: Optional[List[Well]] = Field(None)
    current_state_triggered: bool = Field(default=False)
    current_state: Optional[List[Well]] = Field(None)
    protocol_log_triggered: bool = Field(default=False)
    protocol_log: Optional[str] = Field(None)
    warnings_triggered: bool = Field(default=False)
    warnings: Optional[List[str]] = Field(None)

    # New enhanced tracking
    experiment_state_updated: bool = Field(
        default=False, description="Whether the complete experiment state was updated"
    )
    experiment_state: Optional[ExperimentState] = Field(
        None, description="Complete experiment state with enhanced tracking"
    )

    # Specific event detection
    transfers_detected: List[ReagentTransfer] = Field(
        default_factory=list,
        description="Reagent transfers detected in this frame sequence",
    )
    contamination_warnings_detected: List[ContaminationWarning] = Field(
        default_factory=list,
        description="Contamination warnings detected in this frame sequence",
    )
    volume_discrepancies_detected: List[VolumeDiscrepancy] = Field(
        default_factory=list,
        description="Volume discrepancies detected in this frame sequence",
    )

    # Pipette state changes
    pipette_state_changed: bool = Field(
        default=False,
        description="Whether pipette state changed in this frame sequence",
    )
    new_pipette_state: Optional[PipetteState] = Field(
        None, description="Updated pipette state if changed"
    )

    # Frame analysis metadata
    frame_range: Optional[str] = Field(
        None, description="Frame range analyzed (e.g., '100-170')"
    )
    analysis_confidence: Optional[float] = Field(
        None, description="Confidence in analysis (0-1)"
    )
    key_events_detected: List[str] = Field(
        default_factory=list, description="Key events detected in this frame sequence"
    )
