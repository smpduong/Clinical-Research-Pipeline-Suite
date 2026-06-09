# System Architecture & Data Flow

## Overview

This document describes the technical architecture of the Clinical Research Data Pipeline Suite. The system is designed as three independent but interoperable modules that can be deployed separately or as an integrated platform.

## Design Principles

1. **Separation of Concerns:** Each module handles one domain (data ingestion, statistical analysis, monitoring)
2. **Graceful Degradation:** Optional dependencies (PyMC, Prometheus, RPostgres) are wrapped in availability checks
3. **Defensive Coding:** All models include convergence fallbacks; all API calls include retry logic
4. **Auditability:** Every data touch is logged with cryptographic hashing for compliance
5. **Equity by Design:** All analyses stratify by demographic subgroups with automated disparity detection

## Data Flow Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Sources  │     │   Processing    │     │   Outputs       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│                 │     │                 │     │                 │
│  ┌───────────┐  │     │  ┌───────────┐  │     │  ┌───────────┐  │
│  │ Dexcom    │  │────▶│  │ Unified   │  │────▶│  │ Weekly    │  │
│  │ CGM       │  │     │  │ CGM       │  │     │  │ Reports   │  │
│  └───────────┘  │     │  │ Processor │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
│  ┌───────────┐  │     │                 │     │  ┌───────────┐  │
│  │ FreeStyle │  │────▶│  ┌───────────┐  │────▶│  │ Manuscript│  │
│  │ Libre     │  │     │  │ Glycemic  │  │     │  │ Figures   │  │
│  └───────────┘  │     │  │ Metrics   │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
│  ┌───────────┐  │     │                 │     │  ┌───────────┐  │
│  │ Meal Logs │  │────▶│  ┌───────────┐  │────▶│  │ eGL       │  │
│  │ (REDCap)  │  │     │  │ eGL       │  │     │  │ Validation│  │
│  └───────────┘  │     │  │ Engine    │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
│  ┌───────────┐  │     │                 │     │  ┌───────────┐  │
│  │ Quiz Data │  │────▶│  ┌───────────┐  │────▶│  │ Item      │  │
│  │ (REDCap)  │  │     │  │ Quiz      │  │     │  │ Analysis  │  │
│  └───────────┘  │     │  │ Scorer    │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
│  ┌───────────┐  │     │                 │     │  ┌───────────┐  │
│  │ Workshop  │  │────▶│  ┌───────────┐  │────▶│  │ Mixed     │  │
│  │ Outcomes  │  │     │  │ Mixed     │  │     │  │ Effects   │  │
│  │ (REDCap)  │  │     │  │ Effects   │  │     │  │ Reports   │  │
│  └───────────┘  │     │  │ Models    │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
│  ┌───────────┐  │     │                 │     │  ┌───────────┐  │
│  │ CGM       │  │────▶│  ┌───────────┐  │────▶│  │ Outcome   │  │
│  │ Metrics   │  │     │  │ Outcome   │  │     │  │ Linkage   │  │
│  └───────────┘  │     │  │ Linker    │  │     │  └───────────┘  │
│                 │     │  └───────────┘  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Warehouse│     │   Alert System  │     │   Dashboard     │
│   (TimescaleDB) │     │   (Prometheus)  │     │   (Dash/Shiny)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Module 1: CGM & Meal Tracker Architecture

### Component: UnifiedCGMProcessor
- **Pattern:** Adapter pattern for device-specific parsers
- **Input:** Raw CSV exports from 5 device types
- **Output:** Standardized DataFrame (timestamp, glucose_mgdl, device_type, qc_flag)
- **Quality Gates:**
  1. Parse: Device-specific column renaming
  2. Standardize: UTC timestamp conversion, unit normalization
  3. QC: Flag impossible (<40, >400), duplicate timestamps, out-of-target
  4. Gap-fill: Linear interpolation for gaps ≤15 min; flag larger gaps

### Component: GlycemicLoadEngine
- **Pattern:** Rule engine with lookup tables
- **Input:** MealLog dataclass (cuisine, dish, portion, modifications)
- **Output:** GlycemicMetrics dataclass (eGL, predicted excursion category)
- **Formula:** eGL = (GI/100) × (carbs × portion × protein_factor × fiber_factor)
- **Validation:** Scatter plot of eGL vs. observed CGM excursion with regression

### Component: WeeklyReportGenerator
- **Pattern:** Template method with pluggable visualizations
- **Output:** 4 PNG figures (cuisine comparison, eGL validation, dish heatmap, time series)
- **Config:** DPI 150 (draft) / 300 (publication), color palette optimized for colorblindness

