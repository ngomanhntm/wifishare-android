#!/usr/bin/env python3
"""
Setup script để chuẩn bị môi trường build APK
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, check=True):
    """Chạy command và hiển thị output"""
    print(f"🔄 Đang chạy: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi: {e}")
        if e.stderr:
            print(e.stderr)
        return False

def check_python_version():
    """Kiểm tra phiên bản Python"""
    version = sys.version_info
    print(f"🐍 Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 7:
        print("❌ Cần Python 3.7 trở lên!")
        return False
    
    print("✅ Python version OK")
    return True

def install_dependencies():
    """Cài đặt Python dependencies"""
    print("📦 Cài đặt Python dependencies...")
    
    # Upgrade pip
    if not run_command(f"{sys.executable} -m pip install --upgrade pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt"):
        return False
    
    # Install buildozer
    if not run_command(f"{sys.executable} -m pip install buildozer"):
        return False
    
    # Install cython (required for buildozer)
    if not run_command(f"{sys.executable} -m pip install cython"):
        return False
    
    print("✅ Dependencies installed")
    return True

def setup_buildozer():
    """Setup Buildozer"""
    print("🔧 Setup Buildozer...")
    
    # Kiểm tra OS
    if platform.system() == "Windows":
        print("⚠️  Buildozer không hỗ trợ Windows trực tiếp.")
        print("   Bạn cần sử dụng WSL (Windows Subsystem for Linux) hoặc VM Linux.")
        return False
    
    # Kiểm tra các dependencies hệ thống (Ubuntu/Debian)
    if platform.system() == "Linux":
        print("🔄 Kiểm tra system dependencies...")
        
        # Danh sách packages cần thiết
        packages = [
            "git", "zip", "unzip", "openjdk-8-jdk", "python3-pip",
            "autoconf", "libtool", "pkg-config", "zlib1g-dev",
            "libncurses5-dev", "libncursesw5-dev", "libtinfo5",
            "cmake", "libffi-dev", "libssl-dev"
        ]
        
        print("📋 Cần cài đặt các packages sau (nếu chưa có):")
        print("   " + " ".join(packages))
        print("\n🔄 Chạy lệnh sau để cài đặt:")
        print(f"   sudo apt update && sudo apt install -y {' '.join(packages)}")
        
        # Không tự động cài vì cần sudo
        input("\n⏸️  Nhấn Enter sau khi đã cài đặt system dependencies...")
    
    # Initialize buildozer (nếu chưa có)
    if not os.path.exists("buildozer.spec"):
        print("🔄 Khởi tạo buildozer...")
        if not run_command("buildozer init"):
            return False
    else:
        print("✅ buildozer.spec đã tồn tại")
    
    print("✅ Buildozer setup complete")
    return True

def test_app():
    """Test app trên desktop"""
    print("🧪 Test app trên desktop...")
    
    try:
        # Import test
        import kivy
        import flask
        print("✅ Kivy và Flask import OK")
        
        print("🔄 Bạn có thể test app bằng lệnh: python main.py")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 WiFi File Share - Setup Script")
    print("=" * 50)
    
    # Kiểm tra Python version
    if not check_python_version():
        sys.exit(1)
    
    # Cài đặt dependencies
    if not install_dependencies():
        print("❌ Không thể cài đặt dependencies")
        sys.exit(1)
    
    # Setup buildozer
    if not setup_buildozer():
        print("❌ Không thể setup buildozer")
        sys.exit(1)
    
    # Test app
    if not test_app():
        print("❌ App test thất bại")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup hoàn thành!")
    print("\n📋 Các bước tiếp theo:")
    print("1. Test app: python main.py")
    print("2. Build debug APK: buildozer android debug")
    print("3. APK sẽ được tạo trong thư mục bin/")
    print("\n⚠️  Lưu ý: Đổi username/password trong wifi_server.py trước khi build!")

if __name__ == "__main__":
    main()
