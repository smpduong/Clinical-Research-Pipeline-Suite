# Recruiter Guide: Skills-to-Code Mapping

> **Quick Reference:** This document maps specific job requirements to the exact files and functions that demonstrate each skill. Use this for rapid candidate evaluation.

---

## Data Engineering & ETL

| Skill | Evidence | File | Lines |
|-------|----------|------|-------|
| **Multi-source data ingestion** | Parses 5 CGM device formats into unified schema | `python/src/cgm_processor.py` | 45-120 |
| **Data quality assurance** | 4-layer validation: range, temporal, completeness, cross-reference | `python/playbook1_cgm_meal_tracker.py` | 574-622 |
| **ETL pipeline design** | REDCap → warehouse → dashboard with hourly sync | `python/playbook3_implementation_dashboard.py` | 130-228 |
| **Database design** | TimescaleDB hypertables, connection pooling, materialized views | `python/playbook3_implementation_dashboard.py` | 130-228 |
| **Missing data handling** | FIML-ready gap detection, interpolation rules, pattern-mixture scaffolding | `python/playbook1_cgm_meal_tracker.py` | 240-270 |
| **API integration** | Rate-limited, retry-enabled, audited REDCap client | `python/src/redcap_client.py` | 1-150 |

## Statistical Analysis & Modeling

| Skill | Evidence | File | Lines |
|-------|----------|------|-------|
| **Mixed-effects models** | LMM with random intercepts/slopes, convergence fallback | `python/playbook2_culinary_medicine.py` | 266-371 |
| **Bayesian statistics** | PyMC/brms scaffolding with analytical fallback | `python/playbook2_culinary_medicine.py` | 373-424 |
| **Psychometrics** | Item difficulty, point-biserial correlation, distractor analysis | `python/playbook2_culinary_medicine.py` | 185-260 |
| **Effect size calculation** | Cohen's d with pooled standard deviation | `python/playbook3_implementation_dashboard.py` | 280-340 |
| **Health equity analysis** | Automated disparity flags, stratified summaries | `python/playbook3_implementation_dashboard.py` | 340-380 |
| **Time-series metrics** | TIR, GMI, GRI, CV, MAGE, CONGA computation | `python/playbook1_cgm_meal_tracker.py` | 385-462 |
| **Longitudinal analysis** | Wide-to-long conversion, timepoint coding | `python/playbook2_culinary_medicine.py` | 280-320 |

## Software Engineering

| Skill | Evidence | File | Lines |
|-------|----------|------|-------|
| **Python (advanced)** | Dataclasses, decorators, context managers, type hints | `python/src/*.py` | Throughout |
| **R (advanced)** | tidyverse, lme4, shiny, S3 methods | `r/*.R` | Throughout |
| **Defensive coding** | Try-except chains, dependency checks, graceful degradation | All playbooks | Throughout |
| **Design patterns** | Adapter (CGM parsers), Strategy (scoring), Repository (warehouse) | `python/src/*.py` | Throughout |
| **Unit testing** | pytest with parametrized tests, testthat for R | `python/tests/*.py` | 1-80 |
| **Version control** | Git workflow, semantic commits, CI/CD | `.github/workflows/ci.yml` | 1-50 |
| **Containerization** | Multi-service Docker Compose with health checks | `docker/docker-compose.yml` | 1-60 |

## Healthcare & Regulatory

| Skill | Evidence | File | Lines |
|-------|----------|------|-------|
| **HIPAA compliance** | SHA-256 audit logging, immutable trails, PHI hashing | `python/src/redcap_client.py` | 30-80 |
| **Clinical data standards** | CGM device knowledge, glycemic metrics per ADA guidelines | `python/playbook1_cgm_meal_tracker.py` | 385-462 |
| **REDCap expertise** | API client with batching, metadata caching, DAG support | `python/src/redcap_client.py` | 1-150 |
| **IRB-ready documentation** | Audit trails, data validation rules, reproducible scripts | All playbooks | Throughout |
| **Health equity** | Multi-language support, stratified analysis, disparity flags | `python/playbook3_implementation_dashboard.py` | 340-380 |

## Full-Stack & DevOps

| Skill | Evidence | File | Lines |
|-------|----------|------|-------|
| **Web dashboards** | Reactive Dash/Shiny with 7 tabs, filtering, callbacks | `python/playbook3_implementation_dashboard.py` | 520-678 |
| **Data visualization** | Publication-ready matplotlib/seaborn/plotly | `python/playbook1_cgm_meal_tracker.py` | 625-709 |
| **Monitoring** | Prometheus metrics, Grafana dashboards, alert routing | `python/playbook3_implementation_dashboard.py` | 346-494 |
| **SQL** | Complex joins, window functions, parameterized queries | `python/playbook3_implementation_dashboard.py` | 130-228 |
| **Infrastructure as Code** | Dockerfiles, compose orchestration, environment templates | `docker/` | All |

## Domain Expertise

| Domain | Evidence |
|--------|----------|
| **Diabetes/Endocrinology** | CGM metrics (TIR, GMI, GRI), glycemic load calculations, ADA targets |
| **Nutrition Science** | Glycemic index database, portion modifiers, protein/fiber reduction factors |
| **Implementation Science** | Fidelity monitoring, multi-site stratification, curriculum comparison |
| **Community Health** | CHW workflow integration, 5-language support, cultural adaptation scaffolding |
| **Psychometrics** | Quiz validation, item analysis, motivational interviewing integration |

---

## Interview-Ready Talking Points

**For Data Engineering Roles:**
> "I built a device-agnostic parser using the adapter pattern that handles 5 CGM formats with standardized QC. The pipeline includes rate-limited API ingestion, HIPAA audit logging, and a TimescaleDB warehouse that queries 1M rows in under 1 second."

**For Biostatistics Roles:**
> "I implemented mixed-effects models with automatic convergence fallback---random slopes, then random intercepts, then fixed-effects OLS. I also included Bayesian scaffolding with PyMC for small-sample inference, plus psychometric item analysis for survey validation."

**For Full-Stack/Data Science Roles:**
> "The dashboard is a reactive 7-tab Dash application with real-time filtering, Plotly visualizations, and automated equity analysis that flags disparities in red. The entire stack is containerized with Docker Compose and includes Prometheus monitoring."

**For Healthcare/Clinical Research Roles:**
> "Every component is designed for regulatory readiness: SHA-256 audit trails, immutable logs, data validation rules, and multi-language support for diverse participant populations. The system handles PHI securely and generates IRB-ready documentation automatically."

---

## Verification Checklist

- [ ] Clone repository and run `pip install -r requirements.txt`
- [ ] Run `pytest python/tests/ -v` (all tests should pass)
- [ ] Open `notebooks/demo_playbook1.ipynb` and execute all cells
- [ ] Verify `docker-compose config` parses without errors
- [ ] Check that `.gitignore` excludes `.env`, `data/raw/`, and `*.log`
- [ ] Confirm README includes contact information and LinkedIn
