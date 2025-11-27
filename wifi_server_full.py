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

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== AUTHENTICATION =====
# ⚠️ QUAN TRỌNG: ĐỔI MẬT KHẨU NÀY TRƯỚC KHI SỬ DỤNG!
USERNAME = "admin"
PASSWORD = "123456"  # ĐỔI MẬT KHẨU NÀY!

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

STORAGES = detect_storages()
logger.info(f"Detected storages: {STORAGES}")

# Set ROOT_DIR based on platform
import platform
if platform.system() == "Windows":
    ROOT_DIR = os.path.expanduser("~")  # User home directory on Windows
else:
    ROOT_DIR = "/storage"  # Android storage

# Nếu chỉ muốn thẻ SD thì đổi thành: ROOT_DIR = "/storage/XXXX-XXXX"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".3gp", ".webm"}

MEDIA_IMAGES_PREFIX = "__media_images__"
MEDIA_VIDEOS_PREFIX = "__media_videos__"
MEDIA_SPECIALS = {
    MEDIA_IMAGES_PREFIX: {
        "key": "images",
        "label": "Images",
        "exts": IMAGE_EXTS,
    },
    MEDIA_VIDEOS_PREFIX: {
        "key": "videos",
        "label": "Videos",
        "exts": VIDEO_EXTS,
    },
}

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Thay đổi trong production

# --------- TEMPLATE: Login ----------
LOGIN_HTML = r"""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập - File Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .login-container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 40px;
            width: 100%;
            max-width: 400px;
            animation: slideUp 0.6s ease;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 32px;
        }
        
        .login-icon {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            font-size: 24px;
            color: white;
        }
        
        .login-title {
            font-size: 24px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 8px;
        }
        
        .login-subtitle {
            color: #6b7280;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #374151;
            margin-bottom: 8px;
        }
        
        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            background: #f9fafb;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background: white;
        }
        
        .login-button {
            width: 100%;
            padding: 12px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .login-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }
        
        .login-button:active {
            transform: translateY(0);
        }
        
        .error-message {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #dc2626;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .footer {
            text-align: center;
            margin-top: 32px;
            padding-top: 24px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 12px;
        }
        
        @media (max-width: 480px) {
            .login-container {
                padding: 24px;
                margin: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <div class="login-icon">📁</div>
            <h1 class="login-title">File Manager</h1>
            <p class="login-subtitle">Đăng nhập để truy cập hệ thống</p>
        </div>
        
        {% if error %}
        <div class="error-message">
            <span>⚠️</span>
            <span>{{ error }}</span>
        </div>
        {% endif %}
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label class="form-label" for="username">Tên đăng nhập</label>
                <input type="text" id="username" name="username" class="form-input" 
                       placeholder="Nhập tên đăng nhập" required autofocus>
            </div>
            
            <div class="form-group">
                <label class="form-label" for="password">Mật khẩu</label>
                <input type="password" id="password" name="password" class="form-input" 
                       placeholder="Nhập mật khẩu" required>
            </div>
            
            <button type="submit" class="login-button">Đăng nhập</button>
        </form>
        
        <div class="footer">
            <p>WiFi File Manager - Secure File Sharing</p>
        </div>
    </div>
    
    <script>
        // Auto focus vào username field
        document.getElementById('username').focus();
        
        // Enter key navigation
        document.getElementById('username').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                document.getElementById('password').focus();
            }
        });
    </script>
</body>
</html>
"""

