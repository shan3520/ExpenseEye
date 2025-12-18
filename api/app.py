from flask import Flask, jsonify
import sys
import os

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.subscriptions import detect_subscriptions
from core.overspending import detect_overspending

app = Flask(__name__)

# Database path (absolute path for deployment safety)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "smartspend.db")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})


@app.route('/subscriptions', methods=['GET'])
def subscriptions():
    """
    Detect and return recurring subscriptions.
    Calls core.subscriptions.detect_subscriptions()
    """
    try:
        results = detect_subscriptions(DB_PATH)
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
    Detect and return overspending months.
    Calls core.overspending.detect_overspending()
    """
    try:
        results = detect_overspending(DB_PATH)
        
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
    print("  GET /health")
    print("  GET /subscriptions")
    print("  GET /overspending")
    print("\nListening on http://localhost:5000")
    # Debug mode disabled by default for production safety
    # Set DEBUG=1 environment variable to enable debug mode
    debug_mode = os.getenv('DEBUG', '0') == '1'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
