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
from pathlib import Path

# Import lightweight utilities first (fast startup)
from utils.logger import (
    setup_logger,
    set_session_context,
    clear_session_context,
    register_log_listener,
    unregister_log_listener,
)
from utils.job_manager import JobManager
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

def _sanitize_session_id(raw):
    """Reduce a requested session id to a safe [alnum-_] directory name."""
    sanitized = ''.join(c for c in (raw or '') if c.isalnum() or c in {'-', '_'})
    return sanitized[:40]


def _youtube_uploader():
    from utils.youtube_uploader import YouTubeUploader
    return YouTubeUploader(
        client_secrets_file=config.YOUTUBE_CLIENT_SECRETS,
        token_file=config.YOUTUBE_TOKEN_FILE,
    )


def _youtube_authorized():
    try:
        return _youtube_uploader().is_authorized()
    except Exception:
        return False


def _maybe_upload_youtube(gemini_analyzer, final_video_path, script_text, movie_title, params):
    """Generate metadata + upload. Non-fatal: returns a dict (with 'error' on failure)."""
    try:
        metadata = gemini_analyzer.generate_youtube_metadata(script_text, movie_title)
        uploader = _youtube_uploader()
        result = uploader.upload(
            video_path=final_video_path,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            privacy_status=params.get('youtube_privacy') or config.YOUTUBE_DEFAULT_PRIVACY,
        )
        result['title'] = metadata['title']
        return result
    except Exception as exc:
        logger.error(f"YouTube upload failed (video still produced): {exc}", exc_info=True)
        return {'error': str(exc)}


