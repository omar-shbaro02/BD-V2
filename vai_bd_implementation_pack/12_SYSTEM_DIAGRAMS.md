# 12 — System and Decision Flow Diagrams

## 1. Business decision flow

```mermaid
flowchart TD
    A[Offer Profile] --> D[Decision Cycle Context]
    B[Target Market Boundary] --> D
    C[Capacity Envelope] --> D
    D --> E[Candidate Universe / Coverage]
    E --> F[Company Candidates]
    F --> G[Evidence Records]
    G --> H{Minimum Evidence / Hard Eligibility Gate}
    H -->|Proceed| I[Opportunity Assessment]
    H -->|Evidence Required| H1[Further Evidence]
    H -->|Hard Exclusion| H2[Excluded for Cycle]
    H -->|Contradiction Block| H3[Material Review]
    I --> J[Fit]
    I --> K[Need Hypothesis]
    I --> L[Decision-Owner Hypothesis]
    I --> M[Contactability]
    J --> N[Qualification Outcome]
    K --> N
    L --> N
    M --> N
    N -->|Qualified| O[Commercial Opportunity Case]
    N -->|Further Investigation| H1
    N -->|Indeterminate| H3
    O --> P[Pursuit Demand]
    O --> Q[Qualified Universe Snapshot]
    Q --> R[Canonical Pairwise Comparisons]
    R --> S[Comparative Priority State]
    P --> T[Capacity-Bounded Allocation]
    S --> T
    C --> T
    T --> U[Commercial Action Opportunity]
    U --> V{Release Readiness}
    V -->|Not Ready| V1[Hold / Reassess]
    V -->|Ready| W[Human Review]
    W --> X{Human Authorization}
    X -->|Approved| Y[Execution Eligibility Policy]
    X -->|Declined| Y1[No External Action]
    X -->|Returned| V1
    X -->|Pending| Y1
    Y --> Z[External Execution Disabled in Current Build]
```

## 2. Technical runtime flow

```mermaid
flowchart LR
    API[FastAPI Service] --> ORCH[Deterministic Orchestrator]
    ORCH --> DB[(Governed State DB)]
    ORCH --> A1[OpenAI Agent 1\nMarket Discovery]
    ORCH --> A2[OpenAI Agent 2\nEvidence Intelligence]
    ORCH --> A3[OpenAI Agent 3\nOpportunity Intelligence]
    ORCH --> A4[OpenAI Agent 4\nPortfolio & Allocation]
    ORCH --> A5[OpenAI Agent 5\nCommercial Action]
    A1 --> ORCH
    A2 --> ORCH
    A3 --> ORCH
    A4 --> ORCH
    A5 --> ORCH
    ORCH --> TRACE[Run / Prompt / Trace Audit]
    HUMAN[Authenticated Human] --> AUTH[Human Authorization Service]
    AUTH --> DB
    DB --> ORCH
```

## 3. Responsibility boundary

```mermaid
flowchart TB
    MD[Market Discovery\nFind Candidates]
    EI[Evidence Intelligence\nNormalize Evidence]
    OI[Opportunity Intelligence\nAssess One Opportunity]
    PA[Portfolio & Allocation\nCompare + Allocate]
    CA[Commercial Action\nPrepare Next Action]
    O[Orchestrator\nControl Process Only]
    H[Human\nAuthorize External Action]

    O --> MD
    O --> EI
    O --> OI
    O --> PA
    O --> CA
    CA --> H

    MD -. no qualification .-> X1[ ]
    EI -. no priority .-> X2[ ]
    OI -. no allocation .-> X3[ ]
    PA -. no authorization .-> X4[ ]
    CA -. no execution .-> X5[ ]
```

## 4. Revision and reassessment flow

```mermaid
flowchart TD
    R1[Current Upstream Revision] --> D1[Dependent Object Revision]
    D1 --> D2[Downstream Object Revision]
    N[New Material Revision] --> S[Supersedes R1]
    S --> C{Material impact on D1?}
    C -->|No| K[Keep D1 Current]
    C -->|Yes| RR[Mark D1 Reassessment Required]
    RR --> C2{Material impact on D2?}
    C2 -->|No| K2[Keep D2 Current]
    C2 -->|Yes| RR2[Mark D2 Reassessment Required]
```

## 5. Authorization revision isolation

```mermaid
flowchart LR
    R1[CAO R1 Current] --> A1[Human APPROVED R1]
    A1 --> E1[Eligible only if all policy checks pass]
    R2[Materially Revised CAO R2] --> S[Supersedes R1]
    S --> R1S[R1 Superseded]
    A1 --> HIST[Historical Approval Preserved]
    R1S --> NO1[No New R1 Execution]
    R2 --> A2[Fresh Human Authorization Required]
    A1 -. does not transfer .-> A2
```
