# Uncertainty-aware routing

This policy decides whether to collect public evidence, ask the human, expand diversity, critique, evaluate, decide, or stop inconclusively.

Implementation status: `v0.4.0` implements intake missingness, candidate-specific evidence coverage, finalist-margin routing, and an auditable route log. Evaluation-disagreement and budget-reserve enforcement are not implemented.

```mermaid
flowchart TB
    START["UNDERSTAND"] --> CHALLENGE{"Challenge present?"}
    CHALLENGE -->|No| CLARIFY["CLARIFY_BRIEF<br/>Human input required"]
    CHALLENGE -->|Yes| RESEARCH["RESEARCH<br/>Shared public context"]
    RESEARCH --> COMPLETE{"Required brief fields complete?"}
    COMPLETE -->|No| CLARIFY
    COMPLETE -->|Yes| DIVERGE["DIVERGE<br/>Isolated ideators"]
    DIVERGE --> CRITIQUE["CRITIQUE<br/>Candidate-specific risks"]
    CRITIQUE --> REFINE["REFINE<br/>Revision + parent_id"]
    REFINE --> VERIFY["VERIFY<br/>Candidate-specific evidence"]
    VERIFY --> JURY["CONVERGE<br/>Evidence-informed Jury"]
    JURY --> COVERAGE{"Evidence coverage complete?"}
    COVERAGE -->|No| GATE["HUMAN_GATE"]
    COVERAGE -->|Yes| MARGIN{"Winner margin below threshold?"}
    MARGIN -->|Yes| GATE
    MARGIN -->|No| DECIDE["DECIDE<br/>Persist winner + rationale"]
    GATE --> DECIDE
    DECIDE --> DONE["DONE"]
```

The finalist margin threshold is configurable in the router. Evidence coverage is deliberately conservative: every finalist must have at least one candidate-specific evidence record for automatic selection. These are routing heuristics, not calibrated statistical uncertainty.
