"""
Flask backend for Video Editing Automation
"""
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    Response,
    stream_with_context,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
import json
import queue
import shutil
import traceback
from datetime import datetime

# Import lightweight utilities first (fast startup)
from utils.logger import (
    setup_logger,
    set_session_context,
    clear_session_context,
    register_log_listener,
    unregister_log_listener,
)
import config

# Initialize Flask app
app = Flask(__name__)

# Restrict CORS to configured origins (default "*" for local use).
_cors_origins = [o.strip() for o in (config.CORS_ORIGINS or "*").split(",") if o.strip()]
CORS(app, resources={r"/api/*": {"origins": _cors_origins or "*"}})

# Enforce an upload size cap (0/None disables). Prevents unbounded-upload DoS.
if config.MAX_UPLOAD_MB and config.MAX_UPLOAD_MB > 0:
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_MB * 1024 * 1024

# Setup logger
logger = setup_logger(log_file=config.LOG_FILE)

# Fail fast with a clear message if the API key is missing.
if not config.GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set — copy .env.example to .env and add your key.")

# Lazy-loaded services (initialized on first request for faster startup)
_services = {
    'gemini_analyzer': None,
    'gemini_tts': None,
    'video_processor': None,
    'initialized': False
}

def _get_services():
    """Lazy initialization of heavy services on first use."""
    if not _services['initialized']:
        logger.info("Initializing services on first request...")

        # Import heavy modules only when needed
        from utils.gemini_analyzer import GeminiVideoAnalyzer
        from utils.gemini_tts import GeminiTTS
        from utils.video_processor import VideoProcessor

        _services['gemini_analyzer'] = GeminiVideoAnalyzer(
            api_key=config.GEMINI_API_KEY,
            api_delay_seconds=config.GEMINI_API_DELAY_SECONDS,
            narration_temperature=config.GEMINI_TEMPERATURE,
            timestamp_temperature=config.GEMINI_TIMESTAMP_TEMPERATURE,
            max_retries=config.GEMINI_API_MAX_RETRIES,
            retry_backoff_seconds=config.GEMINI_API_RETRY_BACKOFF_SECONDS,
            model_name=config.GEMINI_MODEL_NAME,
            api_version=config.GEMINI_API_VERSION,
            thinking_level=config.GEMINI_THINKING_LEVEL,
            clip_min=config.CLIP_DURATION_MIN,
            clip_max=config.CLIP_DURATION_MAX,
        )
        _services['gemini_tts'] = GeminiTTS(
            api_key=config.GEMINI_TTS_API_KEY,
            model_name=config.GEMINI_TTS_MODEL,
            voice_name=config.GEMINI_TTS_VOICE,
            api_version=config.GEMINI_API_VERSION,
        )
        _services['video_processor'] = VideoProcessor(config.FFMPEG_PATH)
        _services['initialized'] = True

        logger.info(f"Model: {config.GEMINI_MODEL_NAME} (thinking: {config.GEMINI_THINKING_LEVEL})")
        logger.info(f"Auto-generate script when none provided: "
                    f"{'ENABLED' if config.AUTO_GENERATE_SCRIPT else 'DISABLED'}")
        logger.info(f"Gemini API rate limit: {config.GEMINI_API_DELAY_SECONDS}s delay between calls")
        logger.info(f"Audio-based timing: {'ENABLED' if config.USE_AUDIO_BASED_TIMING else 'DISABLED'}")
        logger.info(f"Audio start delay: {config.AUDIO_START_DELAY_MS}ms")
        logger.info("Services initialized successfully")

    return _services

