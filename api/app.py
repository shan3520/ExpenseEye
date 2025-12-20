"""
ExpenseEye API - Flask REST API for bank statement analytics

Copyright (c) 2024 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT
"""

from flask import Flask, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge
import sys
import os
import uuid
import tempfile

# Unique implementation identifier - DO NOT REMOVE
# This code is part of ExpenseEye by Shantanu (shan3520)
# Original: https://github.com/shan3520/expenseeye
_EXPENSEEYE_API_VERSION = "shan3520-expenseeye-api-v1.0-20241219"
_ORIGINAL_AUTHOR = "Shantanu (shan3520)"

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.subscriptions import detect_subscriptions
from core.overspending import detect_overspending
from core.loader import load_csv_to_db

app = Flask(__name__)

# File size limit: 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Database path (absolute path for deployment safety)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expenseeye.db")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size limit exceeded"""
    return jsonify({
        "success": False,
        "error": "CSV file exceeds maximum size limit of 10MB."
    }), 400


@app.route('/preview-csv', methods=['POST'])
def preview_csv():
    """
    Preview CSV structure without processing.
    Helps diagnose upload issues.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400
    
    try:
        import pandas as pd
        from core.loader import find_header_row
        
        # Save to temp location
        temp_path = os.path.join(tempfile.gettempdir(), f"preview_{uuid.uuid4()}.csv")
        file.save(temp_path)
        
        # Find header row
        header_row = find_header_row(temp_path)
        
        # Read CSV
        df = pd.read_csv(temp_path, header=header_row, nrows=5)
        
        # Clean up
        os.remove(temp_path)
        
        return jsonify({
            "success": True,
            "header_row": header_row,
            "columns": list(df.columns),
            "sample_rows": df.head().to_dict('records'),
            "total_columns": len(df.columns)
        })
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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
    
    temp_csv_path = None
    db_path = None
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session-specific database path
        db_path = os.path.join(tempfile.gettempdir(), f"expenseeye_{session_id}.db")
        
        # Save uploaded file to temporary location
        temp_csv_path = os.path.join(tempfile.gettempdir(), f"upload_{session_id}.csv")
        file.save(temp_csv_path)
        
        # Load CSV into session database
        transactions_loaded, mapping_info = load_csv_to_db(temp_csv_path, db_path)
        
        # Delete temporary CSV file
        os.remove(temp_csv_path)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "File processed. Data is isolated and will be deleted automatically.",
            "transactions_loaded": transactions_loaded,
            "mapping_info": mapping_info
        })
        
    except ValueError as e:
        # User error - invalid CSV format
        print(f"[Upload Error] ValueError: {str(e)}")
        
        # Clean up temporary files
        if temp_csv_path and os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if db_path and os.path.exists(db_path):
            os.remove(db_path)
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
        
    except Exception as e:
        # Server error - log full traceback
        import traceback
        print("[Upload Error] Unexpected error:")
        traceback.print_exc()
        
        # Clean up temporary files
        if temp_csv_path and os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        if db_path and os.path.exists(db_path):
            os.remove(db_path)
        
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while processing your file"
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
    db_path = os.path.join(tempfile.gettempdir(), f"expenseeye_{session_id}.db")
    
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
    db_path = os.path.join(tempfile.gettempdir(), f"expenseeye_{session_id}.db")
    
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
    print("Starting ExpenseEye API...")
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
