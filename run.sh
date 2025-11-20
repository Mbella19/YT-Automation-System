#!/bin/bash

# Video Editing Automation - Quick Start Script

echo "🎬 Video Editing Automation - Starting..."
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python3 found: $(python3 --version)"

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Please install FFmpeg:"
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt install ffmpeg"
    echo "   Windows: choco install ffmpeg"
    exit 1
fi

echo "✓ FFmpeg found: $(ffmpeg -version | head -n1)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing/Updating dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p uploads outputs temp audio

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Starting Flask server..."
echo "Access the app at: http://localhost:5001"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Run the application
python3 app.py

