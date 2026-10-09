import json
import sys
import os
import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data drift')))
from drift_detection import detect_drift

from rca.analyzers.data_drift import DataDriftAnalyzer
from rca.config import (
    CAUSE_SCALE_OR_UNIT_CHANGE,
    CAUSE_LOCATION_SHIFT,
    CAUSE_VARIANCE_CHANGE,
    CAUSE_MISSING_VALUES_INCREASED,
    CAUSE_STUCK_OR_CONSTANT_VALUE,
    CAUSE_NEW_OR_UNSEEN_VALUES,
    CAUSE_OUT_OF_RANGE_VALUES
)

def inject_fault(df: pd.DataFrame, fault_type: str, seed: int):
    np.random.seed(seed)
    df_cur = df.copy()
    
    col = "MonthlyIncome"
    if fault_type == "SCALE":
        df_cur[col] = df_cur[col] * 1.5
    elif fault_type == "LOCATION":
        df_cur[col] = df_cur[col] + df_cur[col].std()
    elif fault_type == "VARIANCE":
        noise = np.random.normal(0, df_cur[col].std(), len(df_cur))
        df_cur[col] = df_cur[col] + noise
    elif fault_type == "MISSING":
        idx = np.random.choice(df_cur.index, size=int(len(df_cur)*0.2), replace=False)
        df_cur.loc[idx, col] = np.nan
    elif fault_type == "STUCK":
        df_cur[col] = df_cur[col].median()
    elif fault_type == "NEW_UNSEEN":
        col = "NumberOfDependents"
        idx = np.random.choice(df_cur.index, size=int(len(df_cur)*0.05), replace=False)
        df_cur.loc[idx, col] = 98
    elif fault_type == "OUT_OF_RANGE":
        idx = np.random.choice(df_cur.index, size=int(len(df_cur)*0.05), replace=False)
        df_cur.loc[idx, col] = df_cur[col].max() * 10
    
    return df_cur, col

def run_evaluation():
    try:
        ref_df = pd.read_csv("data/processed/reference.csv")
    except:
        np.random.seed(0)
        ref_df = pd.DataFrame({
            "MonthlyIncome": np.random.normal(5000, 2000, 5000),
            "NumberOfDependents": np.random.choice([0, 1, 2, 3], 5000),
            "SeriousDlqin2yrs": np.random.choice([0, 1], 5000)
        })
        idx = np.random.choice(ref_df.index, size=int(len(ref_df)*0.2), replace=False)
        ref_df.loc[idx, "MonthlyIncome"] = np.nan

    analyzer = DataDriftAnalyzer()
    
    faults = ["NONE", "SCALE", "LOCATION", "VARIANCE", "MISSING", "STUCK", "NEW_UNSEEN", "OUT_OF_RANGE"]
    expected_causes = {
        "NONE": None,
        "SCALE": CAUSE_SCALE_OR_UNIT_CHANGE,
        "LOCATION": CAUSE_LOCATION_SHIFT,
        "VARIANCE": CAUSE_VARIANCE_CHANGE,
        "MISSING": CAUSE_MISSING_VALUES_INCREASED,
        "STUCK": CAUSE_STUCK_OR_CONSTANT_VALUE,
        "NEW_UNSEEN": CAUSE_NEW_OR_UNSEEN_VALUES,
        "OUT_OF_RANGE": CAUSE_OUT_OF_RANGE_VALUES
    }
    
    results = {}
    confusion_matrix = {f: {e: 0 for e in expected_causes.values() if e is not None} for f in faults}
    for f in faults:
        confusion_matrix[f]["NONE"] = 0
        
    for fault in faults:
        correct = 0
        trials = 30 if fault != "NONE" else 30
        
        for seed in range(trials):
            if fault == "NONE":
                cur_df = ref_df.sample(frac=1.0, replace=True, random_state=seed)
                target_col = "MonthlyIncome"
            else:
                cur_df, target_col = inject_fault(ref_df, fault, seed)
            
            report = detect_drift(ref_df, cur_df)
            incident = analyzer.analyze({"reference_df": ref_df, "current_df": cur_df, "drift_report": report})
            
            finding = next((f for f in incident.findings if f.item_id == target_col), None)
            
            # Since OUT_OF_RANGE is sensitive, we look at whether our expected cause is at least triggered.
            # For strict confusion matrix, we take the top cause.
            top_cause = finding.causes[0].code if finding and finding.causes else "NONE"
            
            if top_cause not in confusion_matrix[fault]:
                confusion_matrix[fault][top_cause] = 0
            confusion_matrix[fault][top_cause] += 1
            
            if top_cause == expected_causes[fault]:
                correct += 1
            elif fault == "NONE" and top_cause == "NONE":
                correct += 1
                
        acc = correct / trials
        results[fault] = {"accuracy": acc, "trials": trials}
        
    print("\n--- FAULT INJECTION EVALUATION ---")
    for fault, res in results.items():
        print(f"Fault: {fault.ljust(15)} | Top-1 Accuracy: {res['accuracy']:.2%}")
        
    print("\nConfusion Matrix:")
    headers = ["NONE"] + [c for c in expected_causes.values() if c is not None]
    
    print(f"{'True \\ Pred'.ljust(15)} " + " ".join([h[:6].ljust(6) for h in headers]))
    for fault in faults:
        row_str = f"{fault.ljust(15)} "
        for h in headers:
            count = confusion_matrix[fault].get(h, 0)
            row_str += str(count).ljust(6) + " "
        print(row_str)
        
    with open("reports/rca_eval_data_drift.json", "w") as f:
        json.dump({"accuracy": results, "confusion_matrix": confusion_matrix}, f, indent=2)
    print("\nEvaluation saved to reports/rca_eval_data_drift.json")

if __name__ == "__main__":
    run_evaluation()