# --------- TEMPLATE: Browse tree ----------
BROWSE_HTML = r"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>WiFi File Explorer</title>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        /* Lucide icon styling */
        .lucide { width: 16px; height: 16px; stroke-width: 2; vertical-align: middle; }
        .view-btn .lucide { width: 14px; height: 14px; }
        .cmd-btn .lucide { width: 14px; height: 14px; margin-right: 4px; }
        
        * , *::before, *::after {
            box-sizing: border-box;
        }
        body {
            margin: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f8fafc;
        }
        a { color: inherit; text-decoration: none; }
        a:hover { text-decoration: underline; }

        .explorer-window {
            width: 100%;
            height: 100vh;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* TITLE BAR */
        .title-bar {
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 10px;
            background: linear-gradient(to right,rgba(241,245,249,0.9),rgba(226,232,240,0.9));
            user-select: none;
        }
        .title-left {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #0f172a;
        }
        .title-icon { font-size: 16px; }
        .title-right { display: flex; }
        .title-btn {
            border: none;
            background: transparent;
            width: 32px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            border-radius: 4px;
            color: #0f172a;
        }
        .title-btn:hover {
            background: rgba(148,163,184,0.25);
        }
        .title-btn-close:hover {
            background: #ef4444;
            color: #fff;
        }

        /* TOOLBAR & COMMAND BAR FORM */
        .toolbar-form {
            display: flex;
            flex-direction: column;
            gap: 0;
            border-bottom: 1px solid #e5e7eb;
            background: #f9fafb;
        }

        .top-toolbar {
            display: grid;
            grid-template-columns: auto minmax(0,1fr) 260px;
            gap: 8px;
            align-items: center;
            padding: 8px 10px 4px 10px;
        }
        .nav-buttons {
            display: flex;
            gap: 4px;
        }
        .nav-btn {
            width: 28px;
            height: 28px;
            border-radius: 999px;
            border: 1px solid #d4d4d8;
            background: #ffffff;
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #111827;
        }
        .nav-btn.disabled {
            opacity: 0.4;
            cursor: default;
        }
        .nav-btn:hover:not(.disabled) {
            background: #eef2ff;
            border-color: #a5b4fc;
        }

        .address-bar {
            background: #ffffff;
            border-radius: 999px;
            border: 1px solid #d4d4d8;
            padding: 0 10px;
            height: 30px;
            display: flex;
            align-items: center;
            overflow: hidden;
            font-size: 12px;
        }
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            overflow: hidden;
            position: relative;
        }
        .breadcrumb.compact {
            justify-content: flex-end;
        }
        .breadcrumb-ellipsis {
            padding: 2px 6px;
            color: #9ca3af;
            cursor: pointer;
            user-select: none;
        }
        .breadcrumb-ellipsis:hover {
            background: #e0e7ff;
            border-radius: 999px;
        }
        .breadcrumb-item {
            padding: 2px 6px;
            border-radius: 999px;
        }
        .breadcrumb-item.clickable a {
            color: #1d4ed8;
            text-decoration: none;
        }
        .breadcrumb-item.clickable:hover {
            background: #e0e7ff;
        }
        .breadcrumb-sep {
            color: #9ca3af;
        }

        .search-area {
            display: flex;
            justify-content: flex-end;
        }
        .search-box {
            width: 100%;
            max-width: 240px;
            height: 30px;
            border-radius: 999px;
            border: 1px solid #d4d4d8;
            padding: 0 12px;
            font-size: 12px;
            outline: none;
            background: #ffffff;
        }
        .search-box:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 1px rgba(99,102,241,0.35);
        }

        .command-bar {
            height: 36px;
            padding: 0 10px 6px 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .command-group {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
        }
        .cmd-label {
            font-size: 11px;
            color: #6b7280;
        }
        .cmd-select {
            padding: 3px 8px;
            border-radius: 999px;
            border: 1px solid #d4d4d8;
            background: #ffffff;
            font-size: 12px;
            outline: none;
        }
        .checkbox-label {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            color: #4b5563;
        }
        .checkbox-label input {
            accent-color: #2563eb;
        }
        .view-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px;
            height: 26px;
            border-radius: 999px;
            border: 1px solid transparent;
            text-decoration: none;
            font-size: 14px;
        }
        .view-btn.active {
            border-color: #a5b4fc;
            background: #eef2ff;
        }
        .cmd-btn {
            height: 26px;
            padding: 0 10px;
            border-radius: 999px;
            border: 1px solid #d4d4d8;
            background: #f3f4f6;
            font-size: 12px;
            cursor: pointer;
            color: #374151;
        }
        .cmd-btn.primary {
            border-color: #2563eb;
            background: #2563eb;
            color: #f9fafb;
        }
        .cmd-btn:hover {
            background: #e0f2fe;
        }
        .cmd-btn.primary:hover {
            background: #1d4ed8;
        }
        .cmd-btn.danger {
            border-color: #dc2626;
            background: #fee2e2;
            color: #991b1b;
        }
        .cmd-btn.danger:hover {
            background: #fecaca;
        }
        .cmd-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .cmd-btn.no-border {
            border: none;
            background: transparent;
        }
        .cmd-btn.no-border:hover {
            background: #e0f2fe;
        }

        /* CONTENT: 3 COLUMNS */
        .content-area {
            flex: 1;
            display: grid;
            grid-template-columns: var(--nav-width, 220px) minmax(0,1fr) 260px;
            min-height: 0;
        }
        .content-area.detail-hidden {
            grid-template-columns: var(--nav-width, 220px) minmax(0,1fr);
        }

        /* LEFT NAV PANE */
        .nav-pane {
            width: var(--nav-width, 220px);
            border-right: 1px solid #e5e7eb;
            padding: 8px;
            background: #f9fafb;
            overflow-y: auto;
            position: relative;
            scrollbar-width: thin;
            scrollbar-color: transparent transparent;
        }
        .nav-pane::-webkit-scrollbar {
            width: 8px;
        }
        .nav-pane::-webkit-scrollbar-track {
            background: transparent;
        }
        .nav-pane::-webkit-scrollbar-thumb {
            background: transparent;
            border-radius: 4px;
        }
        .nav-pane:hover::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.3);
        }
        .nav-pane::-webkit-scrollbar-thumb:hover {
            background: rgba(148, 163, 184, 0.5);
        }
        .nav-resize-handle {
            position: absolute;
            top: 0;
            right: -4px;
            width: 8px;
            height: 100%;
            cursor: col-resize;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .nav-resize-handle:hover {
            background: rgba(99, 102, 241, 0.1);
        }
        .nav-resize-handle:hover::after {
            content: '';
            width: 2px;
            height: 20px;
            background: #6366f1;
            border-radius: 1px;
        }
        .nav-resize-handle.resizing {
            background: rgba(99, 102, 241, 0.2);
        }
        .nav-resize-handle.resizing::after {
            content: '';
            width: 2px;
            height: 20px;
            background: #6366f1;
            border-radius: 1px;
        }
        .nav-section {
            margin-bottom: 12px;
        }
        .nav-section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 6px;
            padding: 0 6px;
        }
        .nav-item {
            width: 100%;
            padding: 4px 8px;
            border-radius: 8px;
            border: none;
            background: transparent;
            text-align: left;
            font-size: 13px;
            color: #111827;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .nav-item span.icon {
            width: 18px;
            text-align: center;
        }
        .nav-item:hover {
            background: #e5e7eb;
        }
        .nav-item.active {
            background: #dbeafe;
            color: #1d4ed8;
        }

        /* MAIN PANE */
        .main-pane {
            display: flex;
            flex-direction: column;
            min-width: 0;
            min-height: 0;
            background: #ffffff;
            overflow-y: auto;
        }

        .column-header {
            display: grid;
            grid-template-columns: minmax(240px,3fr) 2fr 2fr;
            gap: 4px;
            padding: 4px 10px;
            border-bottom: 1px solid #e5e7eb;
            background: #f3f4f6;
            font-size: 12px;
            color: #4b5563;
        }
        .col {
            padding: 2px 4px;
        }

        .items {
            flex: 1;
            overflow-y: auto;
            padding: 4px 6px 6px 6px;
        }
        .items.list {
            display: block;
        }
        .items.grid {
            display: grid;
            grid-template-columns: repeat(auto-fill,minmax(160px,1fr));
            gap: 6px 10px;
            align-items: start;
            align-content: start;
        }

        .item {
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid transparent;
            font-size: 13px;
            cursor: default;
        }
        .item.list {
            display: grid;
            grid-template-columns: minmax(240px,3fr) 2fr 2fr;
            gap: 4px;
            padding: 4px 10px;
            align-items: center;
        }
        .item.grid {
            display: flex;
            flex-direction: column;
            padding: 6px;
        }
        .item.item-folder {
            /* nhẹ nhẹ cho folder */
        }
        .item:hover {
            background: #f3f4ff;
            border-color: #c7d2fe;
        }
        .item.selected {
            background: #dbeafe;
            border-color: #2563eb;
            color: #1d4ed8;
        }
        .item.cut-source {
            opacity: 0.45;
        }
        .file-cell {
            padding: 2px 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .file-name {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .file-icon {
            width: 18px;
            text-align: center;
        }
        .file-info {
            font-size: 12px;
            color: #6b7280;
        }

        /* GRID view thumb */
        .thumb {
            width: 100%;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 12px;
            background: transparent;
            border: 1px solid rgba(148,163,184,0.55);
            margin-bottom: 6px;
        }
        .thumb img, .thumb video {
            max-width: 100%;
            max-height: 100%;
        }
        .meta {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .name {
            word-break: break-all;
        }
        .badge {
            font-size: 11px;
            color: #6b7280;
        }

        .empty {
            font-size: 13px;
            color: #6b7280;
            padding: 10px;
        }

        /* DETAIL PANE */
        .detail-pane {
            border-left: 1px solid #e5e7eb;
            padding: 8px 10px;
            background: #f9fafb;
            display: flex;
            flex-direction: column;
            font-size: 12px;
        }
        .content-area.detail-hidden .detail-pane {
            display: none;
        }
        .detail-title {
            font-size: 13px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }
        .detail-content {
            flex: 1;
            overflow-y: auto;
        }
        .detail-block {
            margin-bottom: 8px;
        }
        .detail-label {
            font-weight: 600;
            color: #6b7280;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 2px;
        }
        .detail-value {
            font-size: 12px;
            color: #111827;
            word-break: break-all;
        }

        /* STATUS BAR */
        .status-bar {
            height: 26px;
            padding: 0 10px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            font-size: 12px;
            color: #4b5563;
            background: #f9fafb;
        }
        .fab-wrapper {
            position: fixed;
            right: 24px;
            bottom: 32px;
            z-index: 2000;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 10px;
            transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .fab-wrapper.fab-hidden {
            opacity: 0;
            transform: translateY(30px);
            pointer-events: none;
        }
        .fab-btn {
            width: 52px;
            height: 52px;
            border-radius: 25%;
            border: none;
            background: #2563eb;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.35);
            cursor: pointer;
            transition: background 0.2s ease, transform 0.2s ease;
        }
        .fab-btn:hover {
            background: #1d4ed8;
            transform: translateY(-1px);
        }
        .fab-wrapper.fab-open .fab-btn {
            background: #1d4ed8;
        }
        .fab-menu {
            position: absolute;
            bottom: 64px;
            right: 0;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(15, 23, 42, 0.2), 0 1px 4px rgba(15, 23, 42, 0.15);
            padding: 8px 0;
            min-width: 220px;
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        .fab-wrapper.fab-open .fab-menu {
            display: flex;
        }
        .fab-menu button {
            background: transparent;
            border: none;
            width: 100%;
            padding: 10px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
            color: #0f172a;
            cursor: pointer;
            text-align: left;
        }
        .fab-menu button:hover {
            background: #f1f5f9;
        }
        .fab-menu button i {
            width: 18px;
            height: 18px;
            color: #2563eb;
        }

        /* PROGRESS & NOTIFICATIONS */
        .progress-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }
        .progress-modal {
            background: white;
            border-radius: 8px;
            padding: 24px;
            min-width: 400px;
            max-width: 500px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        .progress-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            color: #1f2937;
        }
        .progress-bar-container {
            background: #f3f4f6;
            border-radius: 6px;
            height: 8px;
            margin-bottom: 12px;
            overflow: hidden;
        }
        .progress-bar {
            background: #2563eb;
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 6px;
        }
        .progress-text {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 8px;
        }
        .progress-actions {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
            margin-top: 16px;
        }
        .progress-btn {
            padding: 8px 16px;
            border: 1px solid #d1d5db;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .progress-btn.primary {
            background: #2563eb;
            color: white;
            border-color: #2563eb;
        }
        .progress-btn:hover {
            background: #f9fafb;
        }
        .progress-btn.primary:hover {
            background: #1d4ed8;
        }

        /* RENAME MODAL */
        .rename-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        }
        .rename-overlay.show {
            opacity: 1;
            visibility: visible;
        }
        .rename-modal {
            background: white;
            border-radius: 12px;
            padding: 24px;
            width: 90%;
            max-width: 480px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            transform: translateY(20px);
            transition: transform 0.3s ease;
        }
        .rename-overlay.show .rename-modal {
            transform: translateY(0);
        }
        .rename-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }
        .rename-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
        }
        .rename-title {
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }
        .rename-form {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .rename-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .rename-label {
            font-size: 14px;
            font-weight: 500;
            color: #374151;
        }
        .rename-input {
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            font-family: inherit;
        }
        .rename-input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        .rename-input.error {
            border-color: #ef4444;
        }
        .rename-error {
            color: #ef4444;
            font-size: 12px;
            margin-top: 4px;
        }
        .rename-actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            margin-top: 8px;
        }
        .rename-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s ease, transform 0.1s ease;
        }
        .rename-btn:active {
            transform: translateY(1px);
        }
        .rename-btn.secondary {
            background: #f3f4f6;
            color: #374151;
        }
        .rename-btn.secondary:hover {
            background: #e5e7eb;
        }
        .rename-btn.primary {
            background: #3b82f6;
            color: white;
        }
        .rename-btn.primary:hover {
            background: #2563eb;
        }
        .rename-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .notification-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 320px;
            pointer-events: none;
        }
        .notification {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
            font-size: 14px;
            animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            pointer-events: auto;
            cursor: pointer;
            transition: transform 0.2s ease, opacity 0.2s ease;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            min-height: 60px;
        }
        .notification:hover {
            transform: translateX(-4px);
        }
        .notification.removing {
            animation: slideOutRight 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
        .notification-icon {
            font-size: 18px;
            flex-shrink: 0;
            margin-top: 1px;
        }
        .notification-content {
            flex: 1;
            line-height: 1.4;
        }
        .notification-title {
            font-weight: 600;
            margin-bottom: 2px;
            color: #1f2937;
        }
        .notification-message {
            color: #6b7280;
            font-size: 13px;
        }
        .notification-close {
            position: absolute;
            top: 8px;
            right: 8px;
            background: none;
            border: none;
            font-size: 16px;
            cursor: pointer;
            color: #9ca3af;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
            transition: background-color 0.2s ease;
        }
        .notification-close:hover {
            background: #f3f4f6;
            color: #6b7280;
        }
        .notification.success {
            border-left: 4px solid #10b981;
            background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        }
        .notification.success .notification-icon {
            color: #10b981;
        }
        .notification.error {
            border-left: 4px solid #ef4444;
            background: linear-gradient(135deg, #fef2f2 0%, #fef1f1 100%);
        }
        .notification.error .notification-icon {
            color: #ef4444;
        }
        .notification.warning {
            border-left: 4px solid #f59e0b;
            background: linear-gradient(135deg, #fffbeb 0%, #fefce8 100%);
        }
        .notification.warning .notification-icon {
            color: #f59e0b;
        }
        .notification.info {
            border-left: 4px solid #3b82f6;
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        }
        .notification.info .notification-icon {
            color: #3b82f6;
        }
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    </style>
</head>
<body>
    <div class="explorer-window">
        <!-- TITLE BAR -->
        <div class="title-bar">
            <div class="title-left">
                <span class="title-icon">📁</span>
                <span>WiFi File Explorer</span>
            </div>
            <div class="title-right">
                <button class="title-btn" onclick="window.location.href='/browse'" title="Trang chủ">⌂</button>
                <button class="title-btn" onclick="window.location.href='/logout'" title="Đăng xuất">👤</button>
                <button class="title-btn title-btn-close" onclick="window.close()" title="Đóng">✕</button>
            </div>
        </div>

        <!-- TOOLBAR + COMMAND BAR (1 form GET) -->
        <form method="get" class="toolbar-form">
            <input type="hidden" name="path" value="{{ cur_rel }}">

            <div class="top-toolbar">
                <div class="nav-buttons">
                    <button type="button" class="nav-btn" onclick="history.back()">←</button>

                    {% if parent_rel is not none %}
                    <a class="nav-btn" href="/browse?path={{ parent_rel|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}{% if show_hidden %}&hidden=1{% endif %}&view={{ view }}">↑</a>
                    {% else %}
                    <div class="nav-btn disabled">↑</div>
                    {% endif %}
                </div>

                <!-- Address bar với breadcrumb -->
                <div class="address-bar">
                    <div class="breadcrumb">
                        {% if breadcrumb_segments %}
                            {% for seg in breadcrumb_segments %}
                                <span class="breadcrumb-item clickable">
                                    {% if seg.path is none %}
                                        <a href="/browse">{{ seg.name }}</a>
                                    {% else %}
                                        <a href="/browse?path={{ seg.path|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}{% if show_hidden %}&hidden=1{% endif %}&view={{ view }}">{{ seg.name }}</a>
                                    {% endif %}
                                </span>
                                {% if not loop.last %}
                                    <span class="breadcrumb-sep">›</span>
                                {% endif %}
                            {% endfor %}
                        {% else %}
                            <span class="breadcrumb-item clickable">
                                <a href="/browse">storage</a>
                            </span>
                            {% if cur_rel %}
                                <span class="breadcrumb-sep">›</span>
                                {% set parts = cur_rel.split('/') %}
                                {% set ns = namespace(acc="") %}
                                {% for seg in parts if seg %}
                                    {% set ns.acc = (ns.acc ~ "/" ~ seg).lstrip("/") %}
                                    <span class="breadcrumb-item clickable">
                                        <a href="/browse?path={{ ns.acc|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}{% if show_hidden %}&hidden=1{% endif %}&view={{ view }}">{{ seg }}</a>
                                    </span>
                                    {% if not loop.last %}
                                        <span class="breadcrumb-sep">›</span>
                                    {% endif %}
                                {% endfor %}
                            {% endif %}
                        {% endif %}
                    </div>
                </div>

                <!-- Ô search -->
                <div class="search-area">
                    <input type="text" name="q" value="{{ q }}" class="search-box" placeholder="Search here">
                </div>
            </div>

            <div class="command-bar">
                <div class="command-group" style="flex-wrap: wrap; gap: 6px;">
                    <span class="cmd-label">Sort</span>
                    <select name="sort" class="cmd-select">
                        <option value="name" {% if sort == 'name' %}selected{% endif %}>Name</option>
                        <option value="date" {% if sort == 'date' %}selected{% endif %}>Date</option>
                    </select>
                    <select name="order" class="cmd-select">
                        <option value="asc" {% if order == 'asc' %}selected{% endif %}>↑</option>
                        <option value="desc" {% if order == 'desc' %}selected{% endif %}>↓</option>
                    </select>
                    <label class="checkbox-label">
                        <input type="checkbox" name="hidden" value="1" {% if show_hidden %}checked{% endif %}>
                        Hidden
                    </label>
                    <button type="button" class="cmd-btn" onclick="fmCopySelected('copy')"><i data-lucide="copy"></i> Copy</button>
                    <button type="button" class="cmd-btn" onclick="fmCopySelected('cut')"><i data-lucide="scissors"></i> Cut</button>
                    <button type="button" class="cmd-btn" onclick="fmPasteClipboard()" id="fmPasteBtn" disabled><i data-lucide="clipboard-check"></i> Paste</button>
                    <button type="button" class="cmd-btn" onclick="fmRenameSelected()" id="fmRenameBtn" disabled><i data-lucide="edit-3"></i> Rename</button>
                    <button type="button" class="cmd-btn danger" onclick="fmDeleteSelected()"><i data-lucide="trash-2"></i> Delete</button>
                </div>
                <div class="command-group" style="margin-left:auto;">
                    <span class="cmd-label">View</span>
                    <a class="view-btn {% if not is_list %}active{% endif %}"
                       href="/browse?path={{ cur_rel|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}{% if show_hidden %}&hidden=1{% endif %}&view=grid"><i data-lucide="layout-grid"></i></a>
                    <a class="view-btn {% if is_list %}active{% endif %}"
                       href="/browse?path={{ cur_rel|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}{% if show_hidden %}&hidden=1{% endif %}&view=list"><i data-lucide="list"></i></a>
                    <button type="button" class="cmd-btn no-border" onclick="fmToggleDetails()" id="fmToggleDetailsBtn" title="Toggle Details"><i data-lucide="panel-right"></i></button>
                    <button type="button" class="cmd-btn" onclick="fmDownloadSelected()"><i data-lucide="download"></i> Download</button>
                </div>
            </div>
        </form>

        <!-- CONTENT -->
        <div class="content-area">
            <!-- NAV LEFT -->
            <div class="nav-pane">
                <div class="nav-section">
                    <div class="nav-section-title">Quick access</div>
                    <button class="nav-item {% if not cur_rel %}active{% endif %}"
                            onclick="window.location.href='/browse'">
                        <span class="icon">📁</span><span>All files</span>
                    </button>
                    <button class="nav-item {% if active_special == 'images' %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ media_images_prefix|urlencode }}'">
                        <span class="icon">🏞️</span><span>Images</span>
                    </button>
                    <button class="nav-item {% if active_special == 'videos' %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ media_videos_prefix|urlencode }}'">
                        <span class="icon">🎬</span><span>Videos</span>
                    </button>
                </div>

                <div class="nav-section">
                    <div class="nav-section-title">Storage</div>
                    <button class="nav-item {% if cur_rel.startswith('emulated/0') and not cur_rel.startswith('emulated/0/Download') and not cur_rel.startswith('emulated/0/DCIM') %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ 'emulated/0'|urlencode }}'">
                        <span class="icon">💽</span><span>Internal storage</span>
                    </button>
                    <button class="nav-item {% if cur_rel.startswith('0123-4567') %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ '0123-4567'|urlencode }}'">
                        <span class="icon">💾</span><span>SD card</span>
                    </button>
                    <button class="nav-item {% if cur_rel == 'emulated/0/Download' or cur_rel.startswith('emulated/0/Download/') %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ 'emulated/0/Download'|urlencode }}'">
                        <span class="icon">⬇️</span><span>Downloads</span>
                    </button>
                    <button class="nav-item {% if cur_rel == 'emulated/0/DCIM' or cur_rel.startswith('emulated/0/DCIM/') %}active{% endif %}"
                            onclick="window.location.href='/browse?path={{ 'emulated/0/DCIM'|urlencode }}'">
                        <span class="icon">🎥</span><span>Camera</span>
                    </button>
                </div>
                <div class="nav-resize-handle" id="navResizeHandle"></div>
            </div>

            <!-- MAIN CENTER -->
            <div class="main-pane">
                {% if entries %}
                    {% if is_list %}
                    <div class="column-header">
                        <div class="col">Name</div>
                        <div class="col">Info</div>
                        <div class="col">Type</div>
                    </div>
                    {% endif %}

                    <div class="items {{ 'list' if is_list else 'grid' }}">
                        {% for e in entries %}
                        <div class="item {{ 'list' if is_list else 'grid' }}{% if e.is_dir %} item-folder{% endif %}"
                             data-path="{{ e.rel }}"
                             data-is-dir="{{ 1 if e.is_dir else 0 }}"
                             data-mime="{{ e.mime }}"
                             data-name="{{ e.name }}"
                             data-info="{{ e.info }}"
                             onclick="fmHandleClick(event, this)"
                             ondblclick="fmHandleDblClick(event, this)">
                            {% if is_list %}
                                <div class="file-cell file-name">
                                    <span class="file-icon">
                                        {% if e.is_dir %}📁{% elif e.mime.startswith('image/') %}🖼️{% elif e.mime.startswith('video/') %}🎬{% elif e.mime.startswith('audio/') %}🎵{% else %}📄{% endif %}
                                    </span>
                                    <span>{{ e.name }}</span>
                                </div>
                                <div class="file-cell file-info">{{ e.info }}</div>
                                <div class="file-cell">
                                    {% if e.is_dir %}Folder{% elif e.mime %}{{ e.mime }}{% else %}File{% endif %}
                                </div>
                            {% else %}
                                <div class="thumb">
                                    {% if e.is_dir %}
                                        {% if e.preview_rel %}
                                            {% if e.preview_mime and e.preview_mime.startswith("video/") %}
                                                <video class="fm-thumb-video fm-lazy-media"
                                                       data-src="/file?path={{ e.preview_rel|urlencode }}"
                                                       muted playsinline preload="metadata"
                                                       style="width:100%;height:100%;object-fit:cover;border-radius:8px;">
                                                </video>
                                            {% else %}
                                                <img src="/file?path={{ e.preview_rel|urlencode }}"
                                                     loading="lazy"
                                                     style="width:100%;height:100%;object-fit:cover;border-radius:8px;">
                                            {% endif %}
                                        {% else %}
                                            <span style="font-size:48px;">📁</span>
                                        {% endif %}
                                    {% else %}
                                        {% if e.mime.startswith("image/") %}
                                            <img src="/file?path={{ e.rel|urlencode }}" loading="lazy">
                                        {% elif e.mime.startswith("video/") %}
                                            <video class="fm-file-video fm-lazy-media"
                                                   data-src="/file?path={{ e.rel|urlencode }}"
                                                   muted playsinline preload="metadata"></video>
                                        {% elif e.mime.startswith("audio/") %}
                                            <audio src="/file?path={{ e.rel|urlencode }}" controls></audio>
                                        {% else %}
                                            <span style="font-size:40px;">📄</span>
                                        {% endif %}
                                    {% endif %}
                                </div>
                                <div class="meta">
                                    <div class="name">{{ e.name }}</div>
                                    <div class="badge">{{ e.info }}</div>
                                </div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class="empty">Thư mục trống.</div>
                {% endif %}
            </div>

            <!-- DETAIL RIGHT -->
            <div class="detail-pane">
                <div class="detail-title">Details</div>
                <div class="detail-content" id="fmDetail">
                    <div class="detail-block">
                        <div class="detail-label">Tip</div>
                        <div class="detail-value">Select a file or folder to view information.</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- STATUS BAR -->
        <div class="status-bar" id="fmStatus">
            0 items
        </div>
    </div>

    <!-- FORM DOWNLOAD ẨN -->
    <form id="fmDownloadForm" method="post" action="/download" style="display:none;">
        <input type="hidden" name="paths" id="fmDownloadPaths">
    </form>

    <!-- OVERLAY PREVIEW (dùng lại logic cũ) -->
    <div id="fmOverlay" style="display:none;position:fixed;inset:0;
         background:rgba(0,0,0,0.7);align-items:center;justify-content:center;
         z-index:9999;">
        <div onclick="fmHidePreview()" style="position:absolute;inset:0;"></div>

        <div style="position:relative;background:#1e1e1e;border-radius:12px;
                    padding:10px;max-width:95%;max-height:90%;
                    z-index:10000;box-shadow:0 25px 50px rgba(0,0,0,0.7);">
            <div style="display:flex;justify-content:space-between;
                        align-items:center;padding:12px 16px;background:#2d2d2d;
                        border-bottom:1px solid #404040;border-radius:12px 12px 0 0;">
                <button onclick="fmHidePreview()"
                        style="background:#333;border:none;color:#eee;
                               padding:4px 8px;border-radius:4px;cursor:pointer;">
                    ✕
                </button>
                <a id="fmOverlayDownload"
                   href="#"
                   style="padding:4px 8px;border-radius:4px;
                          border:1px solid #4aa3ff;text-decoration:none;
                          color:#4aa3ff;">
                    ⬇ Download
                </a>
            </div>
            <div id="fmOverlayBody" style="text-align:center;"></div>
        </div>
    </div>

    <div class="fab-wrapper" id="fmFabWrapper">
        <div class="fab-menu" id="fmFabMenu">
            <button type="button" onclick="fmPromptNewFolder()">
                <i data-lucide="folder-plus"></i>
                <span>Tạo thư mục mới</span>
            </button>
            <button type="button" onclick="fmTriggerUpload(false)" title="Có thể chọn nhiều file cùng lúc">
                <i data-lucide="upload"></i>
                <span>Tải tệp lên</span>
            </button>
            <button type="button" onclick="fmTriggerUpload(true)">
                <i data-lucide="folder-up"></i>
                <span>Tải thư mục lên</span>
            </button>
        </div>
        <button type="button" class="fab-btn" id="fmFabBtn" onclick="fmToggleFabMenu(event)">
            <i data-lucide="plus"></i>
        </button>
    </div>

    <input type="file" id="fmUploadFilesInput" multiple style="display:none" onchange="fmHandleUpload(event, false)">

    <!-- Progress Modal -->
    <div id="fmProgressOverlay" class="progress-overlay">
        <div class="progress-modal">
            <div id="fmProgressTitle" class="progress-title">Đang tải lên...</div>
            <div class="progress-bar-container">
                <div id="fmProgressBar" class="progress-bar"></div>
            </div>
            <div class="progress-actions">
                <button id="fmProgressCancel" class="progress-btn">Hủy</button>
                <button id="fmProgressBackground" class="progress-btn primary" style="display:none;">Chạy nền</button>
            </div>
        </div>
    </div>

    <!-- Rename Modal -->
    <div id="fmRenameOverlay" class="rename-overlay">
        <div class="rename-modal">
            <div class="rename-header">
                <div class="rename-icon">📝</div>
                <div class="rename-title">Đổi tên</div>
            </div>
            <form class="rename-form" onsubmit="fmSubmitRename(event)">
                <div class="rename-field">
                    <label class="rename-label" for="fmRenameInput">Tên mới:</label>
                    <input type="text" id="fmRenameInput" class="rename-input" placeholder="Nhập tên mới..." required>
                    <div id="fmRenameError" class="rename-error" style="display:none;"></div>
                </div>
                <div class="rename-actions">
                    <button type="button" class="rename-btn secondary" onclick="fmHideRenameModal()">Hủy</button>
                    <button type="submit" class="rename-btn primary">Đổi tên</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Notification Container -->
    <div id="fmNotificationContainer" class="notification-container"></div>

    <!-- Upload Status Indicator - Simplified -->
    <div id="fmUploadStatusIndicator" style="display:none;position:fixed;bottom:80px;right:24px;
         background:white;border-radius:8px;padding:12px;box-shadow:0 6px 20px rgba(0,0,0,0.15);
         border:1px solid #e5e7eb;font-size:13px;z-index:1999;min-width:280px;max-width:320px;">
        
        <!-- Header với vành tròn, tên file và nút đóng cùng hàng -->
        <div style="display:flex;align-items:center;gap:12px;">
            <!-- Circular Progress -->
            <div style="position:relative;width:32px;height:32px;flex-shrink:0;">
                <svg width="32" height="32" style="transform:rotate(-90deg);">
                    <circle cx="16" cy="16" r="14" fill="none" stroke="#f3f4f6" stroke-width="3"/>
                    <circle id="fmProgressCircle" cx="16" cy="16" r="14" fill="none" stroke="#2563eb" stroke-width="3"
                            stroke-dasharray="87.96" stroke-dashoffset="87.96" 
                            style="transition:stroke-dashoffset 0.3s ease;"/>
                </svg>
                <div id="fmProgressPercent" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                     font-size:10px;font-weight:600;color:#2563eb;">0%</div>
            </div>
            
            <!-- File Info -->
            <div style="flex:1;min-width:0;">
                <div id="fmUploadFileName" style="font-weight:500;color:#1f2937;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                    Đang tải lên...
                </div>
                <div id="fmProgressText" style="font-size:12px;color:#6b7280;margin-top:2px;">Chuẩn bị...</div>
            </div>
            
            <!-- Action Buttons -->
            <div style="display:flex;gap:4px;flex-shrink:0;">
                <button onclick="fmMoveUploadToBackground()" 
                        style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:12px;padding:4px;border-radius:4px;"
                        onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'"
                        title="Ẩn thanh tiến trình">−</button>
                <button id="fmUploadCancelBtn" onclick="fmCancelCurrentUpload()" 
                        style="background:none;border:none;color:#6b7280;cursor:pointer;font-size:16px;padding:4px;border-radius:4px;line-height:1;"
                        onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'"
                        title="Hủy upload">×</button>
            </div>
        </div>
    </div>

    <script>
    let fmSelected = [];
    let fmLastIndex = null;
    let fmClipboard = null;
    const fmCurrentPath = {{ (cur_rel or '')|tojson }};
    let fmLastScrollYFab = 0;
    let fmScrollContainer = null;
    let fmCurrentUpload = null; // XMLHttpRequest instance hiện tại
    let fmUploadQueue = []; // Upload queue local

    function fmLoadClipboard() {
        try {
            const raw = localStorage.getItem('fmClipboard');
            if (!raw) {
                return null;
            }
            const parsed = JSON.parse(raw);
            if (!parsed || !Array.isArray(parsed.items) || !parsed.items.length) {
                return null;
            }
            if (parsed.mode !== 'copy' && parsed.mode !== 'cut') {
                return null;
            }
            return parsed;
        } catch (err) {
            console.warn('Failed to parse clipboard', err);
            return null;
        }
    }

    function fmSaveClipboard() {
        if (!fmClipboard || !Array.isArray(fmClipboard.items) || !fmClipboard.items.length) {
            localStorage.removeItem('fmClipboard');
            fmClipboard = null;
            return;
        }
        localStorage.setItem('fmClipboard', JSON.stringify(fmClipboard));
    }

    function fmMarkCutSources() {
        document.querySelectorAll('.item.cut-source').forEach(el => {
            el.classList.remove('cut-source');
        });
        if (!fmClipboard || fmClipboard.mode !== 'cut' || !Array.isArray(fmClipboard.items)) {
            return;
        }
        const marks = new Set(fmClipboard.items);
        document.querySelectorAll('.item[data-path]').forEach(el => {
            const path = el.dataset.path;
            if (path && marks.has(path)) {
                el.classList.add('cut-source');
            }
        });
    }

    function fmUpdateClipboardUI() {
        const pasteBtn = document.getElementById('fmPasteBtn');
        const hasClipboard = fmClipboard && Array.isArray(fmClipboard.items) && fmClipboard.items.length;
        if (pasteBtn) {
            pasteBtn.disabled = !hasClipboard;
            if (hasClipboard) {
                pasteBtn.title = fmClipboard.mode === 'cut'
                    ? 'Paste các mục đã cắt'
                    : 'Paste các mục đã copy';
            } else {
                pasteBtn.title = 'Clipboard trống';
            }
        }
        fmMarkCutSources();
    }

    function fmToggleFabMenu(event) {
        if (event) {
            event.stopPropagation();
        }
        const wrapper = document.getElementById('fmFabWrapper');
        if (!wrapper) return;
        wrapper.classList.toggle('fab-open');
    }

    function fmHideFabMenu() {
        const wrapper = document.getElementById('fmFabWrapper');
        if (!wrapper) return;
        wrapper.classList.remove('fab-open');
    }

    function fmHandleGlobalFabClick(event) {
        const wrapper = document.getElementById('fmFabWrapper');
        if (!wrapper) return;
        if (!wrapper.contains(event.target)) {
            fmHideFabMenu();
        }
    }

    function fmHandleFabScroll() {
        const wrapper = document.getElementById('fmFabWrapper');
        if (!wrapper || !fmScrollContainer) return;
        
        const current = fmScrollContainer.scrollTop || 0;
        const threshold = 20; // Tăng ngưỡng để tránh nhấp nháy
        
        // Ẩn khi cuộn xuống (current > last + threshold)
        if (current > fmLastScrollYFab + threshold) {
            wrapper.classList.add('fab-hidden');
            fmHideFabMenu();
        } 
        // Hiện khi cuộn lên (current < last - threshold) hoặc ở đầu trang
        else if (current < fmLastScrollYFab - threshold || current <= 50) {
            wrapper.classList.remove('fab-hidden');
        }
        
        fmLastScrollYFab = current;
    }

    // ===== PROGRESS & NOTIFICATION SYSTEM =====
    function fmShowProgress(title, canBackground = false) {
        const overlay = document.getElementById('fmProgressOverlay');
        const titleEl = document.getElementById('fmProgressTitle');
        const textEl = document.getElementById('fmProgressText');
        const barEl = document.getElementById('fmProgressBar');
        const backgroundBtn = document.getElementById('fmProgressBackground');
        
        if (overlay && titleEl && textEl && barEl) {
            titleEl.textContent = title;
            textEl.textContent = 'Chuẩn bị...';
            barEl.style.width = '0%';
            backgroundBtn.style.display = canBackground ? 'block' : 'none';
            overlay.style.display = 'flex';
        }
    }

    function fmUpdateProgress(percent, text, fileName) {
        // Update modal progress
        const textEl = document.getElementById('fmProgressText');
        const barEl = document.getElementById('fmProgressBar');
        
        if (textEl && barEl) {
            textEl.textContent = text || `${Math.round(percent)}%`;
            barEl.style.width = `${Math.min(100, Math.max(0, percent))}%`;
        }
        
        // Update compact status indicator
        fmUpdateStatusIndicator(percent, text, fileName);
    }

    function fmUpdateStatusIndicator(percent, text, fileName) {
        const indicator = document.getElementById('fmUploadStatusIndicator');
        const fileNameEl = document.getElementById('fmUploadFileName');
        const progressText = document.getElementById('fmProgressText');
        const progressPercent = document.getElementById('fmProgressPercent');
        const progressCircle = document.getElementById('fmProgressCircle');
        
        if (!indicator) return;
        
        // Show indicator
        indicator.style.display = 'block';
        
        // Update file name
        if (fileNameEl && fileName) {
            fileNameEl.textContent = fileName;
            fileNameEl.title = fileName; // Tooltip for full name
        }
        
        // Update progress text
        if (progressText) {
            progressText.textContent = text || `${Math.round(percent)}%`;
        }
        
        // Update percentage
        if (progressPercent) {
            progressPercent.textContent = `${Math.round(percent)}%`;
        }
        
        // Update circular progress
        if (progressCircle) {
            const circumference = 87.96; // 2 * π * 14
            const offset = circumference - (percent / 100) * circumference;
            progressCircle.style.strokeDashoffset = offset;
        }
    }

    function fmHideStatusIndicator() {
        const indicator = document.getElementById('fmUploadStatusIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    function fmHideProgress() {
        const overlay = document.getElementById('fmProgressOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    function showToast(message, type = 'info', title = '', duration = 5000) {
        const container = document.getElementById('fmNotificationContainer');
        if (!container) return;

        // Icon mapping
        const icons = {
            success: '✅',
            error: '❌', 
            warning: '⚠️',
            info: 'ℹ️'
        };

        // Title mapping nếu không có title
        const defaultTitles = {
            success: 'Thành công',
            error: 'Lỗi',
            warning: 'Cảnh báo', 
            info: 'Thông tin'
        };

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const actualTitle = title || defaultTitles[type] || 'Thông báo';
        
        notification.innerHTML = `
            <div class="notification-icon">${icons[type] || 'ℹ️'}</div>
            <div class="notification-content">
                <div class="notification-title">${actualTitle}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="fmRemoveToast(this.parentElement)">×</button>
        `;

        // Click để đóng
        notification.addEventListener('click', () => {
            fmRemoveToast(notification);
        });

        container.appendChild(notification);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                fmRemoveToast(notification);
            }, duration);
        }

        return notification;
    }

    function fmRemoveToast(notification) {
        if (!notification || !notification.parentElement) return;
        
        notification.classList.add('removing');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }

    // Alias cho backward compatibility
    function fmShowNotification(message, type = 'info', duration = 5000) {
        return showToast(message, type, '', duration);
    }

    // ===== UPLOAD SYSTEM =====

    function fmSaveUploadQueue() {
        try {
            localStorage.setItem('fmUploadQueue', JSON.stringify(fmUploadQueue));
        } catch (e) {
            console.error('Cannot save upload queue:', e);
        }
    }

    function fmRestoreUploadQueue() {
        try {
            const saved = localStorage.getItem('fmUploadQueue');
            if (saved) {
                const savedQueue = JSON.parse(saved);
                
                // Dọn dẹp queue - chỉ giữ lại upload thực sự đang pending/uploading
                // Loại bỏ upload cũ (> 1 giờ) hoặc đã completed/failed
                const now = Date.now();
                const oneHour = 60 * 60 * 1000;
                
                fmUploadQueue = savedQueue.filter(upload => {
                    // Loại bỏ upload cũ
                    if (now - upload.timestamp > oneHour) {
                        return false;
                    }
                    
                    // Chỉ giữ upload đang pending hoặc uploading
                    return upload.status === 'pending' || upload.status === 'uploading';
                });
                
                // Lưu lại queue đã được dọn dẹp
                fmSaveUploadQueue();
                
                // Không hiển thị thông báo nữa - chỉ cập nhật indicator
                fmUpdateQueueIndicator();
            }
        } catch (e) {
            console.error('Cannot restore upload queue:', e);
            fmUploadQueue = [];
            localStorage.removeItem('fmUploadQueue');
        }
    }

    function fmRemoveFromQueue(uploadId) {
        const beforeLength = fmUploadQueue.length;
        fmUploadQueue = fmUploadQueue.filter(u => u.id !== uploadId);
        
        // Chỉ cập nhật nếu thực sự có thay đổi
        if (fmUploadQueue.length !== beforeLength) {
            fmSaveUploadQueue();
            fmUpdateQueueIndicator();
            
            // Nếu không còn upload nào, ẩn status indicator
            if (fmUploadQueue.length === 0) {
                fmHideStatusIndicator();
            }
        }
    }

    function fmClearCompletedUploads() {
        const beforeLength = fmUploadQueue.length;
        fmUploadQueue = fmUploadQueue.filter(u => u.status === 'pending' || u.status === 'uploading');
        
        if (fmUploadQueue.length !== beforeLength) {
            fmSaveUploadQueue();
            fmUpdateQueueIndicator();
        }
    }

    function fmGenerateUploadId() {
        return 'upload_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function fmMoveUploadToBackground() {
        // Đơn giản: chỉ ẩn status indicator, upload vẫn tiếp tục
        // Lưu ý: upload sẽ bị hủy nếu reload/đóng trang
        fmHideStatusIndicator();
        fmShowNotification('Đã ẩn thanh tiến trình. Upload vẫn tiếp tục.', 'info');
    }

    function fmCancelCurrentUpload() {
        if (fmCurrentUpload) {
            // XMLHttpRequest có method abort()
            fmCurrentUpload.abort();
            fmCurrentUpload = null;
        }
        
        fmHideStatusIndicator();
        
        // Xóa upload đang chạy khỏi queue
        const uploadingItems = fmUploadQueue.filter(u => u.status === 'uploading');
        uploadingItems.forEach(item => {
            item.status = 'cancelled';
            fmRemoveFromQueue(item.id);
        });
        
        fmShowNotification('Upload đã bị hủy', 'warning');
    }


    async function fmUploadWithBackground(files, destination) {
        const uploadId = fmGenerateUploadId();
        
        // Thêm vào queue local
        const uploadItem = {
            id: uploadId,
            files: Array.from(files).map(f => ({
                name: f.name,
                size: f.size,
                type: f.type,
                relativePath: f.webkitRelativePath || f.relativePath || f.name
            })),
            destination: destination,
            status: 'pending', // Bắt đầu với pending, sẽ chuyển thành uploading khi bắt đầu
            progress: 0,
            timestamp: Date.now()
        };
        
        fmUploadQueue.push(uploadItem);
        fmSaveUploadQueue();
        fmUpdateQueueIndicator();

        // Upload với XMLHttpRequest (có progress tracking)
        return fmUploadWithXHR(files, destination, uploadId);
    }

    function fmUploadWithXHR(files, destination, uploadId) {
        const totalSize = Array.from(files).reduce((sum, file) => sum + file.size, 0);
        const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(1);
        const fileArray = Array.from(files);
        
        // Tạo tên hiển thị
        let displayName;
        if (fileArray.length === 1) {
            const fileName = fileArray[0].name;
            // Rút gọn tên file dài
            if (fileName.length > 30) {
                const ext = fileName.substring(fileName.lastIndexOf('.'));
                const name = fileName.substring(0, fileName.lastIndexOf('.'));
                displayName = name.substring(0, 20) + '...' + ext;
            } else {
                displayName = fileName;
            }
        } else {
            // Kiểm tra xem có phải upload thư mục không
            const isFolder = fileArray.some(f => f.webkitRelativePath && f.webkitRelativePath.includes('/'));
            if (isFolder) {
                // Lấy tên thư mục từ webkitRelativePath
                const folderPath = fileArray[0].webkitRelativePath;
                const folderName = folderPath.split('/')[0];
                displayName = `📁 ${folderName} (${fileArray.length} files)`;
            } else {
                displayName = `${fileArray.length} files (${totalSizeMB}MB)`;
            }
        }
        
        // Chỉ sử dụng status indicator nhỏ, không cần progress modal lớn
        fmUpdateStatusIndicator(0, 'Chuẩn bị...', displayName);

        const formData = new FormData();
        formData.append('destination', destination);
        fileArray.forEach(file => {
            const rel = file.webkitRelativePath || file.relativePath || file.name;
            formData.append('files', file, rel || file.name);
        });

        return new Promise((resolve, reject) => {
            // Tạo XMLHttpRequest với AbortController
            const xhr = new XMLHttpRequest();
            fmCurrentUpload = xhr;
            
            // Đánh dấu upload đang bắt đầu
            const queueItem = fmUploadQueue.find(u => u.id === uploadId);
            if (queueItem) {
                queueItem.status = 'uploading';
                fmSaveUploadQueue();
            }

            // Progress tracking - QUAN TRỌNG: chỉ XMLHttpRequest mới có
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = (e.loaded / e.total) * 100;
                    const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
                    const text = `Đã tải: ${loadedMB}MB / ${totalSizeMB}MB`;
                    
                    fmUpdateProgress(percent, text, displayName);
                    
                    // Cập nhật progress trong queue
                    if (queueItem) {
                        queueItem.progress = percent;
                        fmSaveUploadQueue();
                    }
                }
            });

            // Upload completed
            xhr.addEventListener('load', () => {
                fmCurrentUpload = null;
                fmHideStatusIndicator();
                
                try {
                    const data = JSON.parse(xhr.responseText);
                    
                    if (xhr.status === 200 && data.success !== false) {
                        // Đánh dấu hoàn thành
                        if (queueItem) {
                            queueItem.status = 'completed';
                            queueItem.progress = 100;
                        }
                        
                        fmShowNotification(data.message || `Đã tải lên thành công ${fileArray.length} file`, 'success');
                        fmRemoveFromQueue(uploadId);
                        
                        if (data.needs_refresh) {
                            setTimeout(() => window.location.reload(), 1000);
                        }
                        resolve(data);
                    } else {
                        // Upload thất bại
                        if (queueItem) {
                            queueItem.status = 'failed';
                        }
                        fmShowNotification(data.message || "Không thể tải lên.", 'error');
                        fmRemoveFromQueue(uploadId);
                        reject(new Error(data.message || 'Upload failed'));
                    }
                } catch (err) {
                    fmShowNotification("Lỗi xử lý phản hồi từ server", 'error');
                    fmRemoveFromQueue(uploadId);
                    reject(err);
                }
            });

            // Upload error
            xhr.addEventListener('error', () => {
                fmCurrentUpload = null;
                fmHideStatusIndicator();
                
                if (queueItem) {
                    queueItem.status = 'failed';
                }
                fmShowNotification("Lỗi kết nối khi tải lên", 'error');
                fmRemoveFromQueue(uploadId);
                reject(new Error('Network error'));
            });

            // Upload aborted
            xhr.addEventListener('abort', () => {
                fmCurrentUpload = null;
                fmHideStatusIndicator();
                
                if (queueItem) {
                    queueItem.status = 'cancelled';
                }
                fmShowNotification("Upload đã bị hủy", 'warning');
                fmRemoveFromQueue(uploadId);
                // Không reject vì đây là hành động có chủ ý
            });

            // Bắt đầu upload
            xhr.open('POST', '/api/files/upload');
            xhr.send(formData);
        });
    }


    function fmUpdateQueueIndicator() {
        // Dọn dẹp queue trước khi kiểm tra
        fmClearCompletedUploads();
        
        const activeUploads = fmUploadQueue.filter(u => u.status === 'pending' || u.status === 'uploading');
        
        if (activeUploads.length === 0) {
            fmHideStatusIndicator();
        } else {
            // Chỉ hiển thị nếu thực sự có upload đang chạy
            const currentUpload = activeUploads[0];
            if (currentUpload && fmCurrentUpload) {
                // Có upload đang chạy, status indicator sẽ được cập nhật bởi fmUpdateStatusIndicator
            } else {
                // Không có upload đang chạy thực tế, ẩn indicator
                fmHideStatusIndicator();
            }
        }
    }


    function fmHandlePageUnload(event) {
        // Khi trang sắp đóng, thông báo user nếu có upload đang chạy
        const activeUploads = fmUploadQueue.filter(u => u.status === 'uploading' || u.status === 'pending');
        
        if (activeUploads.length > 0) {
            // Với fetch + keepalive, upload sẽ tiếp tục
            // Không cần preventDefault vì keepalive đã xử lý
            console.log(`${activeUploads.length} uploads will continue in background`);
        }
    }

    async function fmPromptNewFolder() {
        fmHideFabMenu();
        let name = prompt("Tên thư mục mới", "New folder");
        if (!name) {
            return;
        }
        name = name.trim();
        if (!name) {
            return;
        }
        try {
            const resp = await fetch('/api/files/mkdir', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    destination: fmCurrentPath || "",
                    name: name
                })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || data.success === false) {
                showToast(data.message || "Không thể tạo thư mục mới.", 'error');
                return;
            }
            window.location.reload();
        } catch (err) {
            showToast("Lỗi khi tạo thư mục: " + err.message, 'error');
        }
    }

    function fmTriggerUpload(isFolder) {
        fmHideFabMenu();
        
        if (isFolder) {
            // Tạo input element mới để tránh popup
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            
            // Thử các cách khác nhau để set webkitdirectory
            try {
                input.webkitdirectory = true;
            } catch (e) {
                input.setAttribute('webkitdirectory', '');
            }
            
            input.style.display = 'none';
            input.style.position = 'absolute';
            input.style.left = '-9999px';
            
            input.addEventListener('change', (event) => {
                fmHandleUpload(event, true);
                // Delay xóa để tránh lỗi
                setTimeout(() => {
                    if (input.parentNode) {
                        document.body.removeChild(input);
                    }
                }, 100);
            });
            
            document.body.appendChild(input);
            
            // Thông báo cho user về popup có thể xuất hiện
            fmShowNotification('Chọn thư mục để tải lên. Browser có thể hiển thị popup xác nhận.', 'info', 3000);
            
            // Trigger click trong user gesture context
            setTimeout(() => input.click(), 0);
        } else {
            const input = document.getElementById('fmUploadFilesInput');
            if (!input) return;
            input.value = "";
            input.click();
        }
    }

    async function fmHandleUpload(event, isFolder) {
        const input = event.target;
        const files = Array.from(input.files || []);
        if (!files.length) {
            input.value = "";
            return;
        }

        try {
            await fmUploadWithBackground(files, fmCurrentPath || "");
        } catch (error) {
            console.error('Upload error:', error);
            fmShowNotification('Upload thất bại: ' + error.message, 'error');
        } finally {
            input.value = "";
        }
    }

    function fmCopySelected(mode) {
        if (!fmSelected.length) {
            showToast("Chưa chọn file hoặc thư mục nào", 'warning');
            return;
        }
        const normalizedMode = mode === 'cut' ? 'cut' : 'copy';
        fmClipboard = {
            mode: normalizedMode,
            items: [...fmSelected],
            ts: Date.now()
        };
        fmSaveClipboard();
        fmUpdateClipboardUI();
    }

    function fmHandlePasteResult(data) {
        if (!fmClipboard || fmClipboard.mode !== 'cut') return;
        if (!data || !Array.isArray(data.done) || !data.done.length) return;
        const doneSources = data.done.map(entry => entry.source);
        fmClipboard.items = fmClipboard.items.filter(item => !doneSources.includes(item));
        if (!fmClipboard.items.length) {
            fmClipboard = null;
        }
    }

    async function fmPasteClipboard() {
        if (!fmClipboard || !fmClipboard.items || !fmClipboard.items.length) {
            showToast("Clipboard trống.", 'info');
            return;
        }
        const payload = {
            mode: fmClipboard.mode,
            items: fmClipboard.items,
            destination: fmCurrentPath || ""
        };
        const pasteBtn = document.getElementById('fmPasteBtn');
        if (pasteBtn) {
            pasteBtn.disabled = true;
        }
        try {
            const resp = await fetch('/api/files/paste', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await resp.json().catch(() => ({}));
            const shouldRefresh = !!(data && data.needs_refresh);
            const hasError = !resp.ok || data.success === false;
            fmHandlePasteResult(data);
            fmSaveClipboard();
            if (hasError) {
                showToast(data.message || "Không thể paste các mục đã chọn.", 'error');
                if (shouldRefresh) {
                    window.location.reload();
                }
                return;
            }
            if (shouldRefresh) {
                window.location.reload();
            }
        } catch (err) {
            showToast("Lỗi khi paste: " + err.message, 'error');
        } finally {
            fmUpdateClipboardUI();
        }
    }

    function fmRenameSelected() {
        if (!fmSelected.length) {
            showToast("Chưa chọn file hoặc thư mục nào", 'warning');
            return;
        }
        if (fmSelected.length > 1) {
            showToast("Chỉ có thể đổi tên một mục tại một thời điểm", 'warning');
            return;
        }
        
        const selectedPath = fmSelected[0];
        const fileName = selectedPath.split('/').pop() || selectedPath;
        
        fmShowRenameModal(selectedPath, fileName);
    }

    function fmShowRenameModal(path, currentName) {
        const overlay = document.getElementById('fmRenameOverlay');
        const input = document.getElementById('fmRenameInput');
        const error = document.getElementById('fmRenameError');
        
        if (!overlay || !input) return;
        
        // Reset form
        input.value = currentName;
        input.classList.remove('error');
        error.style.display = 'none';
        
        // Store current path for submission
        overlay.dataset.currentPath = path;
        
        // Show modal
        overlay.classList.add('show');
        
        // Focus and select filename (without extension)
        setTimeout(() => {
            input.focus();
            const lastDotIndex = currentName.lastIndexOf('.');
            if (lastDotIndex > 0) {
                input.setSelectionRange(0, lastDotIndex);
            } else {
                input.select();
            }
        }, 100);
    }

    function fmHideRenameModal() {
        const overlay = document.getElementById('fmRenameOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }

    // Keyboard shortcuts for rename modal
    document.addEventListener('keydown', function(e) {
        const overlay = document.getElementById('fmRenameOverlay');
        
        // F2 to rename selected item
        if (e.key === 'F2' && !overlay.classList.contains('show')) {
            e.preventDefault();
            fmRenameSelected();
            return;
        }
        
        // Escape to close modal
        if (overlay.classList.contains('show') && e.key === 'Escape') {
            e.preventDefault();
            fmHideRenameModal();
        }
    });

    // Click outside to close
    document.addEventListener('click', function(e) {
        const overlay = document.getElementById('fmRenameOverlay');
        if (!overlay || !overlay.classList.contains('show')) return;
        
        if (e.target === overlay) {
            fmHideRenameModal();
        }
    });

    // Keyboard shortcut để đóng preview overlay
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const previewOverlay = document.getElementById("fmOverlay");
            if (previewOverlay && previewOverlay.style.display === 'flex') {
                e.preventDefault();
                fmHidePreview();
            }
        }
    });

    function fmValidateFileName(name) {
        if (!name || name.trim() === '') {
            return 'Tên không được để trống';
        }
        
        const trimmed = name.trim();
        
        // Kiểm tra ký tự không hợp lệ
        const invalidChars = /[<>:"/\\|?*\x00-\x1f]/;
        if (invalidChars.test(trimmed)) {
            return 'Tên chứa ký tự không hợp lệ';
        }
        
        // Kiểm tra tên reserved (Windows)
        const reserved = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)/i;
        if (reserved.test(trimmed)) {
            return 'Tên này không được phép sử dụng';
        }
        
        // Kiểm tra độ dài
        if (trimmed.length > 255) {
            return 'Tên quá dài (tối đa 255 ký tự)';
        }
        
        return null;
    }

    async function fmSubmitRename(event) {
        event.preventDefault();
        
        const overlay = document.getElementById('fmRenameOverlay');
        const input = document.getElementById('fmRenameInput');
        const error = document.getElementById('fmRenameError');
        const submitBtn = event.target.querySelector('button[type="submit"]');
        
        if (!overlay || !input || !submitBtn) return;
        
        const currentPath = overlay.dataset.currentPath;
        const newName = input.value.trim();
        
        // Validate
        const validationError = fmValidateFileName(newName);
        if (validationError) {
            input.classList.add('error');
            error.textContent = validationError;
            error.style.display = 'block';
            return;
        }
        
        // Clear error
        input.classList.remove('error');
        error.style.display = 'none';
        
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang đổi tên...';
        
        try {
            console.log('Rename request:', { currentPath, newName });
            
            const resp = await fetch('/api/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_path: currentPath,
                    new_name: newName
                })
            });
            
            const data = await resp.json().catch(() => ({}));
            
            if (!resp.ok || data.success === false) {
                throw new Error(data.message || 'Không thể đổi tên');
            }
            
            showToast(`Đã đổi tên thành "${newName}"`, 'success', 'Đổi tên thành công');
            fmHideRenameModal();
            
            // Refresh page
            setTimeout(() => window.location.reload(), 500);
            
        } catch (err) {
            input.classList.add('error');
            error.textContent = err.message;
            error.style.display = 'block';
            showToast('Lỗi khi đổi tên: ' + err.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Đổi tên';
        }
    }

    // Update selection UI to enable/disable rename button
    function fmUpdateRenameButton() {
        const renameBtn = document.getElementById('fmRenameBtn');
        if (renameBtn) {
            renameBtn.disabled = fmSelected.length !== 1;
            renameBtn.title = fmSelected.length === 1 
                ? 'Đổi tên mục đã chọn'
                : fmSelected.length === 0 
                    ? 'Chưa chọn mục nào'
                    : 'Chỉ có thể đổi tên một mục';
        }
    }

    async function fmDeleteSelected() {
        if (!fmSelected.length) {
            showToast("Chưa chọn file hoặc thư mục nào", 'warning');
            return;
        }
        try {
            const resp = await fetch('/api/files/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({paths: fmSelected})
            });
            const data = await resp.json().catch(() => ({}));
            const shouldRefresh = !!(data && data.needs_refresh);
            if (!resp.ok || data.success === false) {
                showToast(data.message || "Không thể xóa các mục đã chọn.", 'error');
                if (shouldRefresh) {
                    window.location.reload();
                }
            } else {
                window.location.reload();
            }
        } catch (err) {
            showToast("Lỗi khi xóa: " + err.message, 'error');
        }
    }

    function fmClearSelection() {
        fmSelected = [];
        document.querySelectorAll('.item[data-path]').forEach(el => {
            el.classList.remove('selected');
        });
        fmUpdateStatus();
        fmShowDetail(null);
    }

    function fmSelectRange(startIndex, endIndex) {
        const items = Array.from(document.querySelectorAll('.item[data-path]'));
        if (startIndex > endIndex) {
            [startIndex, endIndex] = [endIndex, startIndex];
        }
        fmClearSelection();
        for (let i = startIndex; i <= endIndex; i++) {
            const el = items[i];
            if (!el) continue;
            const p = el.dataset.path;
            if (!p) continue;
            if (!fmSelected.includes(p)) fmSelected.push(p);
            el.classList.add('selected');
        }
        if (items[startIndex]) fmShowDetail(items[startIndex]);
        fmUpdateStatus();
    }

    function fmHandleClick(ev, el) {
        const items = Array.from(document.querySelectorAll('.item[data-path]'));
        const idx = items.indexOf(el);
        const isCtrl = ev.ctrlKey || ev.metaKey;
        const isShift = ev.shiftKey;

        if (isShift && fmLastIndex !== null) {
            fmSelectRange(fmLastIndex, idx);
            return;
        }

        const path = el.dataset.path;
        if (!path) return;

        if (!isCtrl) {
            fmClearSelection();
        }

        const existed = fmSelected.indexOf(path);
        if (existed >= 0 && isCtrl) {
            fmSelected.splice(existed, 1);
            el.classList.remove('selected');
            fmShowDetail(null);
        } else {
            if (!fmSelected.includes(path)) fmSelected.push(path);
            el.classList.add('selected');
            fmShowDetail(el);
        }

        fmLastIndex = idx;
        fmUpdateStatus();
    }

    function fmHandleDblClick(ev, el) {
        const path = el.dataset.path;
        const isDir = el.dataset.isDir === "1";
        if (!path) return;

        if (isDir) {
            const url = new URL(window.location.href);
            url.searchParams.set("path", path);
            window.location.href = url.toString();
        } else {
            const mime = el.dataset.mime || "";
            fmShowPreview(path, mime);
        }
    }

    function fmShowPreview(path, mime) {
        const overlay = document.getElementById("fmOverlay");
        const body = document.getElementById("fmOverlayBody");
        const link = document.getElementById("fmOverlayDownload");

        if (!overlay || !body || !link) {
            window.open("/file?path=" + encodeURIComponent(path), "_blank");
            return;
        }

        // Đặc biệt cho PDF - sử dụng overlay lớn
        const isPDF = mime === "application/pdf";
        const container = overlay.querySelector('div[style*="position:relative"]');
        
        if (isPDF && container) {
            // Overlay lớn cho PDF
            container.style.width = "96vw";
            container.style.height = "96vh";
            body.style.height = "calc(100% - 60px)";
        } else if (container) {
            // Overlay nhỏ cho các file khác
            container.style.width = "";
            container.style.height = "";
            container.style.maxWidth = "95%";
            container.style.maxHeight = "90%";
            body.style.height = "";
        }

        link.href = "/file?path=" + encodeURIComponent(path) + "&download=1";

        let html = "";
        const fileName = path.split('/').pop().toLowerCase();
        
        if (mime.startsWith("image/")) {
            html = '<img src="/file?path=' + encodeURIComponent(path) +
                   '" style="max-width:100%;max-height:80vh;">';
        } else if (mime.startsWith("video/")) {
            html = '<video src="/file?path=' + encodeURIComponent(path) +
                   '" controls autoplay style="max-width:100%;max-height:80vh;"></video>';
        } else if (mime.startsWith("audio/")) {
            html = '<div style="text-align:center;padding:40px;">' +
                   '<div style="font-size:48px;margin-bottom:20px;">🎵</div>' +
                   '<h3 style="margin-bottom:20px;">' + fileName + '</h3>' +
                   '<audio src="/file?path=' + encodeURIComponent(path) +
                   '" controls autoplay style="width:100%;max-width:400px;"></audio></div>';
        } else if (mime === "application/pdf") {
            html = '<iframe src="/file?path=' + encodeURIComponent(path) +
                   '" style="width:100%;height:100%;border:none;background:white;"></iframe>';
        } else if (mime.startsWith("text/") || 
                   fileName.endsWith('.txt') || fileName.endsWith('.md') || 
                   fileName.endsWith('.json') || fileName.endsWith('.xml') ||
                   fileName.endsWith('.csv') || fileName.endsWith('.log') ||
                   fileName.endsWith('.js') || fileName.endsWith('.css') ||
                   fileName.endsWith('.html') || fileName.endsWith('.py') ||
                   fileName.endsWith('.php') || fileName.endsWith('.java') ||
                   fileName.endsWith('.cpp') || fileName.endsWith('.c') ||
                   fileName.endsWith('.h') || fileName.endsWith('.sh') ||
                   fileName.endsWith('.bat') || fileName.endsWith('.yml') ||
                   fileName.endsWith('.yaml') || fileName.endsWith('.ini') ||
                   fileName.endsWith('.conf') || fileName.endsWith('.cfg')) {
            html = '<div style="height:80vh;overflow:auto;background:#f8f9fa;border-radius:8px;">' +
                   '<pre id="fmTextPreview" style="padding:20px;margin:0;font-family:\'Courier New\',monospace;font-size:14px;line-height:1.5;white-space:pre-wrap;text-align:left;"></pre></div>';
            
            // Load text content
            fetch('/file?path=' + encodeURIComponent(path))
                .then(response => response.text())
                .then(text => {
                    const preview = document.getElementById('fmTextPreview');
                    if (preview) {
                        // Limit text length for performance
                        if (text.length > 50000) {
                            text = text.substring(0, 50000) + '\n\n... (File quá lớn, chỉ hiển thị 50KB đầu)';
                        }
                        preview.textContent = text;
                    }
                })
                .catch(err => {
                    const preview = document.getElementById('fmTextPreview');
                    if (preview) {
                        preview.textContent = 'Không thể tải nội dung file: ' + err.message;
                    }
                });
        } else if (fileName.endsWith('.docx') || fileName.endsWith('.doc') ||
                   fileName.endsWith('.xlsx') || fileName.endsWith('.xls') ||
                   fileName.endsWith('.pptx') || fileName.endsWith('.ppt')) {
            html = '<div style="text-align:center;padding:60px;">' +
                   '<div style="font-size:64px;margin-bottom:20px;">📄</div>' +
                   '<h3 style="margin-bottom:10px;">' + fileName + '</h3>' +
                   '<p style="color:#666;margin-bottom:30px;">File Office - Không thể xem trước</p>' +
                   '<a href="/file?path=' + encodeURIComponent(path) + 
                   '" target="_blank" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Tải xuống để xem</a></div>';
        } else if (fileName.endsWith('.zip') || fileName.endsWith('.rar') ||
                   fileName.endsWith('.7z') || fileName.endsWith('.tar') ||
                   fileName.endsWith('.gz') || fileName.endsWith('.bz2')) {
            html = '<div style="text-align:center;padding:60px;">' +
                   '<div style="font-size:64px;margin-bottom:20px;">📦</div>' +
                   '<h3 style="margin-bottom:10px;">' + fileName + '</h3>' +
                   '<p style="color:#666;margin-bottom:30px;">File nén - Không thể xem trước</p>' +
                   '<a href="/file?path=' + encodeURIComponent(path) + 
                   '" target="_blank" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Tải xuống</a></div>';
        } else {
            html = '<div style="text-align:center;padding:60px;">' +
                   '<div style="font-size:64px;margin-bottom:20px;">📄</div>' +
                   '<h3 style="margin-bottom:10px;">' + fileName + '</h3>' +
                   '<p style="color:#666;margin-bottom:30px;">Không thể xem trước loại file này</p>' +
                   '<a href="/file?path=' + encodeURIComponent(path) + 
                   '" target="_blank" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Mở trong tab mới</a></div>';
        }

        body.innerHTML = html;
        overlay.style.display = "flex";
    }

    function fmHidePreview() {
        const overlay = document.getElementById("fmOverlay");
        if (overlay) {
            // Dừng tất cả video và audio trong overlay
            const videos = overlay.querySelectorAll('video');
            const audios = overlay.querySelectorAll('audio');
            
            videos.forEach(video => {
                video.pause();
                video.currentTime = 0; // Reset về đầu
            });
            
            audios.forEach(audio => {
                audio.pause();
                audio.currentTime = 0; // Reset về đầu
            });
            
            overlay.style.display = "none";
        }
    }

    function fmDownloadSelected() {
        if (!fmSelected.length) {
            showToast("Chưa chọn file hoặc thư mục nào", 'warning');
            return;
        }
        
        // Kiểm tra xem tất cả có phải là file ảnh/video không
        let allMediaFiles = true;
        const mediaFiles = [];
        const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];
        const videoExts = ['.mp4', '.mkv', '.avi', '.mov', '.3gp', '.webm'];
        
        for (const path of fmSelected) {
            const item = document.querySelector(`.item[data-path="${path}"]`);
            if (!item) {
                allMediaFiles = false;
                break;
            }
            
            const isDir = item.dataset.isDir === "1";
            if (isDir) {
                allMediaFiles = false;
                break;
            }
            
            const mime = item.dataset.mime || "";
            const name = item.dataset.name || "";
            const ext = name.substring(name.lastIndexOf('.')).toLowerCase();
            
            if (mime.startsWith("image/") || mime.startsWith("video/") || 
                imageExts.includes(ext) || videoExts.includes(ext)) {
                mediaFiles.push(path);
            } else {
                allMediaFiles = false;
                break;
            }
        }
        
        // Nếu tất cả đều là file ảnh/video và có nhiều hơn 1 file -> download từng file với delay
        if (allMediaFiles && mediaFiles.length > 1) {
            fmShowNotification(`Đang tải xuống ${mediaFiles.length} file media...`, 'info');
            
            let index = 0;
            function downloadNext() {
                if (index >= mediaFiles.length) {
                    fmShowNotification('Hoàn tất tải xuống tất cả file media', 'success');
                    return;
                }
                
                const path = mediaFiles[index];
                const link = document.createElement('a');
                link.href = '/file?path=' + encodeURIComponent(path) + '&download=1';
                link.style.display = 'none';
                link.download = ''; // Thêm attribute download để tránh popup
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                index++;
                // Tăng delay để tránh popup browser
                if (index < mediaFiles.length) {
                    setTimeout(downloadNext, 1200); // Delay 1.2s giữa các download
                }
            }
            downloadNext();
            return;
        }
        
        // Các trường hợp khác: submit form như cũ
        // Hiển thị progress nếu có nhiều file cần zip
        if (fmSelected.length > 3) {
            fmShowProgress(`Đang chuẩn bị tải xuống ${fmSelected.length} mục...`, false);
            fmUpdateProgress(30, 'Đang nén file...');
            
            setTimeout(() => {
                const input = document.getElementById("fmDownloadPaths");
                input.value = fmSelected.join("|");
                document.getElementById("fmDownloadForm").submit();
                
                setTimeout(() => {
                    fmHideProgress();
                    fmShowNotification('Tải xuống đã bắt đầu. File sẽ được tải về khi hoàn tất.', 'success');
                }, 1500);
            }, 800);
        } else {
            const input = document.getElementById("fmDownloadPaths");
            input.value = fmSelected.join("|");
            document.getElementById("fmDownloadForm").submit();
        }
    }

    // Cập nhật status bar
    function fmUpdateStatus() {
        const status = document.getElementById("fmStatus");
        if (!status) return;
        const total = document.querySelectorAll('.item[data-path]').length;
        const selected = fmSelected.length;
        let text = total + " item" + (total !== 1 ? "s" : "");
        if (selected) {
            text += " | " + selected + " selected";
        }
        status.textContent = text;
        
        // Update rename button state
        fmUpdateRenameButton();
    }

    // Hiện detail bên phải
    function fmShowDetail(el) {
        const panel = document.getElementById("fmDetail");
        if (!panel) return;
        if (!el) {
            panel.innerHTML = '<div class="detail-block">' +
                '<div class="detail-label">Tip</div>' +
                '<div class="detail-value">Chọn một file hoặc thư mục để xem thông tin.</div>' +
                '</div>';
            return;
        }
        const name = el.dataset.name || "";
        const info = el.dataset.info || "";
        const path = el.dataset.path || "";
        const mime = el.dataset.mime || "";
        const isDir = el.dataset.isDir === "1";

        panel.innerHTML = ''
          + '<div class="detail-block">'
          + '  <div class="detail-label">Name</div>'
          + '  <div class="detail-value">' + name + '</div>'
          + '</div>'
          + '<div class="detail-block">'
          + '  <div class="detail-label">Type</div>'
          + '  <div class="detail-value">'
          + (isDir ? 'Folder' : (mime || 'File'))
          + '  </div>'
          + '</div>'
          + '<div class="detail-block">'
          + '  <div class="detail-label">Info</div>'
          + '  <div class="detail-value">' + info + '</div>'
          + '</div>'
          + '<div class="detail-block">'
          + '  <div class="detail-label">Path</div>'
          + '  <div class="detail-value">/storage/' + path + '</div>'
          + '</div>';
    }

    // Hover video: chỉ cho 1 video chạy (grid view)
    (function () {
        let currentHoverVideo = null;
        const videos = document.querySelectorAll('.thumb video');

        videos.forEach(v => {
            if (!v.classList.contains('fm-lazy-media')) {
                v.preload = "none";
            }
            v.addEventListener('mouseenter', () => {
                if (currentHoverVideo && currentHoverVideo !== v) {
                    currentHoverVideo.pause();
                    currentHoverVideo.currentTime = 0;
                }
                currentHoverVideo = v;
                v.play().catch(() => {});
            });

            v.addEventListener('mouseleave', () => {
                v.pause();
                v.currentTime = 0;
                if (currentHoverVideo === v) {
                    currentHoverVideo = null;
                }
            });
        });
    })();

    function fmLoadMedia(el) {
        if (!el || !el.dataset.src) return;
        el.src = el.dataset.src;
        el.removeAttribute('data-src');
        if (el.tagName === 'VIDEO') {
            try { el.load(); } catch (err) {}
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const lazyMedia = document.querySelectorAll('.fm-lazy-media[data-src]');
        if (!lazyMedia.length) return;

        if (!('IntersectionObserver' in window)) {
            lazyMedia.forEach(el => fmLoadMedia(el));
            return;
        }

        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    fmLoadMedia(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, {
            root: null,
            rootMargin: '120px',
            threshold: 0.1
        });

        lazyMedia.forEach(el => observer.observe(el));
    });

    document.addEventListener('DOMContentLoaded', function () {
        fmClipboard = fmLoadClipboard();
        fmUpdateClipboardUI();
        document.addEventListener('click', fmHandleGlobalFabClick);
        
        // Khôi phục upload queue từ localStorage
        fmRestoreUploadQueue();
        
        // Đảm bảo upload tiếp tục khi trang sắp đóng
        window.addEventListener('beforeunload', fmHandlePageUnload);
        
        // Dọn dẹp queue định kỳ mỗi 30 giây
        setInterval(fmClearCompletedUploads, 30000);
        
        // Tìm container cuộn đúng (.items) thay vì window
        fmScrollContainer = document.querySelector('.items');
        if (fmScrollContainer) {
            fmLastScrollYFab = fmScrollContainer.scrollTop || 0;
            fmScrollContainer.addEventListener('scroll', fmHandleFabScroll, {passive: true});
        }

        // Không cần event listener cho progress modal nữa vì đã bỏ
    });

    // Toggle Details panel
    function fmToggleDetails() {
        const contentArea = document.querySelector('.content-area');
        const btn = document.getElementById('fmToggleDetailsBtn');
        if (!contentArea || !btn) return;
        
        const isHidden = contentArea.classList.contains('detail-hidden');
        if (isHidden) {
            contentArea.classList.remove('detail-hidden');
            btn.title = 'Hide Details';
            localStorage.setItem('fmDetailsVisible', '1');
        } else {
            contentArea.classList.add('detail-hidden');
            btn.title = 'Show Details';
            localStorage.setItem('fmDetailsVisible', '0');
        }
        
        // Cập nhật icon
        const icon = btn.querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', isHidden ? 'panel-right' : 'panel-left');
            lucide.createIcons();
        }
    }

    // Khôi phục trạng thái Details từ localStorage
    document.addEventListener('DOMContentLoaded', function() {
        const saved = localStorage.getItem('fmDetailsVisible');
        if (saved === '0') {
            const contentArea = document.querySelector('.content-area');
            const btn = document.getElementById('fmToggleDetailsBtn');
            if (contentArea) {
                contentArea.classList.add('detail-hidden');
                if (btn) {
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.setAttribute('data-lucide', 'panel-left');
                        lucide.createIcons();
                    }
                    btn.title = 'Show Details';
                }
            }
        }
    });

    // Tự động submit form khi thay đổi sort, order hoặc hidden
    document.addEventListener('DOMContentLoaded', function() {
        const form = document.querySelector('.toolbar-form');
        if (!form) return;

        const sortSelect = form.querySelector('select[name="sort"]');
        const orderSelect = form.querySelector('select[name="order"]');
        const hiddenCheckbox = form.querySelector('input[name="hidden"]');

        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                form.submit();
            });
        }

        if (orderSelect) {
            orderSelect.addEventListener('change', function() {
                form.submit();
            });
        }

        if (hiddenCheckbox) {
            hiddenCheckbox.addEventListener('change', function() {
                form.submit();
            });
        }
    });

    // Rút gọn breadcrumb khi quá dài (giống File Explorer)
    function compactBreadcrumb() {
        const breadcrumb = document.querySelector('.breadcrumb');
        if (!breadcrumb) return;

        const addressBar = breadcrumb.closest('.address-bar');
        if (!addressBar) return;

        const items = Array.from(breadcrumb.querySelectorAll('.breadcrumb-item'));
        if (items.length <= 3) return; // Không cần rút gọn nếu ít hơn 3 items

        // Kiểm tra xem có vượt quá chiều rộng không
        const maxWidth = addressBar.offsetWidth - 20; // Trừ padding
        breadcrumb.style.maxWidth = 'none';
        const fullWidth = breadcrumb.scrollWidth;
        
        if (fullWidth <= maxWidth) {
            breadcrumb.classList.remove('compact');
            const ellipsis = breadcrumb.querySelector('.breadcrumb-ellipsis');
            if (ellipsis) ellipsis.remove();
            return;
        }

        // Rút gọn: giữ item đầu, ellipsis, và 2-3 items cuối
        breadcrumb.classList.add('compact');
        
        // Xóa ellipsis cũ nếu có
        const oldEllipsis = breadcrumb.querySelector('.breadcrumb-ellipsis');
        if (oldEllipsis) oldEllipsis.remove();

        // Ẩn các items ở giữa (trừ item đầu và 2-3 items cuối)
        const keepLast = 2; // Giữ 2 items cuối
        const allChildren = Array.from(breadcrumb.childNodes);
        
        items.forEach((item, index) => {
            if (index === 0) {
                // Giữ item đầu
                item.style.display = '';
            } else if (index >= items.length - keepLast) {
                // Giữ items cuối
                item.style.display = '';
            } else {
                // Ẩn items ở giữa
                item.style.display = 'none';
                // Ẩn separator sau item này
                const itemIndex = allChildren.indexOf(item);
                if (itemIndex >= 0 && itemIndex < allChildren.length - 1) {
                    const nextNode = allChildren[itemIndex + 1];
                    if (nextNode && nextNode.classList && nextNode.classList.contains('breadcrumb-sep')) {
                        nextNode.style.display = 'none';
                    }
                }
            }
        });

        // Thêm ellipsis sau item đầu (trước separator nếu có)
        const ellipsis = document.createElement('span');
        ellipsis.className = 'breadcrumb-ellipsis';
        ellipsis.textContent = '...';
        ellipsis.title = 'Click để xem toàn bộ đường dẫn';
        ellipsis.onclick = function() {
            // Tạm thời hiển thị tất cả để xem
            items.forEach(item => item.style.display = '');
            allChildren.forEach(node => {
                if (node.style) node.style.display = '';
            });
            ellipsis.style.display = 'none';
            setTimeout(() => {
                compactBreadcrumb();
            }, 2000);
        };
        
        // Tìm vị trí chèn ellipsis (sau item đầu, trước separator hoặc item tiếp theo)
        const firstItem = items[0];
        if (firstItem && firstItem.nextSibling) {
            const nextSibling = firstItem.nextSibling;
            if (nextSibling.classList && nextSibling.classList.contains('breadcrumb-sep')) {
                breadcrumb.insertBefore(ellipsis, nextSibling.nextSibling || nextSibling);
            } else {
                breadcrumb.insertBefore(ellipsis, nextSibling);
            }
        } else if (firstItem) {
            breadcrumb.insertBefore(ellipsis, firstItem.nextSibling);
        }
    }

    // Khởi tạo và theo dõi resize
    document.addEventListener('DOMContentLoaded', function() {
        compactBreadcrumb();
        window.addEventListener('resize', compactBreadcrumb);
    });

    // Resize sidebar
    (function() {
        const resizeHandle = document.getElementById('navResizeHandle');
        const contentArea = document.querySelector('.content-area');
        if (!resizeHandle || !contentArea) return;

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;
        const minWidth = 160;
        const maxWidth = 400;

        // Khôi phục độ rộng từ localStorage
        const savedWidth = localStorage.getItem('navWidth');
        if (savedWidth) {
            const width = parseInt(savedWidth, 10);
            if (width >= minWidth && width <= maxWidth) {
                document.documentElement.style.setProperty('--nav-width', width + 'px');
            }
        }

        resizeHandle.addEventListener('mousedown', function(e) {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(getComputedStyle(contentArea).gridTemplateColumns.split(' ')[0], 10);
            resizeHandle.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            const diff = e.clientX - startX;
            let newWidth = startWidth + diff;
            if (newWidth < minWidth) newWidth = minWidth;
            if (newWidth > maxWidth) newWidth = maxWidth;
            document.documentElement.style.setProperty('--nav-width', newWidth + 'px');
        });

        document.addEventListener('mouseup', function() {
            if (isResizing) {
                isResizing = false;
                resizeHandle.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                // Lưu độ rộng vào localStorage
                const currentWidth = parseInt(getComputedStyle(contentArea).gridTemplateColumns.split(' ')[0], 10);
                localStorage.setItem('navWidth', currentWidth.toString());
            }
        });
    })();

    // Khởi tạo status lần đầu
    fmUpdateStatus();
    
    // Khởi tạo Lucide icons
    lucide.createIcons();
    </script>
