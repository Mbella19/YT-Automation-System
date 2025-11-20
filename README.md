# Apps & Projects

This repository contains multiple projects.

---

## 🎬 Video Editing Automation Software (Current Workspace)

An AI-powered video editing automation tool that uses **Gemini 2.5 Pro** for intelligent scene analysis, **Deepgram Aura 2** for text-to-speech narration, and **FFmpeg** for video processing.

### ✨ Features

- 🎥 **Automatic Scene Detection**: AI analyzes your video to identify the most important scenes
- 📝 **AI-Generated Narration**: Creates engaging narration for each scene that matches on-screen action
- 🔊 **Text-to-Speech**: Converts narration to natural-sounding audio using Deepgram Aura 2
- ✂️ **Automated Video Editing**: Cuts scenes, mutes original audio, and adds AI narration
- 🌐 **Google Drive Support**: Process videos directly from Google Drive URLs
- 📊 **Real-time Logging**: See detailed progress of each processing step
- 💻 **Beautiful Web Interface**: Simple and modern HTML/CSS frontend

### 🚀 How It Works

1. **Upload Video**: Provide a video file or Google Drive URL
2. **AI Analysis**: Gemini 2.5 Pro analyzes the video and identifies key scenes (8-10 seconds each)
3. **Generate Narration**: AI creates engaging narration for each scene
4. **Text-to-Speech**: Deepgram Aura 2 converts narration to high-quality audio
5. **Video Processing**: FFmpeg cuts clips, removes original audio, and adds narration
6. **Download Results**: Get individual clips and a final concatenated video

### 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+**
- **FFmpeg** (command-line tool for video processing)

#### Installing FFmpeg

**macOS** (using Homebrew):
\`\`\`bash
brew install ffmpeg
\`\`\`

**Windows** (using Chocolatey):
\`\`\`bash
choco install ffmpeg
\`\`\`

**Linux** (Ubuntu/Debian):
\`\`\`bash
sudo apt update
sudo apt install ffmpeg
\`\`\`

Verify FFmpeg installation:
\`\`\`bash
ffmpeg -version
\`\`\`

### 📦 Installation

1. **Navigate to the project directory**:
\`\`\`bash
cd "/Users/gervaciusjr/Desktop/ALL FILES/YT automation"
\`\`\`

2. **Install Python dependencies**:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 🔑 API Keys

The following API keys are already configured in \`config.py\`:

- **Gemini API Key**: [REDACTED]
- **Deepgram API Key**: [REDACTED]

> ⚠️ **Security Note**: For production use, move API keys to environment variables or a secure vault.

### 🏃 Running the Application

1. **Start the Flask server**:
\`\`\`bash
python app.py
\`\`\`

2. **Open your browser** and navigate to:
\`\`\`
http://localhost:5001
\`\`\`

3. **Upload a video** or provide a Google Drive URL

4. **Wait for processing** - The app will:
   - Analyze the video with AI
   - Generate narration for each scene
   - Create audio files
   - Process video clips
   - Provide download links

### ⚠️ Important: Audio-Video Synchronization

This system ensures that narration audio matches the exact visual content in each clip. See **[SYNCHRONIZATION_GUIDE.md](SYNCHRONIZATION_GUIDE.md)** for:
- How synchronization works
- How to verify audio matches video
- Troubleshooting sync issues
- Best practices

---

## 👗 Try On - Virtual Fitting Room

A mobile-first virtual try-on web application powered by Google's Gemini 2.5 Flash AI model. Users can upload their photos and clothing items, then use AI to visualize how clothes look on them.

![Try On App](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![React](https://img.shields.io/badge/React-18+-61dafb)

### ✨ Features

- 🔐 **User Authentication** - Secure sign up/login with JWT tokens
- 📸 **Photo Management** - Upload and manage personal photos
- 👔 **Wardrobe System** - Organize clothing items by category (tops, bottoms, dresses, outerwear, accessories)
- 🤖 **AI-Powered Virtual Try-On** - Generate realistic try-on images using Google Gemini 2.5 Flash
- 💾 **Saved Looks** - Save and manage your favorite try-on results
- 📱 **Mobile-First Design** - Optimized for mobile devices with responsive layout
- 🌓 **Dark Mode Support** - Beautiful UI in both light and dark themes

### 🏗️ Tech Stack

#### Backend
- **Flask** - Python web framework
- **SQLAlchemy** - Database ORM
- **Flask-JWT-Extended** - JWT authentication
- **Google Generative AI** - Gemini 2.5 Flash for virtual try-on
- **Pillow** - Image processing
- **SQLite** - Database (easily swappable with PostgreSQL)

#### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Zustand** - State management
- **Axios** - HTTP client

### 🚀 Getting Started (Try On)

#### 1. Backend Setup

\`\`\`bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
\`\`\`

#### 2. Frontend Setup

\`\`\`bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install
\`\`\`

#### 3. Run the Application

**Terminal 1 - Backend:**
\`\`\`bash
cd backend
source venv/bin/activate
python app.py
\`\`\`

**Terminal 2 - Frontend:**
\`\`\`bash
cd frontend
npm run dev
\`\`\`

### 📁 Project Structure

\`\`\`
YT automation/
├── app.py                    # Flask backend server (Video Automation)
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── ...
├── backend/                  # Try On Backend
│   ├── app.py
│   └── ...
├── frontend/                 # Try On Frontend
│   └── ...
\`\`\`


