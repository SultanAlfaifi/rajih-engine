# Research foundations

RAJIH is an engineering synthesis of ideas from multi-agent orchestration, LLM-assisted ideation, sparse collaboration, human steering, and evidence-aware evaluation. No single cited work proposes or validates the complete RAJIH architecture, and these sources do not establish that RAJIH outperforms alternative workflows for hackathons.

Links below point to primary paper records and were last checked on 2026-09-14.

| # | Work | Design principle used in RAJIH | Transfer boundary |
|---:|---|---|---|
| 1 | [Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks](https://arxiv.org/abs/2411.04468) (2024) | A central orchestrator plans, tracks progress, invokes specialists, and can replan after failure. | Its evaluations cover general agentic tasks, not hackathon ideation. RAJIH's state schema and routing rules are project-specific. |
| 2 | [Exploring the Design of Multi-Agent LLM Dialogues for Research Ideation](https://aclanthology.org/2025.sigdial-1.26/) (SIGDIAL 2025) | Role diversity and structured ideation, critique, and revision motivate RAJIH's separated Ideator, Critic, and Refiner stages. | The study concerns scientific ideation and relies substantially on automatic evaluation; it does not establish an optimal configuration for hackathons. |
| 3 | [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) (2025) | Explicit role contracts, centralized responsibility, output validation, and bounded termination reduce common multi-agent failure modes. | The failure taxonomy does not prescribe RAJIH's exact roles or prove that its implementation avoids every identified failure. |
| 4 | [SMoA: Improving Multi-agent Large Language Models with Sparse Mixture-of-Agents](https://arxiv.org/abs/2411.03284) (2024) | Selective specialist activation motivates hub-and-spoke routing instead of dense all-to-all agent communication. | RAJIH adopts the sparse-routing principle, not SMoA's aggregation method or reported empirical performance. |
| 5 | [Deep Ideation: Designing LLM Agents to Generate Novel Research Ideas on Scientific Concept Network](https://arxiv.org/abs/2511.02238) (2025) | Critic-guided evolution and lineage tracking motivate traceable revisions through `parent_id`. | The work targets scientific concept networks. Its reported results must not be presented as RAJIH performance. |
| 6 | [Perspectra: Choosing Your Experts Enhances Critical Thinking in Multi-Agent Research Ideation](https://arxiv.org/abs/2509.20553) (2025) | Targeted expertise and human-steerable decisions motivate specialist selection and explicit human gates. | RAJIH's observable thresholds and routing policy are independent engineering choices. |
| 7 | [Can LLM Agents Really Debate? A Controlled Study of Multi-Agent Debate in Logical Reasoning](https://arxiv.org/abs/2511.07784) (2025) | Independent first-round generation and model diversity help limit premature consensus and majority pressure. | The experiments use logical reasoning tasks; applying the result to creative ideation is a design motivation, not direct evidence. |
| 8 | [On the Limits of LLM-as-Judge for Scientific Novelty Assessment](https://arxiv.org/abs/2606.12071) (2026) | Novelty must not be inferred from an LLM score alone; external evidence and human judgment remain necessary. | The study evaluates scientific-question novelty, not product or hackathon novelty, and does not validate RAJIH's verification process. |
| 9 | [A Review of LLM-Assisted Ideation](https://arxiv.org/abs/2503.00946) (2025) | The broader ideation process should include problem framing, knowledge preparation, generation, refinement, evaluation, and selection. | A review can motivate process coverage but does not causally validate RAJIH's end-to-end sequence. |

## Architecture-to-source traceability

| RAJIH mechanism | Research foundation | RAJIH engineering adaptation |
|---|---|---|
| Central orchestration and persistent progress | Magentic-One | Local state machine, route log, explicit stage exits |
| `Ideate → Critique → Refine` | SIGDIAL 2025; Deep Ideation | Three isolated hackathon perspectives and traceable revisions |
| Sparse specialist routing | SMoA; Magentic-One | Orchestrator-mediated role calls with no open group chat |
| Explicit contracts and completion checks | Multi-agent failure taxonomy | JSON schemas, state invariants, finalist and decision validation |
| Independent first-round candidates | Controlled debate study | Ideators receive shared context but not one another's candidates |
| Targeted human intervention | Perspectra | Human gate for missing candidate evidence or close finalist scores |
| External novelty and prior-art checks | LLM-as-Judge limitations | Candidate-specific evidence with source and access metadata |
| Full ideation lifecycle | Review of LLM-assisted ideation | `UNDERSTAND → RESEARCH → DIVERGE → CRITIQUE → REFINE → VERIFY → CONVERGE → DECIDE` |

## Claim boundary

RAJIH currently supports the following engineering claim:

> RAJIH implements an inspectable, provider-flexible workflow that combines isolated ideation, critique, traceable refinement, candidate-specific evidence, rubric scoring, and human decision gates.

It does **not** currently claim that this combination is more creative, more accurate, less costly, or more effective than a single-agent or another multi-agent workflow. Such comparative claims require completed, independently reviewable evaluation evidence.

## Implementation references

The following documentation supports implementation but is not research evidence for RAJIH's effectiveness:

- [AutoGen Magentic-One documentation](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/magentic-one.html)
- [OpenCode agents](https://opencode.ai/docs/agents)
- [Codex authentication](https://developers.openai.com/codex/auth)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Claude Code subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [MultiAgent Research Ideator repository](https://github.com/g6000/MultiAgent-Research-Ideator)
- [Deep Ideation repository](https://github.com/kyZhao-1/Deep-Ideation)

Private hypotheses, experiment designs, benchmark data, unpublished results, and paper drafts are intentionally outside this public engineering repository.