def _run_pipeline(job):
    """
    Execute the full pipeline for one job. Runs on the JobManager worker thread.
    Returns the result dict; raising marks the job failed.
    """
    params = job.params
    session_id = job.job_id
    set_session_context(session_id)
    try:
        logger.info("=" * 80)
        logger.info(f"PROCESSING JOB {session_id}")
        logger.info("=" * 80)

        services = _get_services()
        gemini_analyzer = services['gemini_analyzer']
        gemini_tts = services['gemini_tts']
        video_processor = services['video_processor']

        session_dir = config.TEMP_DIR / session_id
        session_audio_dir = config.AUDIO_DIR / session_id
        session_output_dir = config.OUTPUT_DIR / session_id
        for directory in [session_dir, session_audio_dir, session_output_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        movie_title = params['movie_title']
        user_instructions = params['user_instructions']
        script_text = params['script_text']
        auto_generate = params['auto_generate']

        # Step 1: Acquire the source video (download here if it's a Drive URL).
        job.set_stage("Acquiring video")
        video_path = params.get('video_path')
        if video_path:
            video_path = Path(video_path)
            if not video_path.exists():
                raise RuntimeError("Uploaded video file is missing.")
        else:
            from utils.drive_downloader import download_from_drive
            logger.info("Downloading video from Google Drive...")
            target = session_dir / f"video_{session_id}.mp4"
            downloaded = download_from_drive(params.get('drive_url'), target)
            if not downloaded:
                raise RuntimeError("Failed to download video from Google Drive")
            video_path = Path(downloaded)
        logger.info(f"✓ Source video ready: {video_path}")

        # Step 2: Split, then ALIGN a provided script or GENERATE one.
        job.set_stage("Analyzing video")
        chunk_seconds = 600
        video_chunks = video_processor.split_video(video_path, chunk_duration=chunk_seconds)
        logger.info(f"✓ Video split into {len(video_chunks)} chunks")

        if auto_generate:
            logger.info("Autonomous mode: generating the recap from the video...")
            scenes_data = gemini_analyzer.generate_scenes_from_video(
                video_chunks=video_chunks,
                custom_instructions=user_instructions,
                chunk_seconds=chunk_seconds,
            )
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

        script_path = session_output_dir / "script.txt"
        script_path.write_text(script_text or '', encoding='utf-8')

        # Validate scenes.
        valid_scenes, skipped_scenes = [], []
        for scene in scenes_data.get('scenes', []):
            status_flag = (scene.get('status') or '').strip().lower()
            has_timestamps = bool(scene.get('start_time') and scene.get('end_time'))
            has_narration = bool(scene.get('narration') and scene['narration'].strip())
            if status_flag == 'review' or not has_timestamps or not has_narration:
                reasons = []
                if status_flag == 'review':
                    reasons.append('flagged for review')
                if not has_timestamps:
                    reasons.append('missing timestamps')
                if not has_narration:
                    reasons.append('missing narration')
                scene['skip_reason'] = ', '.join(reasons)
                skipped_scenes.append(scene)
                continue
            valid_scenes.append(scene)

        if skipped_scenes:
            logger.warning(f"Skipping {len(skipped_scenes)} segments (review/missing data).")
        scenes_data['scenes'] = valid_scenes
        if not valid_scenes:
            raise RuntimeError("No usable segments were produced from the video.")
        if skipped_scenes:
            scenes_data['skipped_scenes'] = skipped_scenes
        logger.info(f"✓ {len(valid_scenes)} usable segments")

        session_output_dir.mkdir(parents=True, exist_ok=True)
        scenes_json_path = session_output_dir / "scenes.json"
        with open(scenes_json_path, 'w', encoding='utf-8') as f:
            json.dump(scenes_data, f, indent=2)

        # Step 3: Narration audio.
        job.set_stage("Generating narration")
        audio_files = gemini_tts.generate_audio_for_scenes(scenes_data, session_audio_dir)
        logger.info(f"✓ Generated {len(audio_files)} audio files")

        # Step 4: Render clips.
        job.set_stage("Rendering clips")
        processed_clips = video_processor.process_all_clips(
            input_video=video_path,
            scenes_data=scenes_data,
            audio_files=audio_files,
            output_dir=session_output_dir,
            start_delay_ms=config.AUDIO_START_DELAY_MS,
            use_audio_timing=config.USE_AUDIO_BASED_TIMING,
        )
        logger.info(f"✓ Processed {len(processed_clips)} clips")

        # Step 5: Concatenate.
        job.set_stage("Finalizing video")
        clip_paths = [clip['clip_path'] for clip in processed_clips]
        final_video_path = session_output_dir / f"final_video_{session_id}.mp4"
        try:
            video_processor.concatenate_clips(clip_paths, final_video_path)
        except Exception as e:
            logger.warning(f"Could not concatenate clips: {str(e)}")
            final_video_path = None

        # Free disk: remove source + chunks (outputs/audio kept for download).
        try:
            if session_dir.exists():
                shutil.rmtree(session_dir)
        except Exception as e:
            logger.warning(f"Could not clean temp dir {session_dir}: {str(e)}")

        result = {
            'success': True,
            'session_id': session_id,
            'scenes_count': len(valid_scenes),
            'scenes': valid_scenes,
            'clips': processed_clips,
            'final_video': str(final_video_path) if final_video_path else None,
            'full_script': script_text,
            'movie_title': movie_title,
            'script_file': script_path.name,
            'scenes_file': scenes_json_path.name,
            'alignment_notes': scenes_data.get('notes'),
            'skipped_scenes': len(skipped_scenes),
            'skipped_scene_numbers': [s.get('scene_number') for s in skipped_scenes],
            'skipped_scene_details': [
                {'scene_number': s.get('scene_number'), 'reason': s.get('skip_reason')}
                for s in skipped_scenes
            ],
            'instructions': user_instructions,
            'youtube': None,
        }

        # Step 6 (optional): upload to YouTube. Non-fatal.
        if params.get('upload_youtube') and final_video_path:
            job.set_stage("Uploading to YouTube")
            result['youtube'] = _maybe_upload_youtube(
                gemini_analyzer, final_video_path, script_text, movie_title, params
            )

        logger.info("=" * 80)
        logger.info(f"JOB {session_id} COMPLETED")
        logger.info("=" * 80)
        return result
    finally:
        clear_session_context()


# Background job queue (single worker). Persists results to outputs/<sid>/job.json.
job_manager = JobManager(runner=_run_pipeline, state_root=config.OUTPUT_DIR)


@app.route('/api/process', methods=['POST'])
def process_video():
    """
    Enqueue a video processing job and return a job id immediately.
    Accepts a video file upload or a Google Drive URL (script optional).
    """
    try:
        session_id = _sanitize_session_id((request.form.get('session_id') or '').strip()) \
            or datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = config.TEMP_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        movie_title = request.form.get('movie_title', '').strip() or "Untitled Video"
        user_instructions = request.form.get('instructions', '').strip() or None
        script_text = request.form.get('script_text', '').strip()
        auto_generate = not script_text
        if auto_generate and not config.AUTO_GENERATE_SCRIPT:
            return jsonify({'error': 'Please provide the full script text.'}), 400

        upload_youtube = request.form.get('upload_youtube', '').strip().lower() in {'1', 'true', 'on', 'yes'}
        if upload_youtube and not _youtube_authorized():
            return jsonify({'error': 'YouTube upload requested but not authorized. '
                                     'Run `python -m utils.youtube_uploader` once to sign in.'}), 400

        params = {
            'movie_title': movie_title,
            'user_instructions': user_instructions,
            'script_text': script_text,
            'auto_generate': auto_generate,
            'upload_youtube': upload_youtube,
            'youtube_privacy': request.form.get('youtube_privacy', config.YOUTUBE_DEFAULT_PRIVACY),
        }

        # Resolve the video source synchronously (the request stream is gone once
        # we return). File uploads are saved now; Drive URLs download in the job.
        if request.form.get('drive_url', '').strip():
            params['drive_url'] = request.form['drive_url'].strip()
        elif 'video' in request.files and request.files['video'].filename:
            video_file = request.files['video']
            if not allowed_file(video_file.filename):
                return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
            save_path = session_dir / secure_filename(video_file.filename)
            video_file.save(save_path)
            params['video_path'] = str(save_path)
        else:
            return jsonify({'error': 'Please provide either a video file or Google Drive URL'}), 400

        job = job_manager.submit(session_id, params)
        return jsonify({
            'success': True,
            'job_id': session_id,
            'session_id': session_id,
            'status': job.status,
            'queue_position': job_manager.queue_position(session_id),
            'message': 'Job queued. Poll /api/jobs/<job_id> for progress.',
        }), 202

    except Exception as e:
        logger.error(f"Error queuing job: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    """Return current status/result for a job."""
    job = job_manager.get(secure_filename(job_id))
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    payload = job.to_dict()
    payload['queue_position'] = job_manager.queue_position(job.job_id)
    return jsonify(payload), 200


@app.route('/api/jobs')
def list_jobs():
    """List known jobs (most recent state, no full results)."""
    return jsonify({'jobs': job_manager.list_jobs()}), 200


@app.route('/api/youtube/status')
def youtube_status():
    """Report whether YouTube upload is authorized (token present)."""
    return jsonify({'authorized': _youtube_authorized()}), 200

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
