# Build APK Online - Không cần Linux

## 🌐 Cách 1: GitHub Codespaces (Free)

1. **Vào GitHub repository của bạn**: https://github.com/ngomanhntm/wifishare-android
2. **Click nút xanh "Code"** → **"Codespaces"** → **"Create codespace"**
3. **Đợi 2-3 phút** để setup environment
4. **Trong terminal của Codespace, chạy**:
   ```bash
   chmod +x build-local.sh
   ./build-local.sh
   ```
5. **Download APK** về máy Windows

## 🌐 Cách 2: Replit (Free)

1. **Vào**: https://replit.com
2. **Import GitHub repo**: https://github.com/ngomanhntm/wifishare-android
3. **Chạy build script** trong terminal
4. **Download APK**

## 🌐 Cách 3: Google Colab

1. **Vào**: https://colab.research.google.com
2. **Tạo notebook mới**
3. **Chạy code**:
   ```python
   !git clone https://github.com/ngomanhntm/wifishare-android.git
   %cd wifishare-android
   !chmod +x build-local.sh
   !./build-local.sh
   ```
4. **Download APK**

## 🖥️ Cách 4: VirtualBox (Nếu muốn GUI)

1. **Download VirtualBox**: https://www.virtualbox.org/
2. **Download Ubuntu ISO**: https://ubuntu.com/download/desktop
3. **Tạo VM Ubuntu** (4GB RAM, 20GB disk)
4. **Cài Ubuntu trong VM**
5. **Build APK trong Ubuntu**

## ⚡ Cách 5: Docker Desktop

1. **Cài Docker Desktop**: https://www.docker.com/products/docker-desktop
2. **Chạy lệnh**:
   ```cmd
   docker run -it --rm -v E:\wifishare:/app ubuntu:20.04 bash
   cd /app
   apt update && apt install -y python3 python3-pip git
   ./build-local.sh
   ```

## 🎯 Khuyến nghị

**Thứ tự ưu tiên**:
1. **GitHub Codespaces** (dễ nhất, free)
2. **WSL** (nếu OK với việc có Linux terminal)
3. **Replit** (backup online)
4. **VirtualBox** (nếu muốn GUI Linux)


