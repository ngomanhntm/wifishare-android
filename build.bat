@echo off
REM WiFi File Share - Build Script for Windows
REM Script này hướng dẫn build APK trên Windows

echo 🚀 WiFi File Share - Build Script (Windows)
echo ===============================================

echo.
echo ⚠️  Buildozer không hỗ trợ build APK trên Windows!
echo.
echo 📋 Để build APK, bạn cần sử dụng một trong các cách sau:
echo.

echo 1️⃣  WSL (Windows Subsystem for Linux) - KHUYẾN NGHỊ:
echo    ----------------------------------------
echo    a) Cài đặt WSL2:
echo       wsl --install Ubuntu
echo.
echo    b) Mở WSL terminal và chạy:
echo       sudo apt update
echo       sudo apt install -y git zip unzip openjdk-8-jdk python3-pip
echo       sudo apt install -y autoconf libtool pkg-config zlib1g-dev
echo       sudo apt install -y libncurses5-dev libncursesw5-dev libtinfo5
echo       sudo apt install -y cmake libffi-dev libssl-dev
echo.
echo    c) Copy project vào WSL:
echo       cp -r /mnt/c/path/to/wifishare ~/wifishare
echo       cd ~/wifishare
echo.
echo    d) Chạy setup và build:
echo       python3 setup.py
echo       chmod +x build.sh
echo       ./build.sh
echo.

echo 2️⃣  GitHub Actions (Cloud Build):
echo    --------------------------------
echo    a) Tạo file .github/workflows/build.yml
echo    b) Push code lên GitHub
echo    c) GitHub sẽ tự động build APK
echo.

echo 3️⃣  Virtual Machine:
echo    -------------------
echo    a) Cài đặt VirtualBox/VMware
echo    b) Tạo Ubuntu VM
echo    c) Chạy build process trong VM
echo.

echo 4️⃣  Test trên Windows (Desktop):
echo    ------------------------------
echo    python main.py
echo.

echo 📋 Chọn một phương pháp và làm theo hướng dẫn trên.
echo.

REM Offer to create GitHub Actions workflow
set /p choice="Bạn có muốn tạo GitHub Actions workflow không? (y/N): "
if /i "%choice%"=="y" goto create_workflow
if /i "%choice%"=="yes" goto create_workflow
goto end

:create_workflow
echo.
echo 🔄 Tạo GitHub Actions workflow...

REM Create .github/workflows directory
if not exist ".github\workflows" mkdir ".github\workflows"

REM Create workflow file
echo name: Build Android APK > .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo on: >> .github\workflows\build.yml
echo   push: >> .github\workflows\build.yml
echo     branches: [ main, master ] >> .github\workflows\build.yml
echo   pull_request: >> .github\workflows\build.yml
echo     branches: [ main, master ] >> .github\workflows\build.yml
echo   workflow_dispatch: >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo jobs: >> .github\workflows\build.yml
echo   build: >> .github\workflows\build.yml
echo     runs-on: ubuntu-latest >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     steps: >> .github\workflows\build.yml
echo     - uses: actions/checkout@v3 >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     - name: Set up Python >> .github\workflows\build.yml
echo       uses: actions/setup-python@v4 >> .github\workflows\build.yml
echo       with: >> .github\workflows\build.yml
echo         python-version: '3.9' >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     - name: Install system dependencies >> .github\workflows\build.yml
echo       run: ^| >> .github\workflows\build.yml
echo         sudo apt update >> .github\workflows\build.yml
echo         sudo apt install -y git zip unzip openjdk-8-jdk python3-pip >> .github\workflows\build.yml
echo         sudo apt install -y autoconf libtool pkg-config zlib1g-dev >> .github\workflows\build.yml
echo         sudo apt install -y libncurses5-dev libncursesw5-dev libtinfo5 >> .github\workflows\build.yml
echo         sudo apt install -y cmake libffi-dev libssl-dev >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     - name: Install Python dependencies >> .github\workflows\build.yml
echo       run: ^| >> .github\workflows\build.yml
echo         python -m pip install --upgrade pip >> .github\workflows\build.yml
echo         pip install -r requirements.txt >> .github\workflows\build.yml
echo         pip install buildozer cython >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     - name: Build APK >> .github\workflows\build.yml
echo       run: ^| >> .github\workflows\build.yml
echo         buildozer android debug >> .github\workflows\build.yml
echo. >> .github\workflows\build.yml
echo     - name: Upload APK >> .github\workflows\build.yml
echo       uses: actions/upload-artifact@v3 >> .github\workflows\build.yml
echo       with: >> .github\workflows\build.yml
echo         name: wifishare-debug-apk >> .github\workflows\build.yml
echo         path: bin/*.apk >> .github\workflows\build.yml

echo ✅ GitHub Actions workflow đã được tạo!
echo.
echo 📋 Bước tiếp theo:
echo 1. git add .
echo 2. git commit -m "Add WiFi Share Android app"
echo 3. git push origin main
echo 4. Kiểm tra tab "Actions" trên GitHub để xem build progress
echo.

:end
pause
