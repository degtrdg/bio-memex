from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Reagent(BaseModel):
    """Simple reagent with name and volume"""
    name: str = Field(..., description="Name of the reagent (e.g., 'Reagent A', 'Buffer')")
    volume_ul: float = Field(..., description="Volume in microliters")


class GoalWell(BaseModel):
    """What each well should contain when complete"""
    well_id: str = Field(..., description="Well position (e.g., 'A1', 'B2')")
    reagents: List[Reagent] = Field(..., description="List of reagents with volumes that should be in this well")


class ProcedureExtraction(BaseModel):
    """Overall protocol/procedure extracted from video"""
    
    thinking: str = Field(
        ..., 
        description="Your reasoning about the overall procedure you observed. You perceive video at 1fps, so reason through the timeline of what you see happening. Include timestamp ranges like '0:29 - 0:32' to indicate when you observed key procedural elements."
    )
    
    timestamp_range: str = Field(
        ..., 
        description="Time range analyzed in format '0:29 - 0:32' indicating start and end timestamps"
    )
    
    protocol_title: str = Field(
        ..., 
        description="Name/description of the experiment or procedure"
    )
    
    goal_wells: List[GoalWell] = Field(
        ..., 
        description="Target end state for each well - what reagents and volumes should be in each well when complete"
    )
    
    reagent_sources: List[str] = Field(
        ..., 
        description="Available reagent names that are being used in this procedure (just names, no volumes since they're aliquoted)"
    )