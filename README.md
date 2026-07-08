# 🎬 Video Editing Automation Software

An AI-powered video editing automation tool that uses **Gemini 3.5 Flash** (high thinking) for intelligent scene analysis, **Gemini native TTS** for narration, and **FFmpeg** for video processing.

## ✨ Features

- 🤖 **Fully Autonomous (no script needed)**: Leave the script blank and Gemini watches the video and *writes* the recap narration itself, with timestamps.
- 📝 **Or Bring Your Own Script**: Paste a script and the system aligns it to the exact timestamps in the video.
- 🎥 **Automatic Scene Detection**: AI identifies the most important story beats as quick clips.
- 🔊 **Text-to-Speech**: Converts narration to natural-sounding audio using Gemini's native TTS (single API key for everything).
- ✂️ **Automated Video Editing**: Cuts scenes, replaces original audio with AI narration, and keeps audio/video in sync.
- 🌐 **Google Drive Support**: Process videos directly from Google Drive URLs.
- 📊 **Real-time Logging**: Live server-sent-events log stream in the browser.
- 💻 **Web Interface**: Simple, modern dark UI.

## 🚀 How It Works

1. **Provide Video**: Upload a file or paste a Google Drive URL.
2. **(Optional) Script**: Paste a script to align, or leave it blank for autonomous generation.
3. **AI Analysis/Generation**: The video is split into 10-minute chunks; Gemini either aligns your script or writes the recap directly, returning timestamped scenes.
4. **Text-to-Speech**: Gemini native TTS converts each scene's narration to a WAV file.
5. **Video Processing**: FFmpeg cuts each clip, sets its length to the narration, and overlays the audio.
6. **Download Results**: Get individual clips, the scenes JSON, the script, and a final concatenated video.

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

Keys are loaded from a `.env` file (never commit it — it's gitignored):

```bash
cp .env.example .env
# then edit .env and set:
#   GEMINI_API_KEY=your_ai_studio_key
```

A single AI Studio Gemini key covers **both** analysis and native TTS. (Note: the
old Google Cloud TTS path required OAuth2 and does **not** accept API keys — the
system now uses Gemini's native TTS instead.)

> ⚠️ **Security Note**: If a key was ever committed to git history, rotate it — removing it from the current file does not remove it from history.

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

## ⏳ Background jobs

Processing runs on a background worker, so requests return immediately and results
survive a page refresh:

- `POST /api/process` enqueues a job and returns `202` with a `job_id`.
- The UI polls `GET /api/jobs/<job_id>` for status/stage and shows the result when done.
- Job state is persisted to `outputs/<job_id>/job.json`.

## ▶️ Optional: auto-upload to YouTube

Uploads use OAuth2 (an API key can't upload). One-time setup:

1. Enable **YouTube Data API v3** in Google Cloud Console.
2. Create an **OAuth client ID → Desktop app**, download it to `client_secrets.json`.
3. Run once: `python -m utils.youtube_uploader` and complete the sign-in.
4. Tick **Auto-upload to YouTube** in the UI (defaults to *private*). Title,
   description, and tags are generated automatically from the recap.

`client_secrets.json` and `youtube_token.json` are gitignored — never commit them.

## 📝 API Endpoints

- `GET /` - Main web interface
- `POST /api/process` - Enqueue a processing job (file upload or Google Drive URL); returns a `job_id`
- `GET /api/jobs/<job_id>` - Job status, stage, and result
- `GET /api/jobs` - List known jobs
- `GET /api/download/<session_id>/<filename>` - Download processed files
- `GET /api/youtube/status` - Whether YouTube upload is authorized
- `GET /api/status` - Health check

## 🛠️ Technologies Used

- **Backend**: Python, Flask
- **AI Analysis / Script Generation**: Google Gemini 3.5 Flash (via `google-genai`)
- **Text-to-Speech**: Gemini native TTS
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
