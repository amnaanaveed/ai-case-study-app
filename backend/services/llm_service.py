"""
services/llm_service.py
------------------------
Enterprise LLM extraction service.

Produces a fully populated ClinicalCaseStudy JSON from rough notes and/or prescription images.

Fallback chain
--------------
1. PRIMARY  → Gemini 1.5 Flash   (google-generativeai) [Supports Text + Vision]
2. FALLBACK → Groq llama-3.3-70b (groq)                [Supports Text Only]
"""

import json
import logging
import os
import re
from typing import Any, Dict

import google.generativeai as genai
from groq import Groq
from pydantic import ValidationError

from models.schemas import ClinicalCaseStudy

logger = logging.getLogger(__name__)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY:   str = os.getenv("GROQ_API_KEY",   "")
# 🔥 UPDATE: Model fixed to gemini-1.5-flash for proper multimodal support
GEMINI_MODEL:   str = os.getenv("GEMINI_MODEL",    "gemini-1.5-flash")
GROQ_MODEL:     str = os.getenv("GROQ_MODEL",      "llama-3.3-70b-versatile")

# =========================================================================
# SYSTEM PROMPT  — the single most important piece of this service
# =========================================================================
_SYSTEM_PROMPT = """
You are a Senior Medical Scribe and Clinical Documentation Specialist with 15 years
of experience in physiotherapy assessment documentation. Your task is to read rough
physiotherapy session notes and/or analyze handwritten prescription images, and produce a 
comprehensive, enterprise-grade clinical case study report in STRICT JSON format.

═══════════════════════════════════════════════════════════════
ABSOLUTE OUTPUT RULES — violating any rule ruins the report
═══════════════════════════════════════════════════════════════
1. Output ONLY the raw JSON object. No markdown, no ```json fences, no prose.
2. Do NOT add any text before or after the JSON.
3. Every key listed in the schema below MUST be present in your output.
4. Use "Not Provided" for fields that cannot be inferred from the notes or image.
5. Use "Normal" for clinical parameters that are described as within normal
   limits or can be safely inferred as normal.
6. NEVER hallucinate trauma history, surgical history, or red flag symptoms
   unless explicitly stated in the input.
7. Expand all medical abbreviations: O/E = On Examination, PMH = Past Medical
   History, NPRS = Numeric Pain Rating Scale, ROM = Range of Motion,
   c/o = complains of, H/O = History of, etc.
8. Write all narrative fields (present_complaint, history_of_present_complaint,
   hypothesis_problem_statement) as full professional clinical paragraphs.
9. For patient_priorities, derive 3-5 realistic functional goals.
10. For treatment_plan, generate evidence-based short-term goals (2 weeks),
    long-term goals (6 weeks), specific physiotherapy interventions, a home
    exercise program, and patient education points.

═══════════════════════════════════════════════════════════════
REQUIRED JSON SCHEMA — output must match this structure exactly
═══════════════════════════════════════════════════════════════
{
  "case_number": "<string, e.g. 'CG-001' or 'Auto-assigned'>",
  "category": "<Outdoor Emergency Indoor |>",
  "date": "<today's date or from notes>",
  "referring_physician": "<string or 'Self-referred / Not specified'>",

  "demographics": {
    "name": "<string or 'Anonymous'>",
    "age": "<string e.g. '55 years'>",
    "gender": "<Male Female Other |>",
    "marital_status": "<string or 'Not Provided'>",
    "language": "<string or 'Not Provided'>",
    "occupation": "<string or 'Not Provided'>",
    "address": "<string or 'Not Provided'>",
    "mode_of_admission": "<Outdoor / Emergency Indoor OPD |>"
  },

  "present_complaint": "<Full chief clinical complaint describing paragraph the>",

  "history_of_present_complaint": "<Detailed better/worse, clinical daily episodes, impact it life makes mechanism, narrative: on onset, previous progression, what>",

  "pain_profile": {
    "location": "<Anatomical description>",
    "onset": "<Gradual / Post-traumatic Sudden>",
    "duration": "<e.g. '1 month'>",
    "nature": "<e.g. 'Dull aching pain with occasional sharp exacerbations'>",
    "aggravating_factors": ["<factor 1>", "<factor 2>"],
    "relieving_factors": ["<factor 1>", "<factor 2>"],
    "nprs_score": "<e.g. '6/10 at rest, 8/10 on movement'>",
    "radiation": "<e.g. 'No radiation to upper limbs' or description>"
  },

  "past_history": {
    "medical": "<e.g. 'Mild hypertension, managed conservatively'>",
    "surgical": "<'No previous surgeries reported' if not mentioned>",
    "medications": "<string or 'Not Provided'>",
    "family": "<string or 'Not Provided'>",
    "socioeconomic": "<string or 'Not Provided'>",
    "pre_morbid_status": "<e.g. 'Independent in all ADLs prior to current episode'>",
    "growth_development": "<'Not applicable / within normal limits' if adult>"
  },

  "patients_priorities": [
    "<Priority 'Reduce 1: allow comfortable e.g. neck pain sleep' to>",
    "<Priority 2>",
    "<Priority 3>"
  ],

  "general_health_status": {
    "vitals": {
      "blood_pressure": "<e.g. 'Normal / Within limits' or actual value>",
      "pulse": "<e.g. 'Normal / Within limits'>",
      "respiratory_rate": "<e.g. 'Normal / Within limits'>",
      "temperature": "<e.g. 'Afebrile'>",
      "oxygen_saturation": "<e.g. 'Normal / Within limits'>",
      "weight": "<string or 'Not Provided'>",
      "height": "<string or 'Not Provided'>",
      "bmi": "<string or 'Not Provided'>"
    },
    "lymph_nodes": "<Not - Palpable describe palpable |>",
    "jaundice": "<Absent Present |>",
    "pallor": "<Absent Present |>",
    "cyanosis": "<Absent Present |>",
    "edema": "<Absent - Present describe if present |>",
    "clubbing": "<Absent Present |>",
    "overall_impression": "<Clinical about general patient's sentence state>"
  },

  "general_health_condition": {
    "malaise": "<None Present reported |>",
    "fatigue": "<None describe reported |>",
    "fever": "<Afebrile describe |>",
    "weight_changes": "<None describe reported |>",
    "sleep": "<Not describe impact reported |>",
    "cognition": "<Intact describe |>",
    "mood": "<Cooperative and describe oriented |>"
  },

  "systems_review": {
    "cardiovascular": "<No complaints describe reported |>",
    "pulmonary": "<No complaints describe reported |>",
    "gastrointestinal": "<No complaints describe reported |>",
    "urinary": "<No complaints describe reported |>",
    "integumentary": "<Skin describe intact, lesions no noted or wounds |>",
    "endocrine": "<No complaints describe reported |>",
    "reproductive": "<Not / Not applicable assessed describe |>"
  },

  "musculoskeletal_system": {
    "gross_symmetry": "<Normal - Asymmetry describe noted |>",
    "posture": "<Clinical assessment postural>",
    "deformity": "<None describe observed |>",
    "swelling": "<None describe observed |>",
    "tenderness": "<Specific anatomical and grade location>",
    "muscle_wasting": "<None describe observed |>",
    "spasm": "<Location and severity>",
    "cervical_rom": "<Describe 'Extension and due e.g. pain' restricted restrictions, right rotation to>",
    "lumbar_rom": "<Normal describe restrictions |>",
    "upper_limb_rom": "<Normal describe restrictions |>",
    "lower_limb_rom": "<Normal describe restrictions |>",
    "muscle_strength": "<Normal describe throughout weakness |>",
    "special_tests": ["<Test Result name:>", "<Test Result name:>"]
  },

  "neurological_system": {
    "consciousness": "<Conscious and oriented person place time, to>",
    "numbness_tingling": "<None describe distribution reported |>",
    "reflexes": "<Normal abnormality describe |>",
    "muscle_tone": "<Normal Hypertonic Hypotonic |>",
    "coordination": "<Normal describe |>",
    "gait": "<Normal describe |>",
    "cranial_nerves": "<Not / Intact assessed describe |>",
    "upper_motor_neuron": "<No UMN describe lesion of signs |>",
    "lower_motor_neuron": "<No LMN describe lesion of signs |>"
  },

  "functional_status": {
    "adl_status": "<Independent Partially dependent describe limitations |>",
    "mobility": "<Independent describe |>",
    "work_status": "<Active Modified Off describe duties work |>",
    "recreational": "<Limitations activities any if in recreational>",
    "assistive_devices": "<None currently describe in use |>",
    "functional_goals": ["<Goal 1>", "<Goal 2>", "<Goal 3>"]
  },

  "investigations": {
    "imaging": "<Describe 'None / Not available' findings or provided>",
    "labs": "<Describe 'None / Not available' or provided>",
    "emg_ncs": "<Describe 'Not assessed' or>",
    "other": "<Any investigations other>"
  },

  "clinical_impression": "<Full ICD clinical description diagnosis if possible with>",

  "hypothesis_problem_statement": "<A 3-5 and approach clinical comprehensive contributing diagnosis, explaining factors, for functional limitations, paragraph rationale sentence synthesis the treatment>",

  "treatment_plan": {
    "short_term_goals": ["<Goal 2 achievable in weeks>", "<Goal 2>"],
    "long_term_goals": ["<Goal 6 achievable in weeks>", "<Goal 2>"],
    "physiotherapy_interventions": [
      "<Intervention 'Shortwave 1 15 Diathermy: cervical continuous e.g. min, mode, parameters, region' with>",
      "<Intervention 2>"
    ],
    "home_exercise_program": [
      "<Exercise 'Chin 1 10 3 5 e.g. hold reps, seconds' sets sets/reps, tucks: with x>",
      "<Exercise 2>"
    ],
    "patient_education": [
      "<Education 'Ergonomic 1, e.g. for neck point posture' setup workstation>",
      "<Education 2 point>"
    ],
    "referrals": "<None at if needed specify this time |>",
    "follow_up": "<e.g. 'Review in 1 week. Full reassessment at 3 weeks.'>",
    "prognosis": "<Clinical prognosis statement>"
  },

  "additional_notes": "<Any 'None' clinical observations or other relevant>"
}
""".strip()


