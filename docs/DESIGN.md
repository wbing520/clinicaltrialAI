# ClinicalTrialAI — Architecture Design Document

> **Version:** 0.1 (Phase 1 baseline)
> **Author:** David
> **Status:** Active

---

## Table of Contents

1. [System context](#1-system-context)
2. [Security boundary model](#2-security-boundary-model)
3. [Layer 1 — EHR ingestion and de-identification](#3-layer-1--ehr-ingestion-and-de-identification)
4. [Layer 2 — Clinical knowledge graph and Graph RAG](#4-layer-2--clinical-knowledge-graph-and-graph-rag)
5. [Layer 3 — Multi-agent orchestration](#5-layer-3--multi-agent-orchestration)
6. [Layer 4 — Multi-modal LLM reasoning](#6-layer-4--multi-modal-llm-reasoning)
7. [Layer 5 — Compliance, audit, and security](#7-layer-5--compliance-audit-and-security)
8. [Data contracts between layers](#8-data-contracts-between-layers)
9. [Deployment topology](#9-deployment-topology)
10. [Performance targets](#10-performance-targets)
11. [Observability](#11-observability)
12. [Open design questions](#12-open-design-questions)

---

## 1. System context

### What the system does

ClinicalTrialAI takes a clinical research question as input (e.g., "Does drug X reduce 6-month
hospitalization in HFpEF patients over 65 with eGFR > 45?") and produces a simulated clinical trial
result as output, including: a CDISC-formatted trial protocol, a synthetic patient cohort with
longitudinal trajectories, endpoint analysis, adverse event predictions, and an IRB-ready simulation
report — all without enrolling a single real patient.

### What the system does NOT do

- It does not make clinical decisions or replace physician judgment.
- It does not replace real clinical trials. It improves their design before enrollment.
- It does not handle raw PHI. PHI is de-identified in an isolated enclave before any AI component
  receives data.
- It does not guarantee regulatory approval. It improves protocol quality and documents the simulation
  process in a way that supports regulatory review.

### External actors

| Actor | Interaction | Trust level |
|---|---|---|
| Clinical investigator | Submits research questions; reviews simulation outputs | Authenticated; INVESTIGATOR role |
| Data scientist | Configures pipelines; inspects cohort data | Authenticated; DATA_SCIENTIST role |
| System administrator | Infrastructure access only | Authenticated; ADMIN role; NO data access |
| Source EHR system | Provides FHIR R4 data via API | External; DUA-governed; no inbound connections |
| IRB | Reviews and approves data use; receives audit packages | External; receives exported reports |
| Regulatory reviewer | Reviews simulation methodology for FDA/IND submissions | External; receives exported reports |

---

## 2. Security boundary model

### Trust zones

```
┌─────────────────────────────────────────────────────────────────┐
│ ZONE 0 — External (untrusted)                                   │
│  EHR systems · Public internet · User browsers                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ FHIR R4 API (TLS 1.3 + OAuth 2.0)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ZONE 1 — Ingestion enclave (isolated, PHI present)              │
│  HAPI FHIR server · De-identification pipeline                  │
│  AWS Nitro Enclave or Azure Confidential Computing              │
│  AES-256 at rest (customer-managed KMS keys)                    │
│  No outbound connections except to Zone 2                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ De-identified OMOP bundles only
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ZONE 2 — PHI-free compute (private VPC)                         │
│  Neo4j graph · PostgreSQL · Redis · Agent services · LLM        │
│  All inter-service communication: mTLS (SPIFFE/SPIRE)           │
│  RBAC enforced at API gateway                                    │
│  Append-only audit ledger (QLDB) receives all events            │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Authenticated API (JWT + RBAC)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ZONE 3 — Output layer (read-only exports)                       │
│  Simulation reports · IRB packages · Audit log exports          │
│  All outputs reviewed by Judge agent before release             │
│  21 CFR Part 11 e-signature on exported packages                │
└─────────────────────────────────────────────────────────────────┘
```

### Key security invariants

1. **PHI never crosses the Zone 1→2 boundary.** OMOP-transformed data with de-identification applied
   is the only format allowed into Zone 2.
2. **No LLM prompt ever contains PHI.** The context assembler is a Zone 2 component and only receives
   de-identified graph context, synthetic patient data, and anonymized clinical notes.
3. **All Zone 2 inter-service traffic is mTLS.** Service identity is managed by SPIFFE/SPIRE with
   short-lived X.509 SVIDs. No service accepts connections without a valid SVID.
4. **Admins cannot access data.** IAM policies enforce infrastructure access ≠ data access. System
   administrators can manage compute resources but cannot query the graph or read simulation results.
5. **The audit ledger is append-only and cryptographically verifiable.** No application code can
   modify or delete audit records. AWS QLDB's SHA-256 digest chain provides tamper evidence.

---

## 3. Layer 1 — EHR ingestion and de-identification

### Data sources

| Source | Format | Ingestion method | Frequency |
|---|---|---|---|
| EHR (Epic, Cerner) | FHIR R4 Bundle | SMART on FHIR OAuth 2.0 API | Incremental daily |
| PACS / radiology | DICOM | DICOM C-MOVE + DICOMweb | On-demand per study |
| Genomics | VCF 4.2 | Secure file transfer (SFTP + PGP) | Per patient consent |
| Clinical notes | FHIR DocumentReference | FHIR API | Incremental daily |
| Reference databases | OMOP vocabularies, PubMed, CT.gov | Batch download | Monthly |

### De-identification pipeline design

```
FHIR Bundle (PHI)
       │
       ▼
┌──────────────────────┐
│  NER PHI detector    │  BioBERT clinical NER: identifies PHI in text fields
│  (spaCy + BioBERT)   │  Deterministic regex: dates, phone numbers, IDs, SSNs
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Track A: Safe Harbor │  Removes/generalizes all 18 HIPAA PHI identifier categories
│  (HIPAA 45 CFR §164) │  Dates → year only; ZIP → first 3 digits; Age → 5-year bin
└──────────┬───────────┘
           │  (optional, for analytic use cases)
           ▼
┌──────────────────────┐
│  Track B: Expert Det │  Retains quasi-identifiers (age bin, county, race/ethnicity)
│  (statistical model) │  Only when re-identification risk < 0.01 per NIST SP 800-188
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  OMOP CDM transform  │  Map FHIR concepts → OMOP standard concept IDs
│                      │  Validate against OHDSI OMOP CDM v5.4 schema
└──────────┬───────────┘
           │
           ▼
  De-identified OMOP Bundle
  → PostgreSQL (structured data)
  → Neo4j (graph load)
```

### Airflow DAG structure

`ingest_dag.py` runs daily at 02:00 UTC with the following task chain:
```
fhir_pull → validate_bundle → deid_track_a → [deid_track_b] → omop_transform
→ load_postgres → load_neo4j → update_vector_index → emit_audit_event
```

Failure at any step halts the pipeline and pages on-call. No partial loads.

### Synthetic augmentation

When the real cohort is too small for statistically powered simulation (target: n > 200 per arm),
`SyntheaAugmentor` generates synthetic patients conditioned on the real cohort's demographic and
comorbidity distribution using a GAN trained on the de-identified OMOP data. Synthetic patients
are flagged with `patient_source: synthetic` in the graph and are never mixed into real-patient
analytics without explicit researcher consent.

---

## 4. Layer 2 — Clinical knowledge graph and Graph RAG

### Graph schema

#### Node types

| Label | Primary key | Key properties |
|---|---|---|
| `Patient` | `person_id` (OMOP) | `age_bin`, `sex`, `race_ethnicity`, `patient_source` |
| `Condition` | `concept_id` (SNOMED-CT) | `concept_name`, `vocabulary_id`, `domain_id` |
| `Drug` | `concept_id` (RxNorm) | `concept_name`, `ingredient_concept_id`, `ATC_code` |
| `Measurement` | `concept_id` (LOINC) | `concept_name`, `unit_concept_id`, `normal_range` |
| `Procedure` | `concept_id` (SNOMED-CT) | `concept_name`, `domain_id` |
| `Trial` | `nct_id` | `phase`, `status`, `enrollment_target`, `primary_endpoint` |
| `Arm` | `arm_id` | `arm_type` (experimental/control), `randomization_ratio` |
| `Endpoint` | `endpoint_id` | `type` (primary/secondary), `measure`, `timepoint` |
| `AdverseEvent` | `concept_id` (MedDRA) | `severity_grade`, `soc_term`, `preferred_term` |
| `Biomarker` | `concept_id` (LOINC/HGNC) | `biomarker_type`, `gene_symbol`, `clinical_significance` |

#### Edge types

| Type | From | To | Key properties |
|---|---|---|---|
| `HAS_CONDITION` | Patient | Condition | `onset_date`, `status`, `source_concept_id` |
| `TAKES_DRUG` | Patient | Drug | `start_date`, `end_date`, `dose`, `route` |
| `HAS_MEASUREMENT` | Patient | Measurement | `value_as_number`, `measurement_date`, `unit` |
| `ENROLLED_IN` | Patient | Trial | `enrollment_date`, `arm_id`, `randomization_date` |
| `TESTS` | Trial | Drug | `dose_level`, `administration_route` |
| `MEASURES` | Trial | Endpoint | `assessment_schedule`, `statistical_method` |
| `MONITORS` | Trial | AdverseEvent | `grading_scale`, `stopping_rule` |
| `CAUSED_BY` | AdverseEvent | Drug | `causal_certainty`, `mechanism`, `source` |
| `STRATIFIED_BY` | Trial | Biomarker | `stratification_ratio`, `cutoff_value` |
| `EVIDENCED_BY` | Drug | LiteratureRef | `evidence_level`, `effect_size`, `study_design` |
| `SIMILAR_TO` | Patient | Patient | `similarity_score`, `comparison_features` |

#### Indexes and constraints (see `schema/constraints.cypher`)

```cypher
-- Uniqueness constraints
CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.person_id IS UNIQUE;
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.concept_id IS UNIQUE;
CREATE CONSTRAINT drug_concept IF NOT EXISTS FOR (d:Drug) REQUIRE d.concept_id IS UNIQUE;
CREATE CONSTRAINT trial_nct IF NOT EXISTS FOR (t:Trial) REQUIRE t.nct_id IS UNIQUE;

-- Full-text indexes for NLP entity linking
CREATE FULLTEXT INDEX concept_name_idx IF NOT EXISTS
  FOR (n:Condition|Drug|Measurement|Procedure|AdverseEvent)
  ON EACH [n.concept_name, n.synonyms];

-- Vector index for semantic node similarity (Neo4j 5.x)
CREATE VECTOR INDEX node_embedding_idx IF NOT EXISTS
  FOR (n:Patient|Drug|Condition) ON (n.embedding)
  OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' }};
```

### Graph RAG retrieval pipeline

```
Agent query (natural language or structured PICO)
       │
       ▼
┌──────────────────────────────────┐
│  Stage 1: Vector similarity      │
│  - Embed query with BioMedBERT   │
│  - FAISS ANN search → top-k=20  │
│    node candidates               │
└──────────────┬───────────────────┘
               │  candidate node IDs
               ▼
┌──────────────────────────────────┐
│  Stage 2: Subgraph expansion     │
│  - 2-hop Cypher traversal from   │
│    each candidate                │
│  - Filter by edge type relevance │
│  - Merge + deduplicate           │
└──────────────┬───────────────────┘
               │  subgraph (nodes + edges)
               ▼
┌──────────────────────────────────┐
│  Context builder                 │
│  - Serialize subgraph as         │
│    structured text (JSON-LD)     │
│  - Add ontology labels           │
│  - LLMLingua-2 compression       │
│    (target: 4K tokens)           │
└──────────────┬───────────────────┘
               │  structured context string
               ▼
          LLM prompt
```

---

## 5. Layer 3 — Multi-agent orchestration

### State machine design

The orchestrator is a LangGraph `StateGraph` where states map to trial simulation phases. Each state
has a defined entry action, a set of permissible agents, and typed exit conditions.

```
States:
  IDLE → PROTOCOL_DESIGN → COHORT_SELECTION → TRAJECTORY_SIMULATION
       → ADVERSARIAL_REVIEW → JUDGE_EVALUATION → EXPORT_READY → ARCHIVED

Transitions:
  IDLE → PROTOCOL_DESIGN           on: simulation.start(research_question)
  PROTOCOL_DESIGN → COHORT_SELECTION     on: trial_designer.protocol_approved()
  COHORT_SELECTION → TRAJECTORY_SIMULATION  on: patient_simulator.cohort_ready()
  TRAJECTORY_SIMULATION → ADVERSARIAL_REVIEW  on: patient_simulator.trajectories_complete()
  ADVERSARIAL_REVIEW → PROTOCOL_DESIGN   on: adversarial.challenge_issued()  [loop back]
  ADVERSARIAL_REVIEW → JUDGE_EVALUATION  on: adversarial.no_critical_issues()
  JUDGE_EVALUATION → PROTOCOL_DESIGN    on: judge.rubric_fail()              [loop back]
  JUDGE_EVALUATION → EXPORT_READY       on: judge.rubric_pass()
  EXPORT_READY → ARCHIVED              on: user.export_confirmed() + esignature.complete()
```

### Agent message contract

All inter-agent messages are `AgentMessage` Pydantic models:

```python
class AgentMessage(BaseModel):
    message_id: UUID
    simulation_id: UUID
    source_agent: AgentRole           # Enum: ORCHESTRATOR | DESIGNER | SIMULATOR | ADVERSARIAL | JUDGE
    target_agent: AgentRole
    message_type: MessageType         # Enum: TASK | RESULT | CHALLENGE | VERDICT | CHECKPOINT
    fhir_resources: list[dict]        # Zero or more FHIR R4 resource dicts
    structured_payload: dict          # Agent-specific typed payload (see each agent's schema)
    timestamp: datetime
    audit_hash: str                   # SHA-256 of message content (written to QLDB)
```

### Agent base class contract

```python
class BaseAgent(ABC):
    @abstractmethod
    async def run(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a result message."""

    async def _llm_call(self, prompt: str, context: str) -> str:
        """LLM call with Graph RAG context injection and audit logging."""

    async def _graph_query(self, query_fn: Callable, **kwargs) -> dict:
        """Execute a graph query and log access event."""

    async def _emit_audit_event(self, event: AuditEvent) -> None:
        """Write event to QLDB ledger. Blocks until confirmed."""
```

### Human-in-loop checkpoints

The orchestrator enforces three mandatory human review gates before advancing:

1. **Post-PROTOCOL_DESIGN:** Investigator must approve the CDISC protocol before cohort selection.
2. **Post-ADVERSARIAL_REVIEW:** If the adversarial agent issues a critical challenge (severity ≥ HIGH),
   a human reviewer must resolve it before the judge can evaluate.
3. **PRE-EXPORT:** 21 CFR Part 11 e-signature required from the principal investigator.

These gates are implemented as `asyncio.Event` waits in the orchestrator with configurable timeouts.
Expired timeouts move the simulation to `SUSPENDED` state and alert the investigator.

---

## 6. Layer 4 — Multi-modal LLM reasoning

### Model registry

| Task | Model | Hosting | Why this model |
|---|---|---|---|
| General clinical reasoning | GPT-4o (Azure OpenAI) | Azure (BAA) | Best-in-class reasoning; BAA available |
| Clinical text (fine-tuned) | Llama-3-70B + QLoRA | Self-hosted (A100) | Full data sovereignty; domain-adapted |
| Medical imaging | MedSAM ViT-H | Self-hosted | Open-source; best benchmark on CT/MRI |
| Genomics annotation | Ensembl VEP + ClinVar | REST API (no PHI) | Official variant annotation; authoritative |
| Context compression | LLMLingua-2 | Self-hosted | Reduces context 4–6× with <5% information loss |

### Prompt structure template

Every LLM call uses the following structured template. Order matters — the model's attention
weights are highest at the beginning and end of the context window.

```
[SYSTEM ROLE]
You are {agent_role_description}. You operate as part of a clinical trial simulation system.
Respond only within the scope of your role. All data you receive is de-identified.

[GRAPH CONTEXT]
{graph_rag_context}   ← up to 2,000 tokens of subgraph-derived structured text

[IMAGING SUMMARY]     ← only if imaging data is present
{imaging_summary}     ← 200-token summary from MedSAM encoder

[GENOMICS SUMMARY]    ← only if genomics data is present
{variant_cards}       ← structured variant card tokens

[TASK INSTRUCTION]
{specific_task}       ← agent-specific instruction

[OUTPUT FORMAT]
Respond as valid JSON conforming to schema: {output_schema_ref}
```

### QLoRA fine-tuning curriculum

The fine-tuning dataset is built from the de-identified EHR cohort via `dataset_builder.py` using
three task types, balanced 40/40/20:

1. **Eligibility matching (40%)** — input: patient summary + trial criteria; output: eligible/ineligible
   + reasoning chain.
2. **Adverse event extraction (40%)** — input: clinical note; output: structured AE list with severity,
   causality, and MedDRA coding.
3. **Protocol critique (20%)** — input: draft trial protocol; output: identified flaws with regulatory
   references.

Training runs for 3 epochs with `r=16, lora_alpha=32, lora_dropout=0.1` on 8× A100 40GB.

---

## 7. Layer 5 — Compliance, audit, and security

### Audit event taxonomy

Every significant system event is classified and written to the QLDB ledger:

| Category | Events |
|---|---|
| `DATA_ACCESS` | Graph query, FHIR API call, cohort export |
| `AGENT_ACTION` | Agent invocation, LLM call, tool use, inter-agent message |
| `SIMULATION_LIFECYCLE` | Simulation created, state transition, export, archive |
| `SECURITY` | Login, token refresh, RBAC decision, mTLS handshake failure |
| `COMPLIANCE` | IRB checkpoint, human review, e-signature |

### RBAC permission matrix

| Permission | INVESTIGATOR | DATA_SCIENTIST | ADMIN |
|---|---|---|---|
| Submit simulation | ✓ | ✓ | — |
| View cohort data (de-id) | ✓ | ✓ | — |
| View raw graph nodes | — | ✓ | — |
| Approve protocol checkpoint | ✓ | — | — |
| Export simulation report | ✓ | — | — |
| Configure pipeline parameters | — | ✓ | — |
| Manage infrastructure | — | — | ✓ |
| View audit log | ✓ | ✓ | ✓ |
| Delete audit records | — | — | — |

### 21 CFR Part 11 compliance checklist

- [x] Audit trail: append-only QLDB ledger with cryptographic verification
- [x] Electronic signatures: principal investigator must sign exports (OIDC + hardware key)
- [x] Access controls: RBAC with MFA enforced
- [x] System validation: documented validation plan, IQ/OQ/PQ protocols
- [ ] Computer system access: automated access review (quarterly) — *Phase 3*
- [ ] Record retention: 21-year retention policy on simulation records — *Phase 3*

---

## 8. Data contracts between layers

| Boundary | Format | Schema reference |
|---|---|---|
| Zone 0 → Zone 1 | FHIR R4 Bundle (JSON) | HL7 FHIR R4 specification |
| Zone 1 → Zone 2 | De-identified OMOP CDM (Parquet + JSON) | OHDSI OMOP CDM v5.4 |
| Graph load contract | OMOP → Neo4j node/edge mapping | `src/graph/schema/nodes.py` |
| Agent message contract | `AgentMessage` Pydantic model | `src/agents/shared/messages.py` |
| LLM prompt contract | Structured template (see §6) | `src/llm/prompt_engineering/templates.py` |
| API response contract | OpenAPI 3.1 spec | `src/api/schemas/responses.py` |
| Audit event contract | `AuditEvent` Pydantic model | `src/security/audit_ledger/ledger_schema.py` |
| Export package | FHIR DocumentBundle + CDISC dataset | IRB-defined format |

---

## 9. Deployment topology

### Kubernetes namespace structure

```
Namespace: ingestion      → ingestion pipeline, HAPI FHIR, Airflow workers
Namespace: graph          → Neo4j connector service, vector index service
Namespace: agents         → orchestrator, 4 agent services
Namespace: llm            → LLM inference (vLLM / Azure proxy), imaging encoder
Namespace: api            → FastAPI gateway, auth service
Namespace: security       → SPIRE server, OPA, QLDB writer
Namespace: monitoring     → Prometheus, Grafana, OpenTelemetry collector
```

Network policies enforce deny-all-by-default with explicit allow rules between namespaces.
The ingestion namespace has NO inbound rules from any other namespace.

### Sizing targets (Phase 1 pilot, 50K patient cohort)

| Component | Replicas | CPU | Memory |
|---|---|---|---|
| HAPI FHIR server | 2 | 2 vCPU | 4 GB |
| Airflow workers | 4 | 4 vCPU | 8 GB |
| Neo4j (AuraDS) | Managed | — | — |
| Orchestrator | 2 | 2 vCPU | 4 GB |
| Agent services (×4) | 2 each | 2 vCPU | 4 GB each |
| LLM proxy / vLLM | 1 (GPU node) | 16 vCPU | A100 40GB ×2 |
| FastAPI gateway | 3 | 2 vCPU | 2 GB |
| PostgreSQL (RDS) | Multi-AZ | 8 vCPU | 32 GB |
| Redis (ElastiCache) | 2-node cluster | — | 8 GB |

---

## 10. Performance targets

| Metric | Target | Rationale |
|---|---|---|
| Graph query p95 latency | < 500ms | Acceptable for interactive cohort exploration |
| Simulation end-to-end | < 30 min | Suitable for iterative protocol design sessions |
| Agent LLM call p95 | < 10s | Below investigator patience threshold |
| FHIR ingestion throughput | > 1,000 records/min | Supports daily incremental loads |
| Vector search p95 | < 200ms | Acceptable for RAG retrieval |
| API response p95 | < 2s | Standard web application SLA |
| Audit ledger write | < 100ms | Must not block agent execution |

---

## 11. Observability

### Metrics (Prometheus)

- `simulation_duration_seconds` — histogram by simulation phase
- `agent_llm_calls_total` — counter by agent + model
- `graph_query_duration_seconds` — histogram by query type
- `deid_phi_detections_total` — counter by PHI category (for pipeline QA)
- `audit_ledger_write_latency_seconds` — histogram

### Traces (OpenTelemetry → Jaeger)

Every simulation run carries a `simulation_id` trace context that propagates across all agent calls,
LLM invocations, graph queries, and audit writes. A complete simulation trace is inspectable
end-to-end in Jaeger.

### Alerts (Alertmanager)

- PHI detection in Zone 2 (severity: CRITICAL, page immediately)
- Audit ledger write failure (severity: CRITICAL, block simulation)
- Judge rubric score < 0.4 (severity: WARNING, notify investigator)
- Agent loop iteration count > 10 (severity: WARNING, possible runaway)
- Graph query p95 > 1s for 5 min (severity: WARNING)

---

## 12. Open design questions

These are unresolved as of v0.1 and need decisions before Phase 2 begins.

| Question | Options | Decision needed by |
|---|---|---|
| Multi-institution graph federation | Single Neo4j AuraDS vs. federated query (GraphQL Federation) | Month 4 |
| Adversarial agent loop termination | Max iteration count vs. convergence metric vs. human gate | Month 5 |
| Imaging modality scope for Phase 2 | CT + MRI only vs. add pathology whole-slide images | Month 5 |
| Fine-tuning data governance | Single institution only vs. federated learning across cohorts | Month 6 |
| Export format for regulatory submissions | CDISC SDTM only vs. add HL7 FHIR DocumentBundle | Month 8 |
