"""
ExpenseEye API - Flask REST API for bank statement analytics

Copyright (c) 2024 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from collections import defaultdict, deque
from functools import wraps
import glob
import logging
import sys
import os
import uuid
import tempfile
import threading
import time

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
from core.forecast import forecast_cashflow
from core.categorizer import categorize_transactions, get_model_card
from core.anomaly import detect_anomalies
from core.reconcile import reconcile_recurring

app = Flask(__name__)

# Server-side logging. Tracebacks and internal errors go here, never to the
# client (responses return a generic message instead of raw exception text).
logging.basicConfig(level=logging.INFO)
logger = app.logger

_DEBUG_MODE = os.getenv('DEBUG', '0') == '1'

# Enable CORS so the React frontend (served from a different origin) can reach
# the API. Set CORS_ORIGINS to a comma-separated list of allowed origins in
# production (e.g. "https://expenseeye.pages.dev"). It defaults to "*" since the
# API is session-based and uses no cookies/credentials, but you can require an
# explicit allowlist by setting CORS_STRICT=1 (recommended for production).
_cors_origins = os.getenv('CORS_ORIGINS', '').strip()
_cors_strict = os.getenv('CORS_STRICT', '0') == '1'

# Safe default frontend origin when CORS_ORIGINS is unset (P2-17): prefer a
# known origin over a wildcard. Override via CORS_ORIGINS in any environment.
_DEFAULT_ORIGIN = os.getenv('DEFAULT_CORS_ORIGIN', 'https://expenseeye.pages.dev')

if _cors_origins == '*':
    _allowed_origins = '*'                       # explicit, deliberate wildcard
elif _cors_origins:
    _allowed_origins = [o.strip() for o in _cors_origins.split(',') if o.strip()]
elif _cors_strict and not _DEBUG_MODE:
    # Fail closed: refuse to start wide-open when strict mode is requested.
    raise RuntimeError(
        "CORS_STRICT=1 but CORS_ORIGINS is not set. Provide an explicit "
        "allowlist of frontend origin(s), e.g. https://expenseeye.pages.dev"
    )
elif _DEBUG_MODE:
    _allowed_origins = '*'                        # convenient for local development
else:
    _allowed_origins = [_DEFAULT_ORIGIN]
    logger.warning(
        "CORS_ORIGINS not set; defaulting to %s. Set CORS_ORIGINS to your "
        "frontend origin(s) to override.", _DEFAULT_ORIGIN,
    )

# allow_headers must include X-Session-Id so the browser's cross-origin
# preflight succeeds: the session id travels in that header (not the query
# string) to keep it out of access / proxy logs and browser history.
CORS(app, origins=_allowed_origins, allow_headers=["Content-Type", "X-Session-Id"])

# File size limit: 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Session databases are written to the system temp dir. They are reaped after
# this TTL so the temp dir does not grow without bound and uploaded financial
# data does not outlive the session (the UI promises automatic deletion).
SESSION_TTL_SECONDS = int(os.getenv('SESSION_TTL_SECONDS', str(30 * 60)))

# Database path (absolute path for deployment safety)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expenseeye.db")


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #
# A small, thread-safe, in-process sliding-window limiter. The upload and
# compute endpoints are unauthenticated, so this caps anonymous abuse / DoS
# without pulling in an external dependency or backing store.
_rate_lock = threading.Lock()
_rate_hits = defaultdict(deque)


def _client_key():
    """Best-effort client identifier, honoring a proxy's X-Forwarded-For."""
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _rate_limited(bucket, max_calls, window_seconds=60):
    """Return True if this client has exceeded max_calls within the window."""
    now = time.time()
    key = (bucket, _client_key())
    cutoff = now - window_seconds
    with _rate_lock:
        dq = _rate_hits[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= max_calls:
            return True
        dq.append(now)
        return False


def rate_limit(bucket, max_calls, window_seconds=60):
    """Decorator: reject with HTTP 429 once a client exceeds the limit."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if _rate_limited(bucket, max_calls, window_seconds):
                return jsonify({
                    "success": False,
                    "error": "Too many requests. Please slow down and try again shortly."
                }), 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# --------------------------------------------------------------------------- #
# Session cleanup (TTL reaper)
# --------------------------------------------------------------------------- #
# Temp artifacts this app creates. Reaped together so nothing lingers.
_SESSION_GLOBS = ("expenseeye_*.db", "upload_*.csv", "preview_*.csv")
_reap_lock = threading.Lock()
_last_reap = 0.0


def _reap_sessions(force=False):
    """
    Delete session databases / temp uploads older than SESSION_TTL_SECONDS.

    Throttled to run at most once per minute regardless of request volume, so
    it is cheap to call from a before_request hook.
    """
    global _last_reap
    now = time.time()
    with _reap_lock:
        if not force and now - _last_reap < 60:
            return
        _last_reap = now

    tmp = tempfile.gettempdir()
    cutoff = now - SESSION_TTL_SECONDS
    for pattern in _SESSION_GLOBS:
        for path in glob.glob(os.path.join(tmp, pattern)):
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass  # already gone or in use; nothing to do

    # Forget rate-limit history older than an hour so the table stays bounded.
    rl_cutoff = now - 3600
    with _rate_lock:
        for key in list(_rate_hits.keys()):
            dq = _rate_hits[key]
            while dq and dq[0] <= rl_cutoff:
                dq.popleft()
            if not dq:
                del _rate_hits[key]


@app.before_request
def _maybe_reap():
    """Opportunistic, throttled cleanup on any incoming request."""
    _reap_sessions()


# --------------------------------------------------------------------------- #
# Session id helpers
# --------------------------------------------------------------------------- #
def is_valid_uuid(val):
    """Check if the provided string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _get_session_id():
    """
    Resolve the session id from the X-Session-Id header, falling back to the
    legacy session_id query parameter for backward compatibility.
    """
    return request.headers.get('X-Session-Id') or request.args.get('session_id')


def _resolve_session_db(session_id):
    """
    Validate a session_id and return its database path.

    Returns (db_path, None) on success or (None, (json_response, status))
    on failure.
    """
    if not session_id:
        return None, (jsonify({
            "success": False,
            "error": "session_id is required (send the X-Session-Id header)"
        }), 400)
    # Security: validate the session id is a proper UUID to prevent path traversal.
    if not is_valid_uuid(session_id):
        return None, (jsonify({
            "success": False,
            "error": "Invalid session_id format"
        }), 400)
    db_path = os.path.join(tempfile.gettempdir(), f"expenseeye_{session_id}.db")
    if not os.path.exists(db_path):
        # 404: the session genuinely does not exist (expired, reaped, or deleted
        # via DELETE /session/<id>), as opposed to a malformed request.
        return None, (jsonify({
            "success": False,
            "error": "Session not found or expired"
        }), 404)
    return db_path, None


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
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
@rate_limit('upload', 20)
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

    temp_path = None
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
        temp_path = None

        return jsonify({
            "success": True,
            "header_row": header_row,
            "columns": list(df.columns),
            "sample_rows": df.head().to_dict('records'),
            "total_columns": len(df.columns)
        })

    except Exception:
        logger.exception("[preview-csv] failed")
        return jsonify({
            "success": False,
            "error": "Could not preview this CSV file."
        }), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.route('/upload', methods=['POST'])
@rate_limit('upload', 20)
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
        temp_csv_path = None

        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "File processed. Data is isolated and will be deleted automatically.",
            "transactions_loaded": transactions_loaded,
            "mapping_info": mapping_info
        })

    except ValueError as e:
        # User error - invalid CSV format. The message is intended for the user.
        logger.info("[upload] rejected (invalid CSV): %s", e)

        # Clean up the session database (the CSV is handled in finally)
        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception:
        # Server error - log full traceback, return a generic message.
        logger.exception("[upload] unexpected error")

        if db_path and os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while processing your file"
        }), 500

    finally:
        if temp_csv_path and os.path.exists(temp_csv_path):
            try:
                os.remove(temp_csv_path)
            except OSError:
                pass


