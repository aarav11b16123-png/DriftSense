import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from river import drift

app = FastAPI(title="AI Observability Logging API")

# Global in-memory storage for logging endpoints
batch_storage: List[Dict[str, Any]] = []
stream_buffer: List[Dict[str, Any]] = []
adwin_detectors: Dict[str, drift.ADWIN] = {}

class PredictionPayload(BaseModel):
    features: Dict[str, float]

class BatchPayload(BaseModel):
    data: List[Dict[str, float]]

@app.post("/api/v1/log-batch")
async def log_batch(payload: BatchPayload):
    """Receives batch logs from user applications."""
    batch_storage.extend(payload.data)
    return {"status": "success", "logged_records": len(payload.data)}

@app.get("/api/v1/get-batch-data")
async def get_batch_data():
    """Exposes batch data logged via API."""
    return {"data": batch_storage}

@app.post("/api/v1/log-stream")
async def log_stream(payload: PredictionPayload):
    """
    Receives live single predictions, updates River ADWIN detector, 
    and checks for real-time drift.
    """
    record = payload.features
    drift_alerts = {}

    for col, val in record.items():
        if col not in adwin_detectors:
            adwin_detectors[col] = drift.ADWIN()
        
        adwin_detectors[col].update(val)
        if adwin_detectors[col].drift_detected:
            drift_alerts[col] = True
            adwin_detectors[col] = drift.ADWIN() # Reset on drift

    record_entry = {
        "features": record,
        "drift_alerts": drift_alerts
    }
    stream_buffer.append(record_entry)
    return {"status": "logged", "drift_alerts": drift_alerts}

@app.get("/api/v1/get-stream-data")
async def get_stream_data():
    """Exposes live stream history to UI."""
    return {"stream": stream_buffer}