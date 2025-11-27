#!/bin/bash

# WiFi File Share - Build Script
# Script để build APK một cách tự động

set -e  # Exit on error

echo "🚀 WiFi File Share - Build Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if buildozer is installed
check_buildozer() {
    print_status "Kiểm tra Buildozer..."
    
    if ! command -v buildozer &> /dev/null; then
        print_error "Buildozer chưa được cài đặt!"
        echo "Chạy: pip install buildozer"
        exit 1
    fi
    
    print_success "Buildozer đã được cài đặt"
}

# Clean previous builds
clean_build() {
    print_status "Dọn dẹp build cũ..."
    
    if [ -d ".buildozer" ]; then
        buildozer android clean
        print_success "Đã dọn dẹp build cũ"
    else
        print_success "Không có build cũ để dọn dẹp"
    fi
}

# Update buildozer
update_buildozer() {
    print_status "Cập nhật Buildozer..."
    buildozer android update
    print_success "Buildozer đã được cập nhật"
}

# Build debug APK
build_debug() {
    print_status "Build debug APK..."
    print_warning "Quá trình này có thể mất 10-30 phút lần đầu tiên..."
    
    buildozer android debug
    
    if [ $? -eq 0 ]; then
        print_success "Build debug APK thành công!"
        
        # Find APK file
        APK_FILE=$(find bin/ -name "*.apk" -type f 2>/dev/null | head -1)
        if [ -n "$APK_FILE" ]; then
            APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
            print_success "APK được tạo: $APK_FILE (${APK_SIZE})"
        fi
    else
        print_error "Build debug APK thất bại!"
        exit 1
    fi
}

# Build release APK (if keystore exists)
build_release() {
    print_status "Kiểm tra khả năng build release APK..."
    
    # Check if keystore configuration exists
    if grep -q "android.release_artifact" buildozer.spec; then
        print_status "Build release APK..."
        buildozer android release
        
        if [ $? -eq 0 ]; then
            print_success "Build release APK thành công!"
        else
            print_error "Build release APK thất bại!"
        fi
    else
        print_warning "Chưa cấu hình keystore cho release build"
        print_warning "Chỉ build debug APK"
    fi
}

# Install APK to connected device
install_apk() {
    print_status "Kiểm tra thiết bị Android..."
    
    if command -v adb &> /dev/null; then
        DEVICES=$(adb devices | grep -v "List of devices" | grep "device$" | wc -l)
        
        if [ $DEVICES -gt 0 ]; then
            print_status "Tìm thấy $DEVICES thiết bị Android"
            
            read -p "Bạn có muốn cài đặt APK vào thiết bị không? (y/N): " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                APK_FILE=$(find bin/ -name "*.apk" -type f 2>/dev/null | head -1)
                if [ -n "$APK_FILE" ]; then
                    print_status "Cài đặt APK..."
                    adb install -r "$APK_FILE"
                    print_success "APK đã được cài đặt!"
                else
                    print_error "Không tìm thấy file APK!"
                fi
            fi
        else
            print_warning "Không tìm thấy thiết bị Android nào"
            print_warning "Kết nối thiết bị và bật USB Debugging"
        fi
    else
        print_warning "ADB chưa được cài đặt"
        print_warning "Cài đặt Android SDK để sử dụng ADB"
    fi
}

# Show build info
show_build_info() {
    echo
    echo "=================================="
    print_success "Build hoàn thành!"
    echo
    
    # Show APK files
    if [ -d "bin" ]; then
        print_status "Các file APK đã tạo:"
        ls -lh bin/*.apk 2>/dev/null || print_warning "Không tìm thấy file APK"
    fi
    
    echo
    print_status "Hướng dẫn cài đặt:"
    echo "1. Copy file APK từ thư mục bin/ vào thiết bị Android"
    echo "2. Bật 'Unknown sources' trong Settings > Security"
    echo "3. Mở file APK và cài đặt"
    echo
    print_warning "Lưu ý: Đổi username/password mặc định trước khi sử dụng!"
}

# Main build process
main() {
    # Parse command line arguments
    BUILD_TYPE="debug"
    CLEAN=false
    INSTALL=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --release)
                BUILD_TYPE="release"
                shift
                ;;
            --clean)
                CLEAN=true
                shift
                ;;
            --install)
                INSTALL=true
                shift
                ;;
            --help)
                echo "Sử dụng: $0 [options]"
                echo "Options:"
                echo "  --release    Build release APK (cần keystore)"
                echo "  --clean      Dọn dẹp build cũ trước khi build"
                echo "  --install    Cài đặt APK vào thiết bị sau khi build"
                echo "  --help       Hiển thị help này"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Start build process
    check_buildozer
    
    if [ "$CLEAN" = true ]; then
        clean_build
    fi
    
    update_buildozer
    
    if [ "$BUILD_TYPE" = "release" ]; then
        build_release
    else
        build_debug
    fi
    
    if [ "$INSTALL" = true ]; then
        install_apk
    fi
    
    show_build_info
}

# Run main function
main "$@"