@app.route('/subscriptions', methods=['GET'])
@rate_limit('compute', 60)
def subscriptions():
    """
    Detect and return recurring subscriptions for a session.

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err

    try:
        results = detect_subscriptions(db_path)
        return jsonify({
            "success": True,
            "count": len(results),
            "subscriptions": results
        })
    except Exception:
        logger.exception("[subscriptions] failed")
        return jsonify({
            "success": False,
            "error": "Could not analyze subscriptions for this session."
        }), 500


@app.route('/overspending', methods=['GET'])
@rate_limit('compute', 60)
def overspending():
    """
    Detect and return overspending months for a session.

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err

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
    except Exception:
        logger.exception("[overspending] failed")
        return jsonify({
            "success": False,
            "error": "Could not analyze overspending for this session."
        }), 500


@app.route('/forecast', methods=['GET'])
@rate_limit('compute', 60)
def forecast():
    """
    Cash-flow forecast (ML / time-series) for a session.

    Forecasts the next 30 days and next month of spending using Holt-Winters
    exponential smoothing, with a moving-average baseline fallback for sparse
    history. Reports holdout accuracy (MAE / RMSE / MAPE).

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err
    try:
        result = forecast_cashflow(db_path)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception:
        logger.exception("[forecast] failed")
        return jsonify({"success": False, "error": "Could not generate a forecast for this session."}), 500


@app.route('/categorize', methods=['GET'])
@rate_limit('compute', 60)
def categorize():
    """
    ML transaction categorization for a session.

    Uses a trained TF-IDF + LogisticRegression text classifier, falling back to
    rule-based keyword matching only for low-confidence predictions.

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err
    try:
        result = categorize_transactions(db_path)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception:
        logger.exception("[categorize] failed")
        return jsonify({"success": False, "error": "Could not categorize transactions for this session."}), 500


