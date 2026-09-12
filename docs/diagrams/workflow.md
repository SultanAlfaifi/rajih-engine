# Workflow and state machine

The workflow can return to evidence collection or refinement. Brief clarification and the final human decision gate are distinct states.

```mermaid
stateDiagram-v2
    [*] --> Understand

    Understand --> Research: Public information missing
    Understand --> ClarifyBrief: Private or team information missing
    Understand --> Diverge: Brief sufficiently grounded

    Research --> Research: Evidence still insufficient and progress continues
    Research --> ClarifyBrief: Private constraint required
    Research --> Diverge: Evidence sufficient

    ClarifyBrief --> Diverge: High-value answer received or gap accepted
    Diverge --> Critique: Independent candidates generated

    Critique --> Refine: Repairable weakness found
    Critique --> Verify: Candidate already strong
    Critique --> Converge: Fatal candidates removed and finalists remain

    Refine --> Verify: Revision recorded with lineage
    Verify --> Research: Prior-art or evidence gap detected
    Verify --> Refine: Repairable feasibility issue
    Verify --> Converge: Finalists sufficiently supported

    Converge --> HumanGate: Product-jury scores are materially close
    Converge --> Decide: Stable leader exists
    HumanGate --> Decide: Human preference resolves consequential tie

    Decide --> Done: Decision, evidence, and cost recorded
    Done --> [*]
```

The implementation must also enforce bounded retries and stall detection. If required evidence remains insufficient, the run ends inconclusively instead of manufacturing a winner.

