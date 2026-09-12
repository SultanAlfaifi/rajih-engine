# Uncertainty-aware routing

This policy decides whether to collect public evidence, ask the human, expand diversity, critique, evaluate, decide, or stop inconclusively.

Implementation status: `v0.1.0` implements intake missingness, evidence coverage, and finalist-margin routing. Evaluation-disagreement and budget-reserve enforcement remain proposed extensions.

```mermaid
flowchart TB
    START["Current Decision Point"] --> SIGNALS["Estimate Observable Routing Signals<br/>Brief completeness · Evidence coverage · Evaluation disagreement<br/>Quality risk · Remaining budget"]

    SIGNALS --> A{"Missing public information?"}
    A -->|Yes| SCOUT["Call Scout"]
    SCOUT --> UPDATE["Update State & Audit Log"]
    UPDATE --> SIGNALS

    A -->|No| B{"Missing private or team information?"}
    B -->|Yes| HUMAN["Ask One High-value Human Question"]
    HUMAN --> UPDATE

    B -->|No| C{"Need more independent diversity?"}
    C -->|Yes| IDEATORS["Run Isolated Ideators"]
    IDEATORS --> MERGE["Merge Candidates Centrally"]
    MERGE --> UPDATE

    C -->|No| D{"Evidence coverage below τe?"}
    D -->|Yes| VERIFY["Scout Prior-art Verification"]
    VERIFY --> UPDATE

    D -->|No| E{"Evaluation disagreement or quality risk above τu?"}
    E -->|Yes| CRITIC["Call Independent Critic"]
    CRITIC --> UPDATE

    E -->|No| F{"Budget above reserve τb?"}
    F -->|Yes| JURY["Product Jury Scores Anonymized Finalists"]
    JURY --> MARGIN{"Finalist score margin Δ below τm?"}
    MARGIN -->|Yes| GATE["Human Decision Gate"]
    GATE --> DECIDE["Record Final Decision<br/>Evidence · Rationale · Cost"]
    MARGIN -->|No| DECIDE

    F -->|No| SUPPORT{"Any sufficiently supported candidate?"}
    SUPPORT -->|Yes| EARLY["Early Supported Decision"]
    EARLY --> DECIDE
    SUPPORT -->|No| INCONCLUSIVE["Stop Inconclusive<br/>Insufficient Evidence or Budget"]
```

The symbols `τe`, `τu`, `τb`, and `τm` are tunable thresholds. Record selected values with each run when these extensions are implemented.