logger.info("=" * 80)
logger.info("Video Automation Server Starting")
logger.info("=" * 80)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main page"""
    logger.info("Main page accessed")
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_video():
    """
    Main endpoint to process video
    Accepts either a video file upload or a Google Drive URL
    """
    try:
        logger.info("=" * 80)
        logger.info("NEW VIDEO PROCESSING REQUEST")
        logger.info("=" * 80)

        # Get lazy-loaded services
        services = _get_services()
        gemini_analyzer = services['gemini_analyzer']
        gemini_tts = services['gemini_tts']
        video_processor = services['video_processor']

        video_path = None
        requested_session_id = (request.form.get('session_id') or '').strip()
        if requested_session_id:
            sanitized = ''.join(
                c for c in requested_session_id if c.isalnum() or c in {'-', '_'}
            )
            session_id = sanitized[:40] if sanitized else datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        set_session_context(session_id)
        
        # Create session-specific directories
        session_dir = config.TEMP_DIR / session_id
        session_audio_dir = config.AUDIO_DIR / session_id
        session_output_dir = config.OUTPUT_DIR / session_id
        
        for directory in [session_dir, session_audio_dir, session_output_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Session ID: {session_id}")
        
        # Optional metadata
        movie_title = request.form.get('movie_title', '').strip()
        if not movie_title:
            movie_title = "Untitled Video"
        logger.info(f"Movie title: {movie_title}")
        
        # Optional creator instructions
        user_instructions = request.form.get('instructions', '').strip()
        if user_instructions:
            logger.info("Custom instructions received for this session")
        else:
            user_instructions = None
        
        # Step 1: Get script input (optional — autonomous mode generates it).
        script_text = request.form.get('script_text', '').strip()
        auto_generate = not script_text
        if auto_generate and not config.AUTO_GENERATE_SCRIPT:
            logger.error("Script text missing and auto-generation disabled")
            return jsonify({'error': 'Please provide the full script text.'}), 400

        if auto_generate:
            logger.info("No script provided — will auto-generate the recap from the video.")
        else:
            logger.info(f"Script received: {len(script_text)} chars")
        
        # Step 2: Acquire the source video
        if 'drive_url' in request.form and request.form['drive_url']:
            drive_url = request.form['drive_url']
            logger.info(f"Processing Google Drive URL: {drive_url}")

            # Download from Google Drive (lazy import)
            from utils.drive_downloader import download_from_drive

            video_filename = f"video_{session_id}.mp4"
            video_path = session_dir / video_filename

            logger.info("Step 2: Downloading video from Google Drive...")
            downloaded_path = download_from_drive(drive_url, video_path)
            
            if not downloaded_path:
                logger.error("Failed to download video from Google Drive")
                return jsonify({'error': 'Failed to download video from Google Drive'}), 400
            
            video_path = downloaded_path
            logger.info(f"✓ Video downloaded successfully: {video_path}")
            
        elif 'video' in request.files:
            video_file = request.files['video']
            
            if video_file.filename == '':
                logger.error("No file selected")
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(video_file.filename):
                logger.error(f"Invalid file type: {video_file.filename}")
                return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
            
            filename = secure_filename(video_file.filename)
            video_path = session_dir / filename
            
            logger.info(f"Step 2: Saving uploaded video: {filename}")
            video_file.save(video_path)
            logger.info(f"✓ Video saved: {video_path}")
            
        else:
            logger.error("No video file or Google Drive URL provided")
            return jsonify({'error': 'Please provide either a video file or Google Drive URL'}), 400
        
        # Step 3: Split video, then either ALIGN a provided script or GENERATE one.
        logger.info("\nStep 3: Splitting video and building the recap...")

        chunk_seconds = 600
        # Split video into 10-minute chunks
        video_chunks = video_processor.split_video(video_path, chunk_duration=chunk_seconds)
        logger.info(f"✓ Video split into {len(video_chunks)} chunks")

        if auto_generate:
            logger.info("Autonomous mode: generating the recap script from the video...")
            scenes_data = gemini_analyzer.generate_scenes_from_video(
                video_chunks=video_chunks,
                custom_instructions=user_instructions,
                chunk_seconds=chunk_seconds,
            )
            # The generated narration becomes the script.
            script_text = scenes_data.get('full_script', '') or script_text
        else:
            scenes_data = gemini_analyzer.analyze_video_chunks(
                video_chunks=video_chunks,
                script_text=script_text,
                custom_instructions=user_instructions,
                chunk_seconds=chunk_seconds,
            )
            scenes_data['full_script'] = script_text

        scenes_data['movie_title'] = movie_title

        # Persist the final script (provided or generated) for download.
        script_path = session_output_dir / "script.txt"
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(script_text or '')
        logger.info(f"✓ Script saved to: {script_path}")
        
        valid_scenes = []
        skipped_scenes = []
        for scene in scenes_data.get('scenes', []):
            status_flag = (scene.get('status') or '').strip().lower()
            has_timestamps = bool(scene.get('start_time') and scene.get('end_time'))
            has_narration = bool(scene.get('narration') and scene['narration'].strip())
            if status_flag == 'review' or not has_timestamps or not has_narration:
                skip_reasons = []
                if status_flag == 'review':
                    skip_reasons.append('flagged for review')
                if not has_timestamps:
                    skip_reasons.append('missing timestamps')
                if not has_narration:
                    skip_reasons.append('missing narration')
                if skip_reasons:
                    scene['skip_reason'] = ', '.join(skip_reasons)
                skipped_scenes.append(scene)
                continue
            valid_scenes.append(scene)
        
        if skipped_scenes:
            logger.warning(f"Skipping {len(skipped_scenes)} segments flagged for review or missing timestamps.")
        
        scenes_data['scenes'] = valid_scenes
        if not valid_scenes:
            logger.error("Alignment returned no usable segments")
            return jsonify({'error': 'Unable to align the script to the provided video.'}), 400
        if skipped_scenes:
            scenes_data['skipped_scenes'] = skipped_scenes
        logger.info(f"✓ Script alignment complete. Found {len(scenes_data['scenes'])} segments")
        
        # Save scenes data
        scenes_json_path = session_output_dir / "scenes.json"
        
        # Robustness: Ensure directory exists (in case it was deleted during processing)
        if not session_output_dir.exists():
            logger.warning(f"Output directory missing, recreating: {session_output_dir}")
            session_output_dir.mkdir(parents=True, exist_ok=True)
            
        with open(scenes_json_path, 'w', encoding='utf-8') as f:
            json.dump(scenes_data, f, indent=2)
        logger.info(f"✓ Scenes data saved to: {scenes_json_path}")
        
        # Step 4: Generate narration audio with Gemini TTS
        logger.info("\nStep 4: Generating narration audio with Gemini TTS...")
        audio_files = gemini_tts.generate_audio_for_scenes(scenes_data, session_audio_dir)
        logger.info(f"✓ Generated {len(audio_files)} audio files")
        
        # Step 5: Process video clips with FFmpeg (audio-based timing for perfect sync)
        logger.info("\nStep 5: Processing video clips with FFmpeg...")
        processed_clips = video_processor.process_all_clips(
            input_video=video_path,
            scenes_data=scenes_data,
            audio_files=audio_files,
            output_dir=session_output_dir,
            start_delay_ms=config.AUDIO_START_DELAY_MS,
            use_audio_timing=config.USE_AUDIO_BASED_TIMING,
        )
        logger.info(f"✓ Processed {len(processed_clips)} video clips")
        
        # Step 6: Concatenate all clips (optional)
        logger.info("\nStep 6: Creating final concatenated video...")
        clip_paths = [clip['clip_path'] for clip in processed_clips]
        final_video_path = session_output_dir / f"final_video_{session_id}.mp4"
        
        try:
            video_processor.concatenate_clips(clip_paths, final_video_path)
            logger.info(f"✓ Final video created: {final_video_path}")
        except Exception as e:
            logger.warning(f"Could not concatenate clips: {str(e)}")
            final_video_path = None

        # Free disk: remove the source video + chunks now that clips are rendered.
        # (Outputs and audio are kept for download; /api/cleanup removes those later.)
        try:
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up temp source/chunks: {session_dir}")
        except Exception as e:
            logger.warning(f"Could not clean temp dir {session_dir}: {str(e)}")

        logger.info("\n" + "=" * 80)
        logger.info("VIDEO PROCESSING COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        # Prepare response
        response_data = {
            'success': True,
            'session_id': session_id,
            'scenes_count': len(scenes_data['scenes']),
            'scenes': scenes_data['scenes'],
            'clips': processed_clips,
            'final_video': str(final_video_path) if final_video_path else None,
            'full_script': script_text,
            'movie_title': movie_title,
            'script_file': script_path.name,
            'scenes_file': scenes_json_path.name,
            'alignment_notes': scenes_data.get('notes'),
            'skipped_scenes': len(scenes_data.get('skipped_scenes', [])),
            'skipped_scene_numbers': [
                scene.get('scene_number') for scene in scenes_data.get('skipped_scenes', [])
            ],
            'skipped_scene_details': [
                {
                    'scene_number': scene.get('scene_number'),
                    'reason': scene.get('skip_reason')
                }
                for scene in scenes_data.get('skipped_scenes', [])
            ],
            'message': 'Video processed successfully!'
        }
        
        if user_instructions:
            response_data['instructions'] = user_instructions
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("ERROR IN VIDEO PROCESSING")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        clear_session_context()

@app.route('/api/download/<session_id>/<filename>')
def download_file(session_id, filename):
    """Download a processed file (path-traversal safe)."""
    try:
        # Sanitize the session id to a single directory name; never allow separators.
        safe_session = secure_filename(session_id)
        session_dir = (config.OUTPUT_DIR / safe_session).resolve()

        # send_from_directory rejects filenames that escape the directory.
        logger.info(f"Serving file: {safe_session}/{filename}")
        return send_from_directory(session_dir, filename, as_attachment=True)

    except NotFound:
        logger.error(f"File not found: {session_id}/{filename}")
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_session():
    """Delete session data (path-traversal safe)."""
    try:
        session_id = (request.json or {}).get('session_id') or ''
        # Reduce to a single safe directory name: strips slashes, '..', and
        # absolute paths. Without this, a crafted session_id could rmtree
        # arbitrary directories (e.g. "../../" or "/Users/...").
        safe_session = secure_filename(str(session_id))
        if not safe_session:
            return jsonify({'error': 'Session ID required'}), 400

        logger.info(f"Cleaning up session: {safe_session}")

        base_dirs = [config.TEMP_DIR, config.AUDIO_DIR, config.OUTPUT_DIR]
        for base in base_dirs:
            directory = (base / safe_session).resolve()
            if directory.parent != base.resolve():
                logger.warning(f"Refusing to delete outside base dir: {directory}")
                continue
            if directory.exists():
                shutil.rmtree(directory)
                logger.info(f"Deleted: {directory}")

        return jsonify({'success': True, 'message': 'Session data cleaned up'}), 200

    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def status():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'services': {
            'gemini_model': config.GEMINI_MODEL_NAME,
            'gemini_tts': config.GEMINI_TTS_MODEL,
            'auto_generate_script': config.AUTO_GENERATE_SCRIPT,
            'ffmpeg': 'available'
        }
    }), 200

@app.route('/api/logs/stream')
def stream_logs():
    """Server-Sent Events endpoint for real-time logs."""
    requested_session_id = request.args.get('session_id') or None
    listener = register_log_listener(requested_session_id)
    log_queue = listener['queue']

    def event_stream():
        try:
            while True:
                try:
                    payload = log_queue.get(timeout=15)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            unregister_log_listener(listener)

    response = Response(stream_with_context(event_stream()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    logger.info(f"Starting Flask server on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    logger.info(f"Debug mode: {config.FLASK_DEBUG} (never enable debug on a public host)")
    logger.info("Press CTRL+C to quit")
    app.run(debug=config.FLASK_DEBUG, host=config.FLASK_HOST, port=config.FLASK_PORT)
