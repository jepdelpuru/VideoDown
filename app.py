import os
import sys
import time
import json
import re
import hashlib
import threading
import logging
import uuid
import secrets
import subprocess
from collections import deque
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, flash, send_file, session, make_response
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

import yt_dlp
import sqlite3
import shutil
import zipfile

# --- Patch yt-dlp os.rename for Windows file locking issues ---
# FFmpeg on Windows doesn't always release file handles immediately,
# causing PermissionError when yt-dlp tries to rename temp files.
_original_os_rename = os.rename
def _retry_rename(src, dst):
    """os.rename with retry for Windows file locking."""
    for attempt in range(15):
        try:
            _original_os_rename(src, dst)
            return
        except PermissionError:
            if attempt < 14:
                time.sleep(0.5)
            else:
                raise
os.rename = _retry_rename

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
DB_PATH = os.path.join(BASE_DIR, "users.db")
COOKIE_FILE_PATH = os.path.join(BASE_DIR, "instagram_cookies.txt")
DOWNLOAD_EXPIRY_SECONDS = 3600  # 1 hour
DOWNLOAD_QUOTA_BYTES = 50 * 1024 * 1024 * 1024  # 50 GB max active downloads per user

# MIME types for streaming (Flask doesn't auto-detect all formats)
MIME_TYPES = {
    '.mp4': 'video/mp4', '.mkv': 'video/x-matroska', '.webm': 'video/webm',
    '.avi': 'video/x-msvideo', '.mov': 'video/quicktime', '.ts': 'video/mp2t',
    '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.ogg': 'audio/ogg',
    '.wav': 'audio/wav', '.flac': 'audio/flac', '.opus': 'audio/opus', '.aac': 'audio/aac',
}

# Ensure downloads directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "web_app.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# --- Flask App ---
app = Flask(__name__)
# Persist secret key across restarts so sessions survive server reboots
_secret_key_path = os.path.join(BASE_DIR, ".secret_key")
if os.path.exists(_secret_key_path):
    with open(_secret_key_path, "r") as f:
        app.config['SECRET_KEY'] = f.read().strip()
else:
    _key = secrets.token_hex(32)
    with open(_secret_key_path, "w") as f:
        f.write(_key)
    app.config['SECRET_KEY'] = _key

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['REMEMBER_COOKIE_DURATION'] = 365 * 24 * 3600  # 1 year
app.config['REMEMBER_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['SESSION_PROTECTION'] = 'basic'  # Don't invalidate on IP/UA changes

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*",
                    ping_timeout=120, ping_interval=25,
                    max_http_buffer_size=10 * 1024 * 1024)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'error'

# --- Middleware for Werkzeug 3.0 + simple-websocket disconnect bug ---
# When a websocket disconnects in threading mode, simple-websocket returns without
# calling start_response, causing Werkzeug 3.0 to raise 'AssertionError: write() before start_response'.
# This middleware detects that case and injects a dummy start_response so Werkzeug throws a 
# ConnectionError (which it ignores) instead of crashing the request handler and spamming logs.
class SupressWerkzeugSocketIOErrorMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        status_set = False

        def wrapped_start_response(status, headers, exc_info=None):
            nonlocal status_set
            status_set = True
            return start_response(status, headers, exc_info)

        app_iter = self.wsgi_app(environ, wrapped_start_response)

        if not status_set and environ.get('HTTP_UPGRADE', '').lower() == 'websocket':
            wrapped_start_response('200 OK', [('Content-Type', 'text/plain')])
            return []

        return app_iter

app.wsgi_app = SupressWerkzeugSocketIOErrorMiddleware(app.wsgi_app)


# --- Database ---
def init_db():
    """Initialize the SQLite database with users and downloads tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    # Downloads history table - persists across restarts
    c.execute('''CREATE TABLE IF NOT EXISTS downloads (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        file_size_str TEXT DEFAULT '',
        video_title TEXT DEFAULT '',
        video_url TEXT DEFAULT '',
        thumbnail TEXT DEFAULT '',
        quality TEXT DEFAULT '',
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        is_saved INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    # Share tokens table for public video links
    c.execute('''CREATE TABLE IF NOT EXISTS share_tokens (
        token TEXT PRIMARY KEY,
        download_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY (download_id) REFERENCES downloads(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    # Collections tables for organizing saved videos
    c.execute('''CREATE TABLE IF NOT EXISTS collections (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#8b5cf6',
        created_at REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS collection_downloads (
        collection_id TEXT NOT NULL,
        download_id TEXT NOT NULL,
        added_at REAL NOT NULL,
        PRIMARY KEY (collection_id, download_id),
        FOREIGN KEY (collection_id) REFERENCES collections(id),
        FOREIGN KEY (download_id) REFERENCES downloads(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS playback_positions (
        user_id TEXT NOT NULL,
        download_id TEXT NOT NULL,
        position REAL NOT NULL DEFAULT 0,
        updated_at REAL NOT NULL,
        PRIMARY KEY (user_id, download_id)
    )''')
    # Migration: add is_saved column if it doesn't exist (for existing databases)
    try:
        c.execute("SELECT is_saved FROM downloads LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE downloads ADD COLUMN is_saved INTEGER DEFAULT 0")
        log.info("Migration: added is_saved column to downloads table")
    # Migration: add max_queue_size and max_quota_bytes columns to users table
    try:
        c.execute("SELECT max_queue_size FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN max_queue_size INTEGER DEFAULT 5")
        log.info("Migration: added max_queue_size column to users table")
    try:
        c.execute("SELECT max_quota_bytes FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute(f"ALTER TABLE users ADD COLUMN max_quota_bytes INTEGER DEFAULT {DOWNLOAD_QUOTA_BYTES}")
        log.info("Migration: added max_quota_bytes column to users table")
    # Create default admin user if not exists
    c.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (id, username, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "admin", generate_password_hash("admin123"), 1)
        )
        log.info("Default admin user 'admin' created.")
    conn.commit()
    conn.close()

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- User Model ---
class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=False, created_at=None,
                 max_queue_size=5, max_quota_bytes=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = bool(is_admin)
        self.created_at = created_at
        self.max_queue_size = max_queue_size if max_queue_size is not None else 5
        self.max_quota_bytes = max_quota_bytes if max_quota_bytes is not None else DOWNLOAD_QUOTA_BYTES

    @staticmethod
    def _from_row(row):
        if not row:
            return None
        return User(
            row['id'], row['username'], row['password_hash'],
            row['is_admin'], row['created_at'],
            row['max_queue_size'] if 'max_queue_size' in row.keys() else 5,
            row['max_quota_bytes'] if 'max_quota_bytes' in row.keys() else DOWNLOAD_QUOTA_BYTES,
        )

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return User._from_row(user)

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return User._from_row(user)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# --- Active Downloads State (in-memory for live tracking) ---
active_downloads = {}  # {download_id: {"cancel_event": threading.Event, "user_id": str, ...}}
download_lock = threading.Lock()  # Protect active_downloads dict

# --- Download Queue (per-user, in-memory) ---
# {user_id: deque([queue_item_dict, ...])}
download_queues = {}
queue_lock = threading.Lock()

# --- Download Quota (based on active downloads in DB) ---
def get_user_quota(user_id):
    """Get current download usage from active (non-expired) downloads in DB."""
    now = time.time()
    try:
        conn = get_db()
        result = conn.execute(
            "SELECT COALESCE(SUM(file_size), 0) FROM downloads WHERE user_id = ? AND expires_at > ?",
            (user_id, now)
        ).fetchone()
        # Get user-specific quota
        user_row = conn.execute("SELECT max_quota_bytes FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        user_quota = (user_row['max_quota_bytes'] if user_row and user_row['max_quota_bytes'] else DOWNLOAD_QUOTA_BYTES)
        bytes_used = result[0] if result else 0
        bytes_remaining = max(0, user_quota - bytes_used)
        return bytes_used, bytes_remaining, user_quota
    except Exception as e:
        log.error(f"Error getting user quota: {e}")
        return 0, DOWNLOAD_QUOTA_BYTES, DOWNLOAD_QUOTA_BYTES

def check_quota_allowed(user_id, is_admin):
    """Check if user can download. Admin users have no limit."""
    if is_admin:
        return True, 0, DOWNLOAD_QUOTA_BYTES
    bytes_used, bytes_remaining, user_quota = get_user_quota(user_id)
    return bytes_remaining > 0, bytes_used, bytes_remaining

# --- Downloads Database Functions ---
def save_download_record(download_id, user_id, filename, filepath, file_size,
                         file_size_str, video_title, video_url, thumbnail, quality):
    """Save a completed download to the database for persistent history."""
    now = time.time()
    expires_at = now + DOWNLOAD_EXPIRY_SECONDS
    try:
        conn = get_db()
        conn.execute(
            """INSERT OR REPLACE INTO downloads
               (id, user_id, filename, filepath, file_size, file_size_str,
                video_title, video_url, thumbnail, quality, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (download_id, user_id, filename, filepath, file_size, file_size_str,
             video_title, video_url, thumbnail, quality, now, expires_at)
        )
        conn.commit()
        conn.close()
        log.info(f"[{download_id}] Download record saved. Expires at {datetime.fromtimestamp(expires_at).strftime('%H:%M:%S')}")
    except Exception as e:
        log.error(f"[{download_id}] Error saving download record: {e}")

