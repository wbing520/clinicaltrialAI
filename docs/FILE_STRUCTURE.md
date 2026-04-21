# ClinicalTrialAI — File Structure

Every directory and file listed here has an explicit reason for existing at that path.
The structure follows domain-driven design: folders map to bounded contexts, not technical layers.

---

```
clinicaltrial-ai/
│
├── README.md                          # Project overview, quick-start, contributor guide
├── SECURITY.md                        # Security policy, responsible disclosure
├── LICENSE                            # Apache 2.0 (maximizes academic/industry adoption)
├── .env.example                       # Required env vars with descriptions (no secrets)
├── .gitignore                         # Never commit .env, *.pem, patient data, model weights
├── pyproject.toml                     # Python project metadata, dependencies (Poetry)
├── Makefile                           # Shortcut targets: make dev, make test, make deploy
│
├── docs/                              # All human-facing documentation
│   ├── PLAN.md                        # This project plan (you are here)
│   ├── DESIGN.md                      # Architecture design document
│   ├── FILE_STRUCTURE.md              # This file
│   ├── SECURITY_MODEL.md              # Threat model, trust boundaries, zero-trust design
│   ├── REGULATORY_COMPLIANCE.md       # HIPAA, 21 CFR Part 11, ICH E6(R3) alignment notes
│   ├── IRB_PROTOCOL_TEMPLATE.md       # IRB application language and data access templates
│   ├── ONBOARDING.md                  # New developer onboarding guide
│   ├── adr/                           # Architecture Decision Records (lightweight)
│   │   ├── 001-graph-database.md
│   │   ├── 002-vector-index-strategy.md
│   │   ├── 003-agent-framework.md
│   │   ├── 004-llm-hosting.md
│   │   └── 005-audit-ledger.md
│   └── diagrams/                      # Architecture diagrams (SVG source + exported PNG)
│       ├── system-overview.svg
│       ├── data-flow.svg
│       ├── agent-state-machine.svg
│       └── security-boundary.svg
│
├── src/                               # All application source code
│   │
│   ├── ingestion/                     # Layer 1 — EHR ingestion & de-identification
│   │   ├── __init__.py
│   │   ├── fhir/
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # FHIR R4 REST client (Epic, Cerner, SMART on FHIR)
│   │   │   ├── resources.py           # Typed FHIR resource models (Patient, Encounter, etc.)
│   │   │   └── validator.py           # FHIR resource schema validation
│   │   ├── dicom/
│   │   │   ├── __init__.py
│   │   │   ├── loader.py              # DICOM file ingestion + metadata extraction
│   │   │   └── anonymizer.py          # DICOM tag scrubbing (DICOM PS3.15 Annex E)
│   │   ├── genomics/
│   │   │   ├── __init__.py
│   │   │   ├── vcf_parser.py          # VCF file parsing + allele normalization
│   │   │   └── vep_annotator.py       # Ensembl VEP annotation pipeline wrapper
│   │   ├── deid/
│   │   │   ├── __init__.py
│   │   │   ├── safe_harbor.py         # HIPAA Safe Harbor: remove all 18 PHI identifiers
│   │   │   ├── expert_determination.py # Statistical disclosure limitation (quasi-identifier model)
│   │   │   ├── ner_pipeline.py        # BioBERT/spaCy NER for PHI detection in clinical notes
│   │   │   └── differential_privacy.py # ε-DP aggregation (ε ≤ 1.0, Laplace/Gaussian mechanism)
│   │   ├── omop/
│   │   │   ├── __init__.py
│   │   │   ├── etl.py                 # FHIR → OMOP CDM transform (Rabbit-in-a-Hat mappings)
│   │   │   ├── vocabulary.py          # SNOMED-CT / LOINC / RxNorm concept lookup
│   │   │   └── cdm_models.py          # SQLAlchemy ORM for OMOP CDM v5.4 tables
│   │   └── pipelines/
│   │       ├── __init__.py
│   │       ├── ingest_dag.py          # Airflow DAG: FHIR pull → de-id → OMOP transform
│   │       └── genomics_dag.py        # Airflow DAG: VCF ingest → VEP annotate → graph load
│   │
│   ├── graph/                         # Layer 2 — Knowledge graph & Graph RAG
│   │   ├── __init__.py
│   │   ├── schema/
│   │   │   ├── __init__.py
│   │   │   ├── nodes.py               # Node type definitions: Patient, Drug, Condition, Trial, etc.
│   │   │   ├── edges.py               # Edge type definitions: enrolled_in, tests, caused_by, etc.
│   │   │   └── constraints.cypher     # Neo4j uniqueness constraints + indexes (run once at setup)
│   │   ├── loaders/
│   │   │   ├── __init__.py
│   │   │   ├── omop_loader.py         # Load OMOP CDM rows → Neo4j nodes + edges
│   │   │   ├── ontology_loader.py     # Load SNOMED/LOINC/RxNorm hierarchy into graph
│   │   │   └── literature_loader.py   # Load PubMed + ClinicalTrials.gov into graph
│   │   ├── queries/
│   │   │   ├── __init__.py
│   │   │   ├── eligibility.py         # Cypher: match patients to trial inclusion/exclusion criteria
│   │   │   ├── drug_safety.py         # Cypher: k-hop AE signal traversal from drug nodes
│   │   │   ├── biomarker.py           # Cypher: biomarker → cohort stratification queries
│   │   │   └── subgraph.py            # Generic k-hop subgraph retrieval for RAG context
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   ├── node_encoder.py        # BioMedBERT node embedding generation
│   │   │   ├── faiss_index.py         # FAISS index build + similarity search
│   │   │   └── pgvector_index.py      # pgvector index (Phase 1 fallback)
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── retriever.py           # Two-stage: vector search → subgraph expansion
│   │       ├── context_builder.py     # Merge subgraph + vector hits → structured LLM context
│   │       └── compression.py         # LLMLingua-2 dynamic context compression
│   │
│   ├── agents/                        # Layer 3 — Multi-agent orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator/
│   │   │   ├── __init__.py
│   │   │   ├── state_machine.py       # LangGraph state machine: trial phase transitions
│   │   │   ├── router.py              # Task routing logic: which agent handles which state
│   │   │   └── checkpoints.py         # Human-in-loop checkpoint gates (IRB, safety review)
│   │   ├── trial_designer/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Trial designer agent: PICO → CDISC protocol
│   │   │   ├── pico_parser.py         # Extract Population/Intervention/Comparator/Outcome
│   │   │   ├── protocol_builder.py    # CDISC Protocol Representation Model output
│   │   │   └── prompts/
│   │   │       ├── system.txt
│   │   │       └── protocol_synthesis.txt
│   │   ├── patient_simulator/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Patient simulator agent: cohort generation
│   │   │   ├── cohort_selector.py     # Graph query → eligible patient set
│   │   │   ├── trajectory_model.py    # DeepHit / transformer time-series trajectory simulation
│   │   │   ├── synthea_augmentor.py   # Synthea wrapper: expand real cohort with synthetic patients
│   │   │   └── prompts/
│   │   │       ├── system.txt
│   │   │       └── cohort_generation.txt
│   │   ├── adversarial/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Adversarial agent: red-team protocol design
│   │   │   ├── bias_detector.py       # Demographic parity + representation gap analysis
│   │   │   ├── edge_case_generator.py # Rare comorbidity + boundary-condition patient generation
│   │   │   └── prompts/
│   │   │       ├── system.txt
│   │   │       └── red_team.txt
│   │   ├── judge/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Judge/auditor agent: rubric scoring + pass/fail gate
│   │   │   ├── rubric.py              # Scoring dimensions: power, equity, regulatory, safety
│   │   │   ├── regulatory_checker.py  # ICH E6(R3) + 21 CFR Part 312 alignment checks
│   │   │   └── prompts/
│   │   │       ├── system.txt
│   │   │       └── evaluation_rubric.txt
│   │   └── shared/
│   │       ├── __init__.py
│   │       ├── messages.py            # Pydantic message schemas (FHIR-typed agent payloads)
│   │       ├── state_store.py         # Redis (ephemeral) + Postgres (persistent) state client
│   │       └── base_agent.py          # Abstract base class: LLM call, Graph RAG, logging
│   │
│   ├── llm/                           # Layer 4 — Multi-modal LLM reasoning
│   │   ├── __init__.py
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── azure_openai.py        # Azure OpenAI client (BAA-covered GPT-4o)
│   │   │   ├── local_llama.py         # Self-hosted Llama-3 client (vLLM / TGI backend)
│   │   │   └── base_client.py         # Abstract LLM client (swap backends without changing agents)
│   │   ├── finetuning/
│   │   │   ├── __init__.py
│   │   │   ├── dataset_builder.py     # Build fine-tuning dataset from de-identified EHR notes
│   │   │   ├── qlora_trainer.py       # QLoRA (4-bit + LoRA adapters) training script
│   │   │   └── evaluation.py          # Fine-tuned model evaluation: BLEU, clinical NER F1
│   │   ├── imaging/
│   │   │   ├── __init__.py
│   │   │   ├── medsam_encoder.py      # MedSAM vision encoder: DICOM → embedding
│   │   │   ├── projector.py           # Cross-modal MLP projector (image emb → LLM token space)
│   │   │   └── dicom_preprocessor.py  # DICOM → normalized tensor (windowing, resampling)
│   │   ├── genomics/
│   │   │   ├── __init__.py
│   │   │   ├── variant_cards.py       # VCF variant → natural language "variant card" tokens
│   │   │   └── genomics_encoder.py    # Genomics feature vector construction
│   │   └── prompt_engineering/
│   │       ├── __init__.py
│   │       ├── templates.py           # Structured prompt templates per agent role
│   │       ├── context_assembler.py   # Assemble: graph context + imaging + genomics + instruction
│   │       └── token_budget.py        # Dynamic context window management + LLMLingua-2 compression
│   │
│   ├── api/                           # Public API layer (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── trials.py              # POST /trials — submit simulation request
│   │   │   ├── cohorts.py             # GET  /cohorts — query eligible patient sets
│   │   │   ├── simulations.py         # GET  /simulations/{id} — poll simulation status/results
│   │   │   ├── reports.py             # GET  /reports/{id} — export IRB-ready report package
│   │   │   └── health.py              # GET  /health — liveness + readiness probes
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # JWT + RBAC middleware (Investigator / DataSci / Admin)
│   │   │   ├── audit.py               # Request/response audit logging middleware
│   │   │   └── rate_limit.py          # Per-user rate limiting
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py            # Pydantic request schemas
│   │   │   └── responses.py           # Pydantic response schemas
│   │   └── dependencies.py            # FastAPI dependency injection (db, graph, llm clients)
│   │
│   └── security/                      # Layer 5 — Compliance, audit, security
│       ├── __init__.py
│       ├── audit_ledger/
│       │   ├── __init__.py
│       │   ├── qldb_writer.py         # AWS QLDB append-only ledger writer
│       │   ├── fabric_writer.py       # Hyperledger Fabric writer (consortium deployments)
│       │   └── ledger_schema.py       # Audit event types + Pydantic schemas
│       ├── rbac/
│       │   ├── __init__.py
│       │   ├── roles.py               # Role definitions: INVESTIGATOR, DATA_SCIENTIST, ADMIN
│       │   ├── permissions.py         # Permission matrix per role per resource
│       │   └── policy_engine.py       # OPA (Open Policy Agent) integration
│       ├── esignature/
│       │   ├── __init__.py
│       │   └── cfr_part11.py          # 21 CFR Part 11 e-signature workflow
│       └── irb/
│           ├── __init__.py
│           └── workflow_engine.py     # IRB approval state machine + document generation
│
├── infrastructure/                    # All infrastructure-as-code
│   ├── terraform/
│   │   ├── main.tf                    # Root module: VPC, EKS/AKS, RDS, ElastiCache
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── vpc/                   # Private VPC with no public ingress
│   │       ├── eks/                   # Kubernetes cluster
│   │       ├── neo4j/                 # Neo4j AuraDS managed graph
│   │       ├── rds_postgres/          # PostgreSQL (OMOP CDM + pgvector + audit)
│   │       ├── redis/                 # ElastiCache Redis (agent state store)
│   │       ├── qldb/                  # AWS QLDB audit ledger
│   │       ├── nitro_enclave/         # Nitro Enclave for de-identification compute
│   │       └── kms/                   # Customer-managed encryption keys
│   └── helm/
│       ├── clinicaltrial-ai/          # Main Helm chart (umbrella)
│       │   ├── Chart.yaml
│       │   ├── values.yaml
│       │   ├── values-dev.yaml
│       │   ├── values-prod.yaml
│       │   └── templates/
│       │       ├── ingestion-deployment.yaml
│       │       ├── api-deployment.yaml
│       │       ├── agent-deployment.yaml
│       │       ├── airflow-deployment.yaml
│       │       ├── configmap.yaml
│       │       ├── secrets-external.yaml  # ExternalSecrets (pulls from AWS Secrets Manager)
│       │       ├── networkpolicy.yaml     # Zero-trust network policy (deny-all default)
│       │       ├── serviceaccount.yaml    # IRSA / Workload Identity
│       │       └── hpa.yaml               # Horizontal Pod Autoscaler
│       └── spire/                     # SPIFFE/SPIRE for mTLS service identity
│
├── tests/
│   ├── unit/
│   │   ├── test_deid.py               # PHI detection + removal unit tests
│   │   ├── test_omop_etl.py           # FHIR → OMOP transform tests
│   │   ├── test_graph_queries.py      # Cypher query correctness tests (Neo4j test container)
│   │   ├── test_agent_messages.py     # Agent message schema validation tests
│   │   └── test_rubric_scoring.py     # Judge agent rubric scoring tests
│   ├── integration/
│   │   ├── test_ingestion_pipeline.py # End-to-end FHIR → OMOP → graph integration test
│   │   ├── test_agent_loop.py         # Full simulation loop on synthetic data
│   │   └── test_audit_ledger.py       # Audit event write + cryptographic verification test
│   ├── security/
│   │   ├── test_phi_leakage.py        # Verify no PHI appears in LLM prompts/responses
│   │   ├── test_rbac.py               # Role permission boundary tests
│   │   └── test_dp_guarantees.py      # Differential privacy ε verification tests
│   └── fixtures/
│       ├── synthetic_patients.json    # Synthea-generated test patients (no real PHI)
│       ├── sample_fhir_bundle.json    # Sample FHIR R4 Bundle for ingestion tests
│       └── sample_protocol.json      # Sample CDISC trial protocol for agent tests
│
└── scripts/
    ├── setup_graph.py                 # One-time: create Neo4j schema + load ontologies
    ├── load_omop.py                   # Load OMOP CDM from Postgres → Neo4j
    ├── run_simulation.py              # CLI: trigger a simulation run end-to-end
    ├── export_report.py               # CLI: export simulation results as IRB-ready package
    └── benchmark_graph.py             # Benchmark graph query latency at different cohort sizes
```

