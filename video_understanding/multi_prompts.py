"""
Multi-stage prompts for needle-in-haystack video analysis.
Each prompt focuses on specific event types and builds on previous results.
"""

from typing import Optional

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

YOUR TASK:
Analyze the entire video to understand:

1. GOAL STATE: What should each well/container contain when complete?
   - If there is a notebook, transcribe what each cell in the notebook says for each well position
   - If there is no notebook, transcribe what you see in the video

LAB NOTEBOOK INTERPRETATION:
- **Cells can contain MULTIPLE reagents** - look for comma-separated or space-separated entries
- **Reagent names can have single letters** (C, D, E, etc.)
- **Count only visible rows** - don't assume missing ones exist
- **Units specified once apply throughout**
- **Poor handwriting** - use context and patterns to interpret unclear letters

Example: Row "B", columns "1,2,3", cells contain "20X 20Y", "20X 20Z", "20Y 20Z":
- Well B1 gets 20µL of reagent X + 20µL of reagent Y
- Well B2 gets 20µL of reagent X + 20µL of reagent Z
- Well B3 gets 20µL of reagent Y + 20µL of reagent Z

CRITICAL INSTRUCTION:
- If you're given a notebook grid, transcribe exactly what's written in each cell
- Column 1 = well X1, Column 2 = well X2, Column 3 = well X3 (read left to right)
- The video shows HOW they executed it, the notebook shows WHAT the end result should be

OUTPUT: Provide ProcedureExtraction with your analysis of the overall experimental procedure.""".strip()

    return system_prompt, user_prompt


def create_objective_events_prompt(procedure_result: ProcedureExtraction) -> tuple[str, str]:
    """
    SECOND PROMPT: Extract core objective events (pipette settings, aspirations, dispensing, tip changes).
    Uses procedure context from first prompt.
    """

    system_prompt = """You are an expert laboratory analyst specializing in detailed pipetting event detection. You identify specific pipetting actions and equipment operations with precise timing."""

    procedure_json = procedure_result.model_dump_json(indent=2)
    user_prompt = f"""OBJECTIVE EVENTS DETECTION TASK

You are analyzing the same laboratory video to identify specific pipetting events. The video is recorded at 1 FPS, so you need to make educated interpolations between frames while being careful not to hallucinate.

CONTEXT FROM PROCEDURE ANALYSIS:
```json
{procedure_json}
```

CRITICAL: The procedure context above represents the INTENDED protocol. When visual details are unclear, TRUST the procedure and use logical reasoning to determine what must be happening.

KEY CONSTRAINTS:
- Video is captured at 1 FPS so you have to make educated interpolations between frames based on what's happened so far and the procedure context
- Make reasonable inferences about what happens between frames
- Only report events you can clearly observe or confidently infer
- Provide precise timestamp ranges for each event (be as specific as possible with timing since these events will be displayed as a HUD with other events)
- When unsure about tube selection, use the procedure context and logical inference:
  * If you've already used tube A, and the procedure calls for reagent B next, you're likely using tube B
  * The procedure sequence is your primary guide for determining reagent sources
- Double-check destination wells against the procedure - visual angles can be deceiving

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

REASONING APPROACH:
- When identifying tube/reagent sources: Use procedure sequence + visual confirmation
- When visual cues conflict with procedure: Trust the procedure and explain your reasoning
- When determining destinations: Cross-reference visual observation with procedure requirements
- Apply logical deduction: If you can't see which tube is being used, infer from the procedure sequence and previous actions

IMPORTANT REMINDERS:
- Video is 1 FPS: make educated interpolations between frames
- Don't hallucinate events - only report what's clearly visible
- Provide timestamp ranges, not just single timestamps (be as specific as possible with timing since these events will be displayed as a HUD with other events)
- Focus on the mechanical actions, not their interpretation
- When in doubt about locations/sources, defer to the procedure context

OUTPUT: Return a list containing all detected events of the four types above. Return an empty list if no events of a particular type are found."""

    return system_prompt, user_prompt


def create_analysis_events_prompt(
    procedure_result: ProcedureExtraction, objective_events_result: ObjectiveEventsList
) -> tuple[str, str]:
    """
    THIRD PROMPT: Extract analysis events (warnings, well state changes).
    Uses context from procedure and objective events.
    """

    system_prompt = """You are an expert laboratory quality control specialist. You identify experimental warnings, errors, and track the completion status of experimental procedures."""

    procedure_json = procedure_result.model_dump_json(indent=2)
    objective_events_json = objective_events_result.model_dump_json(indent=2)
    user_prompt = f"""ANALYSIS EVENTS DETECTION TASK