def get_user_downloads(user_id):
    """Get non-expired, non-saved downloads for a user."""
    now = time.time()
    try:
        conn = get_db()
        downloads = conn.execute(
            """SELECT id, filename, file_size, file_size_str, video_title, video_url,
                      thumbnail, quality, created_at, expires_at
               FROM downloads
               WHERE user_id = ? AND expires_at > ? AND is_saved = 0
               ORDER BY created_at DESC""",
            (user_id, now)
        ).fetchall()
        conn.close()
        return [dict(d) for d in downloads]
    except Exception as e:
        log.error(f"Error getting user downloads: {e}")
        return []

def delete_download_record(download_id):
    """Delete a download record and its share tokens from the database."""
    try:
        conn = get_db()
        conn.execute("DELETE FROM collection_downloads WHERE download_id = ?", (download_id,))
        conn.execute("DELETE FROM share_tokens WHERE download_id = ?", (download_id,))
        conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"Error deleting download record {download_id}: {e}")

def cleanup_expired_downloads():
    """Clean up expired downloads from database and filesystem.
       This runs on startup and periodically."""
    now = time.time()
    cleaned = 0
    try:
        conn = get_db()
        expired = conn.execute(
            "SELECT id, filepath FROM downloads WHERE expires_at <= ?", (now,)
        ).fetchall()

        for record in expired:
            filepath = record['filepath']
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    log.info(f"[{record['id']}] Expired file removed: {filepath}")
                    cleaned += 1
                except OSError as e:
                    log.error(f"[{record['id']}] Error removing expired file: {e}")

            conn.execute("DELETE FROM share_tokens WHERE download_id = ?", (record['id'],))
            conn.execute("DELETE FROM downloads WHERE id = ?", (record['id'],))

        conn.commit()
        conn.close()

        if cleaned > 0:
            log.info(f"Cleaned up {cleaned} expired downloads")
    except Exception as e:
        log.error(f"Error during cleanup: {e}")

    # Also clean orphaned files in download dir (files without DB records)
    try:
        import unicodedata
        conn = get_db()
        db_filenames = set()
        all_records = conn.execute("SELECT filename FROM downloads").fetchall()
        for r in all_records:
            if r['filename']:
                norm_name = unicodedata.normalize('NFC', r['filename']).lower()
                db_filenames.add(norm_name)
        conn.close()

        for f in os.listdir(DOWNLOAD_DIR):
            if f in ('users.db', 'downloads.db'):
                continue
                
            fpath = os.path.join(DOWNLOAD_DIR, f)
            norm_f = unicodedata.normalize('NFC', f).lower()
            
            if os.path.isfile(fpath) and norm_f not in db_filenames:
                # Check if file is older than 1 hour (as requested by user)
                # Safety: ignore files modified in the last 10 minutes to avoid killing very slow downloads
                file_age = now - os.path.getmtime(fpath)
                if file_age > 3600:
                    try:
                        os.remove(fpath)
                        log.info(f"Orphaned file removed: {f}")
                    except OSError as e:
                        log.error(f"Failed to remove orphaned file {f}: {e}")
    except Exception as e:
        log.error(f"Error cleaning orphaned files: {e}")

def periodic_cleanup():
    """Background task that runs every 60 seconds to clean expired downloads."""
    while True:
        socketio.sleep(60)
        cleanup_expired_downloads()

def periodic_ytdlp_update():
    """Background task that runs every 12 hours (43200s) to update yt-dlp."""
    while True:
        try:
            log.info("Checking for yt-dlp updates...")
            # Use sys.executable to ensure we use the same Python environment
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                if "Requirement already satisfied" in result.stdout and "Successfully installed" not in result.stdout:
                    log.info("yt-dlp is already up to date.")
                else:
                    log.info(f"yt-dlp updated successfully:\n{result.stdout.strip()}")
            else:
                log.error(f"Failed to update yt-dlp:\n{result.stderr.strip()}")
        except Exception as e:
            log.error(f"Error during yt-dlp update: {e}")
            
        socketio.sleep(43200)

# --- Helper Functions ---
def format_duration(seconds):
    """Format seconds to HH:MM:SS or MM:SS."""
    if seconds is None or not isinstance(seconds, (int, float)) or seconds <= 0:
        return ""
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
    except Exception:
        return ""

def format_size(bytes_val):
    """Format bytes to human readable size."""
    if bytes_val is None or bytes_val <= 0:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"

def sanitize_filename(name):
    """Sanitize a string to be used as a filename."""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single
    name = re.sub(r'\s+', ' ', name).strip()
    # Limit length
    return name[:200] if name else "video"

# --- Routes ---
@app.route('/sw.js')
def sw():
    response = app.send_static_file('sw.js')
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.get_by_username(username)
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            log.info(f"User '{username}' logged in successfully.")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            log.warning(f"Failed login attempt for user '{username}'.")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log.info(f"User '{current_user.username}' logged out.")
    logout_user()
    return redirect(url_for('login'))

@app.route('/share')
@login_required
def share_target():
    """Handle Web Share Target API - redirect to index with shared URL."""
    shared_url = request.args.get('url') or request.args.get('text') or ''
    # Extract URL from text if it contains more than just a URL
    if shared_url and not shared_url.startswith('http'):
        url_match = re.search(r'https?://\S+', shared_url)
        if url_match:
            shared_url = url_match.group(0)
    if shared_url:
        from urllib.parse import quote
        return redirect(f'/?shared_url={quote(shared_url, safe="")}')
    return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    response = make_response(render_template('index.html', username=current_user.username, is_admin=current_user.is_admin))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# --- API Routes ---
