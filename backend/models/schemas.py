"""
models/schemas.py
-----------------
Enterprise-grade, deeply nested Pydantic schema for a full
physiotherapy clinical case study proforma.

Design rules
------------
- Every field has a safe default ("Not Provided" / "Normal" / [])
  so Pydantic never crashes on missing data from the LLM.
- Nested BaseModel classes group related clinical concepts together,
  making the JSON contract self-documenting.
- field_validator strips blank strings and replaces them with the
  default so the PDF renderer always has something to print.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Shared helper ─────────────────────────────────────────────────── #
NP = "Not Provided"
NL = "Normal"


def _default(v: str, fallback: str = NP) -> str:
    return v.strip() if isinstance(v, str) and v.strip() else fallback


# =========================================================================
# Level-1 nested models
# =========================================================================

class Demographics(BaseModel):
    name:             str = Field(default="Anonymous", description="Patient full name")
    age:              str = Field(default=NP)
    gender:           str = Field(default=NP)
    marital_status:   str = Field(default=NP)
    language:         str = Field(default=NP)
    occupation:       str = Field(default=NP)
    address:          str = Field(default=NP)
    mode_of_admission:str = Field(default="Outdoor / OPD")

    @field_validator("*", mode="before")
    @classmethod
    def no_blank(cls, v):
        return _default(str(v)) if isinstance(v, str) else v


class PainProfile(BaseModel):
    location:           str = Field(default=NP, description="Anatomical site of pain")
    onset:              str = Field(default=NP)
    duration:           str = Field(default=NP)
    nature:             str = Field(default=NP, description="e.g. dull ache, sharp, throbbing")
    aggravating_factors:List[str] = Field(default_factory=list)
    relieving_factors:  List[str] = Field(default_factory=list)
    nprs_score:         str = Field(default=NP, description="Pain score out of 10")
    radiation:          str = Field(default="No radiation reported")


class PastHistory(BaseModel):
    medical:      str = Field(default=NP)
    surgical:     str = Field(default="No previous surgeries reported")
    medications:  str = Field(default=NP)
    family:       str = Field(default=NP)
    socioeconomic:str = Field(default=NP)
    pre_morbid_status: str = Field(default=NP)
    growth_development: str = Field(default="Not applicable / within normal limits")


class Vitals(BaseModel):
    blood_pressure:    str = Field(default=NL)
    pulse:             str = Field(default=NL)
    respiratory_rate:  str = Field(default=NL)
    temperature:       str = Field(default=NL)
    oxygen_saturation: str = Field(default=NL)
    weight:            str = Field(default=NP)
    height:            str = Field(default=NP)
    bmi:               str = Field(default=NP)


class GeneralHealthStatus(BaseModel):
    vitals:             Vitals = Field(default_factory=Vitals)
    lymph_nodes:        str = Field(default="Not palpable")
    jaundice:           str = Field(default="Absent")
    pallor:             str = Field(default="Absent")
    cyanosis:           str = Field(default="Absent")
    edema:              str = Field(default="Absent")
    clubbing:           str = Field(default="Absent")
    overall_impression: str = Field(default="Patient is conscious, cooperative and hemodynamically stable")


class GeneralHealthCondition(BaseModel):
    malaise:        str = Field(default="None reported")
    fatigue:        str = Field(default="None reported")
    fever:          str = Field(default="Afebrile")
    weight_changes: str = Field(default="None reported")
    sleep:          str = Field(default="Not reported")
    cognition:      str = Field(default="Intact")
    mood:           str = Field(default="Cooperative and oriented")


class SystemsReview(BaseModel):
    cardiovascular:  str = Field(default="No complaints reported")
    pulmonary:       str = Field(default="No complaints reported")
    gastrointestinal:str = Field(default="No complaints reported")
    urinary:         str = Field(default="No complaints reported")
    integumentary:   str = Field(default="Skin intact, no wounds or lesions noted")
    endocrine:       str = Field(default="No complaints reported")
    reproductive:    str = Field(default="Not assessed / Not applicable")


class MusculoskeletalSystem(BaseModel):
    gross_symmetry:      str = Field(default=NL)
    posture:             str = Field(default=NP)
    deformity:           str = Field(default="None observed")
    swelling:            str = Field(default="None observed")
    tenderness:          str = Field(default=NP)
    muscle_wasting:      str = Field(default="None observed")
    spasm:               str = Field(default=NP)
    # ROM fields as free text to accommodate any joint
    cervical_rom:        str = Field(default=NP)
    lumbar_rom:          str = Field(default=NP)
    upper_limb_rom:      str = Field(default=NL)
    lower_limb_rom:      str = Field(default=NL)
    muscle_strength:     str = Field(default=NL)
    special_tests:       List[str] = Field(default_factory=list)


class NeurologicalSystem(BaseModel):
    consciousness:       str = Field(default="Conscious and oriented")
    numbness_tingling:   str = Field(default="None reported")
    reflexes:            str = Field(default=NL)
    muscle_tone:         str = Field(default=NL)
    coordination:        str = Field(default=NL)
    gait:                str = Field(default=NL)
    cranial_nerves:      str = Field(default="Not assessed / Intact")
    upper_motor_neuron:  str = Field(default="No signs of UMN lesion")
    lower_motor_neuron:  str = Field(default="No signs of LMN lesion")


class FunctionalStatus(BaseModel):
    adl_status:          str = Field(default=NP, description="Activities of Daily Living")
    mobility:            str = Field(default=NP)
    work_status:         str = Field(default=NP)
    recreational:        str = Field(default=NP)
    assistive_devices:   str = Field(default="None currently in use")
    functional_goals:    List[str] = Field(default_factory=list)


class Investigations(BaseModel):
    imaging:  str = Field(default="None provided / Not available")
    labs:     str = Field(default="None provided / Not available")
    emg_ncs:  str = Field(default="Not assessed")
    other:    str = Field(default="None")


class TreatmentPlan(BaseModel):
    short_term_goals:    List[str] = Field(default_factory=list)
    long_term_goals:     List[str] = Field(default_factory=list)
    physiotherapy_interventions: List[str] = Field(default_factory=list)
    home_exercise_program:       List[str] = Field(default_factory=list)
    patient_education:           List[str] = Field(default_factory=list)
    referrals:                   str = Field(default="None at this time")
    follow_up:                   str = Field(default=NP)
    prognosis:                   str = Field(default=NP)


# =========================================================================
# Root model
# =========================================================================

class ClinicalCaseStudy(BaseModel):
    """
    Full enterprise-grade physiotherapy assessment proforma.
    All fields are optional with safe defaults so the LLM can
    omit fields it cannot infer without crashing the pipeline.
    """

    # ── Case metadata ──────────────────────────────────────────────── #
    case_number:        str = Field(default="Auto-assigned")
    category:           str = Field(default="Outdoor")
    date:               str = Field(default="Not Provided")
    referring_physician:str = Field(default="Self-referred / Not specified")

    # ── Sections ──────────────────────────────────────────────────── #
    demographics:               Demographics         = Field(default_factory=Demographics)
    present_complaint:          str                  = Field(default=NP)
    history_of_present_complaint: str               = Field(default=NP)
    pain_profile:               PainProfile          = Field(default_factory=PainProfile)
    past_history:               PastHistory          = Field(default_factory=PastHistory)
    patients_priorities:        List[str]            = Field(default_factory=list)
    general_health_status:      GeneralHealthStatus  = Field(default_factory=GeneralHealthStatus)
    general_health_condition:   GeneralHealthCondition = Field(default_factory=GeneralHealthCondition)
    systems_review:             SystemsReview        = Field(default_factory=SystemsReview)
    musculoskeletal_system:     MusculoskeletalSystem= Field(default_factory=MusculoskeletalSystem)
    neurological_system:        NeurologicalSystem   = Field(default_factory=NeurologicalSystem)
    functional_status:          FunctionalStatus     = Field(default_factory=FunctionalStatus)
    investigations:             Investigations       = Field(default_factory=Investigations)
    clinical_impression:        str                  = Field(default=NP, description="Diagnosis / impression")
    hypothesis_problem_statement: str               = Field(default=NP)
    treatment_plan:             TreatmentPlan        = Field(default_factory=TreatmentPlan)
    additional_notes:           str                  = Field(default="None")