import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import phase3, simulation, intervention, validation, agent

app = FastAPI(title="DrainTwin API")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","), allow_methods=["*"], allow_headers=["*"])
app.include_router(simulation.router, prefix="/api")
app.include_router(intervention.router, prefix="/api")
app.include_router(validation.router, prefix="/api")

app.include_router(phase3.router, prefix="/api")

app.include_router(agent.router, prefix="/api")
