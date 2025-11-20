#!/bin/bash

echo "🚀 Starting Try On Backend..."

cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/installed
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env and add your GOOGLE_API_KEY"
fi

# Run the app
echo "✅ Starting Flask server on http://localhost:5001"
python app.py

