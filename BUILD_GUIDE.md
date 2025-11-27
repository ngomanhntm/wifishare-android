# 🚀 WiFi Share - Build Guide

Hướng dẫn chi tiết để build APK cho ứng dụng WiFi Share.

## 🎯 Phương pháp được khuyến nghị

### ✅ GitHub Actions (Khuyến nghị cho tất cả users)

**Ưu điểm:**
- ✅ Hoạt động trên tất cả hệ điều hành (Windows, Mac, Linux)
- ✅ Không cần cài đặt gì trên máy local
- ✅ Build environment ổn định và consistent
- ✅ Tự động cache để build nhanh hơn
- ✅ Miễn phí cho public repositories
- ✅ Tự động upload APK files

**Cách sử dụng:**

1. **Push code lên GitHub:**
   ```bash
   git add .
   git commit -m "Update code"
   git push origin main
   ```

2. **Chạy build workflow:**
   - Vào repository trên GitHub
   - Click tab "Actions"
   - Chọn workflow "Build WiFi Share APK (Optimized)"
   - Click "Run workflow"
   - Chọn build type (debug/release)

3. **Download APK:**
   - Đợi build hoàn thành (~15-30 phút)
   - Vào "Artifacts" section
   - Download file APK

### 🔄 Các Workflows có sẵn:

1. **build-optimized.yml** - Workflow chính với cache và features đầy đủ
2. **build-simple.yml** - Workflow đơn giản, backup option

## 🐧 Local Build (Chỉ Linux/Mac)

**Lưu ý:** Buildozer không hỗ trợ Windows. Windows users vui lòng sử dụng GitHub Actions.

### Cài đặt requirements:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-8-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# macOS
brew install python3 git zip unzip openjdk@8 autoconf libtool pkg-config cmake libffi openssl
```

### Build:

```bash
# Sử dụng script có sẵn
./build-local.sh

# Hoặc manual
pip3 install buildozer
buildozer android debug
```

## 🐳 Docker Build (Advanced)

Nếu bạn có Docker và muốn build local với environment consistent:

```bash
# Build using official Kivy buildozer image
docker run --rm -v "$(pwd)":/home/user/app kivy/buildozer:latest \
  bash -c "cd /home/user/app && buildozer android debug"
```

## 📱 Cài đặt APK

1. **Enable Developer Options trên Android:**
   - Settings > About phone
   - Tap "Build number" 7 lần
   - Quay lại Settings > Developer options
   - Enable "USB debugging" và "Install unknown apps"

2. **Cài đặt APK:**
   - Copy APK file vào điện thoại
   - Mở file manager, tap vào APK file
   - Cho phép cài đặt từ unknown sources
   - Tap "Install"

## 🔧 Troubleshooting

### Build fails với lỗi memory:
- Thử build với GitHub Actions (có nhiều RAM hơn)
- Hoặc close các ứng dụng khác khi build local

### APK không cài được:
- Kiểm tra Android version (cần Android 5.0+)
- Enable "Install unknown apps" trong Settings
- Thử uninstall version cũ trước

### Build quá chậm:
- GitHub Actions có cache, lần build thứ 2 sẽ nhanh hơn
- Local build: lần đầu chậm do download dependencies

## 📊 So sánh các phương pháp:

| Phương pháp | Windows | Mac | Linux | Tốc độ | Độ khó |
|-------------|---------|-----|-------|--------|--------|
| **GitHub Actions** | ✅ | ✅ | ✅ | Trung bình | Dễ |
| **Local Build** | ❌ | ✅ | ✅ | Nhanh | Khó |
| **Docker** | ✅* | ✅ | ✅ | Chậm | Trung bình |

*Cần Docker Desktop

## 🎉 Kết luận

**Cho hầu hết users:** Sử dụng **GitHub Actions** - đơn giản, reliable, và hoạt động trên mọi platform.

**Cho developers có kinh nghiệm:** Local build trên Linux/Mac để development nhanh hơn.
