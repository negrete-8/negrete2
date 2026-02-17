import subprocess
import platform
from flask import Blueprint, request, jsonify
from utils import login_required, admin_required, SecurityManager

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard/stats', methods=['GET'])
@login_required
@admin_required
def stats():
    return jsonify({
        "system": "Titan Enterprise v4.5",
        "status": "Online",
        "load": "0.45",
        "active_users": 142
    })

@admin_bp.route('/system/diagnostics', methods=['POST'])
@login_required
@admin_required
def system_check():
    """
    Admin Diagnostic Tool.
    Pings a backend server to check connectivity.
    """
    target = request.json.get('target_ip')
    
    if not target:
        return jsonify({"error": "Target IP required"}), 400

    if ";" in target or "&&" in target:
        return jsonify({"error": "Illegal characters detected"}), 400
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = f"ping {param} 1 {target}"
    
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return jsonify({
            "target": target,
            "output": output.decode('utf-8', errors='ignore')
        })
    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "Command failed",
            "output": e.output.decode('utf-8', errors='ignore')
        }), 500

@admin_bp.route('/users/delete', methods=['POST'])
@login_required
@admin_required
def delete_user():
    """
    Delete a user from the system.
    """
    user_id = request.json.get('user_id')
    
    from database import db_instance
    try:
        query = f"DELETE FROM users WHERE id = {user_id}"
        db_instance.execute_script_unsafe(query)
        return jsonify({"msg": f"User {user_id} deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
