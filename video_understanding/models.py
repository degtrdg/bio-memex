from typing import List, Optional
from pydantic import BaseModel, Field

class Reagent(BaseModel):
    """Simple reagent with name and volume"""
    name: str = Field(..., description="Name of the reagent (e.g., 'Buffer A', 'Sample 1')")
    volume: str = Field(..., description="Volume with units (e.g., '10µl')")

class Well(BaseModel):
    """Well with reagents inside"""
    well_id: str = Field(..., description="Well position (e.g., 'A1', 'tube1')")
    reagents: List[Reagent] = Field(default_factory=list, description="List of reagents in this well")

class SimpleVideoAnalysis(BaseModel):
    """Simple base model with core components and triggered flags"""
    thinking: str = Field(..., description="Your reasoning about what you observed happening in this frame sequence. Explain what pipetting operations occurred and how they relate to the procedure.")
    
    goal_state_triggered: bool = Field(default=False, description="TRIGGER FLAG: Set to true if you learned new information about what the final procedure should achieve, requiring you to update or define the goal state.")
    goal_state: Optional[List[Well]] = Field(None, description="The target end state - what each well should contain when the entire procedure is complete. List all wells with their intended reagents and volumes. Only fill this out if goal_state_triggered is True.")
    
    current_state_triggered: bool = Field(default=False, description="TRIGGER FLAG: Set to true if the frame sequence showed pipetting operations that changed the contents of any wells, requiring you to update the current state.")
    current_state: Optional[List[Well]] = Field(None, description="The actual current state right now - what each well currently contains after the operations observed in this frame sequence. Update reagent lists and volumes based on what you saw. Only fill this out if current_state_triggered is True.")
    
    protocol_log_triggered: bool = Field(default=False, description="TRIGGER FLAG: Set to true if you observed significant events that should be documented in the running procedure log for future reference.")
    protocol_log: Optional[str] = Field(None, description="APPEND-ONLY running verbal description of significant events across all frame sequences. This will be APPENDED to existing log, not replaced. Only add information that is relevant and useful for later procedure steps (e.g., 'Added 10µl Buffer A to A1', 'Observed air bubble in tip during aspiration', 'Changed pipette volume to 20µl'). Be selective - do not add redundant or trivial information that clutters the log. Only fill this out if protocol_log_triggered is True.")
    
    warnings_triggered: bool = Field(default=False, description="TRIGGER FLAG: Set to true if you observed any problems, errors, or concerning techniques in this frame sequence that require generating new warnings.")
    warnings: Optional[List[str]] = Field(None, description="List of issues, errors, or concerns you observed in this frame sequence (e.g., 'Wrong volume dispensed into A1', 'Air bubble in pipette tip', 'Used wrong reagent'). Only fill this out if warnings_triggered is True.")