@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if not current_user.is_admin:
        return jsonify({"error": "Solo administradores pueden gestionar usuarios"}), 403
    conn = get_db()
    users = conn.execute("SELECT id, username, is_admin, created_at, max_queue_size, max_quota_bytes FROM users").fetchall()
    conn.close()
    result = []
    for u in users:
        d = dict(u)
        d['max_queue_size'] = d.get('max_queue_size') or 5
        d['max_quota_bytes'] = d.get('max_quota_bytes') or DOWNLOAD_QUOTA_BYTES
        d['max_quota_gb'] = round(d['max_quota_bytes'] / (1024**3), 1)
        result.append(d)
    return jsonify(result)

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        return jsonify({"error": "Solo administradores pueden crear usuarios"}), 403
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        return jsonify({"error": "Username y password son obligatorios"}), 400
    if len(username) < 3:
        return jsonify({"error": "El username debe tener al menos 3 caracteres"}), 400
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400

    existing = User.get_by_username(username)
    if existing:
        return jsonify({"error": "El usuario ya existe"}), 409

    try:
        conn = get_db()
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, username, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (user_id, username, generate_password_hash(password), 1 if is_admin else 0)
        )
        conn.commit()
        conn.close()
        log.info(f"User '{username}' created by '{current_user.username}'.")
        return jsonify({"message": f"Usuario '{username}' creado correctamente", "id": user_id}), 201
    except Exception as e:
        log.error(f"Error creating user: {e}")
        return jsonify({"error": "Error al crear el usuario"}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Solo administradores pueden eliminar usuarios"}), 403
    if user_id == current_user.id:
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
    try:
        conn = get_db()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        log.info(f"User '{user_id}' deleted by '{current_user.username}'.")
        return jsonify({"message": "Usuario eliminado"}), 200
    except Exception as e:
        log.error(f"Error deleting user: {e}")
        return jsonify({"error": "Error al eliminar el usuario"}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Admin endpoint to update user settings (queue size, quota)."""
    if not current_user.is_admin:
        return jsonify({"error": "Solo administradores pueden modificar usuarios"}), 403
    data = request.get_json()
    max_queue_size = data.get('max_queue_size')
    max_quota_gb = data.get('max_quota_gb')

    updates = []
    params = []
    if max_queue_size is not None:
        max_queue_size = max(1, min(100, int(max_queue_size)))
        updates.append("max_queue_size = ?")
        params.append(max_queue_size)
    if max_quota_gb is not None:
        max_quota_bytes = max(1, int(float(max_quota_gb) * 1024**3))
        updates.append("max_quota_bytes = ?")
        params.append(max_quota_bytes)

    if not updates:
        return jsonify({"error": "No hay cambios que aplicar"}), 400

    try:
        params.append(user_id)
        conn = get_db()
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()
        log.info(f"User '{user_id}' settings updated by '{current_user.username}'.")
        return jsonify({"message": "Configuración actualizada"}), 200
    except Exception as e:
        log.error(f"Error updating user: {e}")
        return jsonify({"error": "Error al actualizar el usuario"}), 500

@app.route('/api/quota')
@login_required
def get_quota():
    """Get current user's download quota status."""
    if current_user.is_admin:
        return jsonify({
            "unlimited": True,
            "remaining_str": "Ilimitado",
            "total_str": format_size(DOWNLOAD_QUOTA_BYTES),
        })
    bytes_used, bytes_remaining, user_quota = get_user_quota(current_user.id)
    return jsonify({
        "unlimited": False,
        "bytes_used": bytes_used,
        "bytes_remaining": bytes_remaining,
        "quota_total": user_quota,
        "used_str": format_size(bytes_used),
        "remaining_str": format_size(bytes_remaining),
        "total_str": format_size(user_quota),
    })

# --- Download File & Recent Downloads API ---
@app.route('/api/download-file/<download_id>')
@login_required
def download_file(download_id):
    """Serve the downloaded file to the browser."""
    # First check in-memory active downloads
    task = active_downloads.get(download_id)
    if task:
        filepath = task.get("final_filepath")
        filename = task.get("filename", "download")
    else:
        # Check in database for recent downloads
        conn = get_db()
        record = conn.execute(
            "SELECT filepath, filename FROM downloads WHERE id = ? AND user_id = ? AND expires_at > ?",
            (download_id, current_user.id, time.time())
        ).fetchone()
        conn.close()
        if record:
            filepath = record['filepath']
            filename = record['filename']
        else:
            return jsonify({"error": "Descarga no encontrada o expirada"}), 404

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no disponible"}), 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/stream/<download_id>')
@login_required
def stream_file(download_id):
    """Serve file inline for browser playback (video/audio)."""
    task = active_downloads.get(download_id)
    if task:
        filepath = task.get("final_filepath")
    else:
        conn = get_db()
        record = conn.execute(
            "SELECT filepath FROM downloads WHERE id = ? AND user_id = ? AND expires_at > ?",
            (download_id, current_user.id, time.time())
        ).fetchone()
        conn.close()
        if record:
            filepath = record['filepath']
        else:
            return jsonify({"error": "Descarga no encontrada o expirada"}), 404

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no disponible"}), 404

    ext = os.path.splitext(filepath)[1].lower()
    mime = MIME_TYPES.get(ext)
    return send_file(filepath, mimetype=mime) if mime else send_file(filepath)

@app.route('/api/media-info/<download_id>')
@login_required
def media_info_endpoint(download_id):
    """Return technical media info for a downloaded file."""
    task = active_downloads.get(download_id)
    if task:
        filepath = task.get("final_filepath")
        record = None
    else:
        conn = get_db()
        record = conn.execute(
            "SELECT * FROM downloads WHERE id = ? AND user_id = ? AND expires_at > ?",
            (download_id, current_user.id, time.time())
        ).fetchone()
        conn.close()
        if record:
            filepath = record['filepath']
        else:
            return jsonify({"error": "No encontrado"}), 404

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no disponible"}), 404

    info = get_media_info(filepath)
    file_size_bytes = os.path.getsize(filepath)

    result = {
        'media_info': info,
        'filename': os.path.basename(filepath),
        'file_size_bytes': file_size_bytes,
        'file_size': format_size(file_size_bytes),
    }
    if record:
        result['video_title'] = record['video_title'] if record['video_title'] else ''
        result['thumbnail'] = record['thumbnail'] if record['thumbnail'] else ''
        result['quality'] = record['quality'] if record['quality'] else ''
        result['video_url'] = record['video_url'] if record['video_url'] else ''
    elif task:
        result['video_title'] = task.get('video_title', '')
        result['thumbnail'] = task.get('thumbnail', '')
        result['quality'] = task.get('quality', '')
        result['video_url'] = task.get('url', '')

    return jsonify(result)

@app.route('/api/playback-position/<download_id>', methods=['GET'])
@login_required
def get_playback_position(download_id):
    conn = get_db()
    row = conn.execute(
        "SELECT position FROM playback_positions WHERE user_id = ? AND download_id = ?",
        (current_user.id, download_id)
    ).fetchone()
    conn.close()
    return jsonify({"position": row['position'] if row else 0})

@app.route('/api/playback-position/<download_id>', methods=['POST'])
@login_required
def save_playback_position(download_id):
    data = request.get_json()
    position = data.get('position', 0)
    conn = get_db()
    conn.execute(
        """INSERT INTO playback_positions (user_id, download_id, position, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, download_id) DO UPDATE SET position = ?, updated_at = ?""",
        (current_user.id, download_id, position, time.time(), position, time.time())
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route('/api/playback-position/<download_id>', methods=['DELETE'])
@login_required
def delete_playback_position(download_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM playback_positions WHERE user_id = ? AND download_id = ?",
        (current_user.id, download_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route('/api/recent-downloads')
@login_required
def recent_downloads():
    """Get list of recent downloads for the current user."""
    downloads = get_user_downloads(current_user.id)
    now = time.time()
    result = []
    for d in downloads:
        remaining = max(0, d['expires_at'] - now)
        result.append({
            'id': d['id'],
            'filename': d['filename'],
            'file_size': d['file_size'],  # Added raw bytes
            'file_size_str': d['file_size_str'],
            'video_title': d['video_title'],
            'thumbnail': d['thumbnail'],
            'quality': d['quality'],
            'created_at': d['created_at'],
            'expires_at': d['expires_at'],
            'remaining_seconds': int(remaining),
            'remaining_text': format_remaining_time(remaining),
        })
    return jsonify(result)

@app.route('/api/delete-download/<download_id>', methods=['POST'])
@login_required
def delete_download_api(download_id):
    """Manually delete a download."""
    conn = get_db()
    record = conn.execute(
        "SELECT filepath FROM downloads WHERE id = ? AND user_id = ?",
        (download_id, current_user.id)
    ).fetchone()
    conn.close()

    if not record:
        return jsonify({"error": "Descarga no encontrada"}), 404

    filepath = record['filepath']
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except OSError as e:
            log.error(f"Error removing file: {e}")

    delete_download_record(download_id)
    # Also remove from active_downloads if present
    active_downloads.pop(download_id, None)
    socketio.emit('saved_downloads_update', {}, room=current_user.id)
    return jsonify({"message": "Descarga eliminada"}), 200

@app.route('/api/save-download/<download_id>', methods=['POST'])
@login_required
def save_download_api(download_id):
    """Toggle saved status of a download."""
    conn = get_db()
    record = conn.execute(
        "SELECT is_saved, file_size FROM downloads WHERE id = ? AND user_id = ?",
        (download_id, current_user.id)
    ).fetchone()

    if not record:
        conn.close()
        return jsonify({"error": "Descarga no encontrada"}), 404

    new_saved = 0 if record['is_saved'] else 1

    if new_saved == 1:
        # Saving: set expires_at to far future (year 9999)
        conn.execute(
            "UPDATE downloads SET is_saved = 1, expires_at = ? WHERE id = ?",
            (253402300800.0, download_id)
        )
    else:
        # Unsaving: restore normal expiry (1 hour from now)
        new_expires = time.time() + DOWNLOAD_EXPIRY_SECONDS
        conn.execute(
            "UPDATE downloads SET is_saved = 0, expires_at = ? WHERE id = ?",
            (new_expires, download_id)
        )

    conn.commit()
    conn.close()

    # Notify frontend via WebSocket
    socketio.emit('saved_downloads_update', {}, room=current_user.id)
    socketio.emit('recent_downloads_update', {}, room=current_user.id)

    return jsonify({
        "message": "Video guardado" if new_saved else "Video removido de guardados",
        "is_saved": new_saved
    }), 200

@app.route('/api/saved-downloads')
@login_required
def saved_downloads():
    """Get list of saved downloads for the current user, optionally filtered by collection."""
    try:
        conn = get_db()
        collection_id = request.args.get('collection')
        if collection_id:
            downloads = conn.execute(
                """SELECT d.id, d.filename, d.file_size, d.file_size_str, d.video_title,
                          d.video_url, d.thumbnail, d.quality, d.created_at
                   FROM downloads d
                   JOIN collection_downloads cd ON d.id = cd.download_id
                   WHERE d.user_id = ? AND d.is_saved = 1 AND cd.collection_id = ?
                   ORDER BY cd.added_at DESC""",
                (current_user.id, collection_id)
            ).fetchall()
        else:
            downloads = conn.execute(
                """SELECT id, filename, file_size, file_size_str, video_title, video_url,
                          thumbnail, quality, created_at
                   FROM downloads
                   WHERE user_id = ? AND is_saved = 1
                   ORDER BY created_at DESC""",
                (current_user.id,)
            ).fetchall()
        # Attach collection info to each download
        result = []
        for d in downloads:
            item = dict(d)
            cols = conn.execute(
                """SELECT c.id, c.name, c.color FROM collections c
                   JOIN collection_downloads cd ON c.id = cd.collection_id
                   WHERE cd.download_id = ?""",
                (item['id'],)
            ).fetchall()
            item['collections'] = [dict(c) for c in cols]
            result.append(item)
        conn.close()
        return jsonify(result)
    except Exception as e:
        log.error(f"Error getting saved downloads: {e}")
        return jsonify([])

# --- Collections API ---
@app.route('/api/collections')
@login_required
def list_collections():
    """Get all collections for the current user with video count."""
    conn = get_db()
    collections = conn.execute(
        """SELECT c.id, c.name, c.color, c.created_at,
                  COUNT(cd.download_id) as video_count
           FROM collections c
           LEFT JOIN collection_downloads cd ON c.id = cd.collection_id
           WHERE c.user_id = ?
           GROUP BY c.id
           ORDER BY c.created_at ASC""",
        (current_user.id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(c) for c in collections])

@app.route('/api/collections', methods=['POST'])
@login_required
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#8b5cf6')
    if not name:
        return jsonify({"error": "El nombre es obligatorio"}), 400
    if len(name) > 50:
        return jsonify({"error": "Nombre demasiado largo (máx 50 caracteres)"}), 400

    collection_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute(
        "INSERT INTO collections (id, user_id, name, color, created_at) VALUES (?, ?, ?, ?, ?)",
        (collection_id, current_user.id, name, color, time.time())
    )
    conn.commit()
    conn.close()
    return jsonify({"id": collection_id, "name": name, "color": color, "video_count": 0}), 201

@app.route('/api/collections/<collection_id>', methods=['PUT'])
@login_required
def update_collection(collection_id):
    """Update a collection's name or color."""
    data = request.get_json()
    conn = get_db()
    record = conn.execute(
        "SELECT id FROM collections WHERE id = ? AND user_id = ?",
        (collection_id, current_user.id)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify({"error": "Colección no encontrada"}), 404

    name = data.get('name', '').strip()
    color = data.get('color', '#8b5cf6')
    if not name:
        conn.close()
        return jsonify({"error": "El nombre es obligatorio"}), 400

    conn.execute(
        "UPDATE collections SET name = ?, color = ? WHERE id = ?",
        (name, color, collection_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Colección actualizada"}), 200

@app.route('/api/collections/<collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    """Delete a collection (does not delete videos)."""
    conn = get_db()
    record = conn.execute(
        "SELECT id FROM collections WHERE id = ? AND user_id = ?",
        (collection_id, current_user.id)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify({"error": "Colección no encontrada"}), 404

    conn.execute("DELETE FROM collection_downloads WHERE collection_id = ?", (collection_id,))
    conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Colección eliminada"}), 200

@app.route('/api/collections/<collection_id>/add/<download_id>', methods=['POST'])
@login_required
def add_to_collection(collection_id, download_id):
    """Add a saved download to a collection."""
    conn = get_db()
    # Verify ownership
    col = conn.execute("SELECT id FROM collections WHERE id = ? AND user_id = ?",
                       (collection_id, current_user.id)).fetchone()
    dl = conn.execute("SELECT id FROM downloads WHERE id = ? AND user_id = ? AND is_saved = 1",
                      (download_id, current_user.id)).fetchone()
    if not col or not dl:
        conn.close()
        return jsonify({"error": "No encontrado"}), 404

    # Check if already in collection
    existing = conn.execute(
        "SELECT 1 FROM collection_downloads WHERE collection_id = ? AND download_id = ?",
        (collection_id, download_id)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO collection_downloads (collection_id, download_id, added_at) VALUES (?, ?, ?)",
            (collection_id, download_id, time.time())
        )
        conn.commit()
    conn.close()
    socketio.emit('saved_downloads_update', {}, room=current_user.id)
    return jsonify({"message": "Añadido a la colección"}), 200

@app.route('/api/collections/<collection_id>/remove/<download_id>', methods=['DELETE'])
@login_required
def remove_from_collection(collection_id, download_id):
    """Remove a download from a collection."""
    conn = get_db()
    col = conn.execute("SELECT id FROM collections WHERE id = ? AND user_id = ?",
                       (collection_id, current_user.id)).fetchone()
    if not col:
        conn.close()
        return jsonify({"error": "Colección no encontrada"}), 404

    conn.execute(
        "DELETE FROM collection_downloads WHERE collection_id = ? AND download_id = ?",
        (collection_id, download_id)
    )
    conn.commit()
    conn.close()
    socketio.emit('saved_downloads_update', {}, room=current_user.id)
    return jsonify({"message": "Eliminado de la colección"}), 200

@app.route('/api/share-link/<download_id>', methods=['POST'])
@login_required
def create_share_link(download_id):
    """Create a public share link for a download."""
    conn = get_db()
    record = conn.execute(
        "SELECT id FROM downloads WHERE id = ? AND user_id = ?",
        (download_id, current_user.id)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify({"error": "Descarga no encontrada"}), 404

    # Check if token already exists
    existing = conn.execute(
        "SELECT token FROM share_tokens WHERE download_id = ?", (download_id,)
    ).fetchone()
    if existing:
        conn.close()
        token = existing['token']
        share_url = f"{request.host_url}s/{token}"
        return jsonify({"token": token, "url": share_url}), 200

    token = secrets.token_urlsafe(16)
    conn.execute(
        "INSERT INTO share_tokens (token, download_id, user_id, created_at) VALUES (?, ?, ?, ?)",
        (token, download_id, current_user.id, time.time())
    )
    conn.commit()
    conn.close()

    share_url = f"{request.host_url}s/{token}"
    log.info(f"[{download_id}] Share link created: {share_url}")
    return jsonify({"token": token, "url": share_url}), 201


@app.route('/api/share-link/<download_id>', methods=['DELETE'])
@login_required
def delete_share_link(download_id):
    """Remove a public share link."""
    conn = get_db()
    conn.execute(
        "DELETE FROM share_tokens WHERE download_id = ? AND user_id = ?",
        (download_id, current_user.id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Enlace público eliminado"}), 200


@app.route('/api/share-link/<download_id>', methods=['GET'])
@login_required
def get_share_link(download_id):
    """Check if a share link exists for this download."""
    conn = get_db()
    record = conn.execute(
        "SELECT token FROM share_tokens WHERE download_id = ? AND user_id = ?",
        (download_id, current_user.id)
    ).fetchone()
    conn.close()
    if record:
        share_url = f"{request.host_url}s/{record['token']}"
        return jsonify({"token": record['token'], "url": share_url}), 200
    return jsonify({"token": None}), 200


def get_media_info(filepath):
    """Extract technical media info using ffprobe."""
    info = {}
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', '-show_streams', filepath],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            fmt = data.get('format', {})
            info['duration'] = float(fmt.get('duration', 0))
            info['bitrate'] = int(fmt.get('bit_rate', 0))
            info['format_name'] = fmt.get('format_long_name', '')
            info['container'] = fmt.get('format_name', '')

            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and 'video_codec' not in info:
                    info['video_codec'] = stream.get('codec_name', '').upper()
                    info['video_codec_long'] = stream.get('codec_long_name', '')
                    info['width'] = stream.get('width', 0)
                    info['height'] = stream.get('height', 0)
                    info['video_bitrate'] = int(stream.get('bit_rate', 0))
                    # FPS
                    r_fps = stream.get('r_frame_rate', '0/1')
                    try:
                        num, den = r_fps.split('/')
                        info['fps'] = round(int(num) / int(den), 2) if int(den) else 0
                    except:
                        info['fps'] = 0
                    info['pix_fmt'] = stream.get('pix_fmt', '')
                    info['color_space'] = stream.get('color_space', '')
                    info['video_profile'] = stream.get('profile', '')
                elif stream.get('codec_type') == 'audio' and 'audio_codec' not in info:
                    info['audio_codec'] = stream.get('codec_name', '').upper()
                    info['audio_codec_long'] = stream.get('codec_long_name', '')
                    info['sample_rate'] = int(stream.get('sample_rate', 0))
                    info['channels'] = stream.get('channels', 0)
                    info['audio_bitrate'] = int(stream.get('bit_rate', 0))
                    info['audio_profile'] = stream.get('profile', '')
    except Exception as e:
        log.warning(f"ffprobe failed for {filepath}: {e}")
    return info


@app.route('/s/<token>')
def public_player(token):
    """Public video player page - no login required."""
    conn = get_db()
    record = conn.execute(
        """SELECT d.id, d.filename, d.filepath, d.video_title, d.thumbnail,
                  d.quality, d.file_size_str, d.file_size, d.expires_at,
                  d.is_saved, d.created_at, d.video_url
           FROM share_tokens s
           JOIN downloads d ON s.download_id = d.id
           WHERE s.token = ?""",
        (token,)
    ).fetchone()
    conn.close()

    if not record:
        return render_template('public_player.html', error="Enlace no válido o el video ha sido eliminado"), 404

    # Check if expired (non-saved videos)
    if not record['is_saved'] and record['expires_at'] <= time.time():
        return render_template('public_player.html', error="Este video ha expirado"), 410

    # Check file exists
    if not record['filepath'] or not os.path.exists(record['filepath']):
        return render_template('public_player.html', error="El archivo ya no está disponible"), 404

    ext = os.path.splitext(record['filename'])[1].lower()
    is_video = ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.ts']
    is_audio = ext in ['.mp3', '.m4a', '.ogg', '.wav', '.flac', '.opus', '.aac']

    # Get technical media info via ffprobe
    media_info = get_media_info(record['filepath'])

    # Calculate time remaining for non-saved videos
    time_remaining = None
    if not record['is_saved']:
        remaining_secs = max(0, record['expires_at'] - time.time())
        if remaining_secs > 0:
            mins = int(remaining_secs // 60)
            secs = int(remaining_secs % 60)
            time_remaining = f"{mins}m {secs}s"

    # Feature 6: Start time from query param
    start_time = request.args.get('t', 0, type=int)

    return render_template('public_player.html',
                           error=None,
                           token=token,
                           title=record['video_title'] or record['filename'],
                           thumbnail=record['thumbnail'],
                           quality=record['quality'],
                           file_size=record['file_size_str'],
                           file_size_bytes=record['file_size'],
                           filename=record['filename'],
                           is_video=is_video,
                           is_audio=is_audio,
                           is_saved=record['is_saved'],
                           time_remaining=time_remaining,
                           expires_at=record['expires_at'] if not record['is_saved'] else None,
                           created_at=record['created_at'],
                           video_url=record['video_url'],
                           media_info=media_info,
                           start_time=start_time)


@app.route('/api/public-stream/<token>')
def public_stream(token):
    """Serve video/audio file for public playback - no login required."""
    conn = get_db()
    record = conn.execute(
        """SELECT d.filepath, d.expires_at, d.is_saved
           FROM share_tokens s
           JOIN downloads d ON s.download_id = d.id
           WHERE s.token = ?""",
        (token,)
    ).fetchone()
    conn.close()

    if not record:
        return jsonify({"error": "Enlace no válido"}), 404

    if not record['is_saved'] and record['expires_at'] <= time.time():
        return jsonify({"error": "Video expirado"}), 410

    filepath = record['filepath']
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no disponible"}), 404

    ext = os.path.splitext(filepath)[1].lower()
    mime = MIME_TYPES.get(ext)
    return send_file(filepath, mimetype=mime) if mime else send_file(filepath)


@app.route('/api/public-download/<token>')
def public_download(token):
    """Serve video/audio file as download for public links - no login required."""
    conn = get_db()
    record = conn.execute(
        """SELECT d.filepath, d.filename, d.expires_at, d.is_saved
           FROM share_tokens s
           JOIN downloads d ON s.download_id = d.id
           WHERE s.token = ?""",
        (token,)
    ).fetchone()
    conn.close()

    if not record:
        return jsonify({"error": "Enlace no válido"}), 404

    if not record['is_saved'] and record['expires_at'] <= time.time():
        return jsonify({"error": "Video expirado"}), 410

    filepath = record['filepath']
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no disponible"}), 404

    return send_file(filepath, as_attachment=True, download_name=record['filename'])


def format_remaining_time(seconds):
    """Format remaining seconds to human readable text."""
    if seconds <= 0:
        return "Expirado"
    seconds = int(seconds)
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"
    elif seconds >= 60:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s:02d}s"
    else:
        return f"{seconds}s"

# --- SocketIO Events ---
@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False
    join_room(current_user.id)
    log.info(f"WebSocket connected: user={current_user.username}")
    
    # Send active downloads status to user on reconnect
    user_active = []
    with download_lock:
        for dl_id, task in active_downloads.items():
            if task.get('user_id') == current_user.id and task.get('downloading'):
                if 'last_progress' in task:
                    user_active.append(task['last_progress'])

    if user_active:
        socketio.emit('active_downloads_status', {'downloads': user_active}, room=current_user.id)

    # Send queue state on reconnect
    _emit_queue_update(current_user.id)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(current_user.id)
    log.info(f"WebSocket disconnected")

@socketio.on('analyze_url')
def handle_analyze_url(data):
    """Analyze a URL and return video information."""
    if not current_user.is_authenticated:
        emit('error', {'message': 'No autenticado'})
        return

    url = data.get('url', '').strip()
    if not url:
        emit('error', {'message': 'URL vacía'})
        return

    # Basic URL validation
    if not re.match(r'https?://', url, re.IGNORECASE):
        # Try adding https://
        if '.' in url and len(url) > 3:
            url = 'https://' + url
        else:
            emit('error', {'message': 'URL no válida'})
            return

    emit('status', {'message': '🔍 Analizando enlace...', 'phase': 'analyzing'})

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'forcejson': True,
        'extract_flat': 'in_playlist',
        'ignoreerrors': True,
        'source_address': '0.0.0.0',  # Force IPv4
        'proxy': 'socks5://jackett2025:aR7f5vK3rT9@217.154.113.243:1080',
        'remote_components': ['ejs:github'],
    }

    if os.path.exists(COOKIE_FILE_PATH):
        ydl_opts['cookiefile'] = COOKIE_FILE_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            emit('error', {'message': 'No se pudo obtener información del video'})
            return

        # Check if it's a live stream
        if info.get('is_live'):
            emit('error', {'message': '🚫 No se pueden descargar transmisiones en vivo'})
            return

        # Process formats
        resolutions = set()
        has_audio = False
        max_audio_bitrate = 0
        total_size_estimate = {}

        entries = info.get('entries', [])
        if not entries and isinstance(info.get('formats'), list):
            entries = [info]

        is_playlist = info.get('_type') == 'playlist' or (
            'entries' in info and isinstance(info.get('entries'), list) and len(info['entries']) > 1
        )

        if is_playlist:
            has_audio = True

        for entry in entries:
            entry_formats = entry.get('formats', [])
            for f in entry_formats:
                if f.get('vcodec') != 'none' and f.get('height'):
                    h = f['height']
                    if h and h > 0:
                        resolutions.add(h)
                        # Try to get size estimate for each resolution
                        size = f.get('filesize') or f.get('filesize_approx')
                        if size and (h not in total_size_estimate or size > total_size_estimate[h]):
                            total_size_estimate[h] = size
                if f.get('acodec') != 'none':
                    if f.get('vcodec') == 'none':
                        has_audio = True
                    abr = f.get('abr') or 0
                    if abr > max_audio_bitrate:
                        max_audio_bitrate = abr

        sorted_resolutions = sorted(resolutions, reverse=True)
        resolution_list = []
        for h in sorted_resolutions:
            size_str = format_size(total_size_estimate.get(h)) if h in total_size_estimate else ""
            resolution_list.append({
                'height': h,
                'label': f"{h}p",
                'size': size_str
            })

        # Get thumbnail
        thumbnail = info.get('thumbnail') or info.get('thumbnails', [{}])[-1].get('url', '') if info.get('thumbnails') else ''
        has_thumbnail = bool(thumbnail)

        # Check for available subtitles
        has_subtitles = bool(info.get('subtitles')) or bool(info.get('automatic_captions'))

        playlist_videos = []
        if is_playlist:
            for idx, entry in enumerate(entries):
                if not entry: continue
                playlist_videos.append({
                    'index': entry.get('playlist_index', idx + 1),
                    'title': entry.get('title', 'Video desconocido'),
                    'duration': format_duration(entry.get('duration')) if entry.get('duration') else '',
                    'thumbnail': entry.get('thumbnail') or ''
                })

        video_info = {
            'title': info.get('title', 'Video desconocido'),
            'uploader': info.get('uploader', ''),
            'duration': format_duration(info.get('duration')),
            'duration_sec': info.get('duration'),
            'thumbnail': thumbnail,
            'url': url,
            'resolutions': resolution_list,
            'has_audio': has_audio,
            'max_audio_bitrate': int(max_audio_bitrate),
            'has_thumbnail': has_thumbnail,
            'has_subtitles': has_subtitles,
            'is_playlist': is_playlist,
            'playlist_count': info.get('playlist_count') or len(info.get('entries', [])) if is_playlist else 0,
            'playlist_videos': playlist_videos,
            'webpage_url': info.get('webpage_url', url),
            'extractor': info.get('extractor', ''),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'description': (info.get('description', '') or '')[:500],
        }

        # Store info for later use
        download_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]
        active_downloads[download_id] = {
            'info': info,
            'is_playlist': is_playlist,
            'playlist_videos': playlist_videos,
            'url': url,
            'user_id': current_user.id,
            'cancel_event': threading.Event()
        }

        video_info['download_id'] = download_id
        emit('video_info', video_info)
        log.info(f"[{download_id}] Video info extracted: {info.get('title', 'unknown')}")

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Unsupported URL" in error_msg:
            emit('error', {'message': '❌ Esta URL no es compatible'})
        elif "Video unavailable" in error_msg:
            emit('error', {'message': '❌ Este video no está disponible'})
        elif "Private video" in error_msg:
            emit('error', {'message': '❌ Este es un video privado'})
        elif "Sign in" in error_msg:
            emit('error', {'message': '❌ Este video requiere inicio de sesión'})
        else:
            emit('error', {'message': f'❌ Error al analizar: {error_msg[:200]}'})
        log.error(f"yt-dlp error: {e}")
    except Exception as e:
        emit('error', {'message': f'❌ Error inesperado: {str(e)[:200]}'})
        log.exception(f"Unexpected error analyzing URL: {e}")


def _get_queue_state(user_id):
    """Build queue state payload for a user."""
    with queue_lock:
        user_queue = download_queues.get(user_id, deque())
        items = []
        for i, item in enumerate(user_queue):
            items.append({
                'queue_id': item['queue_id'],
                'download_id': item['download_id'],
                'title': item['title'],
                'thumbnail': item['thumbnail'],
                'quality': item['quality'],
                'status': item['status'],
                'position': i + 1,
                'queued_at': item['queued_at'],
            })
    # Get user's max queue size
    user = User.get_by_id(user_id)
    is_admin = user.is_admin if user else False
    max_qs = None if is_admin else (user.max_queue_size if user else 5)
    return {
        'queue': items,
        'queue_size': len(items),
        'max_queue_size': max_qs,  # None = unlimited (admin)
    }

def _emit_queue_update(user_id):
    """Send current queue state to a user."""
    state = _get_queue_state(user_id)
    try:
        socketio.emit('queue_updated', state, room=user_id)
        socketio.sleep(0)
    except Exception as e:
        log.error(f"Error emitting queue update: {e}")

def _user_has_active_download(user_id):
    """Check if user has a currently downloading task."""
    with download_lock:
        for task in active_downloads.values():
            if task.get('user_id') == user_id and task.get('downloading'):
                return True
    return False

def _process_next_in_queue(user_id):
    """Start the next queued download for a user if none is active."""
    if _user_has_active_download(user_id):
        return

    next_item = None
    with queue_lock:
        user_queue = download_queues.get(user_id, deque())
        for item in user_queue:
            if item['status'] == 'queued':
                item['status'] = 'downloading'
                next_item = item
                break

    if not next_item:
        return

    _emit_queue_update(user_id)
    _execute_download(next_item, user_id)

def _execute_download(queue_item, user_id):
    """Execute a download from a queue item."""
    download_id = queue_item['download_id']
    quality = queue_item['quality']
    format_pref = queue_item['format']
    audio_quality = queue_item['audio_quality']
    embed_thumbnail = queue_item['embed_thumbnail']
    embed_subtitles = queue_item['embed_subtitles']
    subtitle_lang = queue_item['subtitle_lang']
    playlist_items = queue_item['playlist_items']

    if download_id not in active_downloads:
        log.error(f"[{download_id}] Active download entry not found for queued item")
        queue_item['status'] = 'error'
        _emit_queue_update(user_id)
        _process_next_in_queue(user_id)
        return

    task = active_downloads[download_id]
    task['downloading'] = True
    cancel_event = task['cancel_event']
    info = task['info']
    url = task['url']
    title = info.get('title', 'video')
    thumbnail = info.get('thumbnail', '')

    def do_download():
        try:
            safe_title = sanitize_filename(title)
            base_filename = download_id

            is_playlist = task.get('is_playlist', False)
            if is_playlist and playlist_items:
                temp_filepath_pattern = os.path.join(DOWNLOAD_DIR, f"{base_filename}_%(playlist_index)s.%(ext)s")
            else:
                temp_filepath_pattern = os.path.join(DOWNLOAD_DIR, f"{base_filename}.%(ext)s")

            ydl_opts = {
                'outtmpl': temp_filepath_pattern,
                'retries': 5,
                'fragment_retries': 10,
                'skip_unavailable_fragments': True,
                'quiet': True,
                'no_warnings': True,
                'noprogress': True,
                'source_address': '0.0.0.0',  # Force IPv4
                'proxy': 'socks5://jackett2025:aR7f5vK3rT9@217.154.113.243:1080',
                'remote_components': ['ejs:github'],
                'postprocessors': [],
                'progress_hooks': [create_progress_hook(download_id, cancel_event, user_id)],
                'post_hooks': [create_post_hook(download_id, user_id, quality, title, url, thumbnail, task)],
            }

            if is_playlist:
                ydl_opts['noplaylist'] = False
                if playlist_items:
                    ydl_opts['playlist_items'] = str(playlist_items)
            else:
                ydl_opts['noplaylist'] = True

            if os.path.exists(COOKIE_FILE_PATH):
                ydl_opts['cookiefile'] = COOKIE_FILE_PATH

            if quality == 'audio_mp3':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': audio_quality,
                })
            elif quality == 'audio_original':
                ydl_opts['format'] = 'bestaudio/best'
            else:
                height = quality.rstrip('p') if quality else 'best'
                if height != 'best':
                    ydl_opts['format'] = (
                        f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/"
                        f"bestvideo+bestaudio/best"
                    )
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                ydl_opts['merge_output_format'] = format_pref

            if embed_thumbnail:
                ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
                ydl_opts['writethumbnail'] = True

            if embed_subtitles:
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitleslangs'] = subtitle_lang.split(',')
                ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle'})

            emit_progress(user_id, download_id, 'starting', '⏳ Iniciando descarga...', 0)
            log.info(f"[{download_id}] Starting yt-dlp download: format={ydl_opts.get('format')}, url={url[:80]}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            log.info(f"[{download_id}] yt-dlp download() returned")

            if cancel_event.is_set():
                emit_progress(user_id, download_id, 'cancelled', '❌ Descarga cancelada', 0)
                cleanup_temp_files(base_filename)
                queue_item['status'] = 'cancelled'
                return

            completed = task.get('completed_files', [])
            if not completed:
                emit_progress(user_id, download_id, 'error', '❌ No se pudo completar ninguna descarga', 0)
                queue_item['status'] = 'error'
                return

            total_size_bytes = sum(f['size'] for f in completed)
            total_size_str = format_size(total_size_bytes)

            task['downloading'] = False

            is_playlist_multi = task.get('is_playlist', False) and len(completed) > 1
            if is_playlist_multi:
                summary_filename = f"{len(completed)} videos descargados"
                msg = f'✅ {len(completed)} videos descargados correctamente'
            else:
                summary_filename = completed[0]['filename']
                msg = f'✅ Descarga completada - {total_size_str}'
                task['final_filepath'] = completed[0]['filepath']
                task['filename'] = completed[0]['filename']

            emit_progress(user_id, download_id, 'complete',
                          msg, 100,
                          file_size=total_size_str, filename=summary_filename)

            queue_item['status'] = 'complete'
            log.info(f"[{download_id}] Task finished. Total files: {len(completed)} ({total_size_str})")

        except yt_dlp.utils.DownloadError as e:
            if cancel_event.is_set() or "cancelada" in str(e).lower():
                emit_progress(user_id, download_id, 'cancelled', '❌ Descarga cancelada', 0)
                queue_item['status'] = 'cancelled'
            else:
                emit_progress(user_id, download_id, 'error',
                              f'❌ Error de descarga: {str(e)[:200]}', 0)
                queue_item['status'] = 'error'
            log.error(f"[{download_id}] Download error: {e}")
            if 'base_filename' in locals():
                cleanup_temp_files(base_filename)
        except Exception as e:
            emit_progress(user_id, download_id, 'error',
                          f'❌ Error inesperado: {str(e)[:200]}', 0)
            queue_item['status'] = 'error'
            log.exception(f"[{download_id}] Unexpected error: {e}")
            if 'base_filename' in locals():
                cleanup_temp_files(base_filename)
        finally:
            task['downloading'] = False
            # Remove completed/failed/cancelled items from queue
            with queue_lock:
                user_queue = download_queues.get(user_id, deque())
                download_queues[user_id] = deque(
                    item for item in user_queue if item['status'] == 'queued'
                )
            _emit_queue_update(user_id)
            # Process next item in queue
            _process_next_in_queue(user_id)

    socketio.start_background_task(do_download)


@socketio.on('start_download')
def handle_start_download(data):
    """Add a download to the queue and start processing if possible."""
    if not current_user.is_authenticated:
        emit('error', {'message': 'No autenticado'})
        return

    download_id = data.get('download_id')
    quality = data.get('quality')
    format_pref = data.get('format', 'mp4')
    audio_quality = data.get('audio_quality', '192')
    embed_thumbnail = data.get('embed_thumbnail', False)
    embed_subtitles = data.get('embed_subtitles', False)
    subtitle_lang = data.get('subtitle_lang', 'es,en')
    playlist_items = data.get('playlist_items')

    if not download_id or download_id not in active_downloads:
        emit('error', {'message': 'Sesión de descarga no encontrada. Analiza la URL de nuevo.'})
        return

    task = active_downloads[download_id]
    if task.get('downloading'):
        emit('error', {'message': 'Esta descarga ya está en curso'})
        return

    # Check download quota (admin users are exempt)
    allowed, bytes_used, bytes_remaining = check_quota_allowed(current_user.id, current_user.is_admin)
    if not allowed:
        _, _, user_quota = get_user_quota(current_user.id)
        emit('error', {
            'message': f'Has alcanzado tu limite de {format_size(user_quota)}. '
                       f'Elimina descargas o espera a que expiren para liberar espacio.'
        })
        return

    user_id = current_user.id
    info = task['info']
    title = info.get('title', 'video')
    thumbnail = info.get('thumbnail', '')

    # Check queue size limit (admin = unlimited)
    with queue_lock:
        if user_id not in download_queues:
            download_queues[user_id] = deque()
        user_queue = download_queues[user_id]
        queued_count = sum(1 for item in user_queue if item['status'] in ('queued', 'downloading'))

        if not current_user.is_admin:
            max_queue = current_user.max_queue_size
            if queued_count >= max_queue:
                emit('error', {
                    'message': f'Cola llena ({max_queue} max). Espera a que terminen las descargas en curso.'
                })
                return

        # Check if this download_id is already queued
        for item in user_queue:
            if item['download_id'] == download_id and item['status'] in ('queued', 'downloading'):
                emit('error', {'message': 'Esta descarga ya está en la cola'})
                return

        queue_item = {
            'queue_id': str(uuid.uuid4()),
            'download_id': download_id,
            'user_id': user_id,
            'title': title,
            'thumbnail': thumbnail,
            'quality': quality,
            'format': format_pref,
            'audio_quality': audio_quality,
            'embed_thumbnail': embed_thumbnail,
            'embed_subtitles': embed_subtitles,
            'subtitle_lang': subtitle_lang,
            'playlist_items': playlist_items,
            'queued_at': time.time(),
            'status': 'queued',
        }
        user_queue.append(queue_item)

    _emit_queue_update(user_id)
    _process_next_in_queue(user_id)


@socketio.on('cancel_download')
def handle_cancel_download(data):
    """Cancel an active download or remove a queued item."""
    download_id = data.get('download_id')
    queue_id = data.get('queue_id')
    user_id = current_user.id if current_user.is_authenticated else None

    # Cancel by queue_id (queued item not yet downloading)
    if queue_id and user_id:
        with queue_lock:
            user_queue = download_queues.get(user_id, deque())
            download_queues[user_id] = deque(
                item for item in user_queue
                if not (item['queue_id'] == queue_id and item['status'] == 'queued')
            )
        _emit_queue_update(user_id)
        return

    # Cancel active download by download_id
    if download_id and download_id in active_downloads:
        task = active_downloads[download_id]
        cancel_event = task.get('cancel_event')
        if cancel_event and not cancel_event.is_set():
            cancel_event.set()
            log.info(f"[{download_id}] Download cancelled by user")
            emit('download_progress', {
                'download_id': download_id,
                'phase': 'cancelling',
                'message': '⏳ Cancelando descarga...',
                'percentage': 0
            })


@socketio.on('clear_queue')
def handle_clear_queue():
    """Clear all queued (non-downloading) items for the current user."""
    if not current_user.is_authenticated:
        return
    user_id = current_user.id
    with queue_lock:
        user_queue = download_queues.get(user_id, deque())
        download_queues[user_id] = deque(
            item for item in user_queue if item['status'] == 'downloading'
        )
    _emit_queue_update(user_id)

@socketio.on('trim_video')
def handle_trim_video(data):
    if not current_user.is_authenticated:
        emit('error', {'message': 'No autenticado'})
        return

    download_id = data.get('download_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not download_id or start_time is None or end_time is None:
        emit('error', {'message': 'Datos de recorte incompletos'})
        return

    # Look up original file
    conn = get_db()
    record = conn.execute(
        "SELECT filepath, filename, video_title, thumbnail, quality, video_url FROM downloads WHERE id = ? AND user_id = ?",
        (download_id, current_user.id)
    ).fetchone()
    conn.close()

    if not record or not os.path.exists(record['filepath']):
        emit('error', {'message': 'Video original no encontrado'})
        return

    orig_filepath = record['filepath']
    orig_filename = record['filename']
    video_title = record['video_title']
    thumbnail = record['thumbnail']
    quality = record['quality']
    video_url = record['video_url']

    # Must be playable video format roughly to be trimmable with ffmpeg this way
    ext = os.path.splitext(orig_filename)[1].lower()
    if ext not in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.ts']:
        emit('error', {'message': 'Formato de video no soportado para recortes'})
        return

    user_id = current_user.id
    new_download_id = hashlib.md5(f"{download_id}{start_time}{end_time}{time.time()}".encode()).hexdigest()[:12]

    def do_trim():
        try:
            # Removed the emit_progress call here to avoid stealing UI focus
            name_part, ext_part = os.path.splitext(orig_filename)
            new_filename = f"{name_part} (Recortado){ext_part}"
            new_filepath = os.path.join(DOWNLOAD_DIR, new_filename)

            # Handle filename collision
            counter = 1
            while os.path.exists(new_filepath):
                new_filepath = os.path.join(DOWNLOAD_DIR, f"{name_part} (Recortado {counter}){ext_part}")
                new_filename = os.path.basename(new_filepath)
                counter += 1

            # Silent progress (no orig_download_id to avoid stealing focus from playlists)
            emit_progress(user_id, new_download_id, 'processing', '✂️ Recortando video...', 50)

            duration = float(end_time) - float(start_time)
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', orig_filepath,
                '-t', str(duration),
                '-c', 'copy',
                new_filepath
            ]
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                log.error(f"FFmpeg error during trim: {stderr.decode('utf-8', errors='ignore')}")
                # Emit error without orig_download_id to just show a toast if we implement it, 
                # or keep it simple if we don't want to break the current UI.
                socketio.emit('error', {'message': '❌ Error al recortar el video'}, room=user_id)
                return

            if not os.path.exists(new_filepath):
                emit_progress(user_id, new_download_id, 'error', '❌ Error: archivo no generado', 0, orig_download_id=download_id)
                return

            file_size = os.path.getsize(new_filepath)
            file_size_str = format_size(file_size)

            # Save to database
            save_download_record(
                download_id=new_download_id,
                user_id=user_id,
                filename=new_filename,
                filepath=new_filepath,
                file_size=file_size,
                file_size_str=file_size_str,
                video_title=video_title + " (Recortado)",
                video_url=video_url,
                thumbnail=thumbnail,
                quality=quality
            )

            # Signal library update
            socketio.emit('recent_downloads_update', {}, room=user_id)
            # Show a success toast instead of the full complete card
            socketio.emit('status', {'message': f'✅ Recorte guardado: {new_filename}'}, room=user_id)

            log.info(f"[{new_download_id}] Trim complete: {new_filename} ({file_size_str})")

        except Exception as e:
            socketio.emit('error', {'message': f'❌ Error al recortar: {str(e)[:50]}'}, room=user_id)
            log.exception(f"[{new_download_id}] Unexpected error in trim: {e}")

    socketio.start_background_task(do_trim)

def emit_progress(user_id, download_id, phase, message, percentage, **kwargs):
    """Thread-safe emit of download progress to a specific user."""
    data = {
        'download_id': download_id,
        'phase': phase,
        'message': message,
        'percentage': percentage
    }
    data.update(kwargs)
    
    # Save last progress to allow session restoration
    if download_id in active_downloads:
        active_downloads[download_id]['last_progress'] = data

    try:
        socketio.emit('download_progress', data, room=user_id)
        socketio.sleep(0)  # Yield to allow the event to be sent
    except Exception as e:
        log.error(f"[{download_id}] Error emitting progress: {e}")


def create_progress_hook(download_id, cancel_event, user_id):
    """Create a progress hook for yt-dlp."""
    state = {
        'last_update_time': 0.0,
        'last_percentage': -1.0,
        'start_time': time.time()
    }

    def hook(d):
        if cancel_event.is_set():
            raise yt_dlp.utils.DownloadError("Descarga cancelada por el usuario")

        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            now = time.time()

            if total_bytes and total_bytes > 0:
                percentage = (downloaded_bytes / total_bytes) * 100
            else:
                # Unknown total size — show indeterminate progress
                percentage = min(95, downloaded_bytes / (1024 * 1024))  # ~1% per MB as estimate

            # Throttle updates: at least 1.5 seconds and 1% change
            if (now - state['last_update_time'] >= 1.5 and
                abs(percentage - state['last_percentage']) >= 1.0) or \
               percentage >= 100.0 or state['last_percentage'] < 0:

                state['last_update_time'] = now
                state['last_percentage'] = percentage

                speed = d.get('speed')
                eta = d.get('eta')
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A"
                eta_str = f"{int(eta // 60)}m {int(eta % 60):02d}s" if eta is not None else "N/A"
                downloaded_mb = downloaded_bytes / 1024 / 1024
                total_mb = (total_bytes / 1024 / 1024) if total_bytes else 0

                info_dict = d.get('info_dict', {})
                p_index = info_dict.get('playlist_index')
                n_entries = info_dict.get('n_entries')

                if p_index and n_entries:
                    msg = f'📥 Descargando ({p_index}/{n_entries})...'
                else:
                    msg = '📥 Descargando...'

                emit_progress(user_id, download_id, 'downloading',
                              msg, min(100.0, percentage),
                              speed=speed_str, eta=eta_str,
                              downloaded=f"{downloaded_mb:.1f} MB",
                              total=f"{total_mb:.1f} MB" if total_mb > 0 else "?")

        elif d['status'] == 'finished':
            emit_progress(user_id, download_id, 'processing',
                          '⚙️ Procesando archivo...', 100)

    return hook


def create_post_hook(download_id, user_id, quality, title, url, thumbnail, task):
    """Factory for a hook that runs after each file is fully processed (download + FFmpeg)."""
    def hook(filepath):
        try:
            filename = os.path.basename(filepath)
            log.info(f"[{download_id}] Post-hook processing: {filename}")
            
            # Deduce metadata
            item_title = title
            is_playlist = task.get('is_playlist', False)
            match = re.search(r"_(\d+|NA)\.[^.]+$", filename)
            if is_playlist and match:
                idx_str = match.group(1)
                if idx_str != 'NA':
                    idx = int(idx_str)
                    entry = next((e for e in task.get('playlist_videos', []) if str(e.get('index')) == str(idx)), None)
                    if entry:
                        item_title = entry.get('title', item_title)
            
            item_safe_title = sanitize_filename(item_title)
            ext = os.path.splitext(filename)[1]
            
            if quality in ('audio_original', 'audio_mp3'):
                final_filename = f"{item_safe_title}{ext}"
            else:
                final_filename = f"{item_safe_title} ({quality}){ext}"
            
            final_filepath = os.path.join(DOWNLOAD_DIR, final_filename)
            
            # Handle filename collision
            name_part, ext_part = os.path.splitext(final_filename)
            counter = 1
            while os.path.exists(final_filepath) and final_filepath != filepath:
                final_filepath = os.path.join(DOWNLOAD_DIR, f"{name_part} ({counter}){ext_part}")
                counter += 1
            
            # Rename with retry
            renamed = False
            for attempt in range(15):
                try:
                    os.rename(filepath, final_filepath)
                    filepath = final_filepath
                    renamed = True
                    break
                except PermissionError:
                    time.sleep(0.5)
                except Exception:
                    break
            
            if not renamed:
                log.warning(f"[{download_id}] Could not rename {filepath} to {final_filepath}")
            else:
                log.info(f"[{download_id}] File renamed: {os.path.basename(filepath)}")

            final_filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            file_size_str = format_size(file_size)
            
            # sub_id logic
            sub_id = hashlib.md5(f"{download_id}_{final_filename}".encode()).hexdigest()[:12] if is_playlist else download_id
            
            # Save to DB immediately
            save_download_record(
                download_id=sub_id,
                user_id=user_id,
                filename=final_filename,
                filepath=filepath,
                file_size=file_size,
                file_size_str=file_size_str,
                video_title=item_title,
                video_url=url,
                thumbnail=thumbnail,
                quality=quality
            )
            
            # Track for summary
            if 'completed_files' not in task:
                task['completed_files'] = []
            task['completed_files'].append({'filename': final_filename, 'size': file_size, 'filepath': filepath})
            
            # Signal frontend to refresh the library
            socketio.emit('recent_downloads_update', {}, room=user_id)
            
        except Exception as e:
            log.error(f"[{download_id}] Error in post-hook: {e}", exc_info=True)
            
    return hook


def cleanup_temp_files(base_filename):
    """Clean up temporary files."""
    try:
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(base_filename):
                os.remove(os.path.join(DOWNLOAD_DIR, f))
                log.info(f"Cleaned up temp file: {f}")
    except Exception as e:
        log.error(f"Error cleaning up temp files: {e}")


# --- Initialize ---
init_db()

# Clean up expired downloads on startup
cleanup_expired_downloads()
log.info("Startup cleanup completed.")

if __name__ == '__main__':
    log.info("Starting Video Downloader Web App...")
    # Start periodic cleanup in background
    socketio.start_background_task(periodic_cleanup)
    # Start auto-update for yt-dlp
    socketio.start_background_task(periodic_ytdlp_update)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