@app.route('/model-card', methods=['GET'])
def model_card():
    """Return evaluation metrics for the categorization model (no session)."""
    try:
        return jsonify(get_model_card())
    except Exception:
        logger.exception("[model-card] failed")
        return jsonify({"success": False, "error": "Could not load the model card."}), 500


@app.route('/anomalies', methods=['GET'])
@rate_limit('compute', 60)
def anomalies():
    """
    Statistical anomaly detection for a session.

    Flags unusual transactions using robust per-category z-scores and explains
    why each was flagged.

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err
    try:
        result = detect_anomalies(db_path)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception:
        logger.exception("[anomalies] failed")
        return jsonify({"success": False, "error": "Could not run anomaly detection for this session."}), 500


@app.route('/reconcile', methods=['GET'])
@rate_limit('compute', 60)
def reconcile():
    """
    Reconcile the expected recurring ledger against actual statement charges.

    Closes one finance-ops loop over the whole batch: reports a match rate plus
    a two-sided exception list (expected-but-missing, actual-but-unscheduled).

    Session id: X-Session-Id header (or legacy session_id query parameter).
    """
    db_path, err = _resolve_session_db(_get_session_id())
    if err:
        return err
    try:
        result = reconcile_recurring(db_path)
        status = 200 if result.get("success") else 400
        return jsonify(result), status
    except Exception:
        logger.exception("[reconcile] failed")
        return jsonify({"success": False, "error": "Could not reconcile this session."}), 500


@app.route('/session/<session_id>', methods=['DELETE'])
@rate_limit('compute', 60)
def delete_session(session_id):
    """
    Delete a session's database so its data becomes unreachable (P0-4).

    Idempotent: returns 204 whether or not the session existed. This backs the
    "delete on exit" promise the UI makes; the TTL reaper is the safety net.
    """
    if not is_valid_uuid(session_id):
        return jsonify({"success": False, "error": "Invalid session_id format"}), 400
    db_path = os.path.join(tempfile.gettempdir(), f"expenseeye_{session_id}.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except OSError:
        logger.exception("[session-delete] failed")
        return jsonify({"success": False, "error": "Could not delete the session."}), 500
    return ('', 204)


# Sweep session files left behind by a previous process. This runs at IMPORT,
# not under `__main__`, because under a WSGI server (gunicorn) the __main__
# block never executes and the startup sweep would silently stop happening.
# The per-request reaper would eventually catch stale files, but only once
# traffic arrives -- an idle instance would sit on them indefinitely.
_reap_sessions(force=True)


if __name__ == '__main__':
    print("Starting ExpenseEye API...")
    print("Available endpoints:")
    print("  GET  /health")
    print("  POST /upload")
    print("  GET  /subscriptions   (X-Session-Id header)")
    print("  GET  /overspending    (X-Session-Id header)")
    print("  GET  /forecast        (X-Session-Id header)")
    print("  GET  /categorize      (X-Session-Id header)")
    print("  GET  /anomalies       (X-Session-Id header)")
    print("  GET  /reconcile       (X-Session-Id header)")
    print("  GET  /model-card")
    # Bind to the port provided by the hosting platform (Render/Heroku set
    # $PORT); fall back to 5000 for local development.
    port = int(os.getenv('PORT', '5000'))
    print(f"\nListening on http://0.0.0.0:{port}")
    # Debug mode disabled by default for production safety.
    # Set DEBUG=1 environment variable to enable debug mode.
    app.run(host="0.0.0.0", port=port, debug=_DEBUG_MODE)
