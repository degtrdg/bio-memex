from datetime import datetime
from typing import List, Optional, Union

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

    reagent: Reagent = Field(..., description="Reagent aspirated")


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


class WarningEvent(BaseModel):
    """General warning event"""

    thinking: str = Field(..., description="Reasoning about the warning")
    timestamp_range: str = Field(..., description="When warning occurred")
    warning_message: str = Field(..., description="What the warning is about")
    description: str = Field(..., description="Short description for HUD display")


class WellStateEvent(BaseModel):
    """Well state change event"""

    thinking: str = Field(..., description="Reasoning about well state change")
    timestamp_range: str = Field(..., description="When state changed")
    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B2')")
    is_complete: bool = Field(..., description="Whether well is now complete")
    current_contents: List[Reagent] = Field(..., description="Current reagents in the well")
    missing_reagents: List[Reagent] = Field(..., description="Reagents still needed to complete the well")


class ObjectiveEventsList(BaseModel):
    """Wrapper for list of objective events"""

    events: List[
        Union[PipetteSettingChange, AspirationEvent, DispensingEvent, TipChangeEvent]
    ] = Field(..., description="List of objective events extracted from video")


class AnalysisEventsResult(BaseModel):
    events: List[Union[WarningEvent, WellStateEvent]] = []
