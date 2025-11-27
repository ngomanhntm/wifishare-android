#!/bin/bash

echo "========================================="
echo "WiFi Share - Local Build Script"
echo "========================================="
echo ""

# Check if running on supported OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "❌ ERROR: Local buildozer build is not supported on Windows!"
    echo "Please use GitHub Actions instead:"
    echo "1. Push your code to GitHub"
    echo "2. Go to Actions tab"
    echo "3. Run 'Build WiFi Share APK' workflow"
    echo ""
    exit 1
fi

echo "🔍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 not found!"
    exit 1
fi
python3 --version

echo ""
echo "📦 Installing/upgrading buildozer..."
pip3 install --upgrade buildozer cython

echo ""
echo "🔧 Installing project requirements..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
fi

echo ""
echo "🏗️  Starting Android debug build..."
echo "This may take 10-30 minutes on first run..."
buildozer android debug

echo ""
echo "✅ Build completed!"
if ls bin/*.apk 1> /dev/null 2>&1; then
    echo "📱 APK files created:"
    ls -lh bin/*.apk
    echo ""
    echo "🎉 Success! You can install the APK on your Android device."
else
    echo "❌ No APK files found. Check the build logs above for errors."
    exit 1
fi