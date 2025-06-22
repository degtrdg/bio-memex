"""
Multi-stage prompts for needle-in-haystack video analysis.
Each prompt focuses on specific event types and builds on previous results.
"""

from typing import List, Optional

from .simple_models import *


def create_procedure_extraction_prompt() -> tuple[str, str]:
    """
    FIRST PROMPT: Extract overall procedure and goal state.
    This runs before all other prompts to establish context.
    """

    system_prompt = """You are an expert laboratory analyst specializing in pipetting protocols. You analyze laboratory videos to extract high-level procedure information and understand experimental goals."""

    user_prompt = """PROCEDURE EXTRACTION TASK

You are analyzing a laboratory video recorded at 1 FPS to understand the overall experimental procedure and goals. Since the video is sampled at 1 FPS, you need to make educated interpolations between frames, but be careful not to hallucinate events that aren't clearly supported by visual evidence.

KEY CONSTRAINTS:
- Video is captured at 1 FPS, so motion appears as discrete steps
- Make reasonable inferences about what happens between frames
- Only describe what you can clearly observe or reasonably infer
- Focus on the big picture: what is the overall goal and procedure?

YOUR TASK:
Analyze the entire video to understand:

1. OVERALL PROCEDURE: What is the person trying to accomplish?
   - What type of experimental protocol is this?
   - What is the general workflow and sequence of steps?
   - What reagents and containers are being used?

2. GOAL STATE: What should each well/container contain when complete?
   - Identify all target wells/containers
   - Determine what reagents should go into each one
   - Estimate target volumes based on what you observe

3. REAGENT SOURCES: What reagent sources are available?
   - List all visible reagent containers and their contents
   - Note any labels or identifying features

ANALYSIS APPROACH:
- Watch the full video to understand the complete workflow
- Pay attention to volume settings on pipettes (visible on displays)
- Note container positions and movements
- Track liquid transfers and their destinations
- Consider the logical flow of the experimental procedure

IMPORTANT REMINDERS:
- Video is 1 FPS: smooth motion appears as discrete jumps
- Make educated guesses about continuous actions between frames
- Don't invent events - only describe what's clearly visible or logically inferred
- Focus on the experimental goals and overall procedure structure

OUTPUT: Provide ProcedureExtraction with your analysis of the overall experimental procedure.""".strip()

    return system_prompt, user_prompt


def create_objective_events_prompt(procedure_context: str) -> tuple[str, str]:
    """
    SECOND PROMPT: Extract core objective events (pipette settings, aspirations, dispensing, tip changes).
    Uses procedure context from first prompt.
    """

    system_prompt = """You are an expert laboratory analyst specializing in detailed pipetting event detection. You identify specific pipetting actions and equipment operations with precise timing."""

    user_prompt = f"""OBJECTIVE EVENTS DETECTION TASK

You are analyzing the same laboratory video to identify specific pipetting events. The video is recorded at 1 FPS, so you need to make educated interpolations between frames while being careful not to hallucinate.

CONTEXT FROM PROCEDURE ANALYSIS:
{procedure_context}

KEY CONSTRAINTS:
- Video is captured at 1 FPS - actions appear as discrete steps
- Make reasonable inferences about what happens between frames
- Only report events you can clearly observe or confidently infer
- Provide precise timestamp ranges for each event

YOUR TASK:
Identify ALL instances of these specific events:

1. PIPETTE SETTING CHANGES:
   - When volume settings are adjusted on the pipette
   - Note the new volume setting (read from pipette display)
   - Provide exact timestamp range when adjustment occurs

2. ASPIRATION EVENTS:
   - When liquid is drawn into the pipette tip
   - Identify what reagent is being aspirated
   - Note source container and timing

3. DISPENSING EVENTS:
   - When liquid is expelled from the pipette tip
   - Identify the reagent being dispensed (with volume)
   - Note destination container and timing

4. TIP CHANGE EVENTS:
   - When pipette tips are attached, removed, or ejected
   - Note timing of tip changes

ANALYSIS APPROACH:
- Scan through the video systematically for each event type
- Pay close attention to pipette volume displays
- Track tip changes and liquid movements
- Note container interactions and liquid transfers
- Use the procedure context to understand the purpose of each action

IMPORTANT REMINDERS:
- Video is 1 FPS: make educated interpolations between frames
- Don't hallucinate events - only report what's clearly visible
- Provide timestamp ranges, not just single timestamps
- Focus on the mechanical actions, not their interpretation

OUTPUT: Return a list containing all detected events of the four types above. Return an empty list if no events of a particular type are found."""

    return system_prompt, user_prompt


