#!/bin/bash

# WiFi Share - Local Build Script for WSL/Linux
# Chạy script này trong WSL hoặc Linux để build APK local

set -e

echo "🚀 WiFi Share - Local APK Build Script"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running on WSL/Linux
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    print_error "This script must be run on WSL or Linux, not Windows directly"
    echo "Please install WSL: wsl --install Ubuntu"
    exit 1
fi

print_status "Checking system requirements..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python3 not found. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# Check Java
if ! command -v java &> /dev/null; then
    print_error "Java not found. Installing OpenJDK 8..."
    sudo apt update
    sudo apt install -y openjdk-8-jdk
    export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
fi

print_success "System requirements OK"

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt update
sudo apt install -y \
    git zip unzip openjdk-8-jdk python3-pip \
    autoconf libtool pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev \
    cmake libffi-dev libssl-dev \
    build-essential python3-dev

print_success "System dependencies installed"

# Install Python dependencies
print_status "Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip3 install buildozer==1.4.0
pip3 install cython==0.29.33
pip3 install kivy[base]==2.1.0
pip3 install flask==2.3.3
pip3 install werkzeug==2.3.7
pip3 install pyjnius==1.4.2
pip3 install requests==2.31.0

print_success "Python dependencies installed"

# Use simple buildozer config
print_status "Setting up buildozer config..."
if [ -f "buildozer-simple.spec" ]; then
    cp buildozer-simple.spec buildozer.spec
    print_success "Using simple buildozer config"
else
    print_warning "buildozer-simple.spec not found, using existing buildozer.spec"
fi

# Accept Android licenses
print_status "Accepting Android licenses..."
mkdir -p ~/.android
echo 'count=0' > ~/.android/repositories.cfg

# Build APK
print_status "Building APK... (This may take 15-30 minutes)"
print_warning "First build will download Android SDK/NDK (~2GB)"

if buildozer android debug; then
    print_success "APK build completed!"
    
    # Show results
    if [ -d "bin" ]; then
        APK_FILE=$(find bin/ -name "*.apk" -type f | head -1)
        if [ -n "$APK_FILE" ]; then
            APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
            print_success "APK created: $APK_FILE (${APK_SIZE})"
            
            echo ""
            echo "🎉 Build successful!"
            echo "📱 APK location: $APK_FILE"
            echo "📏 APK size: $APK_SIZE"
            echo ""
            echo "📋 Next steps:"
            echo "1. Copy APK to your Android device"
            echo "2. Enable 'Unknown sources' in Android Settings"
            echo "3. Install the APK"
            echo "4. Grant permissions when prompted"
            echo ""
            print_warning "Remember to change username/password in wifi_server_full.py!"
        else
            print_error "APK file not found in bin/ directory"
        fi
    else
        print_error "bin/ directory not found"
    fi
else
    print_error "APK build failed!"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "1. Check buildozer logs above for specific errors"
    echo "2. Ensure you have enough disk space (~5GB)"
    echo "3. Try running: buildozer android clean"
    echo "4. Then run this script again"
    exit 1
fi
