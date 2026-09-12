# Workflow and state machine

Version 0.4 executes this bounded workflow. Brief clarification and the final human decision gate are distinct states.

```mermaid
stateDiagram-v2
    [*] --> Understand

    Understand --> Research: Challenge is present
    Understand --> ClarifyBrief: Private or team information missing

    Research --> ClarifyBrief: Private constraint required
    Research --> Diverge: Brief complete

    ClarifyBrief --> Diverge: High-value answer received or gap accepted
    Diverge --> Critique: Independent candidates generated

    Critique --> Refine: Risks recorded

    Refine --> Verify: Revision recorded with lineage
    Verify --> Converge: Candidate evidence snapshot recorded

    Converge --> HumanGate: Scores close or evidence missing
    Converge --> Decide: Stable leader exists
    HumanGate --> Decide: Human preference resolves consequential tie

    Decide --> Done: Decision and rationale recorded
    Done --> [*]
```

The route log records every transition. Missing candidate evidence forces a human gate instead of manufacturing an automatically supported winner. Retry and stall policies remain provider/runtime concerns in this alpha.

