# Placeholder ETL functions for FHIR→OMOP mapping (subset)
from typing import Dict, Any, List

OMOPPatient = Dict[str, Any]


def patient_from_fhir(fhir_patient: Dict[str, Any]) -> OMOPPatient:
    return {
        "person_id": fhir_patient.get("id"),
        "year_of_birth": 1970,
        "gender_concept_id": 0,
    }


def transform_bundle(bundle: Dict[str, Any]) -> List[OMOPPatient]:
    return [patient_from_fhir({"id": "P1"})]
