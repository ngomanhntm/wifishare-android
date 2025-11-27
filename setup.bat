@echo off
REM WiFi File Share - Setup Script for Windows
REM Script này chuẩn bị môi trường để build APK

echo 🚀 WiFi File Share - Setup Script (Windows)
echo ==================================================

REM Check Python
echo 🐍 Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python chưa được cài đặt hoặc không có trong PATH!
    echo    Tải Python từ: https://python.org
    pause
    exit /b 1
)

python --version
echo ✅ Python OK

REM Upgrade pip
echo 📦 Cập nhật pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ❌ Không thể cập nhật pip!
    pause
    exit /b 1
)

REM Install requirements
echo 📦 Cài đặt dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Không thể cài đặt requirements!
    pause
    exit /b 1
)

REM Install buildozer
echo 🔧 Cài đặt Buildozer...
python -m pip install buildozer
if errorlevel 1 (
    echo ❌ Không thể cài đặt Buildozer!
    pause
    exit /b 1
)

REM Install cython
echo 🔧 Cài đặt Cython...
python -m pip install cython
if errorlevel 1 (
    echo ❌ Không thể cài đặt Cython!
    pause
    exit /b 1
)

echo.
echo ⚠️  QUAN TRỌNG: Buildozer không hỗ trợ Windows trực tiếp!
echo.
echo 📋 Để build APK trên Windows, bạn có các lựa chọn:
echo.
echo 1. 🐧 Sử dụng WSL (Windows Subsystem for Linux):
echo    - Cài đặt WSL2 với Ubuntu
echo    - Chạy setup trong WSL environment
echo.
echo 2. 🖥️  Sử dụng Virtual Machine:
echo    - Cài đặt Ubuntu/Debian VM
echo    - Chạy build process trong VM
echo.
echo 3. ☁️  Sử dụng GitHub Actions:
echo    - Push code lên GitHub
echo    - Sử dụng CI/CD để build APK
echo.
echo 4. 🧪 Test app trên Windows:
echo    - Chạy: python main.py
echo    - Test giao diện Kivy trên desktop
echo.
echo ✅ Setup dependencies hoàn thành!
echo.
echo 📋 Bước tiếp theo:
echo    python main.py  (để test app)
echo.
pause