# ── Defensive JSON parser ─────────────────────────────────────────── #
def _clean_and_parse(raw: str) -> dict:
    """Strip markdown fences and extract the outermost JSON object."""
    cleaned = re.sub(r"
```(?:json)?", "", raw).strip("`").strip()
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM output: {raw[:300]!r}")
    return json.loads(cleaned[start:end])


# ── Pydantic validation ───────────────────────────────────────────── #
def _validate(raw_dict: dict) -> Dict[str, Any]:
    try:
        return ClinicalCaseStudy(**raw_dict).model_dump()
    except ValidationError as exc:
        logger.warning("Pydantic validation issues (non-fatal): %s", exc)
        # Return raw dict with defaults applied rather than crashing
        return ClinicalCaseStudy.model_validate(raw_dict, strict=False).model_dump()


# ── Provider: Gemini (UPDATED FOR MULTIMODAL) ─────────────────────── #
def _call_gemini(text: str, image_bytes: bytes = None, mime_type: str = None) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=_SYSTEM_PROMPT,
    )
    
    # 🔥 Construct payload for both text and image
    content_parts = [
        "You are documenting a physiotherapy assessment. Read the rough session "
        "notes and/or analyze the attached image, and produce the full clinical "
        "case study JSON exactly as instructed in your system prompt. Expand every "
        "section comprehensively.\n\n"
    ]
    
    if text:
        content_parts.append(f"ROUGH SESSION NOTES:\n{text}")
        
    if image_bytes:
        # Gemini expects image data in this specific dictionary format
        content_parts.append({
            "mime_type": mime_type or "image/jpeg",
            "data": image_bytes
        })

    response = model.generate_content(
        content_parts,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )
    raw = response.text or ""
    logger.debug("Gemini raw output length: %d chars", len(raw))
    return _validate(_clean_and_parse(raw))


