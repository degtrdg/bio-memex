# Lab Video Analysis: State Specification for HUD Demo

## Problem Statement

We're building a real-time HUD overlay for lab procedAnd then from there, understanding that we put, like, that setting and that reagent inside of, well, a one or something. Right? And we have to remember all of from before if we put something else in a one because that's, like, the current state of the target. So those are that kind of fully encompasses the state the erase is right of an experiment like this. And for things like sensors. Warnings, we need to have remembered that, like I mean, if it's if it's We put this specific pet tip inside of reagent a, and we have not switched it out before going to reagent b. Right? Like, that would be, like, a warning. So you kinda need to remember that state in the previously in order to understand the current state that this is something that's wrong. I'm not sure if you get what what I mean. So we need to create, like, structured outputs regarding that.ure videos that tracks pipetting operations. The core challenge is understanding what happened in any video segment by maintaining critical state about:

1. **What the pipette can do** (current volume setting)
2. **What the pipette has done** (contamination history, last reagent)
3. **What's in each well** (cumulative reagents and volumes)
4. **What warnings exist** (cross-contamination, protocol deviations)

The previous batch-by-batch approach suffered from error propagation - by batch 57, the model was hallucinating about eppendorf tube contents because errors compounded across processing steps.

## Core State Requirements

### 1. Pipette State
**Critical for:** Understanding transfer volumes and contamination

```python
{
  "volume_setting": "30µL",           # Current pipette dial setting
  "last_reagent_aspirated": "Reagent A",  # What's currently in the tip
  "aspiration_volume": "30µL",        # How much was last aspirated
  "tip_contamination_history": [      # Full contamination chain
    {"reagent": "Reagent A", "timestamp": "00:05:23"},
    {"reagent": "Buffer", "timestamp": "00:07:15"}
  ],
  "tip_is_clean": false,              # Whether tip needs changing
  "aspirated_from_container": "eppendorf_tube_A"  # Source container
}
```

**Why needed:** 
- Volume setting determines how much is aspirated when tip enters container
- Contamination history enables cross-contamination warnings
- Knowing what's in the tip predicts what goes into target wells

### 2. Container State
**Critical for:** Tracking reagent sources and remaining volumes

```python
{
  "eppendorf_tube_A": {
    "reagent": "Reagent A",
    "initial_volume": "500µL",
    "remaining_volume": "440µL",      # Decreases with aspirations
    "label_visible": true
  },
  "eppendorf_tube_B": {
    "reagent": "Reagent B", 
    "initial_volume": "500µL",
    "remaining_volume": "500µL",
    "label_visible": true
  }
}
```

### 3. Well State  
**Critical for:** Tracking experiment progress and cumulative contents

```python
{
  "A1": {
    "reagents": [
      {"name": "Reagent A", "volume": "30µL", "added_at": "00:05:45"},
      {"name": "Reagent B", "volume": "20µL", "added_at": "00:08:12"}
    ],
    "total_volume": "50µL",
    "target_reagents": ["Reagent A", "Reagent B"],  # From protocol
    "is_complete": false
  },
  "A2": {
    "reagents": [],
    "total_volume": "0µL", 
    "target_reagents": ["Reagent C"],
    "is_complete": false
  }
}
```

### 4. Protocol State
**Critical for:** Detecting deviations and measuring progress

```python
{
  "protocol_steps": [
    {"step": 1, "action": "Add 30µL Reagent A to A1", "completed": true},
    {"step": 2, "action": "Add 30µL Reagent B to A2", "completed": false},
    {"step": 3, "action": "Add 20µL Buffer to A1", "completed": false}
  ],
  "current_step": 2,
  "completion_percentage": 33.3
}
```

### 5. Warning State
**Critical for:** Real-time feedback and error prevention

```python
{
  "active_warnings": [
    {
      "type": "cross_contamination",
      "severity": "high", 
      "message": "Tip used in Reagent A then Reagent B without changing",
      "affected_wells": ["A1", "A2"],
      "timestamp": "00:07:30"
    },
    {
      "type": "volume_discrepancy", 
      "severity": "medium",
      "message": "Dispensed 25µL but aspirated 30µL",
      "well": "A1",
      "timestamp": "00:05:50"
    }
  ],
  "warning_history": [...] // All past warnings
}
```

## State Dependencies

### Understanding Any Video Segment Requires:

1. **Pipette volume setting** at start of segment
   - Determines aspiration volume when tip enters container
   - Must persist across segments until changed

2. **Tip contamination history** 
   - Which reagents this tip has touched
   - When it was last changed/cleaned
   - Enables cross-contamination detection

3. **Well contents** up to this point
   - What reagents and volumes are already in each well
   - Critical for calculating cumulative state after new additions

4. **Protocol context**
   - What step we're currently on
   - What the intended targets are
   - Enables deviation detection

5. **Container state**
   - How much reagent remains in source containers
   - Which containers have been used
   - Enables volume tracking validation

## Key State Transitions

### Volume Setting Change
```
Pipette shows "20µL" → Update pipette.volume_setting = "20µL"
Next aspiration will be 20µL regardless of previous setting
```

### Aspiration Event  
```
Tip enters container + pipette.volume_setting = "30µL" 
→ pipette.aspiration_volume = "30µL"
→ pipette.last_reagent_aspirated = container.reagent
→ container.remaining_volume -= "30µL"
→ Add to tip_contamination_history
```

### Dispensing Event
```
Tip enters well + pipette has aspiration_volume = "30µL"
→ well.reagents.append({reagent, volume})
→ well.total_volume += volume
→ pipette.aspiration_volume = "0µL" 
→ Check for protocol compliance
```

### Tip Change
```
Tip ejected → pipette.tip_contamination_history = []
→ pipette.tip_is_clean = true
→ Clear any contamination warnings for this tip
```

## Critical Failure Modes to Avoid

1. **Volume Tracking Errors**: Losing track of pipette setting → wrong aspiration volumes
2. **Contamination Blindness**: Not tracking tip history → missing cross-contamination  
3. **Well State Drift**: Cumulative errors in well contents → wrong final state
4. **Protocol Confusion**: Not knowing current step → can't detect deviations

## Implementation Strategy

Use "needle in the haystack" queries on full video:

1. **Find all pipette setting changes** → Build volume setting timeline
2. **Find all aspiration events** → Link to volume settings for transfer volumes  
3. **Find all dispensing events** → Update well states
4. **Find all tip changes** → Reset contamination state
5. **Cross-reference with protocol** → Generate warnings and progress

This avoids error propagation by processing the complete video context for each query type.