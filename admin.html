<!DOCTYPE html>
<html>
<head><title>Admin Console</title></head>
<body style="background:#1a1a1a; color:#00ff00; font-family:monospace; padding:20px;">
    <h2>TitanCore Diagnostic Console</h2>
    <p>Introduce IP para comprobar latencia con el servidor central:</p>
    <input id="ip" style="background:#000; color:#00ff00; border:1px solid #00ff00; width:300px;">
    <button onclick="doPing()" style="cursor:pointer;">Ejecutar Ping</button>
    <pre id="out" style="margin-top:20px;"></pre>

    <script>
        function doPing(){
            out.innerText = "Ejecutando...";
            fetch('/api/admin/system/diagnostics', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({target_ip: ip.value})
            }).then(r => r.json()).then(d => {
                out.innerText = d.output || d.error;
            });
        }
    </script>
</body>
</html>