</body>
</html>
"""

# --------- TEMPLATE: Album (Images/Videos) ----------
ALBUM_HTML = r"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }} albums - WiFi File Manager</title>
    <style>
        body {
            font-family: sans-serif;
            background: #111;
            color: #eee;
            margin: 0;
            padding: 0;
        }
        .topbar {
            background: #222;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        a { color: #4aa3ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .heading {
            font-size: 16px;
        }
        .container {
            padding: 12px 16px 32px 16px;
        }
        .items {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }
        .item {
            background: #1b1b1b;
            border-radius: 10px;
            padding: 6px;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            gap: 4px;
            border: 1px solid #333;
        }
        .item:hover { border-color: #4aa3ff; }
        .thumb {
            width: 100%;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 6px;
            background: #000;
        }
        .thumb img, .thumb video {
            max-width: 100%;
            max-height: 100%;
        }
        .name {
            font-size: 13px;
            word-break: break-all;
        }
        .sub {
            font-size: 11px;
            color: #aaa;
        }
        .empty {
            color: #777;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div><a href="/browse" style="color:#eee;text-decoration:none;">⏪ Browse</a></div>
        <div class="heading">{{ heading }}</div>
    </div>
    <div class="container">
        {% if albums %}
        <div class="items">
            {% for a in albums %}
            <a href="{{ base }}?dir={{ a.dir_rel|urlencode }}" style="text-decoration:none;color:inherit;">
                <div class="item">
                    <div class="thumb">
                        {% if is_image %}
                            <img src="/file?path={{ a.sample_rel|urlencode }}" loading="lazy">
                        {% else %}
                            <video src="/file?path={{ a.sample_rel|urlencode }}" muted preload="metadata"></video>
                        {% endif %}
                    </div>
                    <div class="name">{{ a.name }} ({{ a.count }})</div>
                    <div class="sub">{{ a.dir_rel or "/" }}</div>
                </div>
            </a>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">Không tìm thấy album.</div>
        {% endif %}
    </div>
</body>
</html>
"""

