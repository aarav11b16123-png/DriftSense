import os
from typing import Any, Dict
from .schema import Incident
from .base import BaseAnalyzer

class RCAEngine:
    def __init__(self, log_dir: str = "logs"):
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def register(self, analyzer: BaseAnalyzer):
        """Register an analyzer for a specific layer."""
        self.analyzers[analyzer.layer] = analyzer

    def run(self, layer: str, payload: Any) -> Incident:
        """Run the RCA engine for the requested layer."""
        if layer not in self.analyzers:
            raise ValueError(f"No analyzer registered for layer: {layer}")
        
        # Analyze the payload
        incident = self.analyzers[layer].analyze(payload)
        
        # Log the incident persistently
        log_file = os.path.join(self.log_dir, "incidents.jsonl")
        with open(log_file, "a") as f:
            f.write(incident.model_dump_json() + "\n")
            
        return incident