# ── Provider: Groq ────────────────────────────────────────────────── #
def _call_groq(text: str, image_bytes: bytes = None) -> Dict[str, Any]:
    # Groq's text models don't support images directly yet. 
    # If it falls back to Groq and there's an image, it will rely solely on the text provided.
    if image_bytes and not text:
        raise RuntimeError("Groq fallback does not support image-only extraction.")
        
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")
    client = Groq(api_key=GROQ_API_KEY)
    user_msg = (
        "You are documenting a physiotherapy assessment. Read the rough session "
        "notes below and produce the full clinical case study JSON exactly as "
        "instructed in your system prompt. Expand every section comprehensively.\n\n"
        f"ROUGH SESSION NOTES:\n{text}"
    )
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    raw = completion.choices[0].message.content or ""
    logger.debug("Groq raw output length: %d chars", len(raw))
    return _validate(_clean_and_parse(raw))


# ── Public API ────────────────────────────────────────────────────── #
# 🔥 UPDATE: Added image_bytes and mime_type arguments
def extract_clinical_data(text: str, image_bytes: bytes = None, mime_type: str = None) -> Dict[str, Any]:
    """
    Extract a full enterprise clinical case study from rough notes and/or images.
    Tries Gemini (Multimodal) first; falls back to Groq (Text-only) on failure.
    """
    gemini_exc = None
    try:
        logger.info("Calling Gemini (%s) for clinical extraction...", GEMINI_MODEL)
        result = _call_gemini(text, image_bytes, mime_type)
        logger.info("Gemini extraction successful.")
        return result
    except Exception as exc:
        gemini_exc = exc
        logger.warning("Gemini failed (%s). Trying Groq fallback...", exc)

    try:
        logger.info("Calling Groq (%s) for clinical extraction...", GROQ_MODEL)
        result = _call_groq(text, image_bytes)
        logger.info("Groq extraction successful.")
        return result
    except Exception as groq_exc:
        logger.error("Both providers failed. Gemini: %s | Groq: %s", gemini_exc, groq_exc)
        raise RuntimeError(
            f"Both LLM providers failed. Gemini: {gemini_exc} | Groq: {groq_exc}"
        ) from groq_exc