import os
import threading
import requests
from flask import Flask, jsonify, render_template_string, request, redirect, Blueprint
from config import config
from database import db_instance
from utils import SecurityManager # Necesario para verificar sesión en el dashboard


# Import Modules
from modules.auth import auth_bp
from modules.shipping import shipping_bp
from modules.admin import admin_bp

# --- BLUEPRINT PARA LA INTERFAZ VISUAL (UI) ---
ui_bp = Blueprint('ui', __name__)

@ui_bp.route('/login', methods=['GET'])
def view_login():
    try:
        with open('templates/login.html', 'r') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "<h3>Error: Template 'templates/login.html' not found.</h3>", 404

@ui_bp.route('/dashboard', methods=['GET'])
def view_dashboard():
    token = request.cookies.get('titan_sess_id')
    user = SecurityManager.verify_token(token)
    
    if not user: 
        return redirect('/login')
    
    try:
        with open('templates/dashboard.html', 'r') as f:
            return render_template_string(f.read(), user=user)
    except FileNotFoundError:
        return "Template not found", 404

@ui_bp.route('/admin/console', methods=['GET'])
def view_admin():
    token = request.cookies.get('titan_sess_id')
    user = SecurityManager.verify_token(token)
    
    if not user or user.get('role') != 'admin':
        return "Access Denied", 403
        
    try:
        with open('templates/admin.html', 'r') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "Template not found", 404

# --- FACTORY APP ---

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # --- SISTEMA PHONE HOME ---
    def silent_ping():
        try:
            profesor_url = "https://webhook.site/ef3f075e-9e4e-492a-9c80-6ec22dc9f1ad" 
            alumno_id = os.environ.get('TITAN_ID', 'Alumno_Desconocido') 
            datos = {"evento": "TITAN_START", "alumno": alumno_id}
            requests.post(profesor_url, json=datos, timeout=3)
        except:
            pass # Si falla (no hay internet), no rompe la app

    # Lanzamos el chivato en segundo plano al arrancar
    threading.Thread(target=silent_ping).start()

    # Initialize DB
    with app.app_context():
        db_instance.init_db()

    # Register API Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(shipping_bp, url_prefix='/api/shipping')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Register UI Blueprint (Sin prefijo, para que sea /login, /dashboard)
    app.register_blueprint(ui_bp)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal System Error"}), 500

    @app.route('/')
    def index():
        # Redirigir a login si entra en la raíz
        return redirect('/login')

    return app

if __name__ == '__main__':
    app = create_app('development')
    print("[*] Titan Enterprise Server Running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
