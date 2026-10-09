from enum import Enum
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class Severity(str, Enum):
    NONE = "NONE"
    DATA_QUALITY = "DATA_QUALITY"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"

class RootCause(BaseModel):
    code: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: Dict[str, Any]
    recommended_action: str

class Finding(BaseModel):
    item_id: str
    description: str
    verdict: str
    causes: List[RootCause]

class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    layer: Literal["data_drift", "model_drift", "rag_hallucination"]
    severity: Severity
    symptom: str
    metrics: Dict[str, Any]
    findings: List[Finding]
    dataset_level_causes: List[RootCause]
    summary: str
