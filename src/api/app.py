from fastapi import FastAPI
from .routers import simulations

app = FastAPI(title="ClinicalTrialAI API", version="0.1.0")
app.include_router(simulations.router)
