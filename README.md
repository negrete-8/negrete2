# devsecops-pipeline

![CI/CD](https://github.com/negrete-8/devsecops-pipeline/actions/workflows/devsecops.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.9-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-enabled-2496ED?logo=docker&logoColor=white)
![Security](https://img.shields.io/badge/Security-Gitleaks%20%7C%20Snyk%20%7C%20SonarCloud%20%7C%20ZAP-red)

Full DevSecOps pipeline integrating automated security analysis at every stage of the CI/CD lifecycle, built as part of a Master in Cybersecurity.

## Pipeline Stages

```
Code Push
   │
   ├── Secret Detection      Gitleaks — scans for leaked credentials in git history
   │
   ├── Dependency Audit      Snyk — identifies vulnerable dependencies (HTML report)
   │
   ├── Static Analysis       SonarCloud — code quality and security hotspots (SAST)
   │
   └── Dynamic Analysis      OWASP ZAP — active scan against live app (DAST)
```

## Target Application

**Titan** — intentionally vulnerable Flask web application used as the scan target.
Includes authentication, admin panel and shipping module to generate realistic findings.

## Reports

Each pipeline run uploads two artifacts:
- `snyk-report` — HTML dependency vulnerability report
- `zap-report-completo` — OWASP ZAP dynamic scan results

## Stack

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD orchestration |
| Gitleaks | Secret / credential leak detection |
| Snyk | SCA — open source dependency vulnerabilities |
| SonarCloud | SAST — static code analysis |
| OWASP ZAP | DAST — dynamic application security testing |
| Docker | App containerization |
| Flask | Target web application |

## Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python app.py

# Run ZAP scan (requires ZAP running on port 8080)
python zap_scan.py
```

## Legal Notice

> Built for educational purposes as part of a Master in Cybersecurity.
> Target application is intentionally vulnerable — do not deploy in production.
