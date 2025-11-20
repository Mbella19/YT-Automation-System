"""
Flask backend for Video Editing Automation
"""
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    Response,
    stream_with_context,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import queue
import traceback
from datetime import datetime

# Import our utilities
from utils.logger import (
    setup_logger,
    set_session_context,
    clear_session_context,
    register_log_listener,
    unregister_log_listener,
)
from utils.drive_downloader import download_from_drive
from utils.gemini_analyzer import GeminiVideoAnalyzer
from utils.gemini_tts import GeminiTTS
from utils.video_processor import VideoProcessor
import config

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Setup logger
logger = setup_logger(log_file=config.LOG_FILE)

# Initialize services
gemini_analyzer = GeminiVideoAnalyzer(
    api_key=config.GEMINI_API_KEY,
    api_delay_seconds=config.GEMINI_API_DELAY_SECONDS,
    narration_temperature=config.GEMINI_TEMPERATURE,
    timestamp_temperature=config.GEMINI_TIMESTAMP_TEMPERATURE,
    max_retries=config.GEMINI_API_MAX_RETRIES,
    retry_backoff_seconds=config.GEMINI_API_RETRY_BACKOFF_SECONDS,
    model_name=config.GEMINI_MODEL_NAME,
    api_version=config.GEMINI_API_VERSION,
    thinking_level=config.GEMINI_THINKING_LEVEL
)
gemini_tts = GeminiTTS(
    api_key=config.GEMINI_TTS_API_KEY,
    model_name=config.GEMINI_TTS_MODEL
)
video_processor = VideoProcessor(config.FFMPEG_PATH)

logger.info(f"Two-pass analysis: {'ENABLED' if config.GEMINI_TWO_PASS_ANALYSIS else 'DISABLED'}")
logger.info(f"Gemini API rate limit: {config.GEMINI_API_DELAY_SECONDS}s delay between calls")
logger.info(f"Audio-based timing: {'ENABLED' if config.USE_AUDIO_BASED_TIMING else 'DISABLED'}")
logger.info(f"Audio start delay: {config.AUDIO_START_DELAY_MS}ms")

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
        
        # Required metadata
        movie_title = request.form.get('movie_title', '').strip()
        if not movie_title:
            logger.error("Movie title missing from request")
            return jsonify({'error': 'Please provide the movie or TV series title.'}), 400
        logger.info(f"Movie title received: {movie_title}")
        
        # Optional creator instructions
        user_instructions = request.form.get('instructions', '').strip()
        if user_instructions:
            logger.info("Custom instructions received for this session")
        else:
            user_instructions = None
        
        # Step 1: Generate recap script
        logger.info("\nStep 1: Generating grounded recap script with Gemini...")
        recap_script = gemini_analyzer.generate_recap_script(
            movie_title=movie_title,
            custom_instructions=user_instructions
        )
        script_path = session_output_dir / "recap_script.txt"
        with open(script_path, 'w', encoding='utf-8') as script_file:
            script_file.write(recap_script)
        logger.info(f"✓ Recap script saved to: {script_path}")
        
        # Step 2: Acquire the source video
        if 'drive_url' in request.form and request.form['drive_url']:
            drive_url = request.form['drive_url']
            logger.info(f"Processing Google Drive URL: {drive_url}")
            
            # Download from Google Drive
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
        
        # Step 3: Align script to video
        logger.info("\nStep 3: Aligning recap script to the video timeline...")
        scenes_data = gemini_analyzer.align_script_to_video(
            video_path=video_path,
            script_text=recap_script,
            custom_instructions=user_instructions
        )
        scenes_data['full_script'] = recap_script
        scenes_data['movie_title'] = movie_title
        
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
            return jsonify({'error': 'Unable to align the recap script to the provided video. Please verify the title and video content.'}), 400
        if skipped_scenes:
            scenes_data['skipped_scenes'] = skipped_scenes
        logger.info(f"✓ Script alignment complete. Found {len(scenes_data['scenes'])} segments")
        
        # Save scenes data
        scenes_json_path = session_output_dir / "scenes.json"
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
            start_delay_ms=config.AUDIO_START_DELAY_MS
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
            'full_script': recap_script,
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
    """Download a processed file"""
    try:
        file_path = config.OUTPUT_DIR / session_id / filename
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        logger.info(f"Serving file: {file_path}")
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def status():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'services': {
            'gemini': 'configured',
            'deepgram': 'removed',
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
    logger.info("Starting Flask server on http://127.0.0.1:5001")
    logger.info("Press CTRL+C to quit")
    app.run(debug=True, host='0.0.0.0', port=5001)
