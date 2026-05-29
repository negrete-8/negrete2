# devsecops-pipeline

![CI/CD](https://github.com/negrete-8/devsecops-pipeline/actions/workflows/devsecops.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-enabled-2496ED?logo=docker&logoColor=white)
![Security](https://img.shields.io/badge/Security-Gitleaks%20%7C%20Snyk%20%7C%20SonarCloud%20%7C%20ZAP-red)

Full DevSecOps pipeline integrating automated security analysis at every stage of the CI/CD lifecycle against an intentionally vulnerable Flask application (Titan).

## Pipeline stages

```
Code Push
   │
   ├── Gitleaks      → secret detection across git history
   ├── Snyk          → SCA, dependency CVE scan with HTML report
   ├── SonarCloud    → SAST, code quality + security hotspots
   └── OWASP ZAP     → DAST, active scan against the live containerized app
```

The pipeline **fails** if any high-severity finding is produced by Gitleaks, Snyk or ZAP. SonarCloud failures surface in the run summary but do not block.

## Target application — Titan

A deliberately vulnerable Flask app used as DAST target. Documented vulnerabilities (so reviewers can confirm ZAP catches them):

| Endpoint | Method | Vulnerability |
|----------|--------|---------------|
| `/api/auth/login` | POST | SQL injection (string-concatenated query) |
| `/api/shipping/track?code=` | GET | SQL injection + reflected XSS |
| `/api/shipping/shipment/update_notes` | POST | XSS via stored notes |
| `/api/admin/system/diagnostics` | POST | OS command injection (weak `;`/`&&` filter) |
| `/api/admin/users/delete` | POST | SQL injection (integer concat) |

Default admin credentials: `admin / admin123` (also intentional).

## How the ZAP step works

Standard ZAP-in-CI setups miss most JSON-POST findings because the spider can't enumerate them and the active scanner attacks with default (medium) strength. This pipeline addresses both:

1. **Authentication** — `zap_scan.py` logs in to the app through ZAP's proxy and registers `titan_sess_id` as an HTTP session token (`httpsessions` API). Every active-scan request is then sent with the admin cookie attached, so the admin-only endpoints (`/api/admin/...`) are actually attacked.
2. **Endpoint seeding** — every endpoint in `SEED_ENDPOINTS` is hit with a representative request before the scan starts, so the active scanner has something to fuzz on JSON-POST routes.
3. **OpenAPI import** — `openapi.yaml` documents the JSON request schemas; ZAP imports it so it knows valid bodies and can mutate fields.
4. **AJAX spider** — runs in addition to the traditional spider for any JS-driven discovery.
5. **Scanner tuning** — all active scanners forced to `attack strength = HIGH` and `alert threshold = LOW`. This is the change that makes SQLi and command-injection findings actually surface.
6. **Native ZAP report** — instead of hand-building HTML, the scan emits ZAP's own `HTML/XML` reports plus a `zap-summary.json` consumed by the pipeline summary step.

## Artifacts produced

Every run uploads:

- `snyk-report` → `snyk-report.html`, `snyk-report.json`
- `zap-report` → `zap-report.html`, `zap-report.xml`, `zap-summary.json`

The job summary on the run page also shows per-stage outcome and a list of HIGH ZAP findings with their CWE.

## Running locally

```bash
# Install deps
pip install -r requirements.txt
pip install python-owasp-zap-v2.4 requests

# Run the target app
python app.py

# Start ZAP daemon (separate terminal)
docker run -d --name zap --network host \
  zaproxy/zap-stable zap.sh -daemon -host 0.0.0.0 -port 8080 \
  -config api.disablekey=true

# Run the scan
python zap_scan.py
```

## Stack

| Layer | Tool |
|-------|------|
| Orchestration | GitHub Actions |
| Secret scanning | Gitleaks |
| SCA | Snyk |
| SAST | SonarCloud |
| DAST | OWASP ZAP (zaproxy/zap-stable) |
| Target | Flask + Docker |

## Legal notice

> Educational project. The Titan application is intentionally vulnerable. Do not deploy it on a network you do not control.
