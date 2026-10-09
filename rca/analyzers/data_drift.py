import numpy as np
import pandas as pd
from typing import Dict, Any, List

from ..schema import Incident, Finding, RootCause, Severity
from ..base import BaseAnalyzer
from ..config import (
    EXCLUDE_COLUMNS, MIN_SAMPLES, THRESHOLDS, CAUSES_META,
    CAUSE_MISSING_VALUES_INCREASED, CAUSE_STUCK_OR_CONSTANT_VALUE,
    CAUSE_NEW_OR_UNSEEN_VALUES, CAUSE_OUT_OF_RANGE_VALUES,
    CAUSE_SCALE_OR_UNIT_CHANGE, CAUSE_LOCATION_SHIFT,
    CAUSE_VARIANCE_CHANGE, CAUSE_GRADUAL_OR_SEASONAL_SHIFT,
    CAUSE_POPULATION_WIDE_SHIFT
)

class DataDriftAnalyzer(BaseAnalyzer):
    @property
    def layer(self) -> str:
        return "data_drift"

    def _calc_confidence(self, val: float, threshold: float, is_penalty: bool = False) -> float:
        if threshold == 0:
            threshold = 1e-9
        if is_penalty:
            ratio = (threshold - val) / threshold
        else:
            ratio = (val - threshold) / threshold
        conf = 0.5 + 0.5 * np.tanh(ratio)
        return float(np.clip(conf, 0.0, 1.0))

    def _create_cause(self, code: str, val: float, threshold: float, evidence: Dict[str, Any], is_penalty: bool = False, base_penalty: float = 1.0) -> RootCause:
        conf = self._calc_confidence(val, threshold, is_penalty) * base_penalty
        meta = CAUSES_META[code]
        return RootCause(
            code=code,
            label=meta["label"],
            confidence=conf,
            evidence=evidence,
            recommended_action=meta["action"]
        )

    def analyze(self, payload: Dict[str, Any]) -> Incident:
        ref_df: pd.DataFrame = payload["reference_df"]
        cur_df: pd.DataFrame = payload["current_df"]
        drift_report: Dict[str, Any] = payload.get("drift_report", {})
        
        base_penalty = 1.0
        if len(cur_df) < MIN_SAMPLES:
            base_penalty = 0.5
            
        findings: List[Finding] = []
        drifted_features_count = 0
        total_features_count = 0
        max_psi = 0.0
        has_data_quality_issue = False

        for col in ref_df.columns:
            if col in EXCLUDE_COLUMNS or not pd.api.types.is_numeric_dtype(ref_df[col]):
                continue
            
            total_features_count += 1
            
            ref_col = ref_df[col]
            cur_col = cur_df[col]
            
            causes: List[RootCause] = []
            
            # --- 2. Missing values ---
            ref_null_pct = ref_col.isna().mean()
            cur_null_pct = cur_col.isna().mean()
            null_pct_diff = cur_null_pct - ref_null_pct
            
            if null_pct_diff > THRESHOLDS["missing_values_pt_diff"]:
                causes.append(self._create_cause(
                    CAUSE_MISSING_VALUES_INCREASED,
                    val=null_pct_diff,
                    threshold=THRESHOLDS["missing_values_pt_diff"],
                    evidence={"ref_null_pct": ref_null_pct, "cur_null_pct": cur_null_pct, "diff": null_pct_diff},
                    base_penalty=base_penalty
                ))
                has_data_quality_issue = True
                
            ref_clean = ref_col.dropna()
            cur_clean = cur_col.dropna()
            
            if len(ref_clean) == 0 or len(cur_clean) == 0:
                if causes:
                    findings.append(Finding(item_id=col, description="All data missing.", verdict="DRIFT", causes=causes))
                continue
                
            ref_std = ref_clean.std()
            if pd.isna(ref_std) or ref_std == 0:
                ref_std = 1e-9
            cur_std = cur_clean.std()
            if pd.isna(cur_std):
                cur_std = 0.0

            ref_mean = ref_clean.mean()
            cur_mean = cur_clean.mean()
            
            psi_val = 0.0
            is_drifted = False
            if drift_report and "column_level_stats" in drift_report and col in drift_report["column_level_stats"]:
                col_stats = drift_report["column_level_stats"][col]
                psi_val = col_stats["PSI"].get("value", 0.0)
                is_drifted = (
                    col_stats["PSI"].get("drift_detected", False) or
                    col_stats.get("KS_Test", {}).get("drift_detected", False) or
                    col_stats.get("JS_Divergence", {}).get("drift_detected", False) or
                    col_stats.get("Wasserstein", {}).get("drift_detected", False)
                )
            
            max_psi = max(max_psi, psi_val)
            if is_drifted:
                drifted_features_count += 1

            is_discrete = ref_clean.nunique() <= THRESHOLDS["discrete_unique_max"]

            # --- 1. Per-bin PSI contribution ---
            # Used primarily as evidence for the gradual shift if nothing else fires
            top_bin_evidence = {}
            if is_discrete:
                ref_vc = ref_clean.value_counts(normalize=True)
                cur_vc = cur_clean.value_counts(normalize=True)
                all_vals = set(ref_vc.index).union(set(cur_vc.index))
                max_psi_contrib = 0.0
                top_val = None
                for v in all_vals:
                    p = max(ref_vc.get(v, 0.0), 1e-4)
                    q = max(cur_vc.get(v, 0.0), 1e-4)
                    contrib = (q - p) * np.log(q / p)
                    if contrib > max_psi_contrib:
                        max_psi_contrib = contrib
                        top_val = v
                if top_val is not None:
                    top_bin_evidence = {"top_contributing_value": float(top_val), "psi_contribution": max_psi_contrib}
            else:
                try:
                    bins = np.unique(np.percentile(ref_clean, np.linspace(0, 100, 11)))
                    if len(bins) > 1:
                        ref_counts, _ = np.histogram(ref_clean, bins=bins)
                        cur_counts, _ = np.histogram(cur_clean, bins=bins)
                        ref_p = np.maximum(ref_counts / len(ref_clean), 1e-4)
                        cur_p = np.maximum(cur_counts / len(cur_clean), 1e-4)
                        contribs = (cur_p - ref_p) * np.log(cur_p / ref_p)
                        max_idx = np.argmax(contribs)
                        top_bin_evidence = {
                            "top_contributing_range": f"{bins[max_idx]:.4f} to {bins[max_idx+1]:.4f}",
                            "psi_contribution": contribs[max_idx]
                        }
                except:
                    pass

            # --- 6. Stuck / Constant ---
            nunique_cur = cur_clean.nunique()
            std_ratio = cur_std / ref_std
            if std_ratio < THRESHOLDS["stuck_std_ratio"] or nunique_cur == 1:
                causes.append(self._create_cause(
                    CAUSE_STUCK_OR_CONSTANT_VALUE,
                    val=THRESHOLDS["stuck_std_ratio"] - std_ratio,
                    threshold=THRESHOLDS["stuck_std_ratio"],
                    evidence={"ref_std": ref_std, "cur_std": cur_std, "std_ratio": std_ratio, "nunique": nunique_cur},
                    base_penalty=base_penalty
                ))
                has_data_quality_issue = True
                
            # --- 7. New unseen values ---
            if is_discrete:
                ref_unique = set(ref_clean.unique())
                cur_unique = set(cur_clean.unique())
                new_vals = cur_unique - ref_unique
                if new_vals:
                    new_vals_count = cur_clean.isin(new_vals).sum()
                    new_vals_pct = new_vals_count / len(cur_clean)
                    if new_vals_pct > THRESHOLDS["new_unseen_pct"]:
                        causes.append(self._create_cause(
                            CAUSE_NEW_OR_UNSEEN_VALUES,
                            val=new_vals_pct,
                            threshold=THRESHOLDS["new_unseen_pct"],
                            evidence={"new_values_list": list(new_vals)[:5], "new_values_pct": new_vals_pct},
                            base_penalty=base_penalty
                        ))
                        has_data_quality_issue = True

            # --- 5. Out of range ---
            p05 = ref_clean.quantile(0.005)
            p995 = ref_clean.quantile(0.995)
            outliers = cur_clean[(cur_clean < p05) | (cur_clean > p995)]
            outlier_pct = len(outliers) / len(cur_clean)
            if outlier_pct > THRESHOLDS["out_of_range_pct"]:
                causes.append(self._create_cause(
                    CAUSE_OUT_OF_RANGE_VALUES,
                    val=outlier_pct,
                    threshold=THRESHOLDS["out_of_range_pct"],
                    evidence={"ref_p005": p05, "ref_p995": p995, "outlier_pct": outlier_pct},
                    base_penalty=base_penalty
                ))
                has_data_quality_issue = True
                
            # --- 3. Location/Scale (Deciles) ---
            deciles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
            ref_q = ref_clean.quantile(deciles)
            cur_q = cur_clean.quantile(deciles)
            
            d_i = (cur_q - ref_q) / ref_std
            std_di = d_i.std()
            mean_di = d_i.mean()
            
            r_i = []
            for dec in deciles:
                if abs(ref_q[dec]) > 1e-6:
                    r_i.append(cur_q[dec] / ref_q[dec])
            r_i_arr = np.array(r_i)
            
            if len(r_i_arr) > 0:
                mean_ri = r_i_arr.mean()
                std_ri = r_i_arr.std()
                cv_ri = std_ri / abs(mean_ri) if mean_ri != 0 else float('inf')
                
                if cv_ri < THRESHOLDS["scale_cv_tol"] and abs(mean_ri - 1.0) > THRESHOLDS["scale_min_effect"]:
                    causes.append(self._create_cause(
                        CAUSE_SCALE_OR_UNIT_CHANGE,
                        val=abs(mean_ri - 1.0),
                        threshold=THRESHOLDS["scale_min_effect"],
                        evidence={"mean_ratio": mean_ri, "cv_ratio": cv_ri},
                        base_penalty=base_penalty
                    ))
            
            if std_di < THRESHOLDS["location_tol"] and abs(mean_di) > THRESHOLDS["location_min_effect"]:
                causes.append(self._create_cause(
                    CAUSE_LOCATION_SHIFT,
                    val=abs(mean_di),
                    threshold=THRESHOLDS["location_min_effect"],
                    evidence={"mean_diff_std_units": mean_di, "std_diffs": std_di},
                    base_penalty=base_penalty
                ))
                
            # --- 4. Variance change ---
            var_pct_change = abs(cur_std - ref_std) / ref_std
            mean_pct_change = abs(cur_mean - ref_mean) / ref_std
            if var_pct_change > THRESHOLDS["variance_pct_change"] and mean_pct_change < THRESHOLDS["mean_pct_change_tol"]:
                causes.append(self._create_cause(
                    CAUSE_VARIANCE_CHANGE,
                    val=var_pct_change,
                    threshold=THRESHOLDS["variance_pct_change"],
                    evidence={"ref_std": ref_std, "cur_std": cur_std, "pct_change": var_pct_change},
                    base_penalty=base_penalty
                ))
                
            # --- Gradual Shift (Fallback) ---
            if is_drifted and not causes:
                grad_evidence = {"psi": psi_val}
                grad_evidence.update(top_bin_evidence)
                causes.append(RootCause(
                    code=CAUSE_GRADUAL_OR_SEASONAL_SHIFT,
                    label=CAUSES_META[CAUSE_GRADUAL_OR_SEASONAL_SHIFT]["label"],
                    confidence=0.5 * base_penalty,
                    evidence=grad_evidence,
                    recommended_action=CAUSES_META[CAUSE_GRADUAL_OR_SEASONAL_SHIFT]["action"]
                ))
                
            causes.sort(key=lambda x: x.confidence, reverse=True)
            
            if causes:
                verdict = "DRIFT_EXPLAINED" if is_drifted else "DATA_QUALITY_ISSUE"
                if not is_drifted and causes[0].code == CAUSE_GRADUAL_OR_SEASONAL_SHIFT:
                    continue
                
                desc = f"Identified {len(causes)} probable causes for {col}."
                if base_penalty < 1.0:
                    desc += " (Low confidence due to small sample size)"
                
                findings.append(Finding(item_id=col, description=desc, verdict=verdict, causes=causes))
        
        # --- Dataset Level Causes ---
        dataset_causes: List[RootCause] = []
        if total_features_count > 0:
            share = drifted_features_count / total_features_count
            if share >= THRESHOLDS["dataset_drift_share"]:
                dataset_causes.append(RootCause(
                    code=CAUSE_POPULATION_WIDE_SHIFT,
                    label=CAUSES_META[CAUSE_POPULATION_WIDE_SHIFT]["label"],
                    confidence=self._calc_confidence(share, THRESHOLDS["dataset_drift_share"]) * base_penalty,
                    evidence={"drifted_share": share, "drifted_count": drifted_features_count, "total_count": total_features_count},
                    recommended_action=CAUSES_META[CAUSE_POPULATION_WIDE_SHIFT]["action"]
                ))
                
        severity = Severity.NONE
        if max_psi >= THRESHOLDS["psi_major"]:
            severity = Severity.MAJOR
        elif max_psi >= THRESHOLDS["psi_moderate"]:
            severity = Severity.MODERATE
            
        if has_data_quality_issue and severity in [Severity.NONE, Severity.MODERATE]:
            severity = Severity.DATA_QUALITY
            
        summary = "No significant drift or data quality issues detected." if severity == Severity.NONE else f"Detected {len(findings)} features with data drift or quality issues. Max PSI: {max_psi:.2f}."
            
        return Incident(
            layer=self.layer,
            severity=severity,
            symptom=f"Batch drift report identified anomalies across {drifted_features_count} features.",
            metrics={"max_psi": max_psi, "drifted_features": drifted_features_count},
            findings=findings,
            dataset_level_causes=dataset_causes,
            summary=summary
        )
