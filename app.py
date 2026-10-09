import os
import sys
import io
import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from river import drift

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'data drift')))
from drift_detection import detect_drift

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="AI Observability Engine", layout="wide")
st.title("🛡️ Enterprise AI Observability Platform")

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
main_mode = st.sidebar.radio(
    "Observability Module",
    ["📊 Data Drift", "🤖 Model Drift", "🔍 RAG Hallucination"]
)

if main_mode != "📊 Data Drift":
    st.info(f"{main_mode} module is under construction. Data Drift is available now.")
    st.stop()

st.sidebar.markdown("---")
option = st.sidebar.radio(
    "Select Integration Mode",
    [
        "Option 1: CSV File Upload (Batch)",
        "Option 2: Application API Integration",
        "Option 3: Live Real-Time River Simulation (Demo for Mam)"
    ]
)

# ---------------------------------------------------------------------------
# Helper: PDF generator using fpdf2
# ---------------------------------------------------------------------------
def generate_pdf_report(incident) -> bytes:
    """Generate a structured PDF report from an RCA Incident object."""

    import re
    from fpdf import FPDF

    def safe(text) -> str:
        """Remove unsupported characters and normalize whitespace."""
        text = str(text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Keep printable Latin-1 characters and newlines.
        text = re.sub(r"[^\x20-\xFF\n\t]", "", text)
        return text.strip()

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(
                0, 10,
                safe("AI Observability Platform - RCA Report"),
                new_x="LMARGIN", new_y="NEXT", align="C"
            )

            self.set_font("Helvetica", size=9)
            header_text = (
                f"Generated: {incident.created_at} | "
                f"Incident: {incident.incident_id}"
            )
            self.multi_cell(0, 6, safe(header_text), align="C")
            self.ln(3)

            self.set_draw_color(100, 100, 100)
            self.line(
                self.l_margin, self.get_y(),
                self.w - self.r_margin, self.get_y()
            )
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = PDF(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Consistent text rendering and wrapping.
    def write_line(text, height=5, bold=False, size=9):
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            0, height, safe(text),
            new_x="LMARGIN", new_y="NEXT"
        )

    # --- Severity and summary ---
    severity = incident.severity.value
    severity_colors = {
        "MAJOR": (220, 53, 69),
        "DATA_QUALITY": (255, 133, 27),
        "MODERATE": (255, 193, 7),
        "NONE": (40, 167, 69),
    }

    r, g, b = severity_colors.get(severity, (100, 100, 100))

    pdf.set_text_color(r, g, b)
    write_line(f"Severity: {severity}", height=8, bold=True, size=12)

    pdf.set_text_color(0, 0, 0)
    write_line(f"Symptom: {incident.symptom}", height=6, size=10)
    write_line(f"Summary: {incident.summary}", height=6, size=10)
    pdf.ln(4)

    # --- Key metrics ---
    write_line("Key Metrics", height=7, bold=True, size=11)

    for key, value in incident.metrics.items():
        write_line(f" - {key}: {value}", height=5, size=9)

    pdf.ln(4)

    # --- Dataset-level causes ---
    if incident.dataset_level_causes:
        write_line(
            "Dataset-Level Probable Causes",
            height=7, bold=True, size=11
        )

        for cause in incident.dataset_level_causes:
            write_line(
                f"[{cause.code}] {cause.label} "
                f"(Confidence: {cause.confidence:.2f})",
                height=6, bold=True, size=9
            )

            for key, value in cause.evidence.items():
                write_line(f"  {key}: {value}", height=5, size=8)

            write_line(
                f"Action: {cause.recommended_action}",
                height=5, size=9
            )
            pdf.ln(2)

        pdf.ln(2)

    # --- Feature-level findings ---
    write_line("Feature-Level Findings", height=7, bold=True, size=11)

    for finding in incident.findings:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            0, 7,
            safe(f"Feature: {finding.item_id} | Verdict: {finding.verdict}"),
            fill=True,
            new_x="LMARGIN", new_y="NEXT"
        )

        write_line(finding.description, height=5, size=9)

        for cause in finding.causes:
            write_line(
                f"Probable Cause: {cause.label} "
                f"(Confidence: {cause.confidence:.2f})",
                height=5, bold=True, size=9
            )

            for key, value in cause.evidence.items():
                # Limit individual values to keep the report readable.
                value_text = str(value)
                if len(value_text) > 500:
                    value_text = value_text[:500] + "..."

                write_line(
                    f"  {key}: {value_text}",
                    height=4, size=8
                )

            write_line(
                f"Action: {cause.recommended_action}",
                height=5, size=8
            )
            pdf.ln(2)

        pdf.ln(3)

    # --- Disclaimer ---
    pdf.ln(2)
    write_line(
        "Note: All causes are probable causes supported by evidence, "
        "not proven causality. Generated deterministically without an "
        "LLM or paid API.",
        height=4, size=8
    )

    # fpdf2 returns bytearray/bytes; handle legacy string output too.
    raw = pdf.output()

    if isinstance(raw, str):
        return raw.encode("latin-1")

    return bytes(raw)




