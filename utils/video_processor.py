"""
FFmpeg video processing utilities
"""
import subprocess
import re
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger()

class VideoProcessor:
    def __init__(self, ffmpeg_path="ffmpeg"):
        """Initialize video processor"""
        self.ffmpeg_path = ffmpeg_path
        logger.info(f"Video processor initialized with ffmpeg: {ffmpeg_path}")
        
        # Verify ffmpeg and ffprobe are available
        try:
            result = subprocess.run([ffmpeg_path, "-version"], 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                logger.info("FFmpeg is available and working")
                logger.debug(f"FFmpeg version: {result.stdout.split()[2]}")
            else:
                logger.warning("FFmpeg may not be properly installed")
        except Exception as e:
            logger.error(f"Error verifying ffmpeg: {str(e)}")
    
    def get_audio_duration(self, audio_path):
        """
        Get duration of audio file in seconds using ffprobe
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds as float
        """
        try:
            import json
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                logger.debug(f"Audio duration for {Path(audio_path).name}: {duration:.3f}s")
                return duration
            else:
                logger.error(f"ffprobe failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}", exc_info=True)
            return None
    
    def timestamp_to_seconds(self, timestamp):
        """
        Convert MM:SS or HH:MM:SS timestamp to seconds
        
        Args:
            timestamp: Time string in format MM:SS or HH:MM:SS
            
        Returns:
            Total seconds as float
        """
        parts = timestamp.split(':')
        
        if len(parts) == 2:  # MM:SS
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    def extract_and_process_clip(self, input_video, start_time, end_time, 
                                audio_path, output_path, start_delay_ms=250):
        """
        Extract video clip and overlay narration audio with perfect synchronization
        
        NEW APPROACH: Video duration is adapted to match audio duration exactly,
        preventing sync issues from mismatched lengths.
        
        Args:
            input_video: Path to input video file
            start_time: Start timestamp (MM:SS or HH:MM:SS)
            end_time: End timestamp (MM:SS or HH:MM:SS) - used as target
            audio_path: Path to narration audio file
            output_path: Path for output clip
            start_delay_ms: Optional delay in milliseconds before audio starts (default: 250ms)
            
        Returns:
            Path to processed clip
        """
        try:
            logger.info(f"Processing clip: {start_time} to {end_time}")
            
            # Get actual audio duration
            audio_duration = self.get_audio_duration(audio_path)
            if audio_duration is None:
                logger.error("Could not determine audio duration, falling back to timestamp calculation")
                start_seconds = self.timestamp_to_seconds(start_time)
                end_seconds = self.timestamp_to_seconds(end_time)
                audio_duration = end_seconds - start_seconds
            
            start_seconds = self.timestamp_to_seconds(start_time)
            target_end_seconds = self.timestamp_to_seconds(end_time)
            target_duration = target_end_seconds - start_seconds
            
            logger.info(f"Start: {start_seconds}s")
            logger.info(f"Target video duration: {target_duration:.2f}s")
            logger.info(f"Actual audio duration: {audio_duration:.2f}s")
            
            # Calculate duration difference
            duration_diff = abs(audio_duration - target_duration)
            
            if duration_diff > 0.5:
                logger.warning(f"⚠️  Audio-video duration mismatch: {duration_diff:.2f}s difference")
                logger.warning(f"    Will use AUDIO duration ({audio_duration:.2f}s) to ensure perfect sync")
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # SOLUTION: Use AUDIO duration as the final clip duration
            # This ensures narration is never cut off and video adapts to audio
            final_duration = audio_duration
            
            # Build FFmpeg command with audio-based timing
            cmd = [
                self.ffmpeg_path,
                '-y',  # Overwrite output file
                '-ss', str(start_seconds),  # Start time in video
                '-i', str(input_video),  # Input video
                '-i', str(audio_path),  # Input audio (narration)
                '-t', str(final_duration),  # Duration = AUDIO DURATION
                '-map', '0:v',  # Map video from first input
                '-map', '1:a',  # Map audio from second input (narration)
                '-c:v', 'libx264',  # Video codec
                '-preset', 'medium',  # Encoding preset
                '-crf', '23',  # Quality (18-28, lower = better)
                '-c:a', 'aac',  # Audio codec
                '-b:a', '192k',  # Audio bitrate
                # NO -shortest flag! Duration explicitly set to audio length
                str(output_path)
            ]
            
            # Optional: Add slight delay at start for better perception
            if start_delay_ms > 0:
                logger.debug(f"Adding {start_delay_ms}ms audio delay for better sync perception")
                # Insert audio filter before codec settings
                delay_filter_idx = cmd.index('-map') + 4  # After both -map commands
                cmd.insert(delay_filter_idx, '-filter:a')
                cmd.insert(delay_filter_idx + 1, f'adelay={start_delay_ms}|{start_delay_ms}')
            
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            logger.info("🎬 Using AUDIO-BASED timing for perfect synchronization")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully created clip: {output_path}")
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"Clip size: {file_size:.2f} MB")
                
                # Verify output duration matches audio
                output_duration = self.get_audio_duration(output_path)
                if output_duration:
                    sync_accuracy = abs(output_duration - audio_duration)
                    if sync_accuracy < 0.1:
                        logger.info(f"✅ Perfect sync achieved! Difference: {sync_accuracy:.3f}s")
                    else:
                        logger.warning(f"⚠️  Sync accuracy: {sync_accuracy:.2f}s difference")
                
                return output_path
            else:
                logger.error(f"FFmpeg failed with return code {result.returncode}")
                logger.error(f"FFmpeg stderr: {result.stderr}")
                raise Exception(f"FFmpeg processing failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg process timed out")
            raise Exception("Video processing timed out")
        except Exception as e:
            logger.error(f"Error processing clip: {str(e)}", exc_info=True)
            raise
    
    def process_all_clips(self, input_video, scenes_data, audio_files, output_dir, start_delay_ms=250):
        """
        Process all clips from scenes data with audio-based synchronization
        
        Args:
            input_video: Path to input video
            scenes_data: Dictionary with scenes information
            audio_files: List of audio file information
            output_dir: Directory to save processed clips
            start_delay_ms: Milliseconds of delay before audio starts (default: 250ms)
            
        Returns:
            List of processed clip paths
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Processing {len(scenes_data['scenes'])} clips with audio-based timing")
            logger.info(f"Audio start delay: {start_delay_ms}ms")
            
            processed_clips = []
            
            for i, scene in enumerate(scenes_data['scenes']):
                scene_num = scene['scene_number']
                logger.info(f"\nProcessing clip {scene_num}/{len(scenes_data['scenes'])}")
                
                # Find corresponding audio file
                audio_info = next((a for a in audio_files if a['scene_number'] == scene_num), None)
                
                if not audio_info:
                    logger.error(f"No audio file found for scene {scene_num}")
                    continue
                
                # Generate output filename
                output_filename = f"clip_{scene_num:03d}.mp4"
                output_path = output_dir / output_filename
                
                # Process clip with audio-based timing
                clip_path = self.extract_and_process_clip(
                    input_video=input_video,
                    start_time=scene['start_time'],
                    end_time=scene['end_time'],
                    audio_path=audio_info['audio_path'],
                    output_path=output_path,
                    start_delay_ms=start_delay_ms
                )
                
                processed_clips.append({
                    'scene_number': scene_num,
                    'clip_path': str(clip_path),
                    'start_time': scene['start_time'],
                    'end_time': scene['end_time']
                })
                
                logger.info(f"Completed clip {scene_num}/{len(scenes_data['scenes'])}")
            
            logger.info(f"Successfully processed {len(processed_clips)} clips")
            return processed_clips
            
        except Exception as e:
            logger.error(f"Error processing all clips: {str(e)}", exc_info=True)
            raise
    
    def concatenate_clips(self, clip_paths, output_path):
        """
        Concatenate multiple clips into a single video
        
        Args:
            clip_paths: List of paths to clips
            output_path: Path for final concatenated video
            
        Returns:
            Path to concatenated video
        """
        try:
            logger.info(f"Concatenating {len(clip_paths)} clips")
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a file list for ffmpeg
            list_file = output_path.parent / "concat_list.txt"
            
            with open(list_file, 'w') as f:
                for clip_path in clip_paths:
                    f.write(f"file '{Path(clip_path).absolute()}'\n")
            
            logger.debug(f"Created concat list file: {list_file}")
            
            # FFmpeg concatenation command
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            logger.debug(f"Concatenation command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully created final video: {output_path}")
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                logger.info(f"Final video size: {file_size:.2f} MB")
                
                # Clean up list file
                list_file.unlink()
                
                return output_path
            else:
                logger.error(f"Concatenation failed: {result.stderr}")
                raise Exception(f"Video concatenation failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error concatenating clips: {str(e)}", exc_info=True)
            raise

