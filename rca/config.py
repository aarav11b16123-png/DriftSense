from typing import Dict, Any

# Exclude columns from drift analysis (e.g., target labels, index columns)
EXCLUDE_COLUMNS = ["SeriousDlqin2yrs", "Unnamed: 0", "index", "id"]

# Minimum samples to trust results
MIN_SAMPLES = 100

# Cause Codes
CAUSE_MISSING_VALUES_INCREASED = "MISSING_VALUES_INCREASED"
CAUSE_STUCK_OR_CONSTANT_VALUE = "STUCK_OR_CONSTANT_VALUE"
CAUSE_NEW_OR_UNSEEN_VALUES = "NEW_OR_UNSEEN_VALUES"
CAUSE_OUT_OF_RANGE_VALUES = "OUT_OF_RANGE_VALUES"
CAUSE_SCALE_OR_UNIT_CHANGE = "SCALE_OR_UNIT_CHANGE"
CAUSE_LOCATION_SHIFT = "LOCATION_SHIFT"
CAUSE_VARIANCE_CHANGE = "VARIANCE_CHANGE"
CAUSE_GRADUAL_OR_SEASONAL_SHIFT = "GRADUAL_OR_SEASONAL_SHIFT"
CAUSE_POPULATION_WIDE_SHIFT = "POPULATION_OR_PIPELINE_WIDE_SHIFT"

# Thresholds for statistical checks
THRESHOLDS = {
    "missing_values_pt_diff": 0.05,  # 5 percentage points increase
    "scale_cv_tol": 0.15,            # Coefficient of Variation of ratios < 15%
    "scale_min_effect": 0.1,         # |mean(ratio) - 1| > 10%
    "location_tol": 0.15,            # std of diffs < 0.15 (in ref_std units)
    "location_min_effect": 0.2,      # |mean(diff)| > 0.2 std units
    "variance_pct_change": 0.2,      # 20% change in std dev
    "mean_pct_change_tol": 0.1,      # Mean must be relatively stable for pure variance change
    "out_of_range_pct": 0.01,        # > 1% of data outside [p0.5, p99.5]
    "stuck_std_ratio": 0.01,         # current_std / ref_std < 0.01
    "new_unseen_pct": 0.01,          # > 1% new categories in discrete features
    "psi_moderate": 0.10,
    "psi_major": 0.25,
    "dataset_drift_share": 0.5,      # 50% of features drifted triggers dataset-level cause
    "discrete_unique_max": 20        # Max unique values to treat a numeric feature as discrete
}

CAUSES_META: Dict[str, Dict[str, str]] = {
    CAUSE_MISSING_VALUES_INCREASED: {
        "label": "Missing Values Increased",
        "action": "Investigate upstream data pipeline for dropped fields or parsing errors."
    },
    CAUSE_STUCK_OR_CONSTANT_VALUE: {
        "label": "Stuck or Constant Value",
        "action": "Check sensor/default value assignment. The feature has lost its variance."
    },
    CAUSE_NEW_OR_UNSEEN_VALUES: {
        "label": "New or Unseen Values",
        "action": "Review categorical encoding or domain changes (e.g. new codes like 98)."
    },
    CAUSE_OUT_OF_RANGE_VALUES: {
        "label": "Out of Range Values",
        "action": "Check for outlier spikes, unit changes (e.g. ms to sec) or missing decimals."
    },
    CAUSE_SCALE_OR_UNIT_CHANGE: {
        "label": "Scale or Unit Change",
        "action": "Check if upstream units changed (e.g. multiplied by 10, currency conversion)."
    },
    CAUSE_LOCATION_SHIFT: {
        "label": "Additive Location Shift",
        "action": "Check for additive bias/offset applied to the feature."
    },
    CAUSE_VARIANCE_CHANGE: {
        "label": "Variance Change",
        "action": "Check if natural variation changed while mean remained stable."
    },
    CAUSE_GRADUAL_OR_SEASONAL_SHIFT: {
        "label": "Gradual/Seasonal Distribution Shift",
        "action": "Consider retraining model or adapting baseline if shift is natural."
    },
    CAUSE_POPULATION_WIDE_SHIFT: {
        "label": "Population or Pipeline-Wide Shift",
        "action": "Many features moved together: suspect a new customer segment or an upstream change."
    }
}
