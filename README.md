# DriftSense: Data Drift Detection and Root Cause Analysis

> Part of a larger AI observability project. This README covers the **Data Drift** module only.
> Model drift, hallucination detection, and RAG root-cause attribution are planned.

**Live demo:** https://driftsense-ak54gaczudesh3otq3hmoy.streamlit.app/


## What this project does

Machine learning models are trained on past data. When the data they see in production changes, their predictions can get worse without any error message. This is called **data drift**.

This module does two things:

1. **Detects drift:** it compares a reference dataset (what the model was trained on) with current data and measures how much each feature has changed.
2. **Explains drift:** it looks at the evidence behind each change and suggests the most probable cause, for example a unit change, a jump in missing values, or a new customer group.

Most tools stop at step 1. Step 2 is the focus of this project.

## Features

- Batch drift detection on two CSV files
- Four statistical measures per feature: PSI, KS test, Jensen-Shannon divergence, Wasserstein distance
- Dataset-level drift summary using Evidently AI
- Real-time drift detection on live data using ADWIN (River library)
- REST API so other applications can send their data
- Root Cause Analysis (RCA): ranked probable causes with confidence and a recommended action for each drifted feature
- Interactive charts: reference vs current distribution, PSI per feature, drift share
- Downloadable reports in Markdown, JSON, and PDF
- Live demo animation of streaming drift


## How it works

```
 CSV upload / API logs / live stream
              |
              v
     +--------------------+
     |  Drift detection   |  PSI, KS, JS divergence, Wasserstein, Evidently, ADWIN
     +--------------------+
              |
              v
     +--------------------+
     |  Root Cause        |  evidence checks -> ranked probable causes
     |  Analysis (RCA)    |
     +--------------------+
              |
              v
     Dashboard + downloadable report (MD / JSON / PDF)
```

### Drift measures

| Measure | What it tells you | Drift rule used |
|---|---|---|
| **PSI** (Population Stability Index) | How much the share of values in each bucket changed | Below 0.10 stable, 0.10 to 0.25 moderate, above 0.25 major |
| **KS test** | Whether the two distributions differ, with a p-value | p-value below |
| **Jensen-Shannon divergence** | A symmetric distance between two distributions| 
| **Wasserstein distance** | How far values moved, divided by  | |
| **Evidently dataset drift** | Share of columns that drifted, and an overall yes/no | Evidently default settings (version: ``) |

**Streaming:** ADWIN keeps a moving window of recent values for each feature. When the older and newer parts of the window have clearly different averages, it raises a drift alert and resets.

### Root Cause Analysis

For every feature that drifted, the RCA module collects evidence and applies fixed rules. No AI model decides the cause, so every result can be traced back to numbers.

**Evidence collected**

1. Which part of the distribution contributes most to the PSI score
2. Change in the percentage of missing values
3. Whether values were multiplied by a factor (scale or unit change)
4. Whether values were shifted by a fixed amount (location shift)
5. Change in spread (variance)
6. Share of values outside the range seen in the reference data
7. Whether the feature is stuck on one value, or has values never seen before

**Probable causes reported**

| Cause | Typical meaning |
|---|---|
| Missing values increased | Upstream data pipeline or form problem |
| Stuck or constant value | Broken sensor, default value, or ETL bug |
| New or unseen values | New category or code in the data |
| Out-of-range values | Wrong units or a new population |
| Scale or unit change | Values multiplied by a factor, for example currency or unit change |
| Location shift | All values moved by a fixed amount |
| Variance change | New customer mix or outliers |
| Gradual or seasonal shift | Slow change over time (fallback, low confidence) |
| Population or pipeline-wide shift | Many features drifted together (dataset level) |

Each cause has a **confidence score (0 to 1)** and a **recommended action**. Severity is one of: `NONE`, `DATA_QUALITY`, `MODERATE`, `MAJOR`.

> **Important:** the causes are *probable causes supported by evidence*, not proven causes. Always confirm with the data owner before acting.

All thresholds are in `rca/config.py`.

## Ways to connect your data

| Mode | Use it when | How |
|---|---|---|
| **Option 1: CSV upload** | You have two files to compare | Upload a reference CSV and a current CSV, then click *Run Batch Drift Report* |
| **Option 2A: API batch** | Another application sends records in bulk | Send records to the API, fetch them in the dashboard, upload a reference CSV, run drift and RCA |
| **Option 2B: API stream** | Another application sends one record at a time | Send records to `/log-stream`. ADWIN checks each value and returns alerts |
| **Option 3: Live demo** | You want to see streaming drift in action | Choose the shift row, click *Start Live Stream Presentation* |


## Project structure

<!-- TODO: check this tree against your actual folders and edit -->

```
.
|-- app.py                     # Streamlit dashboard
|-- api_server.py              # FastAPI logging API with ADWIN
|-- inject_drift.py            # Creates synthetic drift in current.csv
|-- requirements.txt
|-- data drift/
|   `-- drift_detection.py     # detect_drift(reference_df, current_df)
|-- rca/                       # Root Cause Analysis
|   |-- config.py              # all thresholds
|   |-- schema.py              # Incident / Finding / RootCause models
|   |-- base.py                # base analyzer
|   |-- engine.py              # runs analyzers, logs incidents
|   |-- report.py              # Markdown and JSON reports
|   `-- analyzers/
|       `-- data_drift.py      # data drift analyzer
|-- tests/rca/                 # tests and fault-injection evaluation
|-- data/
|   |-- raw/                   # original dataset (not committed)
|   `-- processed/             # reference.csv, current.csv
`-- logs/                      # incident log (JSONL)
```





## Limitations

- Drift in the experiments is **synthetic**. The module has not been validated on a real production system.
- Only **numeric features** are analysed.
- RCA thresholds are set by hand and may need tuning for other datasets.
- Causes are **probable**, not proven. Some faults can look alike, for example scale change and location shift on skewed data.
- The API stores data **in memory** only, and rejects records with missing values.
- The live demo runs on free hosting and can be slow or sleep when idle.

## Roadmap

| Module | Status |
|---|---|
| Data drift detection (batch and stream) | Done |
| Root Cause Analysis for data drift | Done |
| Model drift (accuracy decay, CBPE) | In progress |
| Hallucination detection | Planned |
| RAG root-cause attribution | Planned |
| Compliance and audit reports | Planned |

## Tech stack

Python, Streamlit, FastAPI, Uvicorn, River (ADWIN), Evidently AI, SciPy, scikit-learn, Pandas, NumPy, Plotly, Pydantic, fpdf2, pytest.








##  AUTHOR
- Aarav Chaudhary




