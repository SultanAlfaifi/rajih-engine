# RAJIH system architecture

RAJIH uses a central orchestrator and sparse specialist invocation. Specialists return bounded outputs to the orchestrator and do not share an open group chat.

```mermaid
flowchart TB
    U["Human / Hackathon Team"]
    O["RAJIH Orchestrator<br/>Planning · Routing · State · Decisions"]
    U <-->|"Goals · Constraints · High-value questions"| O

    subgraph AG["Sparse Specialist Layer"]
        S["Scout<br/>Research & Evidence"]
        I1["Grounded Ideator"]
        I2["Transformational Ideator"]
        I3["Demo-first Ideator"]
        C["Critic<br/>Independent Challenge"]
        J["Product Jury<br/>Rubric Scoring"]
    end

    O -->|"Public evidence gap"| S
    S -->|"Sourced evidence"| O
    O -->|"Isolated brief"| I1
    O -->|"Isolated brief"| I2
    O -->|"Isolated brief"| I3
    I1 -->|"Candidate"| O
    I2 -->|"Candidate"| O
    I3 -->|"Candidate"| O
    O -->|"Targeted review"| C
    C -->|"Falsifiable risks"| O
    O -->|"Anonymized finalists"| J
    J -->|"Scores · uncertainty · ties"| O

    subgraph MEM["Persistent Run State"]
        T[("Task Ledger")]
        P[("Progress Ledger")]
        E[("Evidence Store")]
        L[("Idea Lineage")]
        D[("Decision & Cost Log")]
    end

    O <--> T
    O <--> P
    O <--> E
    O <--> L
    O <--> D
```

The product jury supplies a structured evaluation signal. It does not replace external prior-art verification or the team's final judgment.

