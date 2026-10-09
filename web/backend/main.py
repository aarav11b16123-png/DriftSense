import os
import sys
import re
import io

# ── path setup: backend lives in web/backend, project root is two levels up ──
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "data drift"))

import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from drift_detection import detect_drift
from rca.engine import RCAEngine
from rca.analyzers.data_drift import DataDriftAnalyzer
from rca.report import to_markdown, to_json as rca_to_json

app = FastAPI(title="AI Observability Web API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── shared RCA engine (singleton) ────────────────────────────────────────────
_engine = RCAEngine(log_dir=os.path.join(PROJECT_ROOT, "logs"))
_engine.register(DataDriftAnalyzer())


def _safe(text: str) -> str:
    """Strip non-latin-1 chars so fpdf 1.7.x doesn't crash."""
    return re.sub(r"[^\x00-\xFF]", "", str(text))


def _make_pdf(incident) -> bytes:
    """Generate PDF compatible with fpdf 1.7.x (Anaconda) and fpdf2."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, _safe("AI Observability - RCA Report"), ln=True, align="C")
            self.set_font("Helvetica", size=9)
            self.cell(0, 6, _safe(f"Generated: {incident['created_at']}  |  ID: {incident['incident_id']}"), ln=True, align="C")
            self.ln(3)
            self.set_draw_color(120, 120, 120)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    sev_colors = {
        "MAJOR": (220, 53, 69), "DATA_QUALITY": (255, 133, 27),
        "MODERATE": (255, 193, 7), "NONE": (40, 167, 69),
    }
    r, g, b = sev_colors.get(incident["severity"], (100, 100, 100))

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 8, _safe(f"Severity: {incident['severity']}"), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, _safe(f"Summary: {incident['summary']}"))
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Key Metrics", ln=True)
    pdf.set_font("Helvetica", size=10)
    for k, v in incident.get("metrics", {}).items():
        pdf.cell(0, 6, _safe(f"  {k}: {v}"), ln=True)
    pdf.ln(3)

    if incident.get("dataset_level_causes"):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Dataset-Level Probable Causes", ln=True)
        for c in incident["dataset_level_causes"]:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, _safe(f"  [{c['code']}] {c['label']}  (Confidence: {c['confidence']:.2f})"), ln=True)
            pdf.set_font("Helvetica", size=9)
            for ek, ev in c.get("evidence", {}).items():
                pdf.cell(0, 5, _safe(f"    {ek}: {ev}"), ln=True)
            pdf.multi_cell(0, 5, _safe(f"  Action: {c['recommended_action']}"))
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Feature-Level Findings", ln=True)
    for finding in incident.get("findings", []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 7, _safe(f"Feature: {finding['item_id']}  |  {finding['verdict']}"), ln=True, fill=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 5, _safe(finding["description"]), ln=True)
        for cause in finding.get("causes", []):
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, _safe(f"  {cause['label']}  (Confidence: {cause['confidence']:.2f})"), ln=True)
            pdf.set_font("Helvetica", size=8)
            for ek, ev in cause.get("evidence", {}).items():
                pdf.cell(0, 4, _safe(f"    {ek}: {str(ev)[:80]}"), ln=True)
            pdf.multi_cell(0, 4, _safe(f"  Action: {cause['recommended_action']}"))
        pdf.ln(2)

    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4,
        "Note: All causes are PROBABLE CAUSES WITH EVIDENCE, not proven causality. "
        "Generated deterministically - no LLM or paid API used."
    )
    raw = pdf.output(dest="S")
    return raw.encode("latin-1") if isinstance(raw, str) else bytes(raw)


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_csv(upload: UploadFile) -> pd.DataFrame:
    content = upload.file.read()
    return pd.read_csv(io.BytesIO(content))


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Observability Web API"}


@app.post("/api/drift")
async def run_drift(
    reference: UploadFile = File(...),
    current: UploadFile = File(...),
):
    """Run all drift tests (PSI, KS, JS, Wasserstein, Evidently) and return results."""
    try:
        ref_df = _read_csv(reference)
        cur_df = _read_csv(current)
        report = detect_drift(ref_df, cur_df)
        return JSONResponse(report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rca")
async def run_rca(
    reference: UploadFile = File(...),
    current: UploadFile = File(...),
):
    """Run full drift + RCA in one shot and return structured incident JSON."""
    try:
        ref_df = _read_csv(reference)
        cur_df = _read_csv(current)
        drift_report = detect_drift(ref_df, cur_df)
        incident = _engine.run("data_drift", {
            "reference_df": ref_df,
            "current_df": cur_df,
            "drift_report": drift_report,
        })
        result = incident.model_dump()
        result["drift_report"] = drift_report
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rca/pdf")
async def download_pdf(
    reference: UploadFile = File(...),
    current: UploadFile = File(...),
):
    """Run RCA and return a downloadable PDF report."""
    try:
        ref_df = _read_csv(reference)
        cur_df = _read_csv(current)
        drift_report = detect_drift(ref_df, cur_df)
        incident = _engine.run("data_drift", {
            "reference_df": ref_df,
            "current_df": cur_df,
            "drift_report": drift_report,
        })
        pdf_bytes = _make_pdf(incident.model_dump())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=rca_report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rca/markdown")
async def download_markdown(
    reference: UploadFile = File(...),
    current: UploadFile = File(...),
):
    """Run RCA and return a Markdown report."""
    try:
        ref_df = _read_csv(reference)
        cur_df = _read_csv(current)
        drift_report = detect_drift(ref_df, cur_df)
        incident = _engine.run("data_drift", {
            "reference_df": ref_df,
            "current_df": cur_df,
            "drift_report": drift_report,
        })
        md = to_markdown(incident)
        return Response(
            content=md,
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=rca_report.md"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
