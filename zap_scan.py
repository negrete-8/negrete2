"""
OWASP ZAP DAST Scanner for Titan App.

Improvements over previous version:
- Uses ZAP HTTP Session Token API (no fragile JS auth script).
- Pre-seeds all endpoints (including JSON POST) into the Sites tree so the
  active scanner actually attacks them.
- Imports an OpenAPI spec (openapi.yaml) so ZAP knows the JSON request
  schemas and can fuzz them.
- Enables AJAX Spider in addition to the traditional spider.
- Forces attack strength HIGH and alert threshold LOW on all active scanners
  (the previous default MEDIUM was missing modern SQLi/RCE payloads).
- Generates ZAP's native HTML report instead of hand-building one.
- Exits non-zero when HIGH risk findings are detected, so the pipeline fails.
"""
import os
import sys
import time
import json
import requests
from zapv2 import ZAPv2

TARGET = "http://localhost:5000"
ZAP_PROXY = "http://localhost:8080"
SCAN_TIMEOUT_SEC = 30 * 60          # 30 minutes max for active scan
SPIDER_TIMEOUT_SEC = 5 * 60         # 5 minutes max for spider
AJAX_TIMEOUT_SEC = 5 * 60           # 5 minutes max for ajax spider
CONNECT_RETRIES = 20
CONNECT_DELAY_SEC = 3

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Endpoints to pre-seed so the active scanner sees them.
# (path, method, body_json)
SEED_ENDPOINTS = [
    ("/login",                            "GET",  None),
    ("/dashboard",                        "GET",  None),
    ("/admin/console",                    "GET",  None),
    ("/api/shipping/track?code=ABC123",   "GET",  None),
    ("/api/shipping/my_shipments",        "GET",  None),
    ("/api/auth/login",                   "POST", {"username": "admin", "password": "admin123"}),
    ("/api/auth/profile/1",               "GET",  None),
    ("/api/admin/dashboard/stats",        "GET",  None),
    ("/api/admin/system/diagnostics",     "POST", {"target_ip": "127.0.0.1"}),
    ("/api/admin/users/delete",           "POST", {"user_id": 1}),
    ("/api/shipping/shipment/update_notes","POST",{"id": 1, "notes": "test"}),
]


def log(stage, msg):
    print(f"[{stage}] {msg}", flush=True)


def wait_for_zap(zap):
    for i in range(CONNECT_RETRIES):
        try:
            version = zap.core.version
            log("ZAP", f"connected (version {version})")
            return True
        except Exception:
            log("ZAP", f"waiting ({i + 1}/{CONNECT_RETRIES})")
            time.sleep(CONNECT_DELAY_SEC)
    log("ZAP", "ERROR: not reachable")
    return False


def get_auth_session():
    """Log in to the app and return a requests.Session carrying the cookie."""
    s = requests.Session()
    s.proxies = {"http": ZAP_PROXY, "https": ZAP_PROXY}  # route through ZAP so it sees the login
    s.verify = False
    try:
        r = s.post(
            f"{TARGET}/api/auth/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
            timeout=10,
        )
        if r.status_code == 200 and "titan_sess_id" in s.cookies:
            log("AUTH", f"login OK, cookie titan_sess_id={s.cookies['titan_sess_id'][:16]}...")
            return s
        log("AUTH", f"login failed, status={r.status_code}, body={r.text[:200]}")
    except Exception as e:
        log("AUTH", f"login error: {e}")
    return None


def setup_zap_session(zap, cookie_value):
    """Tell ZAP that titan_sess_id is the session token, then store the value."""
    site = TARGET
    try:
        zap.httpsessions.add_default_session_token("titan_sess_id")
    except Exception:
        pass  # already added
    try:
        zap.httpsessions.create_empty_session(site, "auth-session")
    except Exception:
        pass
    zap.httpsessions.set_session_token_value(site, "auth-session", "titan_sess_id", cookie_value)
    zap.httpsessions.set_active_session(site, "auth-session")
    log("AUTH", "ZAP session token configured")


def seed_endpoints(session):
    """Pre-visit every endpoint so it appears in the Sites tree.

    Without this, ZAP's active scanner has nothing to attack on JSON POST
    routes that the spider can't discover."""
    for path, method, body in SEED_ENDPOINTS:
        url = TARGET + path
        try:
            if method == "GET":
                r = session.get(url, timeout=5)
            else:
                r = session.post(url, json=body, timeout=5)
            log("SEED", f"{method} {path} -> {r.status_code}")
        except Exception as e:
            log("SEED", f"{method} {path} -> ERROR {e}")


def import_openapi(zap):
    """If openapi.yaml exists, import it so ZAP knows JSON schemas."""
    spec_path = os.path.join(os.path.dirname(__file__), "openapi.yaml")
    if not os.path.isfile(spec_path):
        log("OPENAPI", "no openapi.yaml found, skipping")
        return
    try:
        zap.openapi.import_file(spec_path, TARGET)
        log("OPENAPI", f"imported {spec_path}")
    except Exception as e:
        log("OPENAPI", f"import failed: {e}")


def run_spider(zap):
    log("SPIDER", "starting traditional spider")
    scan_id = zap.spider.scan(TARGET)
    deadline = time.time() + SPIDER_TIMEOUT_SEC
    while int(zap.spider.status(scan_id)) < 100:
        if time.time() > deadline:
            log("SPIDER", "timeout reached, stopping")
            zap.spider.stop(scan_id)
            break
        log("SPIDER", f"progress {zap.spider.status(scan_id)}%")
        time.sleep(5)
    log("SPIDER", f"done, URLs found: {len(zap.spider.results(scan_id))}")


