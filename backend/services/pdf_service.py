"""
services/pdf_service.py
------------------------
Enterprise PDF generator for the full ClinicalCaseStudy schema.

Layout philosophy
-----------------
- Full A4 portrait, 15mm margins
- Each major section gets a coloured banner header
- Nested subsections get a lighter indented sub-header
- Key-value pairs rendered as a 2-column table (label | value)
- Bullet lists for list fields (interventions, goals, etc.)
- Pain scale bar for NPRS visualisation
- Page numbers + confidentiality footer on every page
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF, XPos, YPos

logger = logging.getLogger(__name__)


# =========================================================================
# Unicode sanitiser
# Helvetica is a Latin-1 font. The LLM often outputs typographic
# characters outside that range. Replace every known offender with a
# plain ASCII equivalent so fpdf never raises a character-range error.
# =========================================================================
_UNICODE_MAP = str.maketrans({
    # Dashes
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2012": "-",   # figure dash
    "\u2015": "-",   # horizontal bar
    # Quotes
    "\u2018": "'",   # left single quotation mark
    "\u2019": "'",   # right single quotation mark
    "\u201a": ",",   # single low-9 quotation mark
    "\u201c": '"',  # left double quotation mark
    "\u201d": '"',  # right double quotation mark
    "\u201e": '"',  # double low-9 quotation mark
    "\u00ab": '"',  # left-pointing double angle quotation
    "\u00bb": '"',  # right-pointing double angle quotation
    # Ellipsis & bullets
    "\u2026": "...", # horizontal ellipsis
    "\u2022": "*",   # bullet (drawn separately in lists)
    "\u25cf": "*",   # black circle
    "\u00b7": ".",   # middle dot
    # Spaces
    "\u00a0": " ",   # non-breaking space
    "\u202f": " ",   # narrow no-break space
    "\u2009": " ",   # thin space
    # Math / misc
    "\u00d7": "x",        # multiplication sign
    "\u00f7": "/",        # division sign
    "\u00b0": " degrees", # degree symbol
    "\u2264": "<=",
    "\u2265": ">=",
    "\u00b1": "+/-",
    "\u2192": "->",
    "\u2190": "<-",
    # Common accented letters in medical text
    "\u00e9": "e",
    "\u00e8": "e",
    "\u00ea": "e",
    "\u00eb": "e",
    "\u00e0": "a",
    "\u00e1": "a",
    "\u00e2": "a",
    "\u00fc": "u",
    "\u00f6": "o",
    "\u00e4": "a",
})


def _clean(text: str) -> str:
    """
    Sanitise any string before passing it to fpdf.
    1. Replace known Unicode characters with ASCII equivalents.
    2. Drop any remaining non-Latin-1 characters via latin-1 encode/decode.
    """
    if not isinstance(text, str):
        text = str(text)
    text = text.translate(_UNICODE_MAP)
    return text.encode("latin-1", errors="replace").decode("latin-1")

_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "temp_pdfs"
)

# -- Colour palette ------------------------------------------------- #
_TEAL_DARK  = (13,  94, 88)    # section banners
_TEAL_MID   = (20, 150, 140)   # sub-section banners
_TEAL_LIGHT = (204, 251, 241)  # alternating row tint
_WHITE      = (255, 255, 255)
_NEAR_BLACK = (15,  23,  42)
_MID_GRAY   = (71,  85, 105)
_BORDER     = (226, 232, 240)


# =========================================================================
# PDF class with header / footer
# =========================================================================
class _ClinicalPDF(FPDF):

    def header(self):
        self.set_fill_color(*_TEAL_DARK)
        self.rect(0, 0, self.w, 20, style="F")
        self.set_y(5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_WHITE)
        self.cell(0, 7, "PHYSIOTHERAPY CLINICAL CASE STUDY REPORT", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(180, 230, 225)
        self.cell(0, 5,
                  f"CaseGen AI  |  Generated: {datetime.now().strftime('%d %B %Y  %H:%M')}",
                  align="C")
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*_TEAL_MID)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*_MID_GRAY)
        self.cell(0, 5,
                  f"Page {self.page_no()}  |  CONFIDENTIAL - For authorised clinical use only",
                  align="C")


# =========================================================================
# Drawing helpers
# =========================================================================

def _section_banner(pdf: _ClinicalPDF, title: str):
    """Dark teal full-width banner. Ensures at least 20pt of space after it."""
    # If less than 28pt remains (banner + 1 row), start a fresh page
    if pdf.get_y() + 28 > pdf.h - 18:
        pdf.add_page()
    pdf.set_fill_color(*_TEAL_DARK)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 9, f"  {_clean(title).upper()}", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _sub_banner(pdf: _ClinicalPDF, title: str):
    """Lighter teal banner. Ensures at least 16pt of space after it."""
    if pdf.get_y() + 22 > pdf.h - 18:
        pdf.add_page()
    pdf.set_fill_color(*_TEAL_MID)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, f"    {_clean(title)}", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(0.5)


def _kv_row(pdf: _ClinicalPDF, label: str, value: str, shaded: bool = False):
    """
    Two-column key-value row with optional shading.

    Page-break safe: measures the full row height first, then checks
    whether it fits in the remaining page space.  If not, forces a new
    page before drawing so label and value are never split across pages.
    """
    label_w = 52
    val_w   = pdf.w - pdf.l_margin - pdf.r_margin - label_w
    line_h  = 5.5   # pt per text line inside the value cell

    value = _clean(str(value))
    label = _clean(str(label))

    # -- Measure how many lines the value will wrap to --------------- #
    pdf.set_font("Helvetica", "", 8.5)
    lines   = pdf.multi_cell(val_w, line_h, value, dry_run=True, output="LINES")
    n_lines = max(len(lines), 1)
    row_h   = max(n_lines * line_h, 7)

    # -- Page-break guard: if row doesn't fit, start a new page ------- #
    bottom_margin = 18          # matches set_auto_page_break margin
    page_bottom   = pdf.h - bottom_margin
    if pdf.get_y() + row_h > page_bottom:
        pdf.add_page()

    y_start = pdf.get_y()
    x_start = pdf.l_margin
    fill_color = _TEAL_LIGHT if shaded else _WHITE

    # -- Label column ----------------------------------------------- #
    pdf.set_xy(x_start, y_start)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*fill_color)
    pdf.set_text_color(*_NEAR_BLACK)
    pdf.cell(label_w, row_h, f"  {label}:", fill=True,
             border="B", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # -- Value column ----------------------------------------------- #
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_fill_color(*fill_color)
    pdf.set_xy(x_start + label_w, y_start)
    pdf.multi_cell(val_w, row_h / n_lines, value,
                   fill=True, border="B",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _bullet_list(pdf: _ClinicalPDF, items: List[str], indent: float = 6):
    """Render a bulleted list of strings. Page-break safe per item."""
    if not items:
        _kv_row(pdf, "  ", "None specified", shaded=False)
        return
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*_NEAR_BLACK)
    bottom_margin = 18
    page_bottom   = pdf.h - bottom_margin
    for item in items:
        cleaned = _clean(str(item))
        # Measure item height before drawing
        item_lines = pdf.multi_cell(
            pdf.w - pdf.l_margin - pdf.r_margin - indent - 5,
            5.5, cleaned, dry_run=True, output="LINES"
        )
        item_h = max(len(item_lines) * 5.5, 6)
        if pdf.get_y() + item_h > page_bottom:
            pdf.add_page()
        pdf.set_x(pdf.l_margin + indent)
        pdf.cell(5, 6, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.multi_cell(0, 5.5, cleaned,
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def _narrative(pdf: _ClinicalPDF, text: str):
    """Render a full paragraph. Uses fpdf auto page-break for long paragraphs."""
    cleaned = _clean(str(text))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*_NEAR_BLACK)
    # Ensure at least 3 lines of space before starting a narrative block
    bottom_margin = 18
    if pdf.get_y() + 18 > pdf.h - bottom_margin:
        pdf.add_page()
    pdf.set_x(pdf.l_margin + 3)
    # multi_cell with auto page-break enabled handles wrapping naturally
    pdf.multi_cell(0, 5.5, cleaned, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)


def _pain_bar(pdf: _ClinicalPDF, nprs_str: str):
    """Draw 10-segment colour-coded NPRS bar."""
    # Try to parse first digit from the NPRS string
    digits = [c for c in str(nprs_str) if c.isdigit()]
    score  = int(digits[0]) if digits else 0

    bar_x = pdf.l_margin + 55
    bar_y = pdf.get_y() + 1
    sw, sh = 10, 7

    for i in range(10):
        if i < 4:
            colour = (76, 175, 80)
        elif i < 7:
            colour = (255, 193, 7)
        else:
            colour = (244, 67, 54)

        if i < score:
            pdf.set_fill_color(*colour)
            pdf.set_draw_color(*colour)
        else:
            pdf.set_fill_color(220, 220, 220)
            pdf.set_draw_color(180, 180, 180)

        pdf.rect(bar_x + i * (sw + 1), bar_y, sw, sh, style="FD")

    # Label
    pdf.set_xy(bar_x + 10 * (sw + 1) + 3, bar_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_NEAR_BLACK)
    pdf.cell(30, sh, f"{nprs_str}")
    pdf.ln(sh + 3)


# =========================================================================
# Section renderers -- one function per major schema section
# =========================================================================

def _render_metadata(pdf, d: dict):
    _section_banner(pdf, "Case Information")
    fields = [
        ("Case Number",       d.get("case_number", "N/A")),
        ("Category",          d.get("category", "N/A")),
        ("Date",              d.get("date", "N/A")),
        ("Referring Physician", d.get("referring_physician", "N/A")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_demographics(pdf, dem: dict):
    _section_banner(pdf, "Patient Demographics")
    fields = [
        ("Name",             dem.get("name")),
        ("Age",              dem.get("age")),
        ("Gender",           dem.get("gender")),
        ("Marital Status",   dem.get("marital_status")),
        ("Language",         dem.get("language")),
        ("Occupation",       dem.get("occupation")),
        ("Address",          dem.get("address")),
        ("Mode of Admission",dem.get("mode_of_admission")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_complaint(pdf, d: dict):
    _section_banner(pdf, "Present Complaint")
    _narrative(pdf, d.get("present_complaint", "Not Provided"))

    _section_banner(pdf, "History of Presenting Complaint")
    _narrative(pdf, d.get("history_of_present_complaint", "Not Provided"))


def _render_pain(pdf, pain: dict):
    _section_banner(pdf, "Pain Profile")
    basic = [
        ("Location",  pain.get("location")),
        ("Onset",     pain.get("onset")),
        ("Duration",  pain.get("duration")),
        ("Nature",    pain.get("nature")),
        ("Radiation", pain.get("radiation")),
    ]
    for i, (k, v) in enumerate(basic):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))

    # NPRS - render as a standard kv_row (page-break safe, full width)
    nprs_val = _clean(str(pain.get("nprs_score", "N/A")))
    _kv_row(pdf, "NPRS Score", nprs_val, shaded=True)
    # Also draw the visual bar below the row for quick reference
    _pain_bar(pdf, nprs_val)

    _sub_banner(pdf, "Aggravating Factors")
    _bullet_list(pdf, pain.get("aggravating_factors", []))
    _sub_banner(pdf, "Relieving Factors")
    _bullet_list(pdf, pain.get("relieving_factors", []))
    pdf.ln(2)


def _render_past_history(pdf, ph: dict):
    _section_banner(pdf, "Past History")
    fields = [
        ("Medical History",    ph.get("medical")),
        ("Surgical History",   ph.get("surgical")),
        ("Medications",        ph.get("medications")),
        ("Family History",     ph.get("family")),
        ("Socioeconomic",      ph.get("socioeconomic")),
        ("Pre-morbid Status",  ph.get("pre_morbid_status")),
        ("Growth & Development", ph.get("growth_development")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_priorities(pdf, items: list):
    _section_banner(pdf, "Patient's Priorities & Functional Goals")
    _bullet_list(pdf, items)
    pdf.ln(2)


def _render_general_health_status(pdf, ghs: dict):
    _section_banner(pdf, "General Health Status")
    vitals = ghs.get("vitals", {})
    _sub_banner(pdf, "Vitals")
    vfields = [
        ("Blood Pressure",    vitals.get("blood_pressure")),
        ("Pulse",             vitals.get("pulse")),
        ("Respiratory Rate",  vitals.get("respiratory_rate")),
        ("Temperature",       vitals.get("temperature")),
        ("O2 Saturation",     vitals.get("oxygen_saturation")),
        ("Weight",            vitals.get("weight")),
        ("Height",            vitals.get("height")),
        ("BMI",               vitals.get("bmi")),
    ]
    for i, (k, v) in enumerate(vfields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))

    _sub_banner(pdf, "Clinical Examination")
    efields = [
        ("Lymph Nodes",        ghs.get("lymph_nodes")),
        ("Jaundice",           ghs.get("jaundice")),
        ("Pallor",             ghs.get("pallor")),
        ("Cyanosis",           ghs.get("cyanosis")),
        ("Edema",              ghs.get("edema")),
        ("Clubbing",           ghs.get("clubbing")),
        ("Overall Impression", ghs.get("overall_impression")),
    ]
    for i, (k, v) in enumerate(efields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_general_health_condition(pdf, ghc: dict):
    _section_banner(pdf, "General Health Condition")
    fields = [
        ("Malaise",         ghc.get("malaise")),
        ("Fatigue",         ghc.get("fatigue")),
        ("Fever",           ghc.get("fever")),
        ("Weight Changes",  ghc.get("weight_changes")),
        ("Sleep",           ghc.get("sleep")),
        ("Cognition",       ghc.get("cognition")),
        ("Mood / Affect",   ghc.get("mood")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_systems_review(pdf, sr: dict):
    _section_banner(pdf, "Systems Review")
    fields = [
        ("Cardiovascular",    sr.get("cardiovascular")),
        ("Pulmonary",         sr.get("pulmonary")),
        ("Gastrointestinal",  sr.get("gastrointestinal")),
        ("Urinary",           sr.get("urinary")),
        ("Integumentary",     sr.get("integumentary")),
        ("Endocrine",         sr.get("endocrine")),
        ("Reproductive",      sr.get("reproductive")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_musculoskeletal(pdf, ms: dict):
    _section_banner(pdf, "Musculoskeletal System")
    fields = [
        ("Gross Symmetry",    ms.get("gross_symmetry")),
        ("Posture",           ms.get("posture")),
        ("Deformity",         ms.get("deformity")),
        ("Swelling",          ms.get("swelling")),
        ("Tenderness",        ms.get("tenderness")),
        ("Muscle Wasting",    ms.get("muscle_wasting")),
        ("Muscle Spasm",      ms.get("spasm")),
        ("Cervical ROM",      ms.get("cervical_rom")),
        ("Lumbar ROM",        ms.get("lumbar_rom")),
        ("Upper Limb ROM",    ms.get("upper_limb_rom")),
        ("Lower Limb ROM",    ms.get("lower_limb_rom")),
        ("Muscle Strength",   ms.get("muscle_strength")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))

    special = ms.get("special_tests", [])
    if special:
        _sub_banner(pdf, "Special Tests")
        _bullet_list(pdf, special)
    pdf.ln(3)


def _render_neurological(pdf, ns: dict):
    _section_banner(pdf, "Neurological Assessment")
    fields = [
        ("Consciousness",         ns.get("consciousness")),
        ("Numbness / Tingling",   ns.get("numbness_tingling")),
        ("Reflexes",              ns.get("reflexes")),
        ("Muscle Tone",           ns.get("muscle_tone")),
        ("Coordination",          ns.get("coordination")),
        ("Gait",                  ns.get("gait")),
        ("Cranial Nerves",        ns.get("cranial_nerves")),
        ("Upper Motor Neuron",    ns.get("upper_motor_neuron")),
        ("Lower Motor Neuron",    ns.get("lower_motor_neuron")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_functional(pdf, fs: dict):
    _section_banner(pdf, "Functional Status")
    fields = [
        ("ADL Status",       fs.get("adl_status")),
        ("Mobility",         fs.get("mobility")),
        ("Work Status",      fs.get("work_status")),
        ("Recreational",     fs.get("recreational")),
        ("Assistive Devices",fs.get("assistive_devices")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    goals = fs.get("functional_goals", [])
    if goals:
        _sub_banner(pdf, "Functional Goals")
        _bullet_list(pdf, goals)
    pdf.ln(3)


def _render_investigations(pdf, inv: dict):
    _section_banner(pdf, "Investigations & Imaging")
    fields = [
        ("Imaging",  inv.get("imaging")),
        ("Lab Tests",inv.get("labs")),
        ("EMG / NCS",inv.get("emg_ncs")),
        ("Other",    inv.get("other")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_impression(pdf, d: dict):
    _section_banner(pdf, "Clinical Impression & Diagnosis")
    _narrative(pdf, d.get("clinical_impression", "Not Provided"))

    _section_banner(pdf, "Hypothesis / Problem Statement")
    _narrative(pdf, d.get("hypothesis_problem_statement", "Not Provided"))


def _render_treatment(pdf, tp: dict):
    _section_banner(pdf, "Treatment Plan")

    _sub_banner(pdf, "Short-Term Goals (0 - 2 Weeks)")
    _bullet_list(pdf, tp.get("short_term_goals", []))

    _sub_banner(pdf, "Long-Term Goals (3 - 6 Weeks)")
    _bullet_list(pdf, tp.get("long_term_goals", []))

    _sub_banner(pdf, "Physiotherapy Interventions")
    _bullet_list(pdf, tp.get("physiotherapy_interventions", []))

    _sub_banner(pdf, "Home Exercise Program")
    _bullet_list(pdf, tp.get("home_exercise_program", []))

    _sub_banner(pdf, "Patient Education")
    _bullet_list(pdf, tp.get("patient_education", []))

    fields = [
        ("Referrals",  tp.get("referrals")),
        ("Follow-up",  tp.get("follow_up")),
        ("Prognosis",  tp.get("prognosis")),
    ]
    for i, (k, v) in enumerate(fields):
        _kv_row(pdf, k, str(v or "Not Provided"), shaded=(i % 2 == 0))
    pdf.ln(3)


def _render_signature(pdf):
    """Signature block at the end."""
    pdf.ln(6)
    pdf.set_draw_color(*_TEAL_DARK)
    pdf.set_line_width(0.3)
    sig_y = pdf.get_y() + 4
    sig_x = pdf.l_margin
    pdf.line(sig_x, sig_y, sig_x + 65, sig_y)
    pdf.set_xy(sig_x, sig_y + 1)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*_MID_GRAY)
    pdf.cell(65, 5, "Physiotherapist Signature", align="C")

    pdf.set_xy(sig_x + 100, sig_y - 4)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(0, 5,
             f"Date: {datetime.now().strftime('%d %B %Y')}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)
    pdf.set_fill_color(240, 253, 250)
    pdf.set_text_color(*_MID_GRAY)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.multi_cell(
        0, 5,
        "DISCLAIMER: This document was generated with AI assistance to support clinical "
        "documentation. It must be reviewed, verified, and countersigned by the responsible "
        "physiotherapist before use as an official clinical record. CaseGen AI does not "
        "replace professional clinical judgment.",
        fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )


# =========================================================================
# Public API
# =========================================================================

def generate_pdf(patient_data: Dict[str, Any]) -> str:
    """
    Render a full enterprise clinical case study PDF from the
    validated ClinicalCaseStudy dict and return the file path.
    """
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    filename  = f"case_study_{uuid.uuid4().hex[:10]}.pdf"
    file_path = os.path.join(_OUTPUT_DIR, filename)

    pdf = _ClinicalPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(left=15, top=26, right=15)

    d = patient_data  # convenience alias

    _render_metadata(pdf, d)
    _render_demographics(pdf, d.get("demographics", {}))
    _render_complaint(pdf, d)
    _render_pain(pdf, d.get("pain_profile", {}))
    _render_past_history(pdf, d.get("past_history", {}))
    _render_priorities(pdf, d.get("patients_priorities", []))
    _render_general_health_status(pdf, d.get("general_health_status", {}))
    _render_general_health_condition(pdf, d.get("general_health_condition", {}))
    _render_systems_review(pdf, d.get("systems_review", {}))
    _render_musculoskeletal(pdf, d.get("musculoskeletal_system", {}))
    _render_neurological(pdf, d.get("neurological_system", {}))
    _render_functional(pdf, d.get("functional_status", {}))
    _render_investigations(pdf, d.get("investigations", {}))
    _render_impression(pdf, d)
    _render_treatment(pdf, d.get("treatment_plan", {}))

    # Additional notes (if any)
    notes = d.get("additional_notes", "None")
    if notes and notes.lower() not in ("none", "not provided", ""):
        _section_banner(pdf, "Additional Clinical Notes")
        _narrative(pdf, notes)

    _render_signature(pdf)

    try:
        pdf.output(file_path)
        logger.info("PDF saved: %s (%d pages)", file_path, pdf.page)
    except Exception as exc:
        logger.error("PDF write failed: %s", exc)
        raise OSError(f"PDF generation failed: {exc}") from exc

    return file_path