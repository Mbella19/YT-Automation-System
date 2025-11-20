#!/bin/bash

echo "🚀 Starting Try On Frontend..."

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run the dev server
echo "✅ Starting Vite dev server on http://localhost:3000"
npm run dev

