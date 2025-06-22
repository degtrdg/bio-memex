from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Reagent(BaseModel):
    """Simple reagent with name and volume"""

    name: str = Field(..., description="Name of the reagent (e.g., 'Reagent A')")
    volume_ul: float = Field(..., description="Volume in microliters")


class Well(BaseModel):
    """What each well should contain when complete"""

    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B2')")
    reagents: List[Reagent] = Field(
        ..., description="List of reagents with volumes that should be in this well"
    )


class ProcedureExtraction(BaseModel):
    """Overall protocol/procedure extracted from video"""

    thinking: str = Field(
        ..., description="Detailed reasoning about what procedure was observed"
    )

    timestamp_range: str = Field(
        ..., description="Time range analyzed (e.g., '0:29 - 0:32')"
    )

    goal_wells: List[Well] = Field(..., description="Target end state for each well")

    reagent_sources: List[str] = Field(
        ..., description="Available reagent names used in procedure"
    )


# Core objective events
class PipetteSettingChange(BaseModel):
    """Pipette volume setting change event"""

    thinking: str = Field(
        ..., description="Reasoning about the volume setting change observed"
    )
    timestamp_range: str = Field(
        ..., description="Time range analyzed (e.g., '0:29 - 0:32')"
    )

    new_setting_ul: int = Field(..., description="New volume setting in microliters")


class AspirationEvent(BaseModel):
    """Liquid aspiration event"""

    thinking: str = Field(
        ..., description="Reasoning about the aspiration event observed"
    )

    timestamp_range: str = Field(
        ..., description="Time range analyzed (e.g., '0:29 - 0:32')"
    )

    reagent_name: str = Field(..., description="Name of reagent aspirated")


class DispensingEvent(BaseModel):
    """Liquid dispensing event"""

    thinking: str = Field(
        ..., description="Reasoning about the dispensing event observed"
    )
    timestamp_range: str = Field(
        ..., description="Time range analyzed (e.g., '0:29 - 0:32')"
    )
    reagent: Reagent = Field(..., description="Reagent dispensed")


class TipChangeEvent(BaseModel):
    """Tip change/ejection event"""

    thinking: str = Field(..., description="Reasoning about the tip change observed")
    timestamp_range: str = Field(
        ..., description="Time range analyzed (e.g., '0:29 - 0:32')"
    )


# Warning/Contamination Models
class TipContaminationEvent(BaseModel):
    """Track tip contamination from reagent contact"""

    thinking: str = Field(..., description="Reasoning about contamination event")
    timestamp_range: str = Field(..., description="When contamination occurred")
    tip_id: str = Field(..., description="Identifier for the tip")
    contaminating_reagent: str = Field(
        ..., description="Reagent that contaminated the tip"
    )


class ContaminationWarning(BaseModel):
    """Warning about potential cross-contamination"""

    thinking: str = Field(..., description="Reasoning about the contamination risk")
    timestamp_range: str = Field(..., description="When warning was triggered")
    warning_type: str = Field(..., description="Type of contamination warning")
    contaminated_tip: str = Field(..., description="ID of contaminated tip")
    source_reagent: str = Field(..., description="Original contaminating reagent")
    target_reagent: str = Field(..., description="Reagent being contaminated")


# State Tracking Models
class WellState(BaseModel):
    """Current state of a specific well"""

    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B2')")
    current_reagents: List[Reagent] = Field(
        default=[], description="Currently added reagents"
    )
    target_reagents: List[Reagent] = Field(
        ..., description="Target reagents for this well"
    )
    is_complete: bool = Field(default=False, description="Whether well matches target")


class ExperimentState(BaseModel):
    """Overall experiment progress tracking"""

    timestamp: str = Field(..., description="Current analysis timestamp")
    wells: List[WellState] = Field(..., description="State of all wells")
    next_required_actions: List[str] = Field(
        default=[], description="What needs to happen next"
    )


# General Warning Models
class GeneralWarning(BaseModel):
    """General experimental warning or error"""

    thinking: str = Field(..., description="Reasoning about the warning")
    timestamp_range: str = Field(..., description="When warning occurred")
    severity: str = Field(
        ..., description="Warning severity (low, medium, high, critical)"
    )
    warning_message: str = Field(..., description="Human-readable warning message")
    suggested_action: Optional[str] = Field(
        default=None, description="Suggested action to resolve warning"
    )


class ExperimentProgress(BaseModel):
    """Incremental progress tracking for user display"""

    thinking: str = Field(..., description="Analysis of current progress")
    timestamp: str = Field(..., description="Current analysis time")
    current_step: Optional[str] = Field(
        default=None, description="Currently active step"
    )
    remaining_steps: List[str] = Field(
        default=[], description="Steps still to be completed"
    )
    overall_progress_percentage: float = Field(
        ..., description="Overall experiment completion percentage"
    )