You are analyzing the same laboratory video to identify warnings and track experimental progress. The video is recorded at 1 FPS, requiring educated interpolations between frames.

CONTEXT FROM PREVIOUS ANALYSIS:

PROCEDURE:
```json
{procedure_json}
```

OBJECTIVE EVENTS:
```json
{objective_events_json}
```

KEY CONSTRAINTS:
- Video is captured at 1 FPS - make reasonable inferences between frames
- Only report issues you can clearly observe
- Track actual completion status based on what you see
- Be conservative - don't create false warnings
- Provide specific timestamp intervals for events since they will be displayed as a HUD with other events

YOUR TASK:
Identify instances of these analysis events:

1. WARNING EVENTS:
   - Environment/General warnings (report only ONCE at the beginning if present):
     * Poor lighting conditions that affect observation
     * Workspace organization issues
     * General procedural setup concerns
   - Technical errors (air bubbles, incorrect volumes, contamination risks)
   - Safety concerns or poor technique
   - Equipment malfunctions or issues
   - Contamination risks:
     * Tip reuse between different reagents without changing
     * Using contaminated tips or containers
     * Cross-contamination between wells

2. WELL STATE EVENTS:
   - Track EVERY reagent addition to each well (not just completion)
   - When wells/containers transition from incomplete to complete (is_complete=true)
   - When wells receive partial additions but remain incomplete (is_complete=false)
   - When wells reach their target reagent composition
   - Changes in completion status based on experimental progress

ANALYSIS APPROACH:
- Review the objective events in context of the overall procedure
- Look for discrepancies between intended and actual actions
- Identify moments when wells reach their target state
- Watch for technical issues that could affect results
- Consider contamination risks and proper technique

WARNING DETECTION:
- Environment/General (report ONCE at beginning only):
  * Check workspace setup and lighting conditions
  * Note any general procedural concerns
- Technical issues:
  * Look for visible air bubbles in tips
  * Check for volume mismatches (pipette setting vs. actual transfer)
  * Note any liquid handling errors
- Contamination risks (critical for accuracy):
  * Analyze the OBJECTIVE EVENTS timeline to identify contamination patterns
  * Look for tip reuse between different reagents without tip changes
  * Track when tips that contained one reagent are used for another reagent
  * Identify cross-contamination: pipetting into wells containing reagents, then going back to source containers
  * Example contamination pattern: Aspirate from reagent A → Dispense into well A1 → Aspirate from reagent B → Dispense into well A1 → Aspirate from reagent A again (now contaminated with B)
  * Watch for when contaminated tips return to source containers
  * Flag when contaminated containers are used

WELL STATE TRACKING:
- Track EVERY reagent addition to each well, not just final completion
- Create events for partial completions (is_complete=false) when wells receive some but not all required reagents
- Mark wells as complete (is_complete=true) when they contain all required reagents
- For each well state event, specify:
  * current_contents: List of reagents currently in the well
  * missing_reagents: List of reagents still needed to complete the well
- Compare current well contents to target state from procedure
- Note the reasoning for completion status changes
- Generate events for each step of well filling process

IMPORTANT REMINDERS:
- Video is 1 FPS: make educated inferences between frames
- Environment/General warnings: Report ONLY ONCE at the beginning if present
- Be conservative with warnings - only report clear, egregious issues
- Base completion status on observable evidence
- Generate well state events for EVERY reagent addition (both partial and complete)
- Track contamination carefully - this is critical for experimental validity
- Don't create false positives
- Use specific timestamp intervals to avoid HUD noise since these events will be displayed alongside other events

OUTPUT: Return lists of WarningEvent and WellStateEvent objects for all detected issues and state changes. Include both partial completions (is_complete=false) and final completions (is_complete=true) for comprehensive tracking.
- WarningEvent objects must include both warning_message and description fields
- WellStateEvent objects must include current_contents and missing_reagents fields"""

    return system_prompt, user_prompt