# --------- TEMPLATE: Gallery trong 1 album ----------
GALLERY_HTML = r"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ title }} - WiFi File Manager</title>
    <style>
        body {
            font-family: sans-serif;
            background: #111;
            color: #eee;
            margin: 0;
            padding: 0;
        }
        .topbar {
            background: #222;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        a { color: #4aa3ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .heading {
            font-size: 15px;
        }
        .container {
            padding: 10px 16px 32px 16px;
        }
        .toolbar {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
            align-items: center;
            font-size: 12px;
        }
        .toolbar input[type=text] {
            padding: 4px 6px;
            border-radius: 4px;
            border: 1px solid #444;
            background: #111;
            color: #eee;
            min-width: 140px;
        }
        .toolbar select {
            padding: 3px 4px;
            border-radius: 4px;
            border: 1px solid #444;
            background: #111;
            color: #eee;
        }
        .toolbar button {
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #4aa3ff;
            background: #1b1b1b;
            color: #eee;
            cursor: pointer;
        }
        .view-toggle a {
            margin-left: 6px;
            font-size: 16px;
            text-decoration: none;
        }

        .items {
            display: grid;
            gap: 10px;
        }
        .item {
            background: #1b1b1b;
            border-radius: 10px;
            padding: 6px;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            gap: 4px;
            border: 1px solid #333;
        }
        .item.list {
            flex-direction: row;
            align-items: center;
            gap: 10px;
        }
        .item.selected {
            border-color: #4aa3ff;
            background: #252c3b;
        }
        .thumb {
            width: 100%;
            height: 130px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-radius: 6px;
            background: #000;
        }
        .thumb.list {
            width: 90px;
            height: 70px;
        }
        .thumb img, .thumb video {
            max-width: 100%;
            max-height: 100%;
        }
        .name {
            font-size: 12px;
            word-break: break-all;
        }
        .sub {
            font-size: 11px;
            color: #aaa;
        }
        .empty {
            color: #777;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div><a href="{{ back_url }}" style="color:#eee;text-decoration:none;">⏪ {{ back_text }}</a></div>
        <div class="heading">{{ heading }}</div>
    </div>
    <div class="container">
        <form method="get" class="toolbar">
            <input type="hidden" name="dir" value="{{ dir_rel }}">
            <span>Search:</span>
            <input type="text" name="q" value="{{ q }}">
            <span>Sort:</span>
            <select name="sort">
                <option value="name" {% if sort == 'name' %}selected{% endif %}>Name</option>
                <option value="date" {% if sort == 'date' %}selected{% endif %}>Date</option>
            </select>
            <select name="order">
                <option value="asc" {% if order == 'asc' %}selected{% endif %}>↑</option>
                <option value="desc" {% if order == 'desc' %}selected{% endif %}>↓</option>
            </select>
            <span class="view-toggle">
                View:
                <a href="{{ base }}?dir={{ dir_rel|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}&view=grid">🔳</a>
                <a href="{{ base }}?dir={{ dir_rel|urlencode }}&sort={{ sort }}&order={{ order }}&q={{ q|urlencode }}&view=list">📃</a>
            </span>
            <button type="submit">Apply</button>
            <button type="button" onclick="fmDownloadSelected()">Download</button>
        </form>

        <form id="fmDownloadForm" method="post" action="/download">
            <input type="hidden" name="paths" id="fmDownloadPaths">
        </form>

        {% if items %}
        <div class="items" style="grid-template-columns: {{ '1fr' if is_list else 'repeat(auto-fill, minmax(140px, 1fr))' }};">
            {% for e in items %}
            <div class="item {% if is_list %}list{% endif %}"
                 data-path="{{ e.rel }}"
                 data-is-dir="0"
                 data-type="{{ 'image' if is_image else 'video' }}"
                 onclick="fmHandleClick(event, this)"
                 ondblclick="fmHandleDblClick(event, this)">
                <div class="thumb {% if is_list %}list{% endif %}">
            {% if is_image %}
                <img src="/file?path={{ e.rel|urlencode }}" loading="lazy">
            {% else %}
                <video src="/file?path={{ e.rel|urlencode }}" controls muted preload="none"></video>
            {% endif %}
                </div>
                <div>
                    <div class="name">{{ e.name }}</div>
                    <div class="sub">{{ e.dir_display }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">Không có file trong album.</div>
        {% endif %}
    </div>

    <script>
    let fmSelected = [];
    let fmLastIndex = null;

    function fmClearSelection() {
        fmSelected = [];
        document.querySelectorAll('.item[data-path]').forEach(el => {
            el.classList.remove('selected');
        });
    }

    function fmSelectRange(startIndex, endIndex) {
        const items = Array.from(document.querySelectorAll('.item[data-path]'));
        if (startIndex > endIndex) {
            [startIndex, endIndex] = [endIndex, startIndex];
        }
        fmClearSelection();
        for (let i = startIndex; i <= endIndex; i++) {
            const el = items[i];
            if (!el) continue;
            const p = el.dataset.path;
            if (!p) continue;
            if (!fmSelected.includes(p)) fmSelected.push(p);
            el.classList.add('selected');
        }
    }

    function fmHandleClick(ev, el) {
        const items = Array.from(document.querySelectorAll('.item[data-path]'));
        const idx = items.indexOf(el);
        const isCtrl = ev.ctrlKey || ev.metaKey;
        const isShift = ev.shiftKey;

        if (isShift && fmLastIndex !== null) {
            fmSelectRange(fmLastIndex, idx);
            return;
        }

        const path = el.dataset.path;
        if (!path) return;

        if (!isCtrl) {
            fmClearSelection();
        }

        const existed = fmSelected.indexOf(path);
        if (existed >= 0 && isCtrl) {
            fmSelected.splice(existed, 1);
            el.classList.remove('selected');
        } else {
            if (!fmSelected.includes(path)) fmSelected.push(path);
            el.classList.add('selected');
        }

        fmLastIndex = idx;
    }

    function fmHandleDblClick(ev, el) {
        const path = el.dataset.path;
        if (!path) return;
        const t = el.dataset.type || "";
        const isImage = (t === "image");
        fmShowPreview(path, isImage);
    }

    function fmShowPreview(path, isImage) {
        const overlay = document.getElementById("fmOverlay");
        const body = document.getElementById("fmOverlayBody");
        const link = document.getElementById("fmOverlayDownload");

        if (!overlay || !body || !link) {
            window.open("/file?path=" + encodeURIComponent(path), "_blank");
            return;
        }

        link.href = "/file?path=" + encodeURIComponent(path) + "&download=1";

        let html = "";
        if (isImage) {
            html = '<img src="/file?path=' + encodeURIComponent(path) +
                   '" style="max-width:100%;max-height:80vh;">';
        } else {
            html = '<video src="/file?path=' + encodeURIComponent(path) +
                   '" controls autoplay style="max-width:100%;max-height:80vh;"></video>';
        }

        body.innerHTML = html;
        overlay.style.display = "flex";
    }

    function fmHidePreview() {
        const overlay = document.getElementById("fmOverlay");
        if (overlay) {
            // Dừng tất cả video và audio trong overlay
            const videos = overlay.querySelectorAll('video');
            const audios = overlay.querySelectorAll('audio');
            
            videos.forEach(video => {
                video.pause();
                video.currentTime = 0; // Reset về đầu
            });
            
            audios.forEach(audio => {
                audio.pause();
                audio.currentTime = 0; // Reset về đầu
            });
            
            overlay.style.display = "none";
        }
    }


    function fmDownloadSelected() {
        if (!fmSelected.length) {
            showToast("Chưa chọn file hoặc thư mục nào", 'warning');
            return;
        }
        // Hiển thị progress nếu có nhiều file cần zip
        if (fmSelected.length > 3) {
            fmShowProgress(`Đang chuẩn bị tải xuống ${fmSelected.length} mục...`, false);
            fmUpdateProgress(30, 'Đang nén file...');
            
            setTimeout(() => {
                const input = document.getElementById("fmDownloadPaths");
                input.value = fmSelected.join("|");
                document.getElementById("fmDownloadForm").submit();
                
                setTimeout(() => {
                    fmHideProgress();
                    fmShowNotification('Tải xuống đã bắt đầu. File sẽ được tải về khi hoàn tất.', 'success');
                }, 1500);
            }, 800);
        } else {
            const input = document.getElementById("fmDownloadPaths");
            input.value = fmSelected.join("|");
            document.getElementById("fmDownloadForm").submit();
        }
    }
    // Hover video: chỉ cho 1 video chạy
    (function () {
        let currentHoverVideo = null;
        const videos = document.querySelectorAll('.thumb video');

        videos.forEach(v => {
            v.preload = "none";
            v.addEventListener('mouseenter', () => {
                if (currentHoverVideo && currentHoverVideo !== v) {
                    currentHoverVideo.pause();
                    currentHoverVideo.currentTime = 0;
                }
                currentHoverVideo = v;
                v.play().catch(() => {});
            });

            v.addEventListener('mouseleave', () => {
                v.pause();
                v.currentTime = 0;
                if (currentHoverVideo === v) {
                    currentHoverVideo = null;
                }
            });
        });
    })();


    </script>

    <!-- Overlay preview -->
    <div id="fmOverlay" style="display:none;position:fixed;inset:0;
         background:rgba(0,0,0,0.7);align-items:center;justify-content:center;
         z-index:9999;">
        <div onclick="fmHidePreview()" style="position:absolute;inset:0;"></div>

        <div style="position:relative;background:#1e1e1e;border-radius:12px;
                    padding:10px;max-width:95%;max-height:90%;
                    z-index:10000;box-shadow:0 25px 50px rgba(0,0,0,0.7);">
            <div style="display:flex;justify-content:space-between;
                        align-items:center;padding:12px 16px;background:#2d2d2d;
                        border-bottom:1px solid #404040;border-radius:12px 12px 0 0;">
                <button onclick="fmHidePreview()"
                        style="background:#333;border:none;color:#eee;
                               padding:4px 8px;border-radius:4px;cursor:pointer;">
                    ✕
                </button>
                <a id="fmOverlayDownload"
                   href="#"
                   style="padding:4px 8px;border-radius:4px;
                          border:1px solid #4aa3ff;text-decoration:none;
                          color:#4aa3ff;">
                    ⬇ Download
                </a>
            </div>
            <div id="fmOverlayBody" style="text-align:center;"></div>
        </div>
    </div>
</body>
</html>
"""

# --------- TEMPLATE: Preview 1 file ----------
PREVIEW_HTML = r"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Preview - {{ name }}</title>
    <style>
        body {
            font-family: sans-serif;
            background: #111;
            color: #eee;
            margin: 0;
            padding: 0;
        }
        .topbar {
            background: #222;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        a { color: #4aa3ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .container {
            padding: 12px 16px 32px 16px;
        }
        .viewer {
            margin-top: 16px;
        }
        img, video {
            max-width: 100%;
            height: auto;
        }
        audio {
            width: 100%;
        }
        .info {
            font-size: 13px;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div><a href="javascript:history.back()" style="color:#eee;text-decoration:none;">⏪ Back</a></div>
        <div>{{ name }}</div>
        <div>
            <a href="/file?path={{ rel|urlencode }}&download=1">⬇ Download</a>
        </div>
    </div>
    <div class="container">
        <div class="info">{{ mime }}</div>
        <div class="viewer">
            {% if is_image %}
                <img src="/file?path={{ rel|urlencode }}">
            {% elif is_video %}
                <video src="/file?path={{ rel|urlencode }}" controls autoplay></video>
            {% elif is_audio %}
                <audio src="/file?path={{ rel|urlencode }}" controls autoplay></audio>
            {% else %}
                <p>Không có preview cho loại file này. Bạn có thể tải về để mở.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# ========== HÀM PHỤ ==========

def safe_join(base, rel_path):
    """
    An toàn hơn: xử lý symlinks và normalize path, chống path traversal.
    """
    # Normalize base path và resolve symlinks
    base = os.path.abspath(os.path.realpath(base))
    
    # Normalize và loại bỏ các trick path traversal
    if rel_path:
        rel_path = os.path.normpath(rel_path).lstrip(os.sep)
        
        # Loại bỏ các ký tự nguy hiểm
        if '..' in rel_path or rel_path.startswith('/'):
            logger.warning(f"Path traversal attempt: {rel_path}")
            abort(403)
    
    target = os.path.abspath(os.path.realpath(
        os.path.join(base, rel_path)
    ))
    
    # Kiểm tra symlink escape
    if os.path.islink(target):
        link_dest = os.path.realpath(target)
        if not link_dest.startswith(base):
            logger.warning(f"Symlink escape attempt: {target} -> {link_dest}")
            abort(403)
    
    # Kiểm tra path traversal
    if not target.startswith(base):
        logger.warning(f"Path traversal attempt: {rel_path} -> {target}")
        abort(403)
    
    return target

def list_directory(rel_path, q, sort, order, show_hidden, view):
    media_spec = detect_media_special(rel_path)
    if media_spec:
        return render_media_special(
            rel_path,
            media_spec,
            q,
            sort,
            order,
            show_hidden,
            view,
        )

    fs_path = safe_join(ROOT_DIR, rel_path)
    if not os.path.exists(fs_path):
        abort(404)

    if os.path.isfile(fs_path):
        directory = os.path.dirname(fs_path)
        filename = os.path.basename(fs_path)
        return send_from_directory(directory, filename, as_attachment=False)

    entries = []
    try:
        names = os.listdir(fs_path)
    except PermissionError:
        abort(403)  # Thay vì silent fail
    except OSError as e:
        abort(500)  # Lỗi khác
    
    # Fix Android: /storage/emulated không cho list,
    # nhưng /storage/emulated/0 thì đọc được
    if fs_path == "/storage/emulated" and not names:
        sub0 = os.path.join(fs_path, "0")
        if os.path.isdir(sub0):
            names = ["0"]

    # Tối ưu: lọc search ngay khi tạo entries (nếu có search)
    q_lower = q.lower() if q else None
    
    for name in names:
        if not show_hidden and name.startswith("."):
            continue
        
        # Lọc search sớm để tránh xử lý không cần thiết
        if q_lower and q_lower not in name.lower():
            continue
        
        full = os.path.join(fs_path, name)
        try:
            rel_child = os.path.relpath(full, ROOT_DIR).replace("\\", "/")
        except ValueError:
            continue  # Bỏ qua nếu không nằm trong ROOT_DIR
        
        is_dir = os.path.isdir(full)
        
        # Chỉ guess mime cho file (tiết kiệm thời gian)
        mime = ""
        if not is_dir:
            mime, _ = mimetypes.guess_type(full)
            mime = mime or ""
        
        try:
            st = os.stat(full)
            mtime = st.st_mtime
            size = st.st_size if not is_dir else 0
        except OSError:
            mtime = 0
            size = 0
        
        info = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        if not is_dir:
            info += f" · {size//1024} KB"

        entries.append({
            "name": name,
            "rel": rel_child,
            "is_dir": is_dir,
            "mime": mime,
            "mtime": mtime,
            "info": info
        })

    # sort
    reverse = (order == "desc")
    if sort == "date":
        entries.sort(key=lambda e: e["mtime"], reverse=reverse)
    else:
        entries.sort(key=lambda e: e["name"].lower(), reverse=reverse)

    parent_rel = None
    if rel_path:
        parent = os.path.dirname(fs_path)
        if parent.startswith(os.path.abspath(ROOT_DIR)):
            parent_rel = os.path.relpath(parent, ROOT_DIR).replace("\\", "/")
            if parent_rel == ".":
                parent_rel = ""

    is_list = (view == "list")
    return render_template_string(
        BROWSE_HTML,
        entries=entries,
        cur_rel=rel_path,
        parent_rel=parent_rel,
        q=q,
        sort=sort,
        order=order,
        show_hidden=show_hidden,
        view=view,
        is_list=is_list,
        breadcrumb_segments=None,
        active_special=None,
        media_images_prefix=MEDIA_IMAGES_PREFIX,
        media_videos_prefix=MEDIA_VIDEOS_PREFIX,
    )


# Cache cho media scan
_media_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 300  # 5 phút

def _do_scan_media_grouped(exts):
    """
    Thực hiện scan thực tế (không cache).
    """
    albums = {}

    # Lấy danh sách root thật sự để quét
    roots = []
    try:
        roots = list(STORAGES.values())
    except NameError:
        roots = [ROOT_DIR]

    # Loại trùng + chỉ giữ thư mục tồn tại
    uniq_roots = []
    seen = set()
    for r in roots:
        if not r:
            continue
        r = os.path.abspath(r)
        if r not in seen and os.path.isdir(r):
            seen.add(r)
            uniq_roots.append(r)

    if not uniq_roots:
        uniq_roots = [ROOT_DIR]

    # Quét từng storage
    for root in uniq_roots:
        for dirpath, dirnames, filenames in os.walk(
            root, topdown=True, onerror=lambda e: None
        ):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in exts:
                    continue

                full = os.path.join(dirpath, fname)

                # Đường dẫn tương đối so với ROOT_DIR (để /file dùng được)
                try:
                    rel = os.path.relpath(full, ROOT_DIR).replace("\\", "/")
                except ValueError:
                    # Không nằm dưới ROOT_DIR -> bỏ
                    continue

                dir_rel = os.path.dirname(rel)
                if dir_rel == ".":
                    dir_rel = ""

                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    mtime = 0

                if dir_rel not in albums:
                    albums[dir_rel] = {
                        "name": os.path.basename(dirpath) if dir_rel else "/",
                        "dir_rel": dir_rel,
                        "sample_rel": rel,
                        "count": 1,
                        "mtime": mtime,
                    }
                else:
                    albums[dir_rel]["count"] += 1
                    if mtime > albums[dir_rel]["mtime"]:
                        albums[dir_rel]["mtime"] = mtime
                        albums[dir_rel]["sample_rel"] = rel

    album_list = list(albums.values())
    album_list.sort(key=lambda a: a["mtime"], reverse=True)
    return album_list

def scan_media_grouped(exts):
    """
    Quét toàn bộ các storage trong STORAGES, gom file theo thư mục (album).
    Có caching để tối ưu performance.
    Trả về list album: {name, dir_rel, sample_rel, count, mtime}
    """
    cache_key = frozenset(exts)
    current_time = time.time()
    
    with _cache_lock:
        if cache_key in _media_cache:
            cached_data, timestamp = _media_cache[cache_key]
            if current_time - timestamp < CACHE_TTL:
                return cached_data
    
    # Thực hiện scan
    result = _do_scan_media_grouped(exts)
    
    # Lưu vào cache
    with _cache_lock:
        _media_cache[cache_key] = (result, current_time)
    
    return result



def scan_media_in_dir(exts, dir_rel):
    """
    Lấy file media trong đúng thư mục dir_rel (không đệ quy).
    """
    fs_dir = safe_join(ROOT_DIR, dir_rel)
    items = []
    try:
        names = os.listdir(fs_dir)
    except OSError:
        names = []

    for fname in names:
        full = os.path.join(fs_dir, fname)
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in exts:
            continue
        rel = os.path.relpath(full, ROOT_DIR).replace("\\", "/")
        try:
            st = os.stat(full)
            mtime = st.st_mtime
            size = st.st_size
        except OSError:
            mtime = 0
            size = 0
        items.append({
            "name": fname,
            "rel": rel,
            "mtime": mtime,
            "dir_display": dir_rel or "/",
            "size": size,
        })
    return items


def scan_media_subdirs(exts, dir_rel):
    """
    Quét các thư mục con trong dir_rel có chứa file media (1 cấp).
    Trả về list album: {name, dir_rel, sample_rel, count, mtime}
    """
    fs_dir = safe_join(ROOT_DIR, dir_rel)
    albums = {}
    try:
        names = os.listdir(fs_dir)
    except OSError:
        return []

    for name in names:
        subdir_full = os.path.join(fs_dir, name)
        if not os.path.isdir(subdir_full):
            continue

        # Quét file media trong thư mục con này
        subdir_rel = os.path.relpath(subdir_full, ROOT_DIR).replace("\\", "/")
        media_files = scan_media_in_dir(exts, subdir_rel)
        
        if not media_files:
            continue

        # Tìm file mới nhất làm preview
        latest_file = max(media_files, key=lambda x: x["mtime"])
        try:
            preview_mime, _ = mimetypes.guess_type(latest_file["name"])
            preview_mime = preview_mime or ""
        except:
            preview_mime = ""

        albums[subdir_rel] = {
            "name": name,
            "dir_rel": subdir_rel,
            "sample_rel": latest_file["rel"],
            "count": len(media_files),
            "mtime": latest_file["mtime"],
            "preview_mime": preview_mime,
        }

    return list(albums.values())


def scan_all_subdirs(exts, dir_rel):
    """
    Quét tất cả thư mục con trong dir_rel (1 cấp), không chỉ những thư mục có media.
    Trả về list: {name, dir_rel, sample_rel, count, mtime, preview_mime}
    """
    fs_dir = safe_join(ROOT_DIR, dir_rel)
    subdirs = []
    try:
        names = os.listdir(fs_dir)
    except OSError:
        return []

    for name in names:
        subdir_full = os.path.join(fs_dir, name)
        if not os.path.isdir(subdir_full):
            continue

        subdir_rel = os.path.relpath(subdir_full, ROOT_DIR).replace("\\", "/")
        
        # Quét file media trong thư mục con này (nếu có)
        media_files = scan_media_in_dir(exts, subdir_rel)
        
        # Lấy mtime của thư mục
        try:
            st = os.stat(subdir_full)
            mtime = st.st_mtime
        except OSError:
            mtime = 0
        
        # Nếu có media, lấy preview
        preview_rel = None
        preview_mime = ""
        count = len(media_files)
        
        if media_files:
            latest_file = max(media_files, key=lambda x: x["mtime"])
            preview_rel = latest_file["rel"]
            try:
                preview_mime, _ = mimetypes.guess_type(latest_file["name"])
                preview_mime = preview_mime or ""
            except:
                preview_mime = ""
        
        subdirs.append({
            "name": name,
            "dir_rel": subdir_rel,
            "sample_rel": preview_rel,
            "count": count,
            "mtime": mtime,
            "preview_mime": preview_mime,
        })

    return subdirs


def detect_media_special(rel_path):
    if not rel_path:
        return None
    rel_path = rel_path.strip()
    for prefix, meta in MEDIA_SPECIALS.items():
        if rel_path == prefix:
            return {
                "prefix": prefix,
                "meta": meta,
                "dir_rel": "",
                "is_listing": True,
            }
        prefix_with_slash = prefix + "/"
        if rel_path.startswith(prefix_with_slash):
            raw_sub = rel_path[len(prefix_with_slash):]
            if not raw_sub:
                return {
                    "prefix": prefix,
                    "meta": meta,
                    "dir_rel": "",
                    "is_listing": True,
                }
            sub = raw_sub.replace("\\", "/").strip("/")
            if sub == ".":
                sub = ""
            return {
                "prefix": prefix,
                "meta": meta,
                "dir_rel": sub,
                "is_listing": False,
            }
    return None


def build_media_breadcrumb(prefix, label, dir_rel, is_listing):
    segments = [
        {"name": "storage", "path": None},
        {"name": label, "path": prefix},
    ]
    if not is_listing:
        if dir_rel:
            parts = [p for p in dir_rel.split("/") if p]
            acc = ""
            for part in parts:
                acc = f"{acc}/{part}" if acc else part
                segments.append({
                    "name": part,
                    "path": f"{prefix}/{acc}"
                })
        else:
            segments.append({"name": "/", "path": f"{prefix}/."})
    return segments


def render_media_special(rel_path, spec, q, sort, order, show_hidden, view):
    prefix = spec["prefix"]
    meta = spec["meta"]
    dir_rel = spec["dir_rel"]
    is_listing = spec["is_listing"]
    label = meta["label"]
    exts = meta["exts"]

    entries = []
    if is_listing:
        albums = scan_media_grouped(exts)
        if q:
            q_lower = q.lower()
            albums = [
                a for a in albums
                if q_lower in (a["dir_rel"] or "/").lower()
                or q_lower in (a["name"] or "/").lower()
            ]
        reverse = (order == "desc")
        if sort == "name":
            albums.sort(
                key=lambda a: (a["dir_rel"] or "/").lower(),
                reverse=reverse
            )
        else:
            albums.sort(key=lambda a: a["mtime"], reverse=reverse)
        for album in albums:
            rel_suffix = album["dir_rel"] or "."
            preview_rel = album.get("sample_rel")
            preview_mime = ""
            if preview_rel:
                preview_mime, _ = mimetypes.guess_type(preview_rel)
                preview_mime = preview_mime or ""
            # Chỉ lấy tên thư mục cuối cùng, không phải toàn bộ đường dẫn
            dir_rel = album["dir_rel"] or ""
            if dir_rel:
                display_name = os.path.basename(dir_rel.rstrip("/")) or dir_rel
            else:
                display_name = "/"
            entries.append({
                "name": display_name,
                "rel": f"{prefix}/{rel_suffix}",
                "is_dir": True,
                "mime": "",
                "mtime": album["mtime"],
                "info": f"{album['count']} item{'s' if album['count'] != 1 else ''}",
                "preview_rel": preview_rel,
                "preview_mime": preview_mime,
            })
    else:
        # Tìm file media trực tiếp trong thư mục
        items = scan_media_in_dir(exts, dir_rel)
        
        # Tìm tất cả thư mục con (có media hoặc không)
        subdirs = scan_all_subdirs(exts, dir_rel)
        
        # Thêm tất cả thư mục con vào entries
        for subdir in subdirs:
            display_name = subdir["name"]
            rel_suffix = subdir["dir_rel"]
            if subdir["count"] > 0:
                info = f"{subdir['count']} item{'s' if subdir['count'] != 1 else ''}"
            else:
                info = "Folder"
            entries.append({
                "name": display_name,
                "rel": f"{prefix}/{rel_suffix}",
                "is_dir": True,
                "mime": "",
                "mtime": subdir["mtime"],
                "info": info,
                "preview_rel": subdir.get("sample_rel"),
                "preview_mime": subdir.get("preview_mime", ""),
            })
        
        # Thêm các file media trực tiếp vào entries
        for item in items:
            mime, _ = mimetypes.guess_type(item["name"])
            if not mime:
                mime = "image/*" if meta["key"] == "images" else "video/*"
            info = time.strftime(
                "%Y-%m-%d %H:%M",
                time.localtime(item["mtime"])
            )
            info += f" · {item.get('size', 0)//1024} KB"
            entries.append({
                "name": item["name"],
                "rel": item["rel"],
                "is_dir": False,
                "mime": mime,
                "mtime": item["mtime"],
                "info": info
            })
        
        # Lọc search nếu có
        if q:
            q_lower = q.lower()
            entries = [
                e for e in entries
                if q_lower in e["name"].lower()
            ]
        
        # Sắp xếp toàn bộ entries (cả thư mục và file)
        reverse = (order == "desc")
        if sort == "name":
            entries.sort(key=lambda e: e["name"].lower(), reverse=reverse)
        else:
            entries.sort(key=lambda e: e["mtime"], reverse=reverse)

    parent_rel = None
    if not is_listing:
        if dir_rel:
            parent = os.path.dirname(dir_rel).replace("\\", "/")
            if parent in ("", "."):
                parent_rel = prefix
            else:
                parent_rel = f"{prefix}/{parent}"
        else:
            parent_rel = prefix

    breadcrumb_segments = build_media_breadcrumb(prefix, label, dir_rel, is_listing)
    is_list = (view == "list")
    return render_template_string(
        BROWSE_HTML,
        entries=entries,
        cur_rel=rel_path,
        parent_rel=parent_rel,
        q=q,
        sort=sort,
        order=order,
        show_hidden=show_hidden,
        view=view,
        is_list=is_list,
        breadcrumb_segments=breadcrumb_segments,
        active_special=meta["key"],
        media_images_prefix=MEDIA_IMAGES_PREFIX,
        media_videos_prefix=MEDIA_VIDEOS_PREFIX,
    )


# ========== ROUTES ==========

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    """Trang đăng nhập"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if check_auth(username, password):
            session['logged_in'] = True
            session['username'] = username
            next_page = request.args.get('next')
            return redirect(next_page or url_for('browse'))
        else:
            return render_template_string(LOGIN_HTML, error="Tên đăng nhập hoặc mật khẩu không đúng!")
    
    # Nếu đã đăng nhập, redirect về browse
    if session.get('logged_in'):
        return redirect(url_for('browse'))
    
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
def logout():
    """Đăng xuất"""
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
def index():
    """Redirect về browse hoặc login"""
    if session.get('logged_in'):
        return redirect(url_for('browse'))
    return redirect(url_for('login'))

@app.route("/browse")
@requires_auth
def browse():
    rel = request.args.get("path", "").strip()
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")
    view = request.args.get("view", "grid")
    show_hidden = request.args.get("hidden", "0") == "1"
    return list_directory(rel, q, sort, order, show_hidden, view)


@app.route("/images")
@requires_auth
def images():
    dir_rel = request.args.get("dir", "").strip()
    if dir_rel:
        q = request.args.get("q", "").strip()
        sort = request.args.get("sort", "date")
        order = request.args.get("order", "desc")
        view = request.args.get("view", "grid")

        items = scan_media_in_dir(IMAGE_EXTS, dir_rel)
        if q:
            q_lower = q.lower()
            items = [e for e in items if q_lower in e["name"].lower()]

        reverse = (order == "desc")
        if sort == "name":
            items.sort(key=lambda e: e["name"].lower(), reverse=reverse)
        else:
            items.sort(key=lambda e: e["mtime"], reverse=reverse)

        heading = f"Images - {dir_rel or '/'}"
        is_list = (view == "list")
        return render_template_string(
            GALLERY_HTML,
            title=heading,
            heading=heading,
            items=items,
            is_image=True,
            back_url="/images",
            back_text="Albums",
            base="/images",
            dir_rel=dir_rel,
            q=q,
            sort=sort,
            order=order,
            view=view,
            is_list=is_list
        )
    else:
        albums = scan_media_grouped(IMAGE_EXTS)
        return render_template_string(
            ALBUM_HTML,
            title="Images",
            heading="Image albums",
            albums=albums,
            is_image=True,
            base="/images"
        )


@app.route("/videos")
@requires_auth
def videos():
    dir_rel = request.args.get("dir", "").strip()
    if dir_rel:
        q = request.args.get("q", "").strip()
        sort = request.args.get("sort", "date")
        order = request.args.get("order", "desc")
        view = request.args.get("view", "grid")

        items = scan_media_in_dir(VIDEO_EXTS, dir_rel)
        if q:
            q_lower = q.lower()
            items = [e for e in items if q_lower in e["name"].lower()]

        reverse = (order == "desc")
        if sort == "name":
            items.sort(key=lambda e: e["name"].lower(), reverse=reverse)
        else:
            items.sort(key=lambda e: e["mtime"], reverse=reverse)

        heading = f"Videos - {dir_rel or '/'}"
        is_list = (view == "list")
        return render_template_string(
            GALLERY_HTML,
            title=heading,
            heading=heading,
            items=items,
            is_image=False,
            back_url="/videos",
            back_text="Albums",
            base="/videos",
            dir_rel=dir_rel,
            q=q,
            sort=sort,
            order=order,
            view=view,
            is_list=is_list
        )
    else:
        albums = scan_media_grouped(VIDEO_EXTS)
        return render_template_string(
            ALBUM_HTML,
            title="Videos",
            heading="Video albums",
            albums=albums,
            is_image=False,
            base="/videos"
        )

def convert_media_path_to_real(rel_path):
    """
    Chuyển đổi đường dẫn media special (__media_images__/..., __media_videos__/...)
    sang đường dẫn thực tế.
    """
    if not rel_path:
        return rel_path
    spec = detect_media_special(rel_path)
    if spec:
        # Nếu là listing (chỉ prefix), không thể download
        if spec["is_listing"]:
            return None
        # Trả về dir_rel (đường dẫn thực tế)
        return spec["dir_rel"]
    return rel_path


def secure_vietnamese_filename(filename):
    """
    Làm sạch tên file nhưng giữ lại dấu tiếng Việt.
    Thay thế secure_filename() để hỗ trợ Unicode.
    """
    if not filename:
        return ""
    
    # Normalize Unicode để đảm bảo tính nhất quán
    filename = unicodedata.normalize('NFC', filename)
    
    # Loại bỏ các ký tự nguy hiểm nhưng giữ lại tiếng Việt
    # Cho phép: chữ cái, số, dấu gạch ngang, gạch dưới, dấu chấm, khoảng trắng
    # và các ký tự tiếng Việt (Unicode)
    safe_chars = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Thay thế nhiều khoảng trắng liên tiếp bằng một khoảng trắng
    safe_chars = re.sub(r'\s+', ' ', safe_chars)
    
    # Loại bỏ khoảng trắng đầu cuối
    safe_chars = safe_chars.strip()
    
    # Đảm bảo không rỗng
    if not safe_chars:
        return "file"
    
    # Giới hạn độ dài (Windows có giới hạn 255 ký tự cho tên file)
    if len(safe_chars) > 200:
        name, ext = os.path.splitext(safe_chars)
        safe_chars = name[:200-len(ext)] + ext
    
    return safe_chars

def normalize_client_rel(rel_path):
    """
    Chuẩn hóa đường dẫn từ client về dạng tương đối so với ROOT_DIR.
    Trả về None nếu không thể chuyển đổi (ví dụ: đang ở view liệt kê media đặc biệt).
    """
    if rel_path is None:
        rel = ""
    else:
        rel = str(rel_path).strip()
    rel = rel.replace("\\", "/").strip("/")
    if rel == ".":
        rel = ""
    real_rel = convert_media_path_to_real(rel)
    if real_rel is None:
        if not rel:
            return ""
        return None
    normalized = real_rel.replace("\\", "/").strip("/")
    return normalized


def sanitize_upload_subpath(path_value):
    """
    Làm sạch đường dẫn relative được gửi từ input file (kèm thư mục).
    Bỏ các ký tự nguy hiểm và chuẩn hóa separator.
    """
    if not path_value:
        return ""
    parts = []
    for segment in path_value.replace("\\", "/").split("/"):
        segment = segment.strip()
        if not segment or segment in (".", ".."):
            continue
        cleaned = secure_vietnamese_filename(segment)
        if not cleaned:
            continue
        parts.append(cleaned)
    return "/".join(parts)


def ensure_unique_name(dest_dir, name):
    """
    Sinh tên mới nếu tên đã tồn tại trong đích.
    """
    base, ext = os.path.splitext(name)
    if not base:
        base = name
        ext = ""
    candidate = name
    counter = 1
    while os.path.exists(os.path.join(dest_dir, candidate)):
        candidate = f"{base} ({counter}){ext}"
        counter += 1
    return candidate


def add_to_zip(zf, fs_path, arcname_base):
    """
    Thêm file hoặc thư mục vào zip (đệ quy cho thư mục).
    """
    if os.path.isfile(fs_path):
        zf.write(fs_path, arcname_base)
    elif os.path.isdir(fs_path):
        # Thêm thư mục và tất cả nội dung bên trong
        for root, dirs, files in os.walk(fs_path):
            # Thêm tất cả file
            for file in files:
                file_path = os.path.join(root, file)
                # Tính arcname: arcname_base/folder/subfolder/file
                rel_path = os.path.relpath(file_path, fs_path)
                arcname = os.path.join(arcname_base, rel_path).replace("\\", "/")
                zf.write(file_path, arcname)
            # Thêm thư mục rỗng (nếu có)
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # Thư mục rỗng
                        rel_path = os.path.relpath(dir_path, fs_path)
                        arcname = os.path.join(arcname_base, rel_path).replace("\\", "/")
                        zf.writestr(arcname + "/", "")
                except (OSError, PermissionError):
                    pass  # Bỏ qua nếu không đọc được


@app.route("/download", methods=["POST"])
@requires_auth
def download_multi():
    paths_str = request.form.get("paths", "").strip()
    if not paths_str:
        abort(400)

    rel_paths = [p for p in paths_str.split("|") if p]
    if not rel_paths:
        abort(400)

    # Chuyển đổi đường dẫn media special sang đường dẫn thực tế
    real_paths = []
    for rel in rel_paths:
        real_rel = convert_media_path_to_real(rel)
        if real_rel is None:
            continue  # Bỏ qua nếu không thể chuyển đổi (ví dụ: listing)
        real_paths.append(real_rel)
    
    if not real_paths:
        abort(400)

    # Nếu chỉ có 1 item và là file -> download trực tiếp
    if len(real_paths) == 1:
        rel = real_paths[0]
        try:
            fs_path = safe_join(ROOT_DIR, rel)
        except Exception as e:
            logger.error(f"Error in safe_join: {e}")
            abort(403)
        
        if os.path.isfile(fs_path):
            directory = os.path.dirname(fs_path)
            filename = os.path.basename(fs_path)
            return send_from_directory(directory, filename, as_attachment=True)
        # Nếu là thư mục, zip lại
        elif os.path.isdir(fs_path):
            try:
                mem = BytesIO()
                with ZipFile(mem, "w", ZIP_DEFLATED) as zf:
                    add_to_zip(zf, fs_path, os.path.basename(fs_path))
                mem.seek(0)
                folder_name = os.path.basename(fs_path) or "folder"
                
                # Kiểm tra kích thước (giới hạn 500MB để tránh crash)
                if mem.tell() > 500 * 1024 * 1024:
                    logger.warning(f"ZIP too large: {mem.tell()} bytes")
                    abort(413)  # Payload Too Large
                
                return send_file(
                    mem,
                    mimetype="application/zip",
                    as_attachment=True,
                    download_name=f"{folder_name}.zip",
                )
            except Exception as e:
                logger.error(f"Error creating ZIP: {e}")
                abort(500)
        else:
            abort(404)

    # Nhiều items (file và/hoặc thư mục) -> zip lại
    try:
        mem = BytesIO()
        with ZipFile(mem, "w", ZIP_DEFLATED) as zf:
            for rel in real_paths:
                try:
                    fs_path = safe_join(ROOT_DIR, rel)
                except Exception:
                    continue
                if not os.path.exists(fs_path):
                    continue
                arcname = os.path.basename(fs_path)
                add_to_zip(zf, fs_path, arcname)
        
        mem.seek(0)
        
        # Kiểm tra kích thước (giới hạn 500MB)
        if mem.tell() > 500 * 1024 * 1024:
            logger.warning(f"ZIP too large: {mem.tell()} bytes")
            abort(413)  # Payload Too Large
        
        return send_file(
            mem,
            mimetype="application/zip",
            as_attachment=True,
            download_name="files.zip",
        )
    except Exception as e:
        logger.error(f"Error creating multi-file ZIP: {e}")
        abort(500)


@app.route("/api/files/delete", methods=["POST"])
@requires_auth
def api_delete_files():
    payload = request.get_json(silent=True) or {}
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths:
        return jsonify({"success": False, "message": "Không có mục nào được chọn để xóa."}), 400

    deleted = []
    errors = []
    for rel in paths:
        normalized = normalize_client_rel(rel)
        if normalized is None:
            errors.append({"path": rel, "error": "Đường dẫn không hợp lệ trong chế độ này."})
            continue
        try:
            fs_path = safe_join(ROOT_DIR, normalized)
        except HTTPException:
            errors.append({"path": rel, "error": "Không thể truy cập đường dẫn."})
            continue

        if not os.path.exists(fs_path):
            errors.append({"path": rel, "error": "Không tồn tại."})
            continue

        try:
            if os.path.isdir(fs_path):
                shutil.rmtree(fs_path)
            else:
                os.remove(fs_path)
            deleted.append(rel)
        except OSError as err:
            errors.append({"path": rel, "error": str(err)})

    needs_refresh = bool(deleted)
    success = not errors
    message_parts = []
    if deleted:
        message_parts.append(f"Đã xóa {len(deleted)} mục.")
    if errors:
        message_parts.append(f"Không thể xử lý {len(errors)} mục.")
    if not message_parts:
        message_parts.append("Không có mục nào được xóa.")

    status_code = 200 if deleted else 400
    return jsonify({
        "success": success,
        "deleted": deleted,
        "errors": errors,
        "message": " ".join(message_parts),
        "needs_refresh": needs_refresh,
    }), status_code


@app.route("/api/files/paste", methods=["POST"])
@requires_auth
def api_paste_files():
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode")
    items = payload.get("items")
    destination_raw = payload.get("destination", "")

    if mode not in ("copy", "cut"):
        return jsonify({"success": False, "message": "Chế độ paste không hợp lệ."}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"success": False, "message": "Không có mục nào trong clipboard."}), 400

    destination_rel = normalize_client_rel(destination_raw)
    if destination_rel is None:
        return jsonify({"success": False, "message": "Không thể paste trong thư mục này."}), 400

    try:
        dest_path = safe_join(ROOT_DIR, destination_rel)
    except HTTPException:
        return jsonify({"success": False, "message": "Không thể truy cập thư mục đích."}), 403

    if not os.path.isdir(dest_path):
        return jsonify({"success": False, "message": "Thư mục đích không hợp lệ."}), 400

    processed = []
    errors = []
    for rel in items:
        normalized = normalize_client_rel(rel)
        if normalized is None:
            errors.append({"path": rel, "error": "Đường dẫn không hợp lệ."})
            continue
        try:
            src_path = safe_join(ROOT_DIR, normalized)
        except HTTPException:
            errors.append({"path": rel, "error": "Không thể truy cập nguồn."})
            continue

        if not os.path.exists(src_path):
            errors.append({"path": rel, "error": "Nguồn không tồn tại."})
            continue

        name = os.path.basename(src_path)
        same_directory = os.path.dirname(src_path) == dest_path
        if mode == "cut" and same_directory:
            errors.append({"path": rel, "error": "Nguồn và đích trùng nhau."})
            continue

        target_name = name
        target_path = os.path.join(dest_path, target_name)
        if os.path.exists(target_path):
            target_name = ensure_unique_name(dest_path, name)
            target_path = os.path.join(dest_path, target_name)

        abs_src = os.path.abspath(src_path)
        abs_target = os.path.abspath(target_path)
        if abs_target.startswith(abs_src + os.sep):
            errors.append({"path": rel, "error": "Không thể chép vào chính thư mục con của nó."})
            continue

        try:
            if mode == "cut":
                shutil.move(src_path, target_path)
            else:
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, target_path)
                else:
                    shutil.copy2(src_path, target_path)
        except (OSError, shutil.Error) as err:
            errors.append({"path": rel, "error": str(err)})
            continue

        processed.append({
            "source": rel,
            "target": os.path.relpath(target_path, ROOT_DIR).replace("\\", "/"),
        })

    needs_refresh = bool(processed)
    success = not errors
    message_parts = []
    if processed:
        verb = "di chuyển" if mode == "cut" else "copy"
        message_parts.append(f"Đã {verb} {len(processed)} mục.")
    if errors:
        message_parts.append(f"Không thể xử lý {len(errors)} mục.")
    if not message_parts:
        message_parts.append("Không có mục nào được xử lý.")

    status_code = 200 if processed else 400
    return jsonify({
        "success": success,
        "done": processed,
        "errors": errors,
        "message": " ".join(message_parts),
        "needs_refresh": needs_refresh,
    }), status_code


