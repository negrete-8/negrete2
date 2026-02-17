import hashlib
from flask import Blueprint, request, jsonify, make_response
from database import db_instance
from utils import SecurityManager, logger

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Legacy Login Endpoint v1.
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    if not SecurityManager.check_waf(username):
        return jsonify({"error": "Malicious input detected"}), 403

    pwd_hash = hashlib.md5(password.encode()).hexdigest()
    
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{pwd_hash}'"
    
    try:
        results = db_instance.query_unsafe(query)
        
        if results:
            user = results[0] # Row object
            # user[0]=id, user[1]=username, user[3]=role
            
            # Generate Token
            token = SecurityManager.generate_token(user[0], user[3], user[1])
            
            resp = jsonify({
                "status": "success", 
                "message": "Welcome to Titan Enterprise",
                "role": user[3]
            })
            resp.set_cookie('titan_sess_id', token)
            return resp
            
    except Exception as e:
        return jsonify({"error": "Database Error", "details": str(e)}), 500

    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/profile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    """
    View user profile.
    """
    query = "SELECT id, username, role, full_name, api_key FROM users WHERE id = ?"
    user = db_instance.query_secure(query, (user_id,), one=True)
    
    if user:
        return jsonify(dict(user))
    return jsonify({"error": "User not found"}), 404