def run_ajax_spider(zap):
    log("AJAX", "starting AJAX spider")
    zap.ajaxSpider.scan(TARGET)
    deadline = time.time() + AJAX_TIMEOUT_SEC
    while zap.ajaxSpider.status == "running":
        if time.time() > deadline:
            log("AJAX", "timeout reached, stopping")
            zap.ajaxSpider.stop()
            break
        log("AJAX", f"results so far: {zap.ajaxSpider.number_of_results}")
        time.sleep(5)
    log("AJAX", f"done, total results: {zap.ajaxSpider.number_of_results}")


def tune_active_scanner(zap):
    """Force HIGH attack strength and LOW alert threshold on all scanners."""
    zap.ascan.set_option_host_per_scan(2)
    zap.ascan.set_option_thread_per_host(10)
    zap.ascan.set_option_max_scan_duration_in_mins(SCAN_TIMEOUT_SEC // 60)

    # The active scan default policy is the one used when no policy name is given.
    for scanner in zap.ascan.scanners():
        sid = scanner["id"]
        zap.ascan.set_scanner_attack_strength(sid, "HIGH")
        zap.ascan.set_scanner_alert_threshold(sid, "LOW")
    log("TUNE", "all active scanners set to HIGH strength, LOW threshold")


def run_active_scan(zap):
    log("ASCAN", "starting active scan")
    scan_id = zap.ascan.scan(TARGET, recurse=True, inscopeonly=False)
    deadline = time.time() + SCAN_TIMEOUT_SEC
    last_progress = -1
    while int(zap.ascan.status(scan_id)) < 100:
        if time.time() > deadline:
            log("ASCAN", "timeout reached, stopping")
            zap.ascan.stop(scan_id)
            break
        progress = int(zap.ascan.status(scan_id))
        if progress != last_progress:
            log("ASCAN", f"progress {progress}%")
            last_progress = progress
        time.sleep(15)
    log("ASCAN", "done")


def collect_alerts(zap):
    alerts = zap.core.alerts(baseurl=TARGET)
    bucket = {"High": [], "Medium": [], "Low": [], "Informational": []}
    for a in alerts:
        bucket.setdefault(a.get("risk", "Informational"), []).append(a)
    return bucket


def write_summary(bucket):
    summary = {
        "high": len(bucket["High"]),
        "medium": len(bucket["Medium"]),
        "low": len(bucket["Low"]),
        "info": len(bucket["Informational"]),
        "high_alerts": [
            {
                "name": a.get("alert"),
                "url": a.get("url"),
                "param": a.get("param"),
                "evidence": a.get("evidence"),
                "cwe": a.get("cweid"),
                "confidence": a.get("confidence"),
            }
            for a in bucket["High"]
        ],
    }
    with open("zap-summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)
    print(f"HIGH:          {summary['high']}")
    print(f"MEDIUM:        {summary['medium']}")
    print(f"LOW:           {summary['low']}")
    print(f"Informational: {summary['info']}")
    if summary["high_alerts"]:
        print("\nHIGH risk findings:")
        for a in summary["high_alerts"]:
            print(f"  - {a['name']} @ {a['url']} (param={a['param']})")


def write_reports(zap):
    """Use ZAP's native report generation."""
    try:
        html = zap.core.htmlreport()
        with open("zap-report.html", "wb") as f:
            f.write(html.encode("utf-8") if isinstance(html, str) else html)
        log("REPORT", "wrote zap-report.html")
    except Exception as e:
        log("REPORT", f"html report failed: {e}")
    try:
        xml = zap.core.xmlreport()
        with open("zap-report.xml", "wb") as f:
            f.write(xml.encode("utf-8") if isinstance(xml, str) else xml)
        log("REPORT", "wrote zap-report.xml")
    except Exception as e:
        log("REPORT", f"xml report failed: {e}")


def main():
    print("=" * 60)
    print("OWASP ZAP DAST Scan - Titan App")
    print("=" * 60)
    api_key = os.environ.get("ZAP_API_KEY", "")
    log("INIT", f"target={TARGET}, api_key={'set' if api_key else 'empty'}")

    zap = ZAPv2(apikey=api_key, proxies={"http": ZAP_PROXY, "https": ZAP_PROXY})
    if not wait_for_zap(zap):
        sys.exit(2)

    zap.core.new_session(name="titan-scan", overwrite=True)

    session = get_auth_session()
    if session is not None:
        cookie = session.cookies.get("titan_sess_id")
        if cookie:
            setup_zap_session(zap, cookie)
        seed_endpoints(session)
    else:
        # Even without auth, seed the public endpoints.
        anon = requests.Session()
        anon.proxies = {"http": ZAP_PROXY, "https": ZAP_PROXY}
        anon.verify = False
        seed_endpoints(anon)

    import_openapi(zap)
    run_spider(zap)
    run_ajax_spider(zap)
    tune_active_scanner(zap)
    run_active_scan(zap)

    bucket = collect_alerts(zap)
    write_summary(bucket)
    write_reports(zap)

    # Fail the pipeline if any HIGH findings exist - that's the whole point.
    if bucket["High"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
