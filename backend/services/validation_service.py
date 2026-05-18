"""
services/validation_service.py
--------------------------------
Zero-token local gatekeeper.

Performs cheap regex / keyword checks on raw physiotherapy notes
BEFORE touching any external API.  If critical clinical information
is absent, an error dict is returned so the frontend can display a
meaningful warning without incurring any LLM cost.

Return contract
---------------
Success  → {"status": "ok"}
Failure  → {"status": "error", "missing": ["field_a", "field_b"], "message": "..."}
"""

import re
from typing import Dict, Any


# ------------------------------------------------------------------ #
# Internal helpers                                                     #
# ------------------------------------------------------------------ #

# Matches bare numbers or numbers followed by common age words.
# Examples: "45", "45 years", "age 45", "aged 45"
_AGE_PATTERN = re.compile(
    r"""
    (?:                         # optional label
        age[d]?\s+              # "age 45"  / "aged 45"
    )?
    \b(\d{1,3})\b               # capture the number
    (?:\s*(?:years?|yrs?|y/o))? # optional unit
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Matches pain-scale expressions.
# Examples: "pain 7/10", "7 out of 10", "VAS 7", "pain level 7"
_PAIN_SCALE_PATTERN = re.compile(
    r"""
    (?:
        \b(?:pain|vas|nrs|score|level|scale|rating)\b.*?  # optional label first
        \b(\d{1,2})\b                                      # then number
        (?:/10|\s+out\s+of\s+10)?                          # optional "/10"
    |
        \b(\d{1,2})\s*/\s*10\b                             # bare "7/10"
    |
        \b(\d{1,2})\s+out\s+of\s+10\b                     # bare "7 out of 10"
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Broad treatment vocabulary – add more keywords as the project grows.
_TREATMENT_KEYWORDS = [
    # physical modalities
    "diathermy", "ultrasound", "tens", "laser", "heat", "ice", "cryotherapy",
    "electrotherapy", "interferential", "traction",
    # exercise / manual
    "exercise", "stretching", "mobilisation", "mobilization", "manipulation",
    "massage", "therapy", "rehabilitation", "strengthening", "training",
    "physiotherapy", "physical therapy",
    # common abbreviations
    "swd", "mwd", "ift", "mfr",
]

_TREATMENT_PATTERN = re.compile(
    r"\b(?:" + "|".join(_TREATMENT_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Minimum raw-text length to bother parsing (very short inputs are junk).
_MIN_LENGTH = 30


# ------------------------------------------------------------------ #
# Public API                                                           #
# ------------------------------------------------------------------ #

def validate_raw_notes(text: str) -> Dict[str, Any]:
    """
    Validate raw physiotherapy notes without calling any external service.

    Parameters
    ----------
    text : str
        The raw, unstructured clinical notes entered by the physiotherapist.

    Returns
    -------
    dict
        ``{"status": "ok"}`` when all checks pass.
        ``{"status": "error", "missing": [...], "message": "..."}`` otherwise.
    """

    missing: list[str] = []

    # ── 1. Basic length / content guard ────────────────────────────── #
    if not text or not text.strip():
        return {
            "status": "error",
            "missing": ["clinical notes"],
            "message": "Input is empty. Please enter the patient's clinical notes.",
        }

    if len(text.strip()) < _MIN_LENGTH:
        return {
            "status": "error",
            "missing": ["sufficient detail"],
            "message": (
                f"Notes are too brief ({len(text.strip())} chars). "
                "Please provide more clinical detail."
            ),
        }

    # ── 2. Age presence ────────────────────────────────────────────── #
    age_matches = _AGE_PATTERN.findall(text)
    # Filter out implausible values (0 and >110 are likely false positives)
    valid_ages = [m for m in age_matches if m.isdigit() and 1 <= int(m) <= 110]
    if not valid_ages:
        missing.append("patient age")

    # ── 3. Pain scale presence ─────────────────────────────────────── #
    pain_matches = _PAIN_SCALE_PATTERN.search(text)
    if not pain_matches:
        missing.append("pain scale (e.g. '7/10' or '7 out of 10')")

    # ── 4. Treatment / intervention mention ────────────────────────── #
    treatment_match = _TREATMENT_PATTERN.search(text)
    if not treatment_match:
        missing.append("treatment or exercise applied")

    # ── 5. Return result ──────────────────────────────────────────── #
    if missing:
        missing_str = ", ".join(missing)
        return {
            "status": "error",
            "missing": missing,
            "message": (
                f"The following required information could not be detected: "
                f"{missing_str}. "
                "Please review your notes and ensure they include the patient's "
                "age, a pain score, and the treatment/exercise applied."
            ),
        }

    return {"status": "ok"}