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

    thinking: str = Field(..., description="Detailed reasoning about what procedure was observed")

    timestamp_range: str = Field(..., description="Time range analyzed (e.g., '0:29 - 0:32')")

    protocol_title: str = Field(
        ..., description="Name/description of the experiment or procedure"
    )

    goal_wells: List[Well] = Field(..., description="Target end state for each well")

    reagent_sources: List[str] = Field(..., description="Available reagent names used in procedure")


# Core objective events
class PipetteSettingChange(BaseModel):
    """Pipette volume setting change event"""
    
    thinking: str = Field(..., description="Reasoning about the volume setting change observed")
    timestamp_range: str = Field(..., description="Time range when setting change occurred")
    
    old_setting_ul: Optional[float] = Field(None, description="Previous volume setting in microliters")
    new_setting_ul: float = Field(..., description="New volume setting in microliters")


class AspirationEvent(BaseModel):
    """Liquid aspiration event"""
    
    thinking: str = Field(..., description="Reasoning about the aspiration event observed")
    timestamp_range: str = Field(..., description="Time range when aspiration occurred")
    
    container_id: str = Field(..., description="Container where aspiration occurred")
    reagent_name: str = Field(..., description="Name of reagent aspirated")
    volume_ul: float = Field(..., description="Volume aspirated in microliters")


class DispensingEvent(BaseModel):
    """Liquid dispensing event"""
    
    thinking: str = Field(..., description="Reasoning about the dispensing event observed")
    timestamp_range: str = Field(..., description="Time range when dispensing occurred")
    
    well_id: str = Field(..., description="Well where liquid was dispensed")
    reagent_name: str = Field(..., description="Name of reagent dispensed")
    volume_ul: float = Field(..., description="Volume dispensed in microliters")


class TipChangeEvent(BaseModel):
    """Tip change/ejection event"""
    
    thinking: str = Field(..., description="Reasoning about the tip change observed")
    timestamp_range: str = Field(..., description="Time range when tip change occurred")
    
    tip_ejected: bool = Field(..., description="Whether tip was ejected")
    new_tip_attached: bool = Field(..., description="Whether new tip was attached")
