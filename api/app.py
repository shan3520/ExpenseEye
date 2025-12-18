from flask import Flask, jsonify, request
import sys
import os
import uuid
import tempfile
from werkzeug.utils import secure_filename

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.subscriptions import detect_subscriptions
from core.overspending import detect_overspending
from core.loader import load_csv_to_db

app = Flask(__name__)

# Database path (absolute path for deployment safety)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "smartspend.db")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})


@app.route('/upload', methods=['POST'])
def upload():
    """
    Upload a bank statement CSV and create an isolated session.
    
    Accepts:
        multipart/form-data with 'file' field containing CSV
        
    Returns:
        JSON with session_id for use in analytics endpoints
    """
    # Check if file was provided
    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "error": "No file provided"
        }), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400
    
    # Validate file extension
    if not file.filename.endswith('.csv'):
        return jsonify({
            "success": False,
            "error": "File must be a CSV"
        }), 400
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session-specific database path
        db_path = os.path.join(tempfile.gettempdir(), f"smartspend_{session_id}.db")
        
        # Save uploaded file to temporary location
        temp_csv_path = os.path.join(tempfile.gettempdir(), f"upload_{session_id}.csv")
        file.save(temp_csv_path)
        
        # Load CSV into session database
        transactions_loaded = load_csv_to_db(temp_csv_path, db_path)
        
        # Delete temporary CSV file
        os.remove(temp_csv_path)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "File processed. Data is isolated and will be deleted automatically.",
            "transactions_loaded": transactions_loaded
        })
        
    except Exception as e:
        # Clean up temporary files if they exist
        if 'temp_csv_path' in locals() and os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if 'db_path' in locals() and os.path.exists(db_path):
            os.remove(db_path)
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/subscriptions', methods=['GET'])
def subscriptions():
    """
    Detect and return recurring subscriptions for a session.
    
    Required Query Parameter:
        session_id: UUID from /upload endpoint
    """
    # Get session_id from query parameters
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({
            "success": False,
            "error": "session_id query parameter is required"
        }), 400
    
    # Construct session-specific database path
    db_path = os.path.join(tempfile.gettempdir(), f"smartspend_{session_id}.db")
    
    # Check if session database exists
    if not os.path.exists(db_path):
        return jsonify({
            "success": False,
            "error": "Session not found or expired"
        }), 400
    
    try:
        results = detect_subscriptions(db_path)
        return jsonify({
            "success": True,
            "count": len(results),
            "subscriptions": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/overspending', methods=['GET'])
def overspending():
    """
    Detect and return overspending months for a session.
    
    Required Query Parameter:
        session_id: UUID from /upload endpoint
    """
    # Get session_id from query parameters
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({
            "success": False,
            "error": "session_id query parameter is required"
        }), 400
    
    # Construct session-specific database path
    db_path = os.path.join(tempfile.gettempdir(), f"smartspend_{session_id}.db")
    
    # Check if session database exists
    if not os.path.exists(db_path):
        return jsonify({
            "success": False,
            "error": "Session not found or expired"
        }), 400
    
    try:
        results = detect_overspending(db_path)
        
        # Separate overspending and normal months
        overspending_months = [r for r in results if r['status'] == 'OVERSPENDING']
        normal_months = [r for r in results if r['status'] == 'NORMAL']
        
        return jsonify({
            "success": True,
            "summary": {
                "total_analyzed": len(results),
                "overspending_count": len(overspending_months),
                "normal_count": len(normal_months)
            },
            "months": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("Starting SmartSpend API...")
    print("Available endpoints:")
    print("  GET  /health")
    print("  POST /upload")
    print("  GET  /subscriptions?session_id=<UUID>")
    print("  GET  /overspending?session_id=<UUID>")
    print("\nListening on http://localhost:5000")
    # Debug mode disabled by default for production safety
    # Set DEBUG=1 environment variable to enable debug mode
    debug_mode = os.getenv('DEBUG', '0') == '1'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