# ---------------------------------------------------------------------------
# Helper: render RCA incident UI (shared between Option 1 and Option 2A)
# ---------------------------------------------------------------------------
def render_rca_ui(incident, ref_df, cur_df, report):
    """Render the full RCA UI block for a given incident."""
    from rca.report import to_markdown, to_json

    st.subheader("🕵️ Root Cause Analysis Report")

    sev = incident.severity.value
    badge_colors = {"MAJOR": "🔴", "DATA_QUALITY": "🟠", "MODERATE": "🟡", "NONE": "🟢"}
    icon = badge_colors.get(sev, "⚪")
    st.markdown(f"### {icon} Severity: `{sev}`")
    st.info(incident.summary)

    # Dataset-level causes (most important - shown first)
    if incident.dataset_level_causes:
        st.error("⚠️ **Dataset-Level Population Shift Detected** — multiple features drifted together")
        for c in incident.dataset_level_causes:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"**{c.label}**")
                st.caption(f"Evidence: {c.evidence}")
                st.caption(f"🔧 Action: {c.recommended_action}")
            with col_b:
                st.metric("Confidence", f"{c.confidence:.0%}")
        st.markdown("---")

    # Feature-level findings
    if not incident.findings:
        st.success("✅ No significant feature-level drift causes found.")
    else:
        st.markdown(f"**{len(incident.findings)} features have identified probable causes:**")
        for finding in incident.findings:
            header_icon = "🚨" if finding.verdict == "DRIFT_EXPLAINED" else "⚠️"
            with st.expander(f"{header_icon} **{finding.item_id}** — {finding.verdict}", expanded=False):
                st.caption(finding.description)

                # Evidence table
                cause_rows = []
                for cause in finding.causes:
                    cause_rows.append({
                        "Cause": cause.label,
                        "Code": cause.code,
                        "Confidence": f"{cause.confidence:.0%}",
                        "Top Evidence": str(list(cause.evidence.items())[:2])
                    })
                st.dataframe(pd.DataFrame(cause_rows), use_container_width=True, hide_index=True)

                # Ranked causes with progress bars
                st.markdown("#### Ranked Probable Causes")
                for i, cause in enumerate(finding.causes):
                    rank_icon = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                    st.markdown(f"{rank_icon} **{cause.label}**")
                    st.progress(cause.confidence, text=f"Confidence: {cause.confidence:.0%}")
                    with st.container():
                        ev_col, act_col = st.columns(2)
                        with ev_col:
                            st.caption("**Evidence:**")
                            for ek, ev in cause.evidence.items():
                                if isinstance(ev, float):
                                    st.caption(f"• `{ek}`: `{ev:.4f}`")
                                else:
                                    st.caption(f"• `{ek}`: `{ev}`")
                        with act_col:
                            st.info(f"🔧 {cause.recommended_action}", icon="💡")
                    st.markdown("---")

                # Distribution overlay chart
                if finding.item_id in ref_df.columns and finding.item_id in cur_df.columns:
                    ref_col_data = ref_df[finding.item_id].dropna()
                    cur_col_data = cur_df[finding.item_id].dropna()

                    fig = go.Figure()
                    fig.add_trace(go.Histogram(
                        x=ref_col_data, name="Reference", opacity=0.65,
                        histnorm='probability density',
                        marker_color='#1f77b4'
                    ))
                    fig.add_trace(go.Histogram(
                        x=cur_col_data, name="Current", opacity=0.65,
                        histnorm='probability density',
                        marker_color='#ff7f0e'
                    ))

                    # Per-bin PSI contribution bar
                    try:
                        bins = np.linspace(
                            min(ref_col_data.min(), cur_col_data.min()),
                            max(ref_col_data.max(), cur_col_data.max()),
                            11
                        )
                        ref_c, _ = np.histogram(ref_col_data, bins=bins)
                        cur_c, _ = np.histogram(cur_col_data, bins=bins)
                        ref_p = np.maximum(ref_c / len(ref_col_data), 1e-4)
                        cur_p = np.maximum(cur_c / len(cur_col_data), 1e-4)
                        psi_contrib = (cur_p - ref_p) * np.log(cur_p / ref_p)
                        bin_labels = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)]

                        fig.add_trace(go.Bar(
                            x=[(bins[i]+bins[i+1])/2 for i in range(len(bins)-1)],
                            y=psi_contrib,
                            name="PSI Contribution",
                            marker_color='#d62728',
                            opacity=0.55,
                            yaxis='y2',
                            width=[(bins[1]-bins[0])*0.4]*len(psi_contrib)
                        ))
                        fig.update_layout(
                            yaxis2=dict(title="PSI Contribution", overlaying='y', side='right', showgrid=False)
                        )
                    except Exception:
                        pass

                    fig.update_layout(
                        barmode='overlay',
                        title=f"Distribution Overlay + PSI Contribution: {finding.item_id}",
                        xaxis_title=finding.item_id,
                        yaxis_title="Probability Density",
                        height=380,
                        template="plotly_white",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{finding.item_id}")

    # Download buttons
    st.markdown("---")
    st.markdown("#### 📥 Download Reports")
    md_report = to_markdown(incident)
    json_report = to_json(incident)

    dl1, dl2, dl3 = st.columns(3)
    dl1.download_button(
        "📝 Download Markdown", md_report,
        file_name="rca_report.md", mime="text/markdown", use_container_width=True
    )
    dl2.download_button(
        "🗂️ Download JSON", json_report,
        file_name="rca_report.json", mime="application/json", use_container_width=True
    )

    with dl3:
        if st.button("📄 Generate PDF Report", use_container_width=True, key=f"pdf_{incident.incident_id}"):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = generate_pdf_report(incident)
                    st.download_button(
                        "⬇️ Download PDF Now", pdf_bytes,
                        file_name="rca_report.pdf", mime="application/pdf",
                        use_container_width=True, key=f"pdf_dl_{incident.incident_id}"
                    )
                    st.success("PDF ready!")
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")


# ---------------------------------------------------------------------------
# Helper: run RCA engine
# ---------------------------------------------------------------------------
def run_rca(ref_df, cur_df, drift_report):
    from rca.engine import RCAEngine
    from rca.analyzers.data_drift import DataDriftAnalyzer
    engine = RCAEngine()
    engine.register(DataDriftAnalyzer())
    return engine.run("data_drift", {
        "reference_df": ref_df,
        "current_df": cur_df,
        "drift_report": drift_report
    })


# ==============================================================================
# OPTION 1: CSV FILE UPLOAD (BATCH ANALYSIS)
# ==============================================================================
if option == "Option 1: CSV File Upload (Batch)":
    st.header("📄 Option 1: Batch Analysis via CSV Upload")
    st.caption("Upload baseline reference data and current production data to compute statistical drift.")

    col1, col2 = st.columns(2)
    with col1:
        ref_file = st.file_uploader("Upload Baseline / Reference CSV", type=["csv"], key="csv_ref")
    with col2:
        cur_file = st.file_uploader("Upload Current Production CSV", type=["csv"], key="csv_cur")

    if ref_file and cur_file:
        ref_df = pd.read_csv(ref_file)
        cur_df = pd.read_csv(cur_file)

        st.subheader("Dataset Previews")
        c1, c2 = st.columns(2)
        c1.dataframe(ref_df.head(3), use_container_width=True)
        c2.dataframe(cur_df.head(3), use_container_width=True)

        if st.button("▶️ Run Batch Drift Report", type="primary"):
            with st.spinner("Computing PSI, KS-Test, JS Divergence & Evidently Metrics..."):
                report = detect_drift(ref_df, cur_df)
            st.session_state["batch_report"] = report
            st.session_state["batch_ref_df"] = ref_df
            st.session_state["batch_cur_df"] = cur_df
            st.session_state["batch_rca_done"] = False
            st.session_state.pop("batch_incident", None)

    # Show drift metrics if report exists in session
    if "batch_report" in st.session_state:
        report = st.session_state["batch_report"]
        ref_df = st.session_state["batch_ref_df"]
        cur_df = st.session_state["batch_cur_df"]

        st.success("✅ Analysis Completed!")
        ev_drift = report["evidently_overall"]["drift_detected"]
        share_drift = report["evidently_overall"]["share_of_drifted_columns"]

        m1, m2 = st.columns(2)
        m1.metric("Overall Dataset Drift", "🔴 DETECTED" if ev_drift else "🟢 STABLE")
        m2.metric("Share of Drifted Columns", f"{share_drift:.1%}")

        st.subheader("Column-Level Statistical Metrics")
        table_data = []
        for col_name, metrics in report["column_level_stats"].items():
            any_drift = (
                metrics['PSI']['drift_detected'] or
                metrics['KS_Test']['drift_detected'] or
                metrics['JS_Divergence']['drift_detected'] or
                metrics['Wasserstein']['drift_detected']
            )
            table_data.append({
                "Feature": col_name,
                "PSI": f"{metrics['PSI']['value']:.4f}",
                "PSI 🚨": "✅" if metrics['PSI']['drift_detected'] else "—",
                "KS p-val": f"{metrics['KS_Test']['p_value']:.3e}",
                "KS 🚨": "✅" if metrics['KS_Test']['drift_detected'] else "—",
                "JS Div": f"{metrics['JS_Divergence']['divergence']:.4f}",
                "JS 🚨": "✅" if metrics['JS_Divergence']['drift_detected'] else "—",
                "Wasserstein": f"{metrics['Wasserstein']['normalized_distance']:.4f}",
                "W 🚨": "✅" if metrics['Wasserstein']['drift_detected'] else "—",
                "Any Drift": "🔴 YES" if any_drift else "🟢 NO"
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        # Evidently share pie chart
        col_pie, col_bar = st.columns(2)
        with col_pie:
            n_drifted = int(share_drift * len(report["column_level_stats"]))
            n_stable = len(report["column_level_stats"]) - n_drifted
            pie_fig = go.Figure(go.Pie(
                labels=["Drifted", "Stable"], values=[n_drifted, n_stable],
                marker_colors=["#d62728", "#2ca02c"], hole=0.45
            ))
            pie_fig.update_layout(title="Evidently: Feature Drift Share", height=260, margin=dict(t=40, b=0))
            st.plotly_chart(pie_fig, use_container_width=True)

        with col_bar:
            bar_df = pd.DataFrame(table_data)
            psi_vals = [float(m['PSI']['value']) for m in report["column_level_stats"].values()]
            cols_names = list(report["column_level_stats"].keys())
            bar_fig = go.Figure(go.Bar(
                x=cols_names, y=psi_vals,
                marker_color=['#d62728' if p > 0.25 else '#ff7f0e' if p > 0.10 else '#2ca02c' for p in psi_vals]
            ))
            bar_fig.add_hline(y=0.10, line_dash="dash", line_color="orange", annotation_text="Moderate (0.10)")
            bar_fig.add_hline(y=0.25, line_dash="dash", line_color="red", annotation_text="Major (0.25)")
            bar_fig.update_layout(title="PSI per Feature", yaxis_title="PSI", height=260, margin=dict(t=40, b=0))
            st.plotly_chart(bar_fig, use_container_width=True)

        # RCA Section
        st.markdown("---")
        st.markdown("### 🔍 Root Cause Analysis")
        st.caption("Drill down into WHY each feature drifted using 7 deterministic evidence checks.")

        if st.button("🔍 Run Root Cause Analysis (RCA)", type="primary", key="rca_btn_1"):
            with st.spinner("Analyzing probable causes across all features..."):
                incident = run_rca(ref_df, cur_df, report)
            st.session_state["batch_incident"] = incident

        if "batch_incident" in st.session_state:
            render_rca_ui(
                st.session_state["batch_incident"],
                st.session_state["batch_ref_df"],
                st.session_state["batch_cur_df"],
                st.session_state["batch_report"]
            )


# ==============================================================================
# OPTION 2: API INTEGRATION (BATCH & LIVE STREAMING MODES)
# ==============================================================================
elif option == "Option 2: Application API Integration":
    st.header("🔌 Option 2: Live API Connection Engine")
    st.caption("Applications send inference logs to FastAPI endpoints (`/log-batch` and `/log-stream`).")

    api_sub_mode = st.tabs(["2A. API Batch Processing", "2B. API Live Stream Listener"])

    # -------------------------------------------------------------------------
    # 2A. API Batch
    # -------------------------------------------------------------------------
    with api_sub_mode[0]:
        st.subheader("Batch Data Ingested via REST API")
        st.code("POST http://localhost:8000/api/v1/log-batch", language="bash")

        if st.button("Fetch Ingested Batch Logs from API"):
            try:
                res = requests.get("http://localhost:8000/api/v1/get-batch-data", timeout=3)
                data = res.json().get("data", [])
                if data:
                    api_df = pd.DataFrame(data)
                    st.success(f"Fetched {len(api_df)} production records from API!")
                    st.dataframe(api_df.head(), use_container_width=True)
                    st.session_state["api_cur_df"] = api_df
                else:
                    st.warning("No batch logs found. POST records to `/api/v1/log-batch` first.")
            except Exception as e:
                st.error(f"Cannot connect to FastAPI backend: {e}")

        if "api_cur_df" in st.session_state:
            st.markdown("---")
            st.markdown("#### Upload Reference Baseline for Comparison")
            ref_file_api = st.file_uploader("Upload Reference CSV", type=["csv"], key="api_ref")
            if ref_file_api:
                ref_baseline = pd.read_csv(ref_file_api)
                st.session_state["api_ref_df"] = ref_baseline

            if "api_ref_df" in st.session_state:
                if st.button("▶️ Run Drift Report on API Logs", type="primary"):
                    with st.spinner("Running drift analysis..."):
                        report = detect_drift(st.session_state["api_ref_df"], st.session_state["api_cur_df"])
                    st.session_state["api_report"] = report
                    st.session_state.pop("api_incident", None)

                if "api_report" in st.session_state:
                    st.json(st.session_state["api_report"]["column_level_stats"])
                    st.markdown("---")
                    if st.button("🔍 Run RCA on API Logs", type="primary", key="rca_btn_2a"):
                        with st.spinner("Analyzing root causes..."):
                            incident = run_rca(
                                st.session_state["api_ref_df"],
                                st.session_state["api_cur_df"],
                                st.session_state["api_report"]
                            )
                        st.session_state["api_incident"] = incident

                    if "api_incident" in st.session_state:
                        render_rca_ui(
                            st.session_state["api_incident"],
                            st.session_state["api_ref_df"],
                            st.session_state["api_cur_df"],
                            st.session_state["api_report"]
                        )

    # -------------------------------------------------------------------------
    # 2B. API Streaming Listener
    # -------------------------------------------------------------------------
    with api_sub_mode[1]:
        st.subheader("Live Real-Time Stream via API Endpoint")
        st.code("POST http://localhost:8000/api/v1/log-stream", language="json")

        if st.button("Poll Live API Stream Buffer"):
            try:
                res = requests.get("http://localhost:8000/api/v1/get-stream-data", timeout=3)
                stream_records = res.json().get("stream", [])
                if stream_records:
                    st.info(f"Retrieved {len(stream_records)} live stream events.")
                    records_list = [r["features"] for r in stream_records]
                    alerts_list = [r["drift_alerts"] for r in stream_records]
                    df_stream = pd.DataFrame(records_list)
                    st.line_chart(df_stream)
                    drift_rows = [idx for idx, alert in enumerate(alerts_list) if len(alert) > 0]
                    if drift_rows:
                        st.error(f"🚨 API reported River drift alerts at stream indices: {drift_rows}")
                else:
                    st.warning("Stream buffer empty. Send POST requests to `/api/v1/log-stream`.")
            except Exception as e:
                st.error(f"FastAPI connection failed: {e}")


# ==============================================================================
# OPTION 3: LIVE REAL-TIME RIVER SIMULATION
# ==============================================================================
elif option == "Option 3: Live Real-Time River Simulation (Demo for Mam)":
    st.header("⚡ Real-Time Streaming Drift Animation (River ADWIN)")
    st.caption("Live row-by-row streaming simulation with real-time chart animation and River drift alerts.")

    c_ctrl1, c_ctrl2 = st.columns(2)
    with c_ctrl1:
        stream_delay = st.slider("Stream Interval (seconds)", 0.01, 0.20, 0.05)
    with c_ctrl2:
        drift_trigger_row = st.number_input("Row Index to Inject Shift", min_value=50, max_value=400, value=200)

    if st.button("🚀 Start Live Stream Presentation"):
        np.random.seed(42)
        baseline_data = np.random.normal(loc=10.0, scale=1.0, size=int(drift_trigger_row))
        shifted_data = np.random.normal(loc=15.0, scale=1.5, size=400 - int(drift_trigger_row))
        full_payload = np.concatenate([baseline_data, shifted_data])

        alert_container = st.empty()
        status_container = st.empty()
        chart_container = st.empty()

        adwin = drift.ADWIN()
        processed_values = []
        detected_drift_points = []

        for row_idx, value in enumerate(full_payload):
            adwin.update(value)
            processed_values.append(value)

            if adwin.drift_detected:
                detected_drift_points.append(row_idx)
                adwin = drift.ADWIN()

            if row_idx % 3 == 0 or row_idx == len(full_payload) - 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=processed_values, mode='lines', name='Feature Value',
                    line=dict(color='#00e676', width=2)
                ))
                for d_point in detected_drift_points:
                    fig.add_vline(x=d_point, line_width=2, line_dash="dash", line_color="#ff1744")

                fig.update_layout(
                    title=f"Live Stream (Row {row_idx + 1}/{len(full_payload)})",
                    xaxis_title="Stream Row Index", yaxis_title="Feature Value",
                    height=450, template="plotly_dark"
                )
                chart_container.plotly_chart(fig, use_container_width=True)

            status_container.metric(
                "Stream Ingestion Status",
                f"Row {row_idx + 1} of {len(full_payload)}",
                delta=f"Drift Alerts: {len(detected_drift_points)}"
            )
            if detected_drift_points:
                alert_container.error(
                    f"🚨 Real-Time Drift at Row {detected_drift_points[-1]}! River ADWIN flagged a distribution shift."
                )

            time.sleep(stream_delay)

        st.success("🎉 Live streaming simulation completed!")