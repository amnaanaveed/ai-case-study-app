"""
main.py
--------
Entry point for the AI Case Study Generator backend.

Run locally with:
    uvicorn main:app --reload
"""

import logging
import os
from contextlib import asynccontextmanager

# 1. LOAD THE KEYS FIRST!
from dotenv import load_dotenv
load_dotenv()

# 2. THEN IMPORT THE REST OF YOUR APP!
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Startup / Shutdown lifecycle                                       #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code inside the 'with' block runs on startup.
    Code after 'yield' runs on graceful shutdown.
    """
    # -- Startup ---------------------------------------------------- #
    temp_pdf_dir = os.path.join("data", "temp_pdfs")
    os.makedirs(temp_pdf_dir, exist_ok=True)
    logger.info("Temp PDF directory ready: %s", temp_pdf_dir)

    patient_history_path = os.path.join("data", "patient_history.json")
    if not os.path.exists(patient_history_path):
        import json
        with open(patient_history_path, "w") as f:
            json.dump([], f)
        logger.info("Initialised empty patient_history.json")

    logger.info("=" * 60)
    logger.info("  AI Case Study Generator — Backend started")
    logger.info("=" * 60)

    yield  # Application runs here

    # -- Shutdown --------------------------------------------------- #
    logger.info("AI Case Study Generator — Backend shutting down.")


# ------------------------------------------------------------------ #
# FastAPI application                                                #
# ------------------------------------------------------------------ #

app = FastAPI(
    title="AI Case Study Generator",
    description=(
        "Automated clinical case study generation for physiotherapists. "
        "Raw session notes → structured JSON → PDF → Google Drive."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Ensure the folder exists, then mount it so the browser can access the PDFs
os.makedirs(os.path.join("data", "temp_pdfs"), exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=os.path.join("data", "temp_pdfs")), name="pdfs")


# ------------------------------------------------------------------ #
# CORS Middleware (UPDATED FOR LIVE HOSTING)                         #
# ------------------------------------------------------------------ #

# Using "*" allows your Vercel frontend to connect without getting blocked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False, # Must be False when origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Routers                                                            #
# ------------------------------------------------------------------ #

app.include_router(router, prefix="/api/v1")


# ------------------------------------------------------------------ #
# Health-check endpoints                                             #
# ------------------------------------------------------------------ #

@app.get("/", tags=["Health"], summary="Root health check")
async def root():
    """
    Quick liveness probe.
    Returns a 200 OK with a status message.
    """
    return {"status": "AI Case Study Generator Backend is running smoothly!"}


@app.get("/health", tags=["Health"], summary="Detailed health check")
async def health_check():
    """
    Confirms that critical environment variables are loaded
    (without exposing their values).
    """
    return {
        "status":            "ok",
        "gemini_key_loaded": bool(os.getenv("GEMINI_API_KEY")),
        "groq_key_loaded":   bool(os.getenv("GROQ_API_KEY")),
    }