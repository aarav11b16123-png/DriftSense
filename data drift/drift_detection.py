import time
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance
from scipy.spatial.distance import jensenshannon
try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
except ImportError:
    from evidently.legacy.report import Report
    from evidently.legacy.metric_preset import DataDriftPreset
from river import drift

# ==========================================
# 1. BATCH STATISTICAL DRIFT FUNCTIONS
# ==========================================

def calculate_psi(expected, actual, buckets=10):
    """Calculate Population Stability Index (PSI) between two distributions."""
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    min_val = min(np.min(expected), np.min(actual))
    max_val = max(np.max(expected), np.max(actual))
    
    if min_val == max_val:
        return 0.0
        
    breakpoints = np.linspace(min_val, max_val, buckets + 1)
    
    expected_counts, _ = np.histogram(expected, bins=breakpoints)
    actual_counts, _ = np.histogram(actual, bins=breakpoints)
    
    expected_percents = expected_counts / len(expected)
    actual_percents = actual_counts / len(actual)
    
    epsilon = 1e-4
    expected_percents = np.where(expected_percents == 0, epsilon, expected_percents)
    actual_percents = np.where(actual_percents == 0, epsilon, actual_percents)
    
    psi_value = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
    return float(psi_value)

def check_ks_test(expected, actual):
    """Kolmogorov-Smirnov Test."""
    stat, p_value = ks_2samp(expected, actual)
    return {"statistic": float(stat), "p_value": float(p_value), "drift_detected": bool(p_value < 0.05)}

def check_js_divergence(expected, actual, bins=10):
    """Jensen-Shannon Divergence."""
    min_val = min(np.min(expected), np.min(actual))
    max_val = max(np.max(expected), np.max(actual))
    
    if min_val == max_val:
        return {"divergence": 0.0, "drift_detected": False}

    breakpoints = np.linspace(min_val, max_val, bins + 1)
    hist_expected, _ = np.histogram(expected, bins=breakpoints, density=True)
    hist_actual, _ = np.histogram(actual, bins=breakpoints, density=True)
    
    epsilon = 1e-10
    hist_expected = hist_expected + epsilon
    hist_actual = hist_actual + epsilon
    
    hist_expected /= np.sum(hist_expected)
    hist_actual /= np.sum(hist_actual)
    
    js_div = float(jensenshannon(hist_expected, hist_actual))
    return {"divergence": js_div, "drift_detected": bool(js_div > 0.1)}

def check_wasserstein(expected, actual):
    """Normalized Wasserstein Distance."""
    std_expected = np.std(expected)
    if std_expected == 0:
        std_expected = 1e-6
        
    raw_distance = wasserstein_distance(expected, actual)
    normalized_distance = raw_distance / std_expected
    
    return {
        "raw_distance": float(raw_distance),
        "normalized_distance": float(normalized_distance),
        "drift_detected": bool(normalized_distance > 0.2)
    }

def run_evidently_drift(reference_df, current_df):
    """Run Evidently AI Data Drift Report."""
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference_df, current_data=current_df)
    report_dict = report.as_dict()
    
    metrics_res = report_dict['metrics'][0]['result']
    return {
        "drift_detected": metrics_res['dataset_drift'],
        "share_of_drifted_columns": metrics_res['share_of_drifted_columns']
    }

def detect_drift(reference_data, current_data):
    """Combine customized batch statistical tests with Evidently AI reporting."""
    results = {}
    
    print("Running custom statistical tests...")
    for column in reference_data.columns:
        if pd.api.types.is_numeric_dtype(reference_data[column]):
            ref_col = reference_data[column].dropna().values
            cur_col = current_data[column].dropna().values
            
            if len(ref_col) == 0 or len(cur_col) == 0:
                continue

            psi_val = calculate_psi(ref_col, cur_col)
            ks_res = check_ks_test(ref_col, cur_col)
            js_res = check_js_divergence(ref_col, cur_col)
            wass_res = check_wasserstein(ref_col, cur_col)
            
            results[column] = {
                "PSI": {"value": psi_val, "drift_detected": psi_val > 0.25},
                "KS_Test": ks_res,
                "JS_Divergence": js_res,
                "Wasserstein": wass_res
            }
    
    print("Running Evidently AI report...")
    evidently_res = run_evidently_drift(reference_data, current_data)
    
    return {
        "column_level_stats": results,
        "evidently_overall": evidently_res
    }

