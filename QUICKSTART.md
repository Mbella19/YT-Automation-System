# 🚀 Quick Start Guide

Get Try On running in 5 minutes!

## Prerequisites

Make sure you have installed:
- Python 3.8+ ([Download](https://www.python.org/downloads/))
- Node.js 16+ ([Download](https://nodejs.org/))
- A Google API Key for Gemini ([Get one here](https://makersuite.google.com/app/apikey))

## Step 1: Run Setup

Open Terminal and navigate to the project folder:

```bash
cd "/Users/gervaciusjr/Desktop/Try on"
```

Run the setup script:

```bash
./setup.sh
```

This will:
- Install Python dependencies
- Install Node.js dependencies
- Create necessary directories
- Generate configuration files

## Step 2: Add Your API Key

1. Get your Google API Key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Open `backend/.env` in a text editor
3. Replace the `GOOGLE_API_KEY=` line with your actual key:
   ```
   GOOGLE_API_KEY=AIzaSy...your-actual-key-here
   ```
4. Save the file

## Step 3: Start the Backend

Open a terminal and run:

```bash
./start-backend.sh
```

You should see:
```
✅ Starting Flask server on http://localhost:5000
```

Keep this terminal open!

## Step 4: Start the Frontend

Open a **NEW** terminal and run:

```bash
./start-frontend.sh
```

You should see:
```
✅ Starting Vite dev server on http://localhost:3000
```

## Step 5: Open the App

1. Open your browser
2. Go to `http://localhost:3000`
3. Click "Try It Now" to create an account

## 🎉 You're Ready!

### What to Do Next:

1. **Create Account** - Sign up with your email
2. **Upload Photo** - Add a clear photo of yourself
3. **Add Clothes** - Upload some clothing items to your wardrobe
4. **Try On** - Go to Try On Studio and select photo + clothing
5. **Generate** - Click the "Try On" button and wait for AI magic!

## 📱 Using on Mobile

To test on your phone:

1. Find your computer's IP address:
   ```bash
   # On macOS/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On Windows:
   ipconfig
   ```

2. On your phone, visit:
   ```
   http://YOUR_IP:3000
   ```
   (Replace YOUR_IP with your computer's IP address)

## ❓ Troubleshooting

### "Port already in use"
```bash
# Kill processes on ports
lsof -ti:5000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### "Module not found"
```bash
# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### "Virtual try-on not working"
- Check that your Google API key is correct
- Verify you have API quota
- Try smaller image files (< 5MB)
- Check backend terminal for error messages

## 🛑 Stopping the App

Press `Ctrl+C` in each terminal window to stop the servers.

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the code in `frontend/src/pages/` for the UI
- Check `backend/app.py` for API endpoints
- Customize the theme in `frontend/tailwind.config.js`

---

Need help? Check the main README or create an issue on GitHub!

