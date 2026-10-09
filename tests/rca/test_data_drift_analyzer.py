import numpy as np
import pandas as pd
import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data drift')))
from drift_detection import detect_drift

from rca.analyzers.data_drift import DataDriftAnalyzer
from rca.schema import Severity
from rca.config import (
    CAUSE_SCALE_OR_UNIT_CHANGE,
    CAUSE_LOCATION_SHIFT,
    CAUSE_VARIANCE_CHANGE,
    CAUSE_MISSING_VALUES_INCREASED,
    CAUSE_STUCK_OR_CONSTANT_VALUE,
    CAUSE_NEW_OR_UNSEEN_VALUES,
    CAUSE_OUT_OF_RANGE_VALUES,
    CAUSE_POPULATION_WIDE_SHIFT
)

@pytest.fixture
def analyzer():
    return DataDriftAnalyzer()

def generate_baseline(size=1000, seed=42):
    np.random.seed(seed)
    return pd.DataFrame({
        "f_scale": np.random.normal(10, 2, size),
        "f_loc": np.random.normal(5, 1, size),
        "f_var": np.random.normal(0, 1, size),
        "f_miss": np.random.normal(0, 1, size),
        "f_stuck": np.random.normal(100, 10, size),
        "f_new": np.random.choice([1, 2, 3], size),
        "f_out": np.random.normal(0, 1, size),
        "f_control": np.random.normal(0, 1, size)
    })

def test_no_fault_control(analyzer):
    ref_df = generate_baseline()
    cur_df = generate_baseline(seed=43) 
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    # Check that if it found out_of_range, it's just due to natural variance.
    # We allow DATA_QUALITY since natural 1% might trigger OUT_OF_RANGE if threshold is 1%
    assert incident.severity in [Severity.NONE, Severity.DATA_QUALITY]

def test_scale_change(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df["f_scale"] = cur_df["f_scale"] * 1.5
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_scale"), None)
    assert finding is not None
    # Depending on severity of out-of-range vs scale, check if scale is present
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_SCALE_OR_UNIT_CHANGE in causes_codes

def test_location_shift(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df["f_loc"] = cur_df["f_loc"] + 1.0
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_loc"), None)
    assert finding is not None
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_LOCATION_SHIFT in causes_codes

def test_variance_change(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df["f_var"] = cur_df["f_var"] * 2.0 
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_var"), None)
    assert finding is not None
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_VARIANCE_CHANGE in causes_codes

def test_missing_values_increased(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df.loc[np.random.choice(cur_df.index, size=int(len(cur_df)*0.2), replace=False), "f_miss"] = np.nan
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_miss"), None)
    assert finding is not None
    assert finding.causes[0].code == CAUSE_MISSING_VALUES_INCREASED
    assert incident.severity == Severity.DATA_QUALITY

def test_stuck_or_constant(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df["f_stuck"] = 100.0 
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_stuck"), None)
    assert finding is not None
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_STUCK_OR_CONSTANT_VALUE in causes_codes

def test_new_or_unseen_values(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    cur_df.loc[np.random.choice(cur_df.index, size=50, replace=False), "f_new"] = 98
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_new"), None)
    assert finding is not None
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_NEW_OR_UNSEEN_VALUES in causes_codes

def test_out_of_range(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    max_val = ref_df["f_out"].max()
    cur_df.loc[np.random.choice(cur_df.index, size=50, replace=False), "f_out"] = max_val * 10
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    finding = next((f for f in incident.findings if f.item_id == "f_out"), None)
    assert finding is not None
    causes_codes = [c.code for c in finding.causes]
    assert CAUSE_OUT_OF_RANGE_VALUES in causes_codes

def test_population_wide_shift(analyzer):
    ref_df = generate_baseline()
    cur_df = ref_df.copy()
    
    cur_df["f_scale"] = cur_df["f_scale"] * 1.5
    cur_df["f_loc"] = cur_df["f_loc"] + 2.0
    cur_df["f_var"] = cur_df["f_var"] * 2.0
    cur_df["f_out"] = cur_df["f_out"] + 10.0
    
    report = detect_drift(ref_df, cur_df)
    incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
    
    assert len(incident.dataset_level_causes) > 0
    assert incident.dataset_level_causes[0].code == CAUSE_POPULATION_WIDE_SHIFT
