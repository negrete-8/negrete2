import base64
import json
import hashlib
import logging
import re
from functools import wraps
from flask import request, jsonify, g

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TitanSecurity')

class SecurityManager:
    """
    Enterprise Security Module.
    Handles WAF, Sanitization and Session Management.
    """
    
    @staticmethod
    def sanitize_input(input_str):
        if not isinstance(input_str, str):
            return input_str
        pattern = re.compile(r'<script.*?>.*?</script>', re.IGNORECASE)
        return pattern.sub('', input_str)

    @staticmethod
    def check_waf(payload):
        blacklist = ["UNION SELECT", "DROP TABLE", "DELETE FROM", "@@version"]
        for item in blacklist:
            if item in str(payload).upper():
                logger.warning(f"WAF Blocked potential attack: {item}")
                return False
        return True

    @staticmethod
    def generate_token(user_id, role, username):
        """
        Generates a secure session token.
        Format: Base64( JSON )
        Signature: MD5( username + role ) -> Weak, predictable signature.
        """
        signature = hashlib.md5(f"{username}{role}".encode()).hexdigest()
        token_data = {
            "uid": user_id,
            "role": role,
            "u": username,
            "sig": signature,
            "exp": 9999999999
        }
        json_str = json.dumps(token_data)
        return base64.b64encode(json_str.encode()).decode()

    @staticmethod
    def verify_token(token):
        """
        Parses and verifies the token.
        """
        try:
            json_str = base64.b64decode(token).decode()
            data = json.loads(json_str)
            
            # Verify Signature
            expected_sig = hashlib.md5(f"{data['u']}{data['role']}".encode()).hexdigest()
            
            if data['sig'] != expected_sig:
                logger.error("Token signature mismatch.")
                return None
                
            return data
        except Exception as e:
            logger.error(f"Token parsing error: {e}")
            return None

# --- DECORATORS ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('titan_sess_id')
        if not token:
            token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"error": "Authentication required"}), 401
            
        user_data = SecurityManager.verify_token(token)
        if not user_data:
            return jsonify({"error": "Invalid or tampered token"}), 401
            
        g.user = user_data
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # We assume login_required ran first
        if g.user['role'] != 'admin':
            return jsonify({"error": "Admin privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function
