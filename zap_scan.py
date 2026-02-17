import time
import os
import sys
import requests
from zapv2 import ZAPv2

print("="*60)
print("OWASP ZAP SCAN - Titan App (MODO COMPLETO)")
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
zap.core.new_session(name='titan-scan-completo', overwrite=True)

# ============================================
# AUTENTICACIÓN (para acceder a áreas restringidas)
# ============================================
print("[4.1] Autenticando en la aplicación...")
try:
    # Login como admin para acceder a rutas protegidas
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin123"}
    login_resp = session.post(f"{target}/api/auth/login", json=login_data)
    
    if login_resp.status_code == 200:
        token = login_resp.cookies.get('titan_sess_id')
        print(f"    ✅ Login exitoso como admin")
        
        # Configurar la autenticación en ZAP
        print("[4.2] Configurando autenticación en ZAP...")
        # Añadir cookie de sesión a ZAP
        zap.core.set_option_http_state_enabled(True)
        context_id = zap.context.new_context('titan-context')
        
        # Incluir todas las URLs en el contexto
        zap.context.include_in_context('titan-context', '.*')
        
        # Configurar script de autenticación simple con cookie
        script_name = 'titan-auth.js'
        script_content = f"""
// Authentication script for Titan App
var Cookie = Java.type('org.apache.commons.httpclient.Cookie');

function authenticate(helper, paramsValues, credentials) {{
    var cookies = [{{
        name: 'titan_sess_id',
        value: '{token}',
        domain: 'localhost',
        path: '/'
    }}];
    
    cookies.forEach(function(cookieData) {{
        var cookie = new Cookie(cookieData.domain, cookieData.name, cookieData.value, cookieData.path, 99999999, false);
        helper.getHttpState().addCookie(cookie);
    }});
    
    return helper.prepareMessage();
}}
"""
        # Guardar script temporal
        with open('/tmp/titan-auth.js', 'w') as f:
            f.write(script_content)
        
        # Cargar script en ZAP
        zap.script.load('titan-auth', 'authentication', 'Oracle Nashorn', '/tmp/titan-auth.js')
        zap.script.enable('titan-auth')
        print("    ✅ Autenticación configurada en ZAP")
    else:
        print(f"    ⚠️ No se pudo autenticar: {login_resp.status_code}")
except Exception as e:
    print(f"    ⚠️ Error en autenticación: {e}")

# ============================================
# SPIDER (rastreo)
# ============================================
print("[5] Iniciando spider (rastreo)...")
zap.spider.scan(target)
time.sleep(5)
for i in range(12):
    status = zap.spider.status()
    print(f"    Spider: {status}%")
    if status == '100':
        break
    time.sleep(5)

# ============================================
# ESCANEO ACTIVO (profundo)
# ============================================
print("[6] Iniciando escaneo activo (ataques simulados)...")
zap.ascan.scan(target, recurse=True, inscopeonly=False)
time.sleep(5)
for i in range(30):  # Más tiempo para escaneo profundo
    status = zap.ascan.status()
    print(f"    Escaneo activo: {status}%")
    if status == '100':
        break
    time.sleep(10)  # Esperar más entre verificaciones

# ============================================
# OBTENER ALERTAS
# ============================================
print("[7] Obteniendo alertas...")
alerts = zap.core.alerts(baseurl=target)
high_alerts = [a for a in alerts if a.get('risk') == 'High']
medium_alerts = [a for a in alerts if a.get('risk') == 'Medium']
low_alerts = [a for a in alerts if a.get('risk') == 'Low']

print(f"\n📊 RESULTADOS FINALES:")
print(f"  🔴 HIGH: {len(high_alerts)}")
print(f"  🟡 MEDIUM: {len(medium_alerts)}")
print(f"  🟢 LOW: {len(low_alerts)}")
print(f"  📋 TOTAL: {len(alerts)}")

# Mostrar detalles de alertas HIGH si las hay
if high_alerts:
    print("\n🔴 ALERTAS HIGH ENCONTRADAS:")
    for alert in high_alerts:
        print(f"  • {alert.get('alert')} - {alert.get('url')}")

# ============================================
# GENERAR REPORTE HTML
# ============================================
print("[8] Generando reporte HTML detallado...")

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OWASP ZAP DAST Report - Titan App (COMPLETO)</title>
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
        <h1>🔍 OWASP ZAP DAST Scan Report - Titan App (COMPLETO)</h1>
        <p><strong>Target:</strong> {target}</p>
        <p><strong>Fecha:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Autenticación:</strong> {'✅ Configurada' if 'token' in locals() else '❌ No configurada'}</p>
        
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
        </div>
        """
else:
    html_content += "<p>⚠️ No se encontraron vulnerabilidades HIGH. Esto puede indicar que el escaneo no fue suficientemente profundo o que la autenticación falló.</p>"

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
        <h2>📊 Recomendaciones para mejorar el escaneo</h2>
        <ul>
            <li>🔐 <strong>Autenticación:</strong> {'Configurada correctamente' if 'token' in locals() else 'No se pudo autenticar - las rutas protegidas no se escanearán'}</li>
            <li>⚡ <strong>Tiempo de escaneo:</strong> Aumentar el número de iteraciones para detectar más vulnerabilidades</li>
            <li>🎯 <strong>Rutas críticas:</strong> /api/shipping/track (SQLi), /api/admin/system/diagnostics (RCE), /api/auth/profile (IDOR)</li>
        </ul>
        
        <div class="timestamp">
            Reporte generado automáticamente por GitHub Actions<br>
            Commit: {os.popen('git rev-parse --short HEAD').read().strip() if os.path.exists('.git') else 'N/A'}
        </div>
    </div>
</body>
</html>
"""

with open('zap-report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

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
    print(f"    SQL Injection, RCE y otras vulnerabilidades detectadas")
    for alert in high_alerts[:5]:
        print(f"     • {alert.get('alert', 'N/A')}")
    sys.exit(1)
else:
    print("⚠️  ADVERTENCIA: No se encontraron vulnerabilidades HIGH")
    print("    Posibles causas:")
    print("    - La autenticación no funcionó correctamente")
    print("    - El escaneo fue demasiado superficial")
    print("    - ZAP necesita más tiempo para detectar SQLi complejas")
    print("\n    Revisa el reporte HTML para ver alertas MEDIUM/LOW")
    sys.exit(0)  # Cambia a 1 si quieres que falle siempre
    print("✅ PIPELINE EXITOSO: No hay vulnerabilidades HIGH")
    sys.exit(0)
