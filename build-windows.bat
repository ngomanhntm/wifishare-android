@echo off
REM WiFi Share - Windows Build Helper
REM Script này sẽ hướng dẫn build APK trên Windows

echo 🚀 WiFi Share - Windows Build Helper
echo =====================================
echo.

echo ⚠️  Buildozer không hỗ trợ Windows trực tiếp!
echo.
echo 📋 Bạn có các lựa chọn sau:
echo.

echo 1️⃣  WSL (Windows Subsystem for Linux) - KHUYẾN NGHỊ
echo    - Vẫn dùng Windows bình thường
echo    - Thêm terminal Linux nhỏ bên trong
echo    - Dễ cài đặt, an toàn
echo.

echo 2️⃣  GitHub Codespaces (Online) - DỄ NHẤT
echo    - Không cần cài gì
echo    - Build trên cloud
echo    - Free 60 giờ/tháng
echo.

echo 3️⃣  VirtualBox + Ubuntu
echo    - Cài máy ảo Linux
echo    - Nặng hơn nhưng full control
echo.

echo 4️⃣  Docker Desktop
echo    - Chạy container Linux
echo    - Cho người có kinh nghiệm
echo.

set /p choice="Bạn chọn cách nào? (1/2/3/4): "

if "%choice%"=="1" goto wsl
if "%choice%"=="2" goto codespaces  
if "%choice%"=="3" goto virtualbox
if "%choice%"=="4" goto docker
goto invalid

:wsl
echo.
echo 🐧 Cài đặt WSL:
echo.
echo 1. Mở PowerShell as Administrator
echo 2. Chạy: wsl --install Ubuntu
echo 3. Restart máy
echo 4. Mở Ubuntu app từ Start Menu
echo 5. Chạy: cp -r /mnt/e/wifishare ~/wifishare
echo 6. Chạy: cd ~/wifishare
echo 7. Chạy: chmod +x build-local.sh
echo 8. Chạy: ./build-local.sh
echo.
echo 📱 APK sẽ được tạo trong ~/wifishare/bin/
echo.
pause
goto end

:codespaces
echo.
echo ☁️  GitHub Codespaces (Online):
echo.
echo 1. Vào: https://github.com/ngomanhntm/wifishare-android
echo 2. Click nút "Code" → "Codespaces" → "Create codespace"
echo 3. Đợi 2-3 phút setup
echo 4. Trong terminal, chạy: chmod +x build-local.sh
echo 5. Chạy: ./build-local.sh
echo 6. Download APK về máy
echo.
echo ✅ Không cần cài gì, build trên cloud!
echo.
pause
goto end

:virtualbox
echo.
echo 🖥️  VirtualBox + Ubuntu:
echo.
echo 1. Download VirtualBox: https://www.virtualbox.org/
echo 2. Download Ubuntu: https://ubuntu.com/download/desktop
echo 3. Tạo VM mới (4GB RAM, 20GB disk)
echo 4. Cài Ubuntu trong VM
echo 5. Copy project vào Ubuntu
echo 6. Chạy build script
echo.
echo ⚠️  Cần ~5GB dung lượng và 4GB RAM
echo.
pause
goto end

:docker
echo.
echo 🐳 Docker Desktop:
echo.
echo 1. Cài Docker Desktop: https://www.docker.com/products/docker-desktop
echo 2. Restart máy
echo 3. Mở PowerShell và chạy:
echo    docker run -it --rm -v E:\wifishare:/app ubuntu:20.04 bash
echo 4. Trong container: cd /app && ./build-local.sh
echo.
echo ⚠️  Cần kinh nghiệm với Docker
echo.
pause
goto end

:invalid
echo.
echo ❌ Lựa chọn không hợp lệ!
echo.
pause
goto end

:end
echo.
echo 🎯 Khuyến nghị:
echo    - Nếu muốn dễ nhất: GitHub Codespaces
echo    - Nếu muốn build local: WSL
echo.
echo 📞 Cần hỗ trợ? Hỏi tôi bất kỳ lúc nào!
echo.
pause