def create_analysis_events_prompt(
    procedure_context: str, objective_events: str
) -> tuple[str, str]:
    """
    THIRD PROMPT: Extract analysis events (warnings, well state changes).
    Uses context from procedure and objective events.
    """

    system_prompt = """You are an expert laboratory quality control specialist. You identify experimental warnings, errors, and track the completion status of experimental procedures."""

    user_prompt = f"""ANALYSIS EVENTS DETECTION TASK

You are analyzing the same laboratory video to identify warnings and track experimental progress. The video is recorded at 1 FPS, requiring educated interpolations between frames.

CONTEXT FROM PREVIOUS ANALYSIS:
PROCEDURE: {procedure_context}
OBJECTIVE EVENTS: {objective_events}

KEY CONSTRAINTS:
- Video is captured at 1 FPS - make reasonable inferences between frames
- Only report issues you can clearly observe
- Track actual completion status based on what you see
- Be conservative - don't create false warnings

YOUR TASK:
Identify instances of these analysis events:

1. WARNING EVENTS:
   - Technical errors (air bubbles, incorrect volumes, contamination risks)
   - Procedural mistakes (wrong reagents, incorrect destinations)
   - Safety concerns or poor technique
   - Equipment malfunctions or issues

2. WELL STATE EVENTS:
   - When wells/containers transition from incomplete to complete
   - When wells reach their target reagent composition
   - Changes in completion status based on experimental progress

ANALYSIS APPROACH:
- Review the objective events in context of the overall procedure
- Look for discrepancies between intended and actual actions
- Identify moments when wells reach their target state
- Watch for technical issues that could affect results
- Consider contamination risks and proper technique

WARNING DETECTION:
- Look for visible air bubbles in tips
- Check for volume mismatches (pipette setting vs. actual transfer)
- Note any liquid handling errors
- Identify contamination risks (tip reuse, cross-contamination)

WELL STATE TRACKING:
- Compare current well contents to target state from procedure
- Mark wells as complete when they contain all required reagents
- Note the reasoning for completion status changes

IMPORTANT REMINDERS:
- Video is 1 FPS: make educated inferences between frames
- Be conservative with warnings - only report clear issues
- Base completion status on observable evidence
- Don't create false positives

OUTPUT: Return lists of WarningEvent and WellStateEvent objects for all detected issues and state changes."""

    return system_prompt, user_prompt


# Helper function to format context for subsequent prompts
def format_procedure_context(procedure_result: ProcedureExtraction) -> str:
    """Format procedure extraction result for use in subsequent prompts"""
    return f"""
THINKING: {procedure_result.thinking}
TIMESTAMP RANGE: {procedure_result.timestamp_range}
GOAL WELLS: {[f"{w.well_id}: {[f'{r.name} ({r.volume_ul}µl)' for r in w.reagents]}" for w in procedure_result.goal_wells]}
REAGENT SOURCES: {procedure_result.reagent_sources}
""".strip()


def format_objective_events_context(events: List) -> str:
    """Format objective events for use in analysis prompt"""
    event_summaries = []
    for event in events:
        if hasattr(event, "new_setting_ul"):
            event_summaries.append(
                f"Pipette setting changed to {event.new_setting_ul}µl at {event.timestamp_range}"
            )
        elif hasattr(event, "reagent_name"):
            event_summaries.append(
                f"Aspirated {event.reagent_name} at {event.timestamp_range}"
            )
        elif hasattr(event, "reagent"):
            event_summaries.append(
                f"Dispensed {event.reagent.name} ({event.reagent.volume_ul}µl) at {event.timestamp_range}"
            )
        else:
            event_summaries.append(f"Tip change at {event.timestamp_range}")
    return "\n".join(event_summaries)