# ==========================================
# 2. REAL-TIME STREAMING DRIFT (RIVER)
# ==========================================

def detect_streaming_drift(stream_data, feature_name="feature1", delay=0.001):
    """
    Simulates row-by-row streaming ingestion and detects real-time drift 
    using River's ADWIN (Adaptive Windowing) algorithm.
    """
    print(f"\n--- STARTING RIVER REAL-TIME DRIFT ENGINE FOR [{feature_name}] ---")
    adwin = drift.ADWIN()
    drift_events = []

    for idx, val in enumerate(stream_data[feature_name]):
        adwin.update(val)
        
        if adwin.drift_detected:
            print(f"🚨 REAL-TIME DRIFT DETECTED at Stream Index {idx} | Feature Value: {val:.4f}")
            drift_events.append({"index": idx, "value": val})
            # Reset detector to continue monitoring future stream points
            adwin = drift.ADWIN()
            
        time.sleep(delay)  # Simulates live latency/data arrival

    print(f"--- STREAMING COMPLETE | Total Drift Events Detected: {len(drift_events)} ---\n")
    return drift_events


# ==========================================
# 3. EXECUTION & TESTING BLOCK
# ==========================================

if __name__ == "__main__":
    print("Generating synthetic dataset to test drift detection pipeline...")
    
    # 1. Generate reference baseline distribution
    np.random.seed(42)
    reference_df = pd.DataFrame({
        "feature1": np.random.normal(loc=0, scale=1, size=1000),
        "feature2": np.random.uniform(low=0, high=10, size=1000)
    })
    
    # 2. Generate current distribution (Shift feature1 mean to simulate drift)
    current_df = pd.DataFrame({
        "feature1": np.random.normal(loc=1.5, scale=1, size=1000),  # Drifted feature
        "feature2": np.random.uniform(low=0, high=10, size=1000)     # Normal feature
    })
    
    # ----------------------------------------------------
    # TEST 1: BATCH DRIFT ANALYSIS
    # ----------------------------------------------------
    report = detect_drift(reference_df, current_df)
    
    print("\n================ BATCH DRIFT REPORT ================")
    print(f"Evidently AI Dataset Drift Detected: {report['evidently_overall']['drift_detected']}")
    print(f"Share of Drifted Columns: {report['evidently_overall']['share_of_drifted_columns']:.2%}")
    
    print("\nColumn-Level Statistical Metrics:")
    for col, metrics in report["column_level_stats"].items():
        print(f"\n[+] Feature: {col}")
        print(f"  - PSI: {metrics['PSI']['value']:.4f} (Drift: {metrics['PSI']['drift_detected']})")
        print(f"  - KS-Test p-value: {metrics['KS_Test']['p_value']:.4e} (Drift: {metrics['KS_Test']['drift_detected']})")
        print(f"  - JS Divergence: {metrics['JS_Divergence']['divergence']:.4f} (Drift: {metrics['JS_Divergence']['drift_detected']})")
        print(f"  - Wasserstein Distance (Normalized): {metrics['Wasserstein']['normalized_distance']:.4f} (Drift: {metrics['Wasserstein']['drift_detected']})")

    # ----------------------------------------------------
    # TEST 2: REAL-TIME STREAMING DRIFT ANALYSIS (RIVER)
    # ----------------------------------------------------
    # Concatenate normal data (500 rows) followed by shifted data (500 rows) to form a stream
    normal_stream = np.random.normal(loc=0, scale=1, size=500)
    drifted_stream = np.random.normal(loc=2.0, scale=1, size=500)
    
    streaming_df = pd.DataFrame({
        "feature1": np.concatenate([normal_stream, drifted_stream])
    })
    
    # Run River real-time streaming detector
    detect_streaming_drift(streaming_df, feature_name="feature1", delay=0.001)