---

## Key design choices in the file structure

### Why `src/` not `app/`

`src/` is the Python convention for a top-level importable package root. It works cleanly with
`pyproject.toml` and prevents accidental imports of test or script modules.

### Why `agents/shared/` for base classes

Agent-to-agent communication contracts (Pydantic schemas, FHIR types) must be shared without creating
circular imports. `agents/shared/` is a dependency-free module that all four specialized agents import.
No specialized agent imports another.

### Why `prompts/` inside each agent directory

Prompt text changes frequently during development — treating prompts as first-class files (not
hard-coded strings) makes them diffable in git, reviewable by clinical domain experts who are not
Python developers, and hot-swappable without code changes.

### Why `tests/security/` as a separate test suite

PHI leakage and DP guarantee tests are not unit tests or integration tests — they are *compliance*
tests that run on every PR and block merge if they fail. Separating them makes CI gate logic explicit.

### Why `infrastructure/` at root, not inside `src/`

Infrastructure code is not a Python module. It is managed by a different team (DevOps), uses different
tooling (Terraform, Helm), and has a different change cadence. Co-locating it with application source
creates noise in both directions.

### Why `docs/adr/` for Architecture Decision Records

ADRs capture the *why* of architectural choices in a format that survives personnel changes. Each ADR
is a short markdown file with: context, decision, rationale, and consequences. The decision log in
`PLAN.md` is a summary; ADRs contain the full reasoning.