## Module 2: Intervention Evaluator Architecture

### Component: EnhancedQuizScorer
- **Pattern:** Strategy pattern for scoring algorithms
- **Psychometrics:**
  - Difficulty index: proportion correct (target 0.30-0.80)
  - Discrimination: point-biserial correlation with total score (target >0.30)
  - Distractor analysis: frequency of each option selection

### Component: MixedEffectsAnalyzer
- **Pattern:** Chain of responsibility with fallback
- **Model hierarchy:**
  1. Attempt: Random intercept + random slope for time
  2. Fallback: Random intercept only
  3. Fallback: Fixed-effects OLS
- **Rationale:** Small samples (n<30 per group) often fail convergence with complex models

### Component: BayesianKnowledgeGain
- **Pattern:** Plugin architecture with fallback
- **Primary:** PyMC/brms with MCMC sampling (NUTS sampler)
- **Fallback:** Analytical normal approximation with 95% CI
- **Output:** Probability of positive effect (more intuitive than p-value)

## Module 3: Dashboard Architecture

### Component: DataWarehouse
- **Pattern:** Repository pattern with connection pooling
- **Database:** PostgreSQL + TimescaleDB extension
- **Schema:**
  - `cgm_readings` hypertable (partitioned by time)
  - `workshop_outcomes` standard table
  - `cgm_daily_summary` continuous aggregate (materialized view)
- **Performance:** Queries on 10M rows execute in <1s via time-based partitioning

### Component: ProductionDashboard
- **Pattern:** Model-View-Controller with reactive callbacks
- **Framework:** Python (Dash + Plotly) / R (Shiny + plotly)
- **Tabs:**
  1. Overview KPIs (participant count, workshop count, fidelity)
  2. Outcomes by Cuisine (stratified bar charts with error bars)
  3. Outcomes by Language (equity visualization)
  4. CGM Metrics (box plots of TIR/CV change)
  5. Fidelity Analysis (scatter with trendline)
  6. Equity Analysis (red/green disparity flags)
  7. Real-time Alerts (severity-sorted digest)

### Component: AlertSystem
- **Pattern:** Observer pattern with severity routing
- **Thresholds:**
  - Critical: DDS > 4 (severe distress), TIR < 40% (dangerous hypoglycemia)
  - Warning: DDS > 3 (moderate distress), TIR < 50%, fidelity < 80%
  - Info: Missing follow-up, minor data quality issues
- **Routing:** Critical → SMS/page; Warning → Email (4h SLA); Info → Daily digest

## Infrastructure Architecture

### Docker Microservices
```yaml
services:
  timescaledb:    # Time-series database
  redcap-etl:     # Hourly data sync from REDCap API
  cgm-processor:  # Batch CGM file processing
  dashboard:      # Web application (port 8050)
  prometheus:     # Metrics collection (port 9090)
  grafana:        # Metrics visualization (port 3000)
```

### CI/CD Pipeline (GitHub Actions)
```
Push to main ──▶ Run pytest (Python) ──▶ Run testthat (R) ──▶ Upload coverage
     │
     └────────▶ Build Docker images ──▶ Push to registry
```

## Security & Compliance

### Audit Trail
- Every API export/import logged with: timestamp, user, action, record_id, SHA-256 hash of PHI
- Immutable append-only log files
- 7-year retention (HIPAA standard)

### Data Validation
- Range checks: Biologically impossible values flagged before analysis
- Temporal checks: Future dates rejected
- Completeness checks: Required fields enforced
- Cross-reference checks: CGM timestamps must align with meal log timestamps (±2 hours)

### Access Control
- API tokens stored in environment variables (never committed)
- `.env` file template provided; actual secrets in `.env.local` (gitignored)
- Database connections use SSL/TLS with certificate verification

## Performance Characteristics

| Component | Dataset Size | Processing Time | Memory |
|-----------|-------------|-----------------|--------|
| CGM Parser | 30 days, 5-min intervals (~8,640 rows) | <2s | ~50MB |
| eGL Engine | 100 meal logs | <1s | ~20MB |
| Mixed Model | 200 participants, 3 timepoints | 5-30s | ~200MB |
| Dashboard Query | 1M warehouse rows | <1s | ~100MB |
| Weekly Report | 50 participants, 1 week | 10s | ~150MB |

## Scalability Roadmap

1. **Current:** Single-machine processing, file-based logs
2. **Near-term:** Apache Airflow for scheduled ETL, S3 for data lake
3. **Long-term:** dbt for warehouse transformations, Great Expectations for data validation, MLflow for model tracking
