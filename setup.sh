#!/bin/bash

echo "🎨 Try On - Virtual Fitting Room Setup"
echo "======================================"
echo ""

# Backend setup
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Create upload directories
mkdir -p uploads/photos uploads/clothing uploads/results

cd ..

# Frontend setup
echo ""
echo "📦 Setting up Frontend..."
cd frontend

# Install Node dependencies
echo "Installing Node dependencies..."
npm install

cd ..

# Make start scripts executable
chmod +x start-backend.sh start-frontend.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  IMPORTANT: Edit backend/.env and add your Google API Key"
echo "   Get your API key from: https://makersuite.google.com/app/apikey"
echo ""
echo "To start the app:"
echo "  1. Terminal 1: ./start-backend.sh"
echo "  2. Terminal 2: ./start-frontend.sh"
echo "  3. Open http://localhost:3000 in your browser"
echo ""

