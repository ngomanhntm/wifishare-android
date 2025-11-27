"""
WiFi Server Module
Chứa Flask server được tách ra từ file gốc để dễ tích hợp vào Kivy app
"""

from flask import Flask, request, send_from_directory, abort, render_template_string, send_file, Response, jsonify, session, redirect, url_for
import os
import mimetypes
import time
import threading
import logging
import shutil
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from functools import lru_cache, wraps
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
import re
import unicodedata
import socket

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== AUTHENTICATION =====
USERNAME = "admin"
PASSWORD = "123456"  # Đổi mật khẩu này!

def check_auth(username, password):
    """Kiểm tra username và password"""
    return username == USERNAME and password == PASSWORD

def requires_auth(f):
    """Decorator để bảo vệ routes với session-based auth"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ===== AUTO-DETECT STORAGE =====
def detect_storages():
    """Tự động phát hiện storage thay vì hardcode"""
    storages = {}
    
    # Detect platform
    import platform
    system = platform.system()
    
    if system == "Windows":
        # Windows: Detect drives
        import string
        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                try:
                    os.listdir(drive_path)
                    storages[f"Drive_{drive}"] = drive_path
                except (PermissionError, OSError):
                    pass
        
        # Add common Windows folders
        user_home = os.path.expanduser("~")
        common_folders = {
            "Desktop": os.path.join(user_home, "Desktop"),
            "Documents": os.path.join(user_home, "Documents"), 
            "Downloads": os.path.join(user_home, "Downloads"),
            "Pictures": os.path.join(user_home, "Pictures"),
            "Videos": os.path.join(user_home, "Videos"),
            "Music": os.path.join(user_home, "Music")
        }
        
        for name, path in common_folders.items():
            if os.path.exists(path):
                try:
                    os.listdir(path)
                    storages[name] = path
                except (PermissionError, OSError):
                    pass
    
    else:
        # Android/Linux: Original logic
        storage_base = "/storage"
        
        # Kiểm tra Internal storage trước (emulated/0)
        internal_storage = "/storage/emulated/0"
        if os.path.exists(internal_storage):
            try:
                # Test read access
                os.listdir(internal_storage)
                storages["internal"] = internal_storage
            except (PermissionError, OSError):
                pass
        
        # Kiểm tra các storage khác trong /storage
        if os.path.exists(storage_base):
            try:
                for item in os.listdir(storage_base):
                    # Bỏ qua emulated vì đã xử lý riêng
                    if item == "emulated":
                        continue
                        
                    path = os.path.join(storage_base, item)
                    if os.path.isdir(path):
                        try:
                            # Test read access
                            os.listdir(path)
                            # Tránh trùng với internal storage
                            if path not in storages.values():
                                storages[item] = path
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
        
        # Fallback nếu không detect được gì
        if not storages:
            if os.path.exists("/storage/emulated/0"):
                storages["internal"] = "/storage/emulated/0"
    
    return storages

def get_local_ip():
    """Lấy địa chỉ IP local"""
    try:
        # Kết nối tới Google DNS để lấy IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback method
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return None

# Global variables
STORAGES = detect_storages()

# Set ROOT_DIR based on platform
import platform
if platform.system() == "Windows":
    ROOT_DIR = os.path.expanduser("~")  # User home directory on Windows
else:
    ROOT_DIR = "/storage"  # Android storage
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".3gp", ".webm"}

MEDIA_IMAGES_PREFIX = "__media_images__"
MEDIA_VIDEOS_PREFIX = "__media_videos__"
MEDIA_SPECIALS = {
    MEDIA_IMAGES_PREFIX: {
        "key": "images",
        "display_name": "📷 Tất cả hình ảnh",
        "extensions": IMAGE_EXTS
    },
    MEDIA_VIDEOS_PREFIX: {
        "key": "videos", 
        "display_name": "🎬 Tất cả video",
        "extensions": VIDEO_EXTS
    }
}

def create_app():
    """Tạo và cấu hình Flask app"""
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-change-this'  # Đổi secret key này!
    
    # Import và đăng ký các routes từ file gốc
    # Tạm thời sử dụng routes cơ bản, sau này sẽ import đầy đủ
    
    @app.route('/')
    @requires_auth
    def index():
        """Trang chủ"""
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WiFi File Share</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .storage-list { list-style: none; padding: 0; }
                .storage-item { 
                    background: #f5f5f5; 
                    margin: 10px 0; 
                    padding: 15px; 
                    border-radius: 5px; 
                }
                .storage-item a { 
                    text-decoration: none; 
                    color: #333; 
                    font-weight: bold; 
                }
                .storage-item a:hover { color: #007bff; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 WiFi File Share</h1>
                <p>Chọn storage để duyệt:</p>
                
                <ul class="storage-list">
                    {% for key, path in storages.items() %}
                    <li class="storage-item">
                        <a href="/browse?path={{ path }}">
                            📁 {{ key.title() }} Storage
                            <br><small>{{ path }}</small>
                        </a>
                    </li>
                    {% endfor %}
                </ul>
                
                <hr>
                <p><a href="/logout">🚪 Đăng xuất</a></p>
            </div>
        </body>
        </html>
        """, storages=STORAGES)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Trang đăng nhập"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            if check_auth(username, password):
                session['logged_in'] = True
                return redirect(url_for('index'))
            else:
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Đăng nhập - WiFi File Share</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                        .login-form { 
                            max-width: 400px; 
                            margin: 100px auto; 
                            background: white; 
                            padding: 30px; 
                            border-radius: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        }
                        .form-group { margin: 15px 0; }
                        label { display: block; margin-bottom: 5px; font-weight: bold; }
                        input[type="text"], input[type="password"] { 
                            width: 100%; 
                            padding: 10px; 
                            border: 1px solid #ddd; 
                            border-radius: 5px; 
                            box-sizing: border-box;
                        }
                        .btn { 
                            background: #007bff; 
                            color: white; 
                            padding: 12px 20px; 
                            border: none; 
                            border-radius: 5px; 
                            cursor: pointer; 
                            width: 100%;
                        }
                        .btn:hover { background: #0056b3; }
                        .error { color: red; margin: 10px 0; }
                    </style>
                </head>
                <body>
                    <div class="login-form">
                        <h2>🔐 Đăng nhập</h2>
                        <div class="error">❌ Sai tên đăng nhập hoặc mật khẩu!</div>
                        <form method="post">
                            <div class="form-group">
                                <label>Tên đăng nhập:</label>
                                <input type="text" name="username" required>
                            </div>
                            <div class="form-group">
                                <label>Mật khẩu:</label>
                                <input type="password" name="password" required>
                            </div>
                            <button type="submit" class="btn">Đăng nhập</button>
                        </form>
                    </div>
                </body>
                </html>
                """)
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Đăng nhập - WiFi File Share</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                .login-form { 
                    max-width: 400px; 
                    margin: 100px auto; 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .form-group { margin: 15px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input[type="text"], input[type="password"] { 
                    width: 100%; 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    box-sizing: border-box;
                }
                .btn { 
                    background: #007bff; 
                    color: white; 
                    padding: 12px 20px; 
                    border: none; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    width: 100%;
                }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="login-form">
                <h2>🔐 Đăng nhập</h2>
                <form method="post">
                    <div class="form-group">
                        <label>Tên đăng nhập:</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>Mật khẩu:</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit" class="btn">Đăng nhập</button>
                </form>
            </div>
        </body>
        </html>
        """)
    
    @app.route('/logout')
    def logout():
        """Đăng xuất"""
        session.pop('logged_in', None)
        return redirect(url_for('login'))
    
    @app.route('/browse')
    @requires_auth
    def browse():
        """Browse files - simplified version"""
        path = request.args.get('path', ROOT_DIR)
        
        try:
            if not os.path.exists(path):
                abort(404)
            
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'folder',
                        'path': item_path
                    })
                else:
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': item_path,
                        'size': os.path.getsize(item_path)
                    })
            
            # Sort: folders first, then files
            items.sort(key=lambda x: (x['type'] == 'file', x['name'].lower()))
            
            return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Browse - {{ current_path }}</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .container { max-width: 1000px; margin: 0 auto; }
                    .breadcrumb { background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
                    .file-list { list-style: none; padding: 0; }
                    .file-item { 
                        display: flex; 
                        align-items: center; 
                        padding: 10px; 
                        border-bottom: 1px solid #eee; 
                    }
                    .file-item:hover { background: #f5f5f5; }
                    .file-icon { margin-right: 10px; font-size: 20px; }
                    .file-name { flex: 1; }
                    .file-size { color: #666; font-size: 14px; }
                    a { text-decoration: none; color: #333; }
                    a:hover { color: #007bff; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="breadcrumb">
                        📁 {{ current_path }}
                    </div>
                    
                    {% if parent_path %}
                    <div class="file-item">
                        <span class="file-icon">⬆️</span>
                        <a href="/browse?path={{ parent_path }}" class="file-name">.. (Thư mục cha)</a>
                    </div>
                    {% endif %}
                    
                    <ul class="file-list">
                        {% for item in items %}
                        <li class="file-item">
                            <span class="file-icon">
                                {% if item.type == 'folder' %}📁{% else %}📄{% endif %}
                            </span>
                            {% if item.type == 'folder' %}
                                <a href="/browse?path={{ item.path }}" class="file-name">{{ item.name }}</a>
                            {% else %}
                                <a href="/file?path={{ item.path }}" class="file-name">{{ item.name }}</a>
                                <span class="file-size">{{ "%.1f"|format(item.size/1024/1024) }} MB</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                    
                    <hr>
                    <p><a href="/">🏠 Trang chủ</a> | <a href="/logout">🚪 Đăng xuất</a></p>
                </div>
            </body>
            </html>
            """, 
            current_path=path, 
            items=items,
            parent_path=os.path.dirname(path) if path != ROOT_DIR else None
            )
            
        except Exception as e:
            logger.error(f"Browse error: {e}")
            abort(500)
    
    @app.route('/file')
    @requires_auth
    def serve_file():
        """Serve file for download"""
        file_path = request.args.get('path')
        if not file_path or not os.path.exists(file_path):
            abort(404)
        
        try:
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            logger.error(f"File serve error: {e}")
            abort(500)
    
    return app

if __name__ == '__main__':
    # Test server
    app = create_app()
    logger.info("Starting WiFi File Manager...")
    logger.info(f"Detected storages: {STORAGES}")
    logger.warning("Security: Ensure this is only accessible on local network!")
    logger.warning(f"Authentication: username='{USERNAME}', password='{PASSWORD}'")
    
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        threaded=True
    )
