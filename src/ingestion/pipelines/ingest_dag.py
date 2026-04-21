from __future__ import annotations

"""
Airflow DAG (skeleton) for Phase-1 ingestion: FHIR -> de-id -> OMOP -> graph load.
Uses local stubs; replace Python callables with real implementations as they land.
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

# Stub functions pulled from our codebase
from src.ingestion.deid.safe_harbor import remove_safe_harbor
from src.ingestion.omop.etl import transform_bundle
from pathlib import Path
import json


def task_fetch_fhir(**_):
    # Phase-1: read synthetic bundle fixture
    p = Path("tests/fixtures/sample_fhir_bundle.json")
    return json.loads(p.read_text(encoding="utf-8"))


def task_deidentify(bundle: dict, **_):
    # Apply a trivial transformation to emulate safe harbor on top-level keys
    return {k: (remove_safe_harbor(v) if isinstance(v, dict) else v) for k, v in bundle.items()}


def task_transform_to_omop(bundle: dict, **_):
    return transform_bundle(bundle)


def task_graph_load(**_):
    # Placeholder: init graph schema and load synthetic patients via script, in-proc alternative
    from src.graph.schema.nodes import SCHEMA_CYPHER
    from src.graph.neo4j.driver import get_driver

    with get_driver().session() as s:
        for stmt in SCHEMA_CYPHER:
            s.run(stmt)
    return "ok"


def _xcom_passthrough(value, **_):
    return value


def make_dag() -> DAG:
    with DAG(
        dag_id="ingest_fhir_to_graph",
        start_date=datetime(2024, 1, 1),
        schedule=None,
        catchup=False,
        tags=["clinicaltrial-ai", "phase1"],
    ) as dag:
        fetch = PythonOperator(task_id="fetch_fhir", python_callable=task_fetch_fhir)
        deid = PythonOperator(task_id="deidentify", python_callable=task_deidentify, op_kwargs={"bundle": fetch.output})
        omop = PythonOperator(task_id="transform_omop", python_callable=task_transform_to_omop, op_kwargs={"bundle": deid.output})
        load = PythonOperator(task_id="graph_load", python_callable=task_graph_load)
        # Simple dependency chain
        fetch >> deid >> omop >> load
        return dag


ingest_fhir_to_graph = make_dag()
