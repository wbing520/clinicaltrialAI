from __future__ import annotations

"""
Airflow DAG (skeleton) for Phase-1 ingestion: FHIR -> de-id -> OMOP -> graph load.
- If USE_SMART_FHIR=true and FHIR_* env vars are set, pulls from FHIR endpoint via SMART-on-FHIR.
- Otherwise, uses local fixture at tests/fixtures/sample_fhir_bundle.json.
"""

import os
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

from pathlib import Path
import json

from src.ingestion.deid.safe_harbor import remove_safe_harbor
from src.ingestion.omop.etl import transform_bundle
from src.ingestion.fhir.client import SmartFhirClient


def task_fetch_fhir(**_):
    use_smart = os.getenv("USE_SMART_FHIR", "false").lower() in ("1", "true", "yes")
    if use_smart:
        client = SmartFhirClient()
        return client.fetch_bundle("Patient", params={"_count": 10})
    # Fixture fallback
    p = Path("tests/fixtures/sample_fhir_bundle.json")
    return json.loads(p.read_text(encoding="utf-8"))


def task_deidentify(bundle: dict, **_):
    # Apply a trivial transformation to emulate safe harbor on top-level keys
    return {k: (remove_safe_harbor(v) if isinstance(v, dict) else v) for k, v in bundle.items()}


def task_transform_to_omop(bundle: dict, **_):
    return transform_bundle(bundle)


def task_graph_load(**_):
    from src.graph.schema.nodes import SCHEMA_CYPHER
    from src.graph.neo4j.driver import get_driver

    with get_driver().session() as s:
        for stmt in SCHEMA_CYPHER:
            s.run(stmt)
    return "ok"


def make_dag() -> DAG:
    with DAG(
        dag_id="ingest_fhir_to_graph",
        start_date=datetime(2024, 1, 1),
        schedule=None,
        catchup=False,
        tags=["clinicaltrial-ai", "phase1"],
        doc_md=__doc__,
    ) as dag:
        fetch = PythonOperator(task_id="fetch_fhir", python_callable=task_fetch_fhir)
        deid = PythonOperator(task_id="deidentify", python_callable=task_deidentify, op_kwargs={"bundle": fetch.output})
        omop = PythonOperator(task_id="transform_omop", python_callable=task_transform_to_omop, op_kwargs={"bundle": deid.output})
        load = PythonOperator(task_id="graph_load", python_callable=task_graph_load)
        fetch >> deid >> omop >> load
        return dag


ingest_fhir_to_graph = make_dag()
