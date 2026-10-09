from .schema import Incident

def to_markdown(incident: Incident) -> str:
    """Format the Incident as a readable Markdown report."""
    lines = []
    lines.append(f"# RCA Report: {incident.layer.upper()} (Severity: {incident.severity.value})")
    lines.append(f"**Date:** {incident.created_at}")
    lines.append(f"**Symptom:** {incident.symptom}")
    lines.append(f"**Summary:** {incident.summary}")
    
    if incident.dataset_level_causes:
        lines.append("\n## Dataset-Level Causes")
        for cause in incident.dataset_level_causes:
            lines.append(f"- **{cause.label}** (Confidence: {cause.confidence:.2f})")
            lines.append(f"  - *Evidence:* {cause.evidence}")
            lines.append(f"  - *Action:* {cause.recommended_action}")
            
    if incident.findings:
        lines.append("\n## Feature-Level Findings")
        for finding in incident.findings:
            lines.append(f"### {finding.item_id}")
            lines.append(f"**Verdict:** {finding.verdict} | {finding.description}")
            for cause in finding.causes:
                lines.append(f"- **{cause.label}** (Confidence: {cause.confidence:.2f})")
                lines.append(f"  - *Evidence:* {cause.evidence}")
                lines.append(f"  - *Action:* {cause.recommended_action}")
                
    return "\n".join(lines)

def to_json(incident: Incident) -> str:
    """Format the Incident as a JSON string."""
    return incident.model_dump_json(indent=2)
