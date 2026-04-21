# ClinicalTrialAI — Project Plan

> **Mission:** Build an industry-ready, IRB-compliant AI platform that simulates and emulates clinical trials
> using real EHRs, a clinical knowledge graph, multi-agent orchestration, and multi-modal LLMs —
> compressing trial design cycles and surfacing safety signals before a single patient is enrolled.

---

## Table of Contents

1. [Why we are building this](#1-why-we-are-building-this)
2. [Core design principles](#2-core-design-principles)
3. [Architecture rationale](#3-architecture-rationale)
4. [Build phases](#4-build-phases)
5. [Milestone schedule](#5-milestone-schedule)
6. [Risk register](#6-risk-register)
7. [Funding and publication strategy](#7-funding-and-publication-strategy)
8. [Decision log](#8-decision-log)

---

## 1. Why we are building this

### The problem

Clinical trials are broken at the infrastructure level:

| Metric | Reality |
|---|---|
| Average cost to bring a drug to market | **$2.6 billion** |
| Typical timeline from design to approval | **10–15 years** |
| Phase II/III trials that fail | **>50%** |
| Primary cause of late-stage failure | Poor cohort design, missed safety signals, insufficient power |

Most failures are *predictable in silico* given sufficient patient data and clinical knowledge. They happen
anyway because the tools to run that analysis before enrolling patients either do not exist or are locked
inside proprietary pharma infrastructure inaccessible to academic researchers and small biotechs.

### The opportunity

Three converging capabilities make this platform buildable now, for the first time:

1. **Real EHR interoperability** — FHIR R4 adoption across Epic, Cerner, and most large health systems
   means structured, queryable patient data is finally accessible via standard APIs under appropriate IRB
   and data use agreements.

2. **Graph-structured clinical knowledge** — OMOP CDM, SNOMED-CT, LOINC, RxNorm, and MedDRA provide
   ontological scaffolding that turns a flat patient record into a semantically rich knowledge node.
   Neo4j's graph traversal lets us reason across drug-disease-biomarker-outcome relationships in ways
   that relational databases and flat-document RAG cannot.

3. **Multi-modal foundation models** — Clinical LLMs (GatorTron, BioMedBERT, fine-tuned Llama-3),
   medical imaging encoders (MedSAM, CONCH), and genomics annotation pipelines (Ensembl VEP) can now be
   composed into a multi-modal reasoning stack that mirrors how a real trial statistician thinks.

### Why now, and why us

- David's background in clinical trial systems and large-scale data engineering gives us the domain
  credibility to navigate IRB approvals and EHR data use agreements — the hardest non-technical barrier.
- The multi-agent Judge/Adversarial design pattern developed for CyberRangeAI (AIED 2026) maps directly
  onto trial simulation needs, giving us a validated architecture and a cross-domain research narrative
  that strengthens grant applications.
- No open-source platform currently combines Graph RAG + multi-agent simulation + regulatory compliance
  in a single deployable system. The closest academic work is single-modal or uses only synthetic data.

---

## 2. Core design principles

These principles are *architectural constraints*, not aspirations. Every technical decision should be
tested against them.

### P1 — Safety first, always
PHI never enters an LLM context window. De-identification runs in an isolated compute enclave before any
AI component touches the data. This is non-negotiable and implemented at the infrastructure level, not
via application-layer policy.

### P2 — Auditability by design
Every agent action, every LLM prompt and response, every data access event is written to an append-only
ledger. A regulatory reviewer must be able to reconstruct the full provenance of any simulation output
from the audit log alone. This satisfies 21 CFR Part 11 and is required for any FDA submission package.

### P3 — Ontological grounding over free text
Clinical concepts are always represented as standard ontology IDs (SNOMED-CT, LOINC, RxNorm) before
being stored in the graph or passed to agents. Free-text clinical notes are a secondary input that feeds
entity extraction, not the source of truth. This prevents hallucination-driven reasoning and makes
outputs reproducible.

### P4 — Agent contracts over chatbots
Agent-to-agent communication uses Pydantic-typed message schemas backed by FHIR resource types. Agents
are not free-form LLM chatbots — they are typed state machine transitions with defined inputs, outputs,
and failure modes. The orchestrator enforces these contracts.

### P5 — Deployable from day one
Every component ships with a Helm chart and a Terraform module. The system must be deployable to a
university research computing cluster, AWS GovCloud, or Azure Government without rewriting application
code. This is what separates a research prototype from an industry-ready product.

### P6 — Modularity with semantic coupling
Each of the five layers is independently deployable and testable. But they share a unified ontology
layer (OMOP + FHIR resource types) so that swapping out Neo4j for ArangoDB, or GPT-4o for Llama-3,
does not break the semantic contracts between layers.

---

## 3. Architecture rationale

### Why five layers, not microservices?

The five-layer model (ingestion → graph → agents → LLM → compliance) reflects the *data flow* of a real
clinical trial simulation, not an arbitrary decomposition. Each layer transforms the data in a
semantically meaningful way:

```
Raw EHR (PHI) → De-identified OMOP → Knowledge graph → Agent reasoning → LLM inference → Audited output
```

We chose this layered model over a pure microservices mesh because:
- **Testability**: Each layer has clear input/output contracts (FHIR Bundles in, FHIR Bundles out).
- **Compliance boundary**: The de-identification layer creates a hard security perimeter. Everything
  above it is PHI-free.
- **Incremental delivery**: We can ship Layer 1+2 as a standalone clinical data warehouse while Layers
  3–5 are under development. Each layer delivers research value independently.

### Why Graph RAG over flat-document RAG?

Flat-document RAG (embedding clinical guidelines as text chunks) fails for clinical trial simulation
because:
- It has no mechanism to enforce referential integrity. A drug can be "associated with" a safety signal
  without that association being traversable and verifiable.
- It cannot answer multi-hop queries: "Find patients eligible for this protocol who have a biomarker
  that predicts resistance to the intervention drug."
- It cannot represent the *structure* of a trial protocol (arms, strata, randomization rules, endpoints)
  in a way agents can programmatically query.

Graph RAG solves all three. The knowledge graph stores ontological relationships as first-class edges.
Cypher/AQL traversal gives agents structured, verifiable answers. Vector similarity search over node
embeddings handles fuzzy semantic retrieval. The two stages compose naturally.

### Why four specialized agents over one general agent?

A single general-purpose LLM agent tasked with "design and evaluate a clinical trial" will optimize for
the most likely/average outcome and systematically underweight edge cases, minority populations, and rare
adverse events. Specialization forces each concern to be addressed explicitly:

| Agent | Why specialized | What fails without it |
|---|---|---|
| Trial designer | Protocol synthesis requires deep PICO/CDISC knowledge | Generic LLM produces protocols that fail regulatory review |
| Patient simulator | Trajectory modeling requires time-series + survival models | Static cohort snapshots miss longitudinal safety signals |
| Adversarial agent | Bias/edge-case detection requires red-team framing | Evaluation anchors on the most common patient profile |
| Judge/auditor | Validity scoring requires a rubric-grounded LLM | No objective pass/fail gate before output export |

The orchestrator is not a fifth agent — it is a typed state machine that routes tasks and enforces
handoff contracts. This is implemented in LangGraph so the state transitions are explicit, inspectable,
and replayable.

### Why OMOP CDM as the canonical data model?

OMOP CDM is the standard for observational clinical research. It is:
- **Vendor-neutral**: Epic, Cerner, and most major EHRs can export to OMOP via certified ETL tools.
- **Ontology-aligned**: Every concept maps to a standard vocabulary ID (SNOMED, LOINC, RxNorm). This is
  what makes the knowledge graph coherent across heterogeneous source systems.
- **Community-maintained**: The OHDSI network has validated OMOP mappings across 330M+ patient records.
  We inherit that validation rather than building our own.

FHIR R4 is used for real-time ingestion and agent message payloads. OMOP CDM is used for the graph
substrate and longitudinal analytics. The two coexist via a well-defined FHIR-to-OMOP ETL layer.

### Why differential privacy at the aggregation layer?

Individual-level de-identification (HIPAA Safe Harbor / Expert Determination) is necessary but not
sufficient. Re-identification attacks on de-identified datasets are well-documented, especially for rare
conditions or unusual combinations of demographics and diagnoses. ε-DP (ε ≤ 1.0) applied at the
aggregation layer adds a mathematically provable privacy guarantee to any population-level output the
system produces. This is required for any public research outputs or shared simulation results.

---

## 4. Build phases

### Phase 1 — Data foundation (Months 1–4)

**Goal:** IRB-approved EHR access, a running de-identification pipeline, and a loaded OMOP+Neo4j graph.

**Deliverables:**
- IRB protocol submitted and approved for EHR data access
- HIPAA data use agreement executed with at least one health system
- FHIR R4 ingestion pipeline (HAPI FHIR server + Apache Airflow DAGs)
- De-identification pipeline running in AWS Nitro Enclave or equivalent
- OMOP CDM transform complete for pilot cohort (target: 50,000 patients)
- Neo4j graph loaded with OMOP nodes + SNOMED/LOINC/RxNorm ontology edges
- Baseline graph query benchmarks (p95 Cypher traversal latency)

**Why this first:**
Without real, de-identified patient data in the graph, everything else is a demo. The IRB and DUA
processes are the longest lead-time items in the entire project — starting them on day 1 is critical.
The data foundation also de-risks the LLM fine-tuning in Phase 2: we need the cohort data to build
the training curriculum.

**Research output:** Submit a data paper describing the de-identification pipeline architecture to JAMIA
or the Journal of Biomedical Informatics.

---

### Phase 2 — Agent prototype (Months 5–8)

**Goal:** A working multi-agent simulation loop on the de-identified cohort.

**Deliverables:**
- LangGraph orchestrator with typed state machine (trial phases as states)
- Trial designer agent (GPT-4o + PICO tool + CDISC Protocol Representation Model output)
- Patient simulator agent (Synthea augmentation + DeepHit trajectory model)
- Adversarial agent (red-team prompting framework + demographic parity checker)
- Judge/auditor agent (multi-dimension rubric: power, equity, regulatory alignment)
- Redis + PostgreSQL shared state store with FHIR-typed message payloads
- LLM fine-tuning: QLoRA (4-bit + LoRA adapters) on de-identified clinical notes
- End-to-end simulation run on a synthetic Phase II trial design

**Why this order:**
The orchestrator and state machine must exist before any subagent, because the subagents are tested
*in context* — their outputs are only meaningful when connected to the shared state. Fine-tuning
happens in parallel with agent development and feeds the patient simulator and trial designer.

**Research output:** Submit a conference paper on the multi-agent architecture to AMIA 2026 Annual
Symposium or NeurIPS Clinical AI Workshop.

---

### Phase 3 — Full integration and hardening (Months 9–12)

**Goal:** Production-ready platform with complete Graph RAG, security hardening, and a validated
simulation study.

**Deliverables:**
- Full Graph RAG integration: FAISS vector index + Cypher subgraph retrieval fused into agent context
- Medical imaging modality: MedSAM encoder + cross-modal MLP projector
- Genomics modality: ClinVar/VEP annotation pipeline + variant card tokenization
- Zero-trust network (private VPC, mTLS, SPIFFE/SPIRE service identity)
- Append-only audit ledger (AWS QLDB or Hyperledger Fabric)
- 21 CFR Part 11 e-signature workflow for simulation outputs
- Validation study: run platform on a retrospective trial design where the real outcome is known;
  measure protocol quality, cohort coverage, and adverse event detection accuracy
- Terraform + Helm IaC for single-command deployment to EKS/AKS

**Why this order:**
Graph RAG and multi-modal fusion are the highest-complexity integrations. Attempting them in Phase 1 or
2 would block the simpler, higher-value agent work. Security hardening is intentionally last because it
is most efficiently done once the attack surface is fully defined — hardening an incomplete system
creates false confidence.

**Research output:** Submit the full platform paper to Nature Digital Medicine or JAMIA. Submit the
validation study to a clinical trials methods journal (Clinical Trials, Contemporary Clinical Trials).

---

## 5. Milestone schedule

```
Month:   1    2    3    4    5    6    7    8    9    10   11   12
         |    |    |    |    |    |    |    |    |    |    |    |

IRB/DUA: [====================]
FHIR:         [========]
De-id:              [========]
OMOP/Graph:              [====]
Orchestrator:                  [====]
Agents:                        [============]
Fine-tune:                          [========]
Graph RAG:                                    [====]
Multi-modal:                                       [========]
Security:                                               [====]
IaC:                                                    [====]
Validation:                                                  [==]

AMIA paper:                           [submit]
Nature DM:                                                       [submit]
```

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IRB approval delayed >4 months | Medium | High | Begin IRB prep in Month 0; identify backup synthetic-only path |
| EHR data use agreement not executed | Medium | High | Target 2+ health systems; use Synthea as fallback for Phase 1 |
| LLM fine-tuning underperforms on clinical text | Medium | Medium | Benchmark against BioMedBERT baseline; use RAG augmentation as fallback |
| Graph query latency exceeds 500ms p95 | Low | Medium | Shard Neo4j by patient subgraph; add Redis cache layer |
| Azure OpenAI BAA revoked or pricing changes | Low | Medium | Maintain self-hosted Llama-3 as hot standby; design inference layer as swappable |
| Adversarial agent generates unsafe protocol variants | Low | High | Constitutional AI guardrails; human-in-loop checkpoint before any output export |
| Re-identification attack on de-identified cohort | Very Low | Very High | ε-DP at aggregation layer; quarterly re-identification risk assessment |
| Key personnel departure | Low | High | All design decisions documented in this repo; no single point of knowledge |

---

## 7. Funding and publication strategy

### NIH R21 (mechanism: exploratory/developmental)

**Target:** NLM (National Library of Medicine) or NCATS (National Center for Advancing Translational
Sciences).

**Narrative hook:** "We propose the first open-source platform that combines Graph RAG over real EHR
data with multi-agent LLM simulation to improve the design quality of Phase II clinical trials, with
particular focus on underrepresented populations."

**Estimated budget:** $275K over 2 years. Phase 1 (IRB + data foundation) provides the preliminary data
required for the R21 application, which should be submitted at the end of Month 6.

### NSF Convergence Accelerator

**Track:** AI in support of biomedical and health innovation.

**Narrative hook:** "Cross-domain contribution: the Red/Blue/Judge multi-agent pattern validated in
clinical simulation is architecturally identical to the pattern used in AI-powered cybersecurity
education (CyberRangeAI, AIED 2026), demonstrating that adversarial multi-agent evaluation is a
generalizable framework for high-stakes AI safety across domains."

### ARPA-H

**Target:** Clinical AI translation track. ARPA-H funds high-risk, high-reward platforms. The
regulatory alignment story (21 CFR Part 11, ICH E6(R3)) is directly relevant to their mandate.

### Industry partnerships

- Phase II trial design consulting with mid-size biotech (target: $150–300K/year)
- Hospital system licensing for cohort feasibility modeling
- Regulatory submission support tooling for FDA/EMA IND-enabling studies

---

## 8. Decision log

Decisions that were actively considered and resolved. Recorded here so they are not re-litigated.

| Date | Decision | Alternatives considered | Rationale |
|---|---|---|---|
| 2026-04 | Graph DB: Neo4j AuraDS | ArangoDB, Amazon Neptune | Neo4j has the best OMOP community tooling (OHDSI); AuraDS removes self-managed ops burden |
| 2026-04 | Vector index: pgvector (Phase 1), FAISS (Phase 3) | Pinecone, Weaviate, Qdrant | pgvector runs in existing Postgres; FAISS for billion-scale when needed; avoids external SaaS dependency |
| 2026-04 | Agent framework: LangGraph | AutoGen, CrewAI, custom | LangGraph's explicit state machine maps directly to trial phase transitions; AutoGen is a fallback for multi-model dialogue scenarios |
| 2026-04 | LLM hosting: Azure OpenAI (BAA) for research, self-hosted Llama-3 for production | AWS Bedrock, Anthropic Claude API | Azure OpenAI has a signed HIPAA BAA; self-hosted Llama-3 on A100s gives full data sovereignty for production PHI-adjacent workloads |
| 2026-04 | Pipeline orchestration: Apache Airflow | Prefect, Dagster | Airflow has the largest community and native support on EKS; team has existing Airflow expertise |
| 2026-04 | IaC: Terraform + Helm | Pulumi, CDK | Terraform is lingua franca for cloud infrastructure; Helm for Kubernetes app packaging; both are hiring-friendly |
| 2026-04 | Audit ledger: AWS QLDB | Hyperledger Fabric, custom Postgres append-only | QLDB is fully managed, cryptographically verifiable, and satisfies 21 CFR Part 11 without operational overhead; Fabric reserved for multi-institution consortium deployment |
