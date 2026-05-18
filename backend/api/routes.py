"""
api/routes.py
--------------
FastAPI router that wires the four pipeline services together.

Endpoint: POST /api/v1/generate-case-study
Input   : JSON body  { "notes": "<raw physiotherapy text>" }
Output  : JSON body  { "drive_link": "<Google Drive URL>",
                       "patient_data": { ... }  }

Error responses follow RFC 7807 / standard FastAPI HTTPException format:
    { "detail": "<human-readable message>" }
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field

from services.validation_service import validate_raw_notes
from services.llm_service         import extract_clinical_data
from services.pdf_service         import generate_pdf
from services.drive_service       import upload_to_drive

logger = logging.getLogger(__name__)

router = APIRouter()


# ------------------------------------------------------------------ #
# Request / Response schemas (route-level, NOT the LLM schema)       #
# ------------------------------------------------------------------ #

class GenerateRequest(BaseModel):
    """Body expected by the generate endpoint."""
    notes: str = Field(
        ...,
        min_length=30,
        description="Raw, unstructured physiotherapy session notes.",
        examples=["Patient age 45, male. Lower back pain 7/10. Applied SWD 15 min."],
    )


class GenerateResponse(BaseModel):
    """Successful response payload."""
    drive_link:   str   = Field(..., description="Google Drive webViewLink of the PDF.")
    patient_data: dict  = Field(..., description="Structured clinical data extracted by the LLM.")
    message:      str   = Field(default="Case study generated successfully.")


# ------------------------------------------------------------------ #
# Endpoint                                                           #
# ------------------------------------------------------------------ #

@router.post(
    "/generate-case-study",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a clinical case study from raw physiotherapy notes.",
    description=(
        "Validates raw notes locally, extracts structured clinical data via LLM, "
        "generates a formatted PDF, uploads it to Google Drive, and returns the "
        "shareable link."
    ),
    tags=["Case Study"],
)
async def generate_case_study(
    body: GenerateRequest,
    authorization: Optional[str] = Header(None) # Catches the token from React!
) -> GenerateResponse:
    """
    Full pipeline:
        Raw text → Validation → LLM extraction → PDF generation → Drive upload
    """

    # --- SECURITY CHECK ---
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Google Access Token. Please sign in on the frontend first."
        )
    
    # Extract the actual token string
    user_access_token = authorization.split("Bearer ")[1]

    raw_notes: str = body.notes.strip()
    logger.info("Received generate-case-study request (%d chars).", len(raw_notes))

    # ── Step 1: Zero-token local validation ───────────────────────── #
    validation_result = validate_raw_notes(raw_notes)

    if validation_result["status"] == "error":
        logger.warning("Validation failed: %s", validation_result.get("missing"))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error":   "Validation failed – insufficient clinical data.",
                "missing": validation_result.get("missing", []),
                "message": validation_result.get("message", ""),
            },
        )

    logger.info("Local validation passed.")

    # ── Step 2: LLM JSON extraction ───────────────────────────────── #
    try:
        patient_data: dict = extract_clinical_data(raw_notes)
        logger.info("LLM extraction successful.")
    except (ValueError, RuntimeError) as exc:
        logger.error("LLM extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI data extraction failed: {exc}",
        )

    # ── Step 3: Local PDF generation ──────────────────────────────── #
    try:
        pdf_path: str = generate_pdf(patient_data)
        logger.info("PDF generated at %s.", pdf_path)
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    # ── Step 4: Google Drive upload ───────────────────────────────── #
    try:
        # Pass the frontend token to the drive service!
        drive_link: str = upload_to_drive(pdf_path, user_access_token)
        logger.info("PDF uploaded. Drive link: %s", drive_link)
    except Exception as exc:
        logger.error("Drive upload failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloud upload failed: {exc}",
        )

    return GenerateResponse(
        drive_link=drive_link,
        patient_data=patient_data,
    )