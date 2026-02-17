import time
import os
import sys
from zapv2 import ZAPv2

print("="*60)
print("OWASP ZAP SCAN - Titan App")
print("="*60)

api_key = os.environ.get('ZAP_API_KEY', '')
target = 'http://localhost:5000'

print(f"[1] Target: {target}")
print(f"[2] API Key: {'✅ OK' if api_key else '❌ NO'}")

# Conectar a ZAP
print(f"[3] Conectando a ZAP en http://localhost:8080...")
zap = ZAPv2(apikey=api_key, proxies={'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})

# Intentar conectar con reintentos
conectado = False
for i in range(20):
    try:
        version = zap.core.version
        print(f"    ✅ ZAP conectado. Versión: {version}")
        conectado = True
        break
    except Exception as e:
        print(f"    ⏳ Intento {i+1}/20: ZAP no responde, esperando 3s...")
        time.sleep(3)

if not conectado:
    print("    ❌ No se pudo conectar a ZAP")
    sys.exit(1)

# Nueva sesión
print("[4] Creando nueva sesión...")
zap.core.new_session(name='titan-scan', overwrite=True)

# Spider
print("[5] Iniciando spider...")
zap.spider.scan(target)
time.sleep(5)
for i in range(12):
    status = zap.spider.status()
    print(f"    Spider: {status}%")
    if status == '100':
        break
    time.sleep(5)

# Escaneo activo
print("[6] Iniciando escaneo activo...")
zap.ascan.scan(target)
time.sleep(5)
for i in range(15):
    status = zap.ascan.status()
    print(f"    Escaneo: {status}%")
    if status == '100':
        break
    time.sleep(5)

# Obtener alertas
print("[7] Obteniendo alertas...")
alerts = zap.core.alerts()
high_alerts = [a for a in alerts if a.get('risk') == 'High']
medium_alerts = [a for a in alerts if a.get('risk') == 'Medium']
low_alerts = [a for a in alerts if a.get('risk') == 'Low']

print(f"\n📊 RESULTADOS:")
print(f"  🔴 HIGH: {len(high_alerts)}")
print(f"  🟡 MEDIUM: {len(medium_alerts)}")
print(f"  🟢 LOW: {len(low_alerts)}")
print(f"  📋 TOTAL: {len(alerts)}")

# ============================================
# GENERAR REPORTE HTML
# ============================================
print("[8] Generando reporte HTML detallado...")

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OWASP ZAP DAST Report - Titan App</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; }}
        .stat {{ text-align: center; padding: 20px; border-radius: 5px; min-width: 150px; margin: 10px; }}
        .stat-high {{ background-color: #ffebee; }}
        .stat-medium {{ background-color: #fff3e0; }}
        .stat-low {{ background-color: #e8f5e9; }}
        .stat-total {{ background-color: #e3f2fd; }}
        .number {{ font-size: 48px; font-weight: bold; }}
        .high {{ color: #d32f2f; }}
        .medium {{ color: #f57c00; }}
        .low {{ color: #388e3c; }}
        .alert {{ margin: 20px 0; padding: 15px; border-left: 5px solid; background-color: #fafafa; border-radius: 0 5px 5px 0; }}
        .alert-high {{ border-left-color: #d32f2f; }}
        .alert-medium {{ border-left-color: #f57c00; }}
        .alert-low {{ border-left-color: #388e3c; }}
        .url {{ color: #666; font-size: 0.9em; word-break: break-all; }}
        .solution {{ background-color: #e8f5e9; padding: 10px; margin-top: 10px; border-radius: 5px; }}
        .timestamp {{ color: #999; text-align: right; margin-top: 30px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 OWASP ZAP DAST Scan Report</h1>
        <p><strong>Target:</strong> {target}</p>
        <p><strong>Fecha:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <div class="stat stat-high">
                <div class="number high">{len(high_alerts)}</div>
                <div>Alertas HIGH</div>
            </div>
            <div class="stat stat-medium">
                <div class="number medium">{len(medium_alerts)}</div>
                <div>Alertas MEDIUM</div>
            </div>
            <div class="stat stat-low">
                <div class="number low">{len(low_alerts)}</div>
                <div>Alertas LOW</div>
            </div>
            <div class="stat stat-total">
                <div class="number">{len(alerts)}</div>
                <div>Total Alertas</div>
            </div>
        </div>
        
        <h2>❌ Alertas de Alto Riesgo (HIGH) - {len(high_alerts)} encontradas</h2>
"""

if high_alerts:
    for alert in high_alerts:
        html_content += f"""
        <div class="alert alert-high">
            <h3>{alert.get('alert', 'N/A')}</h3>
            <p class="url"><strong>URL:</strong> {alert.get('url', 'N/A')}</p>
            <p><strong>Riesgo:</strong> <span class="high">{alert.get('risk', 'N/A')}</span></p>
            <p><strong>Confianza:</strong> {alert.get('confidence', 'N/A')}</p>
            <p><strong>Descripción:</strong> {alert.get('description', 'N/A')}</p>
            <div class="solution">
                <strong>Solución:</strong> {alert.get('solution', 'No disponible')}
            </div>
            <p><small><strong>Referencia:</strong> {alert.get('reference', 'N/A')}</small></p>
        </div>
        """
else:
    html_content += "<p>No se encontraron vulnerabilidades de alto riesgo.</p>"

html_content += f"""
        <h2>🟡 Alertas de Riesgo Medio (MEDIUM) - {len(medium_alerts)} encontradas</h2>
"""

if medium_alerts:
    for alert in medium_alerts:
        html_content += f"""
        <div class="alert alert-medium">
            <h3>{alert.get('alert', 'N/A')}</h3>
            <p class="url"><strong>URL:</strong> {alert.get('url', 'N/A')}</p>
            <p><strong>Riesgo:</strong> <span class="medium">{alert.get('risk', 'N/A')}</span></p>
            <p><strong>Confianza:</strong> {alert.get('confidence', 'N/A')}</p>
            <p><strong>Descripción:</strong> {alert.get('description', 'N/A')}</p>
            <div class="solution">
                <strong>Solución:</strong> {alert.get('solution', 'No disponible')}
            </div>
        </div>
        """
else:
    html_content += "<p>No se encontraron vulnerabilidades de riesgo medio.</p>"

html_content += f"""
        <h2>🟢 Alertas de Riesgo Bajo (LOW) - {len(low_alerts)} encontradas</h2>
"""

if low_alerts:
    for alert in low_alerts:
        html_content += f"""
        <div class="alert alert-low">
            <h3>{alert.get('alert', 'N/A')}</h3>
            <p class="url"><strong>URL:</strong> {alert.get('url', 'N/A')}</p>
            <p><strong>Riesgo:</strong> <span class="low">{alert.get('risk', 'N/A')}</span></p>
            <p><strong>Confianza:</strong> {alert.get('confidence', 'N/A')}</p>
            <p><strong>Descripción:</strong> {alert.get('description', 'N/A')}</p>
        </div>
        """
else:
    html_content += "<p>No se encontraron vulnerabilidades de riesgo bajo.</p>"

html_content += f"""
        <h2>📊 Resumen General</h2>
        <ul>
            <li><strong>Total de alertas:</strong> {len(alerts)}</li>
            <li><strong>🔴 HIGH:</strong> {len(high_alerts)}</li>
            <li><strong>🟡 MEDIUM:</strong> {len(medium_alerts)}</li>
            <li><strong>🟢 LOW:</strong> {len(low_alerts)}</li>
            <li><strong>Escaneo activo:</strong> Completado</li>
            <li><strong>Spider:</strong> Completado</li>
            <li><strong>Versión ZAP:</strong> {zap.core.version}</li>
        </ul>
        
        <div class="timestamp">
            Reporte generado automáticamente por GitHub Actions<br>
            Commit: {os.popen('git rev-parse --short HEAD').read().strip() if os.path.exists('.git') else 'N/A'}
        </div>
    </div>
</body>
</html>
"""

# Guardar reporte
with open('zap-report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# Verificar
if os.path.exists('zap-report.html'):
    size = os.path.getsize('zap-report.html')
    print(f"    ✅ Reporte HTML generado: {size} bytes")
else:
    print("    ❌ No se pudo generar el reporte")
    sys.exit(1)

# ============================================
# RESULTADO FINAL
# ============================================
print("\n" + "="*60)
if len(high_alerts) > 0:
    print(f"❌ PIPELINE FALLIDO: {len(high_alerts)} vulnerabilidades HIGH encontradas")
    print(f"    Revisa el reporte HTML para más detalles")
    print("\n   Vulnerabilidades HIGH detectadas:")
    for alert in high_alerts[:5]:
        print(f"     • {alert.get('alert', 'N/A')}")
    if len(high_alerts) > 5:
        print(f"     • ... y {len(high_alerts)-5} más")
    sys.exit(1)  # 🔴 ROJO
else:
    print("✅ PIPELINE EXITOSO: No hay vulnerabilidades HIGH")
    sys.exit(0)
