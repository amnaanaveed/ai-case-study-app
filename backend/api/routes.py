"""
api/routes.py
--------------
FastAPI router that wires the four pipeline services together.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Header, Form, File, UploadFile
from pydantic import BaseModel, Field

from services.validation_service import validate_raw_notes
from services.llm_service        import extract_clinical_data
from services.pdf_service        import generate_pdf
from services.drive_service      import upload_to_drive

logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Response schema (Request schema hata diya kyunke ab Form Data hai) #
# ------------------------------------------------------------------ #

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
    summary="Generate a clinical case study from notes and/or images.",
    tags=["Case Study"],
)
async def generate_case_study(
    authorization: Optional[str] = Header(None), # Catches the token from React!
    notes: Optional[str] = Form(""),             # 🔥 Text input (optional)
    file: Optional[UploadFile] = File(None)      # 🔥 Image input (optional)
) -> GenerateResponse:
    """
    Full pipeline: Text/Image → Validation → LLM extraction → PDF → Drive
    """

    # --- SECURITY CHECK ---
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Google Access Token. Please sign in on the frontend first."
        )
    
    user_access_token = authorization.split("Bearer ")[1]
    raw_notes = notes.strip() if notes else ""
    
    logger.info("Received request. Text length: %d, File attached: %s", len(raw_notes), bool(file))

    # ── Step 1: Validation (Zero-token check) ─────────────────────── #
    # Agar na text hai aur na file, toh error do
    if not file and len(raw_notes) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Please provide enough text notes or upload a prescription picture."}
        )

    # Agar sirf text hai (file nahi hai), tabhi local validation karo
    if not file:
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
        logger.info("Local validation passed (Text only).")
    else:
        logger.info("File uploaded, skipping local text validation (LLM will handle it).")

    # ── Prepare Image Data for LLM ────────────────────────────────── #
    image_bytes = None
    mime_type = None
    if file:
        image_bytes = await file.read() # Image ko memory mein parh liya
        mime_type = file.content_type

    # ── Step 2: LLM JSON extraction ───────────────────────────────── #
    try:
        # 🔥 UPDATE: Ab extract_clinical_data ko image data bhi bhej rahe hain
        patient_data: dict = extract_clinical_data(raw_notes, image_bytes, mime_type)
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