@app.route("/api/files/mkdir", methods=["POST"])
@requires_auth
def api_create_folder():
    payload = request.get_json(silent=True) or {}
    name_raw = (payload.get("name") or "").strip()
    destination_raw = payload.get("destination", "")
    dest_rel = normalize_client_rel(destination_raw)
    if dest_rel is None:
        return jsonify({"success": False, "message": "Không thể tạo thư mục tại vị trí này."}), 400

    clean_name = secure_vietnamese_filename(name_raw)
    if not clean_name:
        return jsonify({"success": False, "message": "Tên thư mục không hợp lệ."}), 400

    try:
        base_dir = safe_join(ROOT_DIR, dest_rel)
    except HTTPException:
        return jsonify({"success": False, "message": "Không thể truy cập thư mục hiện tại."}), 403

    if not os.path.isdir(base_dir):
        return jsonify({"success": False, "message": "Thư mục hiện tại không hợp lệ."}), 400

    new_rel = "/".join(filter(None, [dest_rel, clean_name]))
    try:
        new_path = safe_join(ROOT_DIR, new_rel)
    except HTTPException:
        return jsonify({"success": False, "message": "Đường dẫn mới không hợp lệ."}), 403

    if os.path.exists(new_path):
        return jsonify({"success": False, "message": "Thư mục đã tồn tại."}), 400

    try:
        os.makedirs(new_path, exist_ok=False)
    except OSError as err:
        logger.error("Failed to create folder: %s", err)
        return jsonify({"success": False, "message": "Không thể tạo thư mục."}), 500

    return jsonify({
        "success": True,
        "message": "Đã tạo thư mục mới.",
        "path": new_rel,
        "needs_refresh": True,
    }), 200


@app.route("/api/rename", methods=["POST"])
@requires_auth
def api_rename():
    """API để đổi tên file/folder"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dữ liệu không hợp lệ"})
        
        current_path = data.get("current_path", "").strip()
        new_name = data.get("new_name", "").strip()
        
        if not current_path or not new_name:
            return jsonify({"success": False, "message": "Thiếu thông tin cần thiết"})
        
        # Validate new name
        if not new_name or len(new_name) > 255:
            return jsonify({"success": False, "message": "Tên không hợp lệ"})
        
        # Check for invalid characters
        import re
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', new_name):
            return jsonify({"success": False, "message": "Tên chứa ký tự không hợp lệ"})
        
        # Normalize current path
        current_rel = normalize_client_rel(current_path)
        if current_rel is None:
            return jsonify({"success": False, "message": "Đường dẫn không hợp lệ"})
        
        # Build new file path (same directory, new name)
        if "/" in current_rel:
            parent_dir = "/".join(current_rel.split("/")[:-1])
            new_rel = "/".join(filter(None, [parent_dir, new_name]))
        else:
            new_rel = new_name
        
        try:
            current_full_path = safe_join(ROOT_DIR, current_rel)
            new_full_path = safe_join(ROOT_DIR, new_rel)
        except HTTPException:
            return jsonify({"success": False, "message": "Đường dẫn không hợp lệ"})
        
        # Debug logging
        logger.info(f"Rename debug - current_path: {current_path}")
        logger.info(f"Rename debug - current_rel: {current_rel}")
        logger.info(f"Rename debug - current_full_path: {current_full_path}")
        logger.info(f"Rename debug - new_name: {new_name}")
        logger.info(f"Rename debug - new_full_path: {new_full_path}")
        
        # Check if source exists
        if not os.path.exists(current_full_path):
            return jsonify({"success": False, "message": f"File/thư mục không tồn tại: {current_full_path}"})
        
        # Check if destination already exists
        if os.path.exists(new_full_path):
            return jsonify({"success": False, "message": "Tên đã tồn tại"})
        
        # Perform rename
        os.rename(current_full_path, new_full_path)
        
        logger.info(f"Renamed: {current_full_path} -> {new_full_path}")
        
        return jsonify({
            "success": True, 
            "message": f"Đã đổi tên thành '{new_name}'"
        })
        
    except PermissionError:
        return jsonify({"success": False, "message": "Không có quyền đổi tên"})
    except OSError as e:
        return jsonify({"success": False, "message": f"Lỗi hệ thống: {str(e)}"})
    except Exception as e:
        logger.error(f"Error in rename API: {e}")
        return jsonify({"success": False, "message": "Lỗi không xác định"})

@app.route("/api/files/upload", methods=["POST"])
@requires_auth
def api_upload_files():
    destination_raw = request.form.get("destination", "")
    dest_rel = normalize_client_rel(destination_raw)
    if dest_rel is None:
        return jsonify({"success": False, "message": "Không thể tải lên tại vị trí này."}), 400

    try:
        base_dir = safe_join(ROOT_DIR, dest_rel)
    except HTTPException:
        return jsonify({"success": False, "message": "Không thể truy cập thư mục hiện tại."}), 403

    if not os.path.isdir(base_dir):
        return jsonify({"success": False, "message": "Thư mục hiện tại không hợp lệ."}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"success": False, "message": "Không có tệp nào được chọn."}), 400

    saved = []
    errors = []

    for storage in files:
        original_name = storage.filename or storage.name or ""
        cleaned_rel = sanitize_upload_subpath(original_name)
        if not cleaned_rel:
            errors.append({"name": original_name or "(unknown)", "error": "Tên tệp không hợp lệ."})
            continue

        target_rel = "/".join(filter(None, [dest_rel, cleaned_rel]))
        try:
            target_path = safe_join(ROOT_DIR, target_rel)
        except HTTPException:
            errors.append({"name": original_name or cleaned_rel, "error": "Đường dẫn không hợp lệ."})
            continue

        target_dir = os.path.dirname(target_path)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as err:
            errors.append({"name": original_name or cleaned_rel, "error": str(err)})
            continue

        final_name = os.path.basename(target_path) or secure_vietnamese_filename(original_name) or "file"
        final_path = os.path.join(target_dir, final_name)
        if os.path.exists(final_path):
            unique_name = ensure_unique_name(target_dir, final_name)
            final_path = os.path.join(target_dir, unique_name)

        try:
            storage.save(final_path)
        except OSError as err:
            errors.append({"name": original_name or final_name, "error": str(err)})
            continue

        saved.append(os.path.relpath(final_path, ROOT_DIR).replace("\\", "/"))

    needs_refresh = bool(saved)
    success = not errors
    status_code = 200 if saved else 400

    message_parts = []
    if saved:
        message_parts.append(f"Đã tải lên {len(saved)} mục.")
    if errors:
        message_parts.append(f"{len(errors)} mục gặp lỗi.")
    if not message_parts:
        message_parts.append("Không có mục nào được tải lên.")

    return jsonify({
        "success": success,
        "saved": saved,
        "errors": errors,
        "message": " ".join(message_parts),
        "needs_refresh": needs_refresh,
    }), status_code


@app.route("/view")
@requires_auth
def view_file():
    rel = request.args.get("path", "").strip()
    fs_path = safe_join(ROOT_DIR, rel)
    if not os.path.isfile(fs_path):
        abort(404)
    name = os.path.basename(fs_path)
    mime, _ = mimetypes.guess_type(fs_path)
    mime = mime or ""
    is_image = mime.startswith("image/")
    is_video = mime.startswith("video/")
    is_audio = mime.startswith("audio/")
    return render_template_string(
        PREVIEW_HTML,
        name=name,
        rel=rel,
        mime=mime,
        is_image=is_image,
        is_video=is_video,
        is_audio=is_audio,
    )

@app.route("/file")
@requires_auth
def serve_file():
    rel = request.args.get("path", "").strip()
    download = request.args.get("download", "0") == "1"
    fs_path = safe_join(ROOT_DIR, rel)
    if not os.path.isfile(fs_path):
        abort(404)
    directory = os.path.dirname(fs_path)
    filename = os.path.basename(fs_path)
    return send_from_directory(directory, filename, as_attachment=download)


# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(e):
    return render_template_string("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>404 - File không tồn tại</title>
            <style>
                body {
                    background: #111;
                    color: #eee;
                    font-family: sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                a { color: #4aa3ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>404 - File không tồn tại</h1>
            <p><a href="/browse">← Về trang chủ</a></p>
        </body>
        </html>
    """), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template_string("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>403 - Truy cập bị từ chối</title>
            <style>
                body {
                    background: #111;
                    color: #eee;
                    font-family: sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                a { color: #4aa3ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>403 - Truy cập bị từ chối</h1>
            <p>Bạn không có quyền truy cập tài nguyên này.</p>
            <p><a href="/browse">← Về trang chủ</a></p>
        </body>
        </html>
    """), 403

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}", exc_info=True)
    return render_template_string("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>500 - Lỗi server</title>
            <style>
                body {
                    background: #111;
                    color: #eee;
                    font-family: sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                a { color: #4aa3ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>500 - Lỗi server</h1>
            <p>Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.</p>
            <p><a href="/browse">← Về trang chủ</a></p>
        </body>
        </html>
    """), 500

@app.errorhandler(400)
def bad_request(e):
    return render_template_string("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>400 - Yêu cầu không hợp lệ</title>
            <style>
                body {
                    background: #111;
                    color: #eee;
                    font-family: sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                a { color: #4aa3ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>400 - Yêu cầu không hợp lệ</h1>
            <p><a href="/browse">← Về trang chủ</a></p>
        </body>
        </html>
    """), 400

@app.errorhandler(413)
def payload_too_large(e):
    return render_template_string("""
        <html>
        <head>
            <meta charset="utf-8">
            <title>413 - File quá lớn</title>
            <style>
                body {
                    background: #111;
                    color: #eee;
                    font-family: sans-serif;
                    text-align: center;
                    padding-top: 100px;
                }
                a { color: #4aa3ff; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>413 - File quá lớn</h1>
            <p>Kích thước file/quản lý vượt quá giới hạn (500MB).</p>
            <p>Vui lòng tải từng file riêng lẻ.</p>
            <p><a href="/browse">← Về trang chủ</a></p>
        </body>
        </html>
    """), 413




if __name__ == "__main__":
    logger.info("Starting WiFi File Manager...")
    logger.warning("Security: Ensure this is only accessible on local network!")
    logger.warning(f"Authentication: username='{USERNAME}', password='{PASSWORD}'")
    
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
        threaded=True
    )