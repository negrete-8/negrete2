from flask import Blueprint, request, jsonify, render_template_string, g
from database import db_instance
from utils import login_required, SecurityManager

shipping_bp = Blueprint('shipping', __name__)

@shipping_bp.route('/track', methods=['GET'])
def track_package():
    """
    Public tracking endpoint.
    """
    code = request.args.get('code', '')
    
    # Sanitize input for XSS
    safe_code = SecurityManager.sanitize_input(code)
    
    query = f"SELECT * FROM shipments WHERE tracking_code = '{code}'"
    
    try:
        results = db_instance.query_unsafe(query)
        
        if not results:
            html = f"""
            <h3>Titan Logistics Tracking</h3>
            <div style="color:red; border:1px solid red; padding:10px;">
                No shipment found for code: <b>{safe_code}</b>
            </div>
            """
            return render_template_string(html)
              
        html_output = "<h3>Tracking Results</h3><table border='1' cellpadding='5' style='border-collapse:collapse; width:100%;'>"
        html_output += "<tr style='background:#ccc'><th>Code</th><th>Status</th><th>Notes (Driver Updates)</th><th>Destination</th></tr>"
        
        for row in results:
            html_output += f"<tr><td>{row[1]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td></tr>"
            
        html_output += "</table>"
        
        return render_template_string(html_output)

    except Exception as e:
        return str(e), 500

@shipping_bp.route('/shipment/update_notes', methods=['POST'])
@login_required
def update_notes():
    """
    Update delivery notes for drivers.
    """
    data = request.json
    shipment_id = data.get('id')
    raw_notes = data.get('notes')
    
    clean_notes = SecurityManager.sanitize_input(raw_notes)
    
    query = "UPDATE shipments SET notes = ? WHERE id = ?"
    
    try:
        db_instance.query_secure(query, (clean_notes, shipment_id))
        db_instance.get_connection().commit()
        
        return jsonify({"status": "success", "msg": "Notes updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@shipping_bp.route('/my_shipments', methods=['GET'])
@login_required
def my_shipments():
    """
    List shipments for the logged in user.
    """
    query = "SELECT * FROM shipments WHERE user_id = ?"
    results = db_instance.query_secure(query, (g.user['uid'],))
    
    out = []
    for r in results:
        out.append(dict(r))
    return jsonify(out)
