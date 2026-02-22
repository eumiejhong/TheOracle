#!/bin/bash

echo "🎯 The Oracle iOS App Setup Script"
echo "=================================="

# Check if Xcode is installed
if ! command -v xcrun &> /dev/null; then
    echo "❌ Error: Xcode is required but not found."
    echo "Please install Xcode from the Mac App Store first."
    exit 1
fi

# Check if we can find iOS SDK
if ! xcrun --show-sdk-path --sdk iphoneos &> /dev/null; then
    echo "❌ Error: iOS SDK not found."
    echo "Please make sure Xcode is properly installed and run:"
    echo "sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer"
    exit 1
fi

echo "✅ Xcode found!"

# Install npm dependencies
echo "📦 Installing npm dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ npm dependencies installed successfully!"
else
    echo "❌ Failed to install npm dependencies"
    exit 1
fi

# Install iOS pods
echo "🍎 Installing iOS CocoaPods dependencies..."
cd ios
pod install

if [ $? -eq 0 ]; then
    echo "✅ iOS dependencies installed successfully!"
    cd ..
    echo ""
    echo "🎉 Setup complete! You can now run the app with:"
    echo "   npx react-native run-ios"
    echo ""
    echo "Or open the workspace in Xcode:"
    echo "   open ios/TheOracleApp.xcworkspace"
else
    echo "❌ Failed to install iOS dependencies"
    echo "You may need to run: sudo gem install cocoapods"
    cd ..
    exit 1
fi