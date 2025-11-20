# 🎬 Video Editing Automation Software

An AI-powered video editing automation tool that uses **Gemini 2.5 Pro** for intelligent scene analysis, **Deepgram Aura 2** for text-to-speech narration, and **FFmpeg** for video processing.

## ✨ Features

- 🎥 **Automatic Scene Detection**: AI analyzes your video to identify the most important scenes
- 📝 **AI-Generated Narration**: Creates engaging narration for each scene that matches on-screen action
- 🔊 **Text-to-Speech**: Converts narration to natural-sounding audio using Deepgram Aura 2
- ✂️ **Automated Video Editing**: Cuts scenes, mutes original audio, and adds AI narration
- 🌐 **Google Drive Support**: Process videos directly from Google Drive URLs
- 📊 **Real-time Logging**: See detailed progress of each processing step
- 💻 **Beautiful Web Interface**: Simple and modern HTML/CSS frontend

## 🚀 How It Works

1. **Upload Video**: Provide a video file or Google Drive URL
2. **AI Analysis**: Gemini 2.5 Pro analyzes the video and identifies key scenes (8-10 seconds each)
3. **Generate Narration**: AI creates engaging narration for each scene
4. **Text-to-Speech**: Deepgram Aura 2 converts narration to high-quality audio
5. **Video Processing**: FFmpeg cuts clips, removes original audio, and adds narration
6. **Download Results**: Get individual clips and a final concatenated video

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+**
- **FFmpeg** (command-line tool for video processing)

### Installing FFmpeg

**macOS** (using Homebrew):
```bash
brew install ffmpeg
```

**Windows** (using Chocolatey):
```bash
choco install ffmpeg
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install ffmpeg
```

Verify FFmpeg installation:
```bash
ffmpeg -version
```

## 📦 Installation

1. **Navigate to the project directory**:
```bash
cd "/Users/gervaciusjr/Desktop/ALL FILES/YT automation"
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

## 🔑 API Keys

The following API keys are already configured in `config.py`:

- **Gemini API Key**: AIzaSyBdVXRrKPHLi_S5SI4njHKTWzDt36V6hTc
- **Deepgram API Key**: 29d808e3ff519bf3f7427ba7f6799785ad16bb75

> ⚠️ **Security Note**: For production use, move API keys to environment variables or a secure vault.

## 🏃 Running the Application

1. **Start the Flask server**:
```bash
python app.py
```

2. **Open your browser** and navigate to:
```
http://localhost:5001
```

3. **Upload a video** or provide a Google Drive URL

4. **Wait for processing** - The app will:
   - Analyze the video with AI
   - Generate narration for each scene
   - Create audio files
   - Process video clips
   - Provide download links

## ⚠️ Important: Audio-Video Synchronization

This system ensures that narration audio matches the exact visual content in each clip. See **[SYNCHRONIZATION_GUIDE.md](SYNCHRONIZATION_GUIDE.md)** for:
- How synchronization works
- How to verify audio matches video
- Troubleshooting sync issues
- Best practices

## 📁 Project Structure

```
YT automation/
├── app.py                    # Flask backend server
├── config.py                 # Configuration and API keys
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── SYNCHRONIZATION_GUIDE.md  # Audio-video sync guide
├── FIXES.md                  # Bug fixes documentation
├── utils/                # Utility modules
│   ├── __init__.py
│   ├── logger.py         # Logging utility
│   ├── drive_downloader.py  # Google Drive downloader
│   ├── gemini_analyzer.py   # Gemini AI integration
│   ├── deepgram_tts.py      # Deepgram TTS integration
│   └── video_processor.py   # FFmpeg video processing
├── templates/            # HTML templates
│   └── index.html        # Frontend interface
├── static/               # Static files
│   ├── style.css         # Styles
│   └── script.js         # Frontend JavaScript
├── uploads/              # Temporary uploaded videos
├── outputs/              # Processed video clips
├── audio/                # Generated audio files
└── temp/                 # Temporary processing files
```

## 🎯 Usage Example

### Processing a Video from Google Drive

1. Get a public Google Drive link (e.g., `https://drive.google.com/file/d/FILE_ID/view`)
2. Paste it in the "Google Drive URL" field
3. Click "Process Video"
4. Wait for processing to complete
5. Download individual clips or the final video

### Processing a Local Video File

1. Click "Upload Video File"
2. Select a video file (MP4, AVI, MOV, MKV, etc.)
3. Click "Process Video"
4. Wait for processing to complete
5. Download results

## 📊 Output Format

The system generates:

1. **Individual Clips**: Each scene as a separate video file with AI narration
2. **Final Video**: All clips concatenated into one complete video
3. **Scenes JSON**: Detailed scene information including timestamps and narration
4. **Audio Files**: Generated narration audio for each scene

Example scenes.json:
```json
{
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "00:15",
      "end_time": "00:24",
      "duration_seconds": 9,
      "narration": "In the middle of the ocean..."
    }
  ]
}
```

## 🔍 Logging

All processing steps are logged to:
- **Console**: Real-time output
- **automation.log**: Detailed log file

View logs to track:
- Video upload/download status
- AI analysis progress
- Audio generation
- Video processing steps
- Any errors or warnings

## ⚙️ Configuration

Edit `config.py` to customize:

- API keys
- Directory paths
- Clip duration (8-10 seconds default)
- Deepgram TTS model and settings
- FFmpeg parameters

## 🐛 Troubleshooting

### FFmpeg not found
- Ensure FFmpeg is installed and in your PATH
- Test with: `ffmpeg -version`

### API errors
- Check that API keys are valid
- Verify internet connection
- Check API quota limits

### Video processing fails
- Ensure video file is not corrupted
- Check video format is supported
- Verify sufficient disk space

### Google Drive download fails
- Ensure the link is public
- Check the file is a video
- Try downloading manually first

## 📝 API Endpoints

- `GET /` - Main web interface
- `POST /api/process` - Process video (accepts file upload or Google Drive URL)
- `GET /api/download/<session_id>/<filename>` - Download processed files
- `GET /api/status` - Health check

## 🛠️ Technologies Used

- **Backend**: Python, Flask
- **AI Analysis**: Google Gemini 2.5 Pro API
- **Text-to-Speech**: Deepgram Aura 2 API
- **Video Processing**: FFmpeg
- **Frontend**: HTML5, CSS3, JavaScript
- **File Management**: Google Drive API (via gdown)

## 📄 License

This project is for educational and personal use.

## 🤝 Support

For issues or questions:
1. Check the logs in `automation.log`
2. Verify all dependencies are installed
3. Ensure API keys are valid
4. Check FFmpeg is working

## 🎉 Credits

Powered by:
- **Google Gemini 2.5 Pro** - Advanced AI video analysis
- **Deepgram Aura 2** - Natural text-to-speech
- **FFmpeg** - Powerful video processing

---

**Happy Video Editing! 🎬✨**

