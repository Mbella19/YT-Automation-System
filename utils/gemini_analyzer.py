"""
Gemini AI video analyzer using the new google-genai library
"""
from google import genai
from google.genai import types
import json
import time
import textwrap
from pathlib import Path
import httpx
from utils.logger import setup_logger

logger = setup_logger()

class GeminiVideoAnalyzer:
    
    def _wait_for_rate_limit(self):
        """
        Wait if necessary to respect rate limits between API calls
        
        For free tier: Need ~2 minutes between calls
        For paid tier: Can set delay to 0
        """
        if self.api_delay_seconds > 0:
            current_time = time.time()
            time_since_last_call = current_time - self.last_api_call_time
            
            if time_since_last_call < self.api_delay_seconds and self.last_api_call_time > 0:
                wait_time = self.api_delay_seconds - time_since_last_call
                logger.info(f"⏳ Rate limit: Waiting {wait_time:.0f}s before next API call...")
                logger.info(f"   (Free tier requires ~{self.api_delay_seconds}s between calls)")
                
                # Show countdown for long waits
                if wait_time > 10:
                    for remaining in range(int(wait_time), 0, -30 if wait_time > 60 else -10):
                        if remaining <= wait_time:
                            logger.info(f"   ⏰ {remaining}s remaining...")
                            time.sleep(min(30 if wait_time > 60 else 10, remaining))
                else:
                    time.sleep(wait_time)
                
                logger.info("CORRECT: Rate limit wait complete, proceeding with API call")
            
            self.last_api_call_time = time.time()
    

    def __init__(self, api_key, api_delay_seconds=60,
                 narration_temperature=0.5, timestamp_temperature=0.2,
                 max_retries=3, retry_backoff_seconds=5,
                 model_name="gemini-3-pro-preview",
                 api_version=None,
                 thinking_level="high"):
        """
        Initialize Gemini API client
        
        Args:
            api_key: Gemini API key
            api_delay_seconds: Delay between API calls to avoid rate limits (default: 60s for free tier)
        """
        self.api_key = api_key
        
        # Create httpx client with 10-minute timeout
        custom_httpx_client = httpx.Client(
            timeout=httpx.Timeout(600.0, connect=60.0)  # 600s total, 60s connect
        )
        
        # Set HTTP options with custom client
        http_options = types.HttpOptions(
            api_version=api_version if api_version else None,
            httpx_client=custom_httpx_client
        )
        
        self.client = genai.Client(
            api_key=api_key,
            http_options=http_options
        )
        
        self.api_delay_seconds = api_delay_seconds
        self.last_api_call_time = 0  # Track last API call for rate limiting
        self.narration_temperature = narration_temperature
        self.timestamp_temperature = timestamp_temperature
        self.max_retries = max(max_retries, 1)
        self.retry_backoff_seconds = max(retry_backoff_seconds, 1)
        self.model_name = model_name
        self.thinking_level = thinking_level
        
        logger.info("Gemini API client initialized successfully")
        logger.info(f"API rate limit delay: {api_delay_seconds}s between calls")
        logger.info(f"Narration temperature: {narration_temperature}")
        logger.info(f"Timestamp temperature: {timestamp_temperature}")
        logger.info(f"Model: {self.model_name}")
        if api_version:
            logger.info(f"API version override: {api_version}")
        logger.info(f"Thinking level: {self.thinking_level}")
    
    def _format_user_instructions(self, custom_instructions):
        """
        Format optional user instructions so they can be embedded in prompts safely.
        """
        if not custom_instructions:
            return ""
        
        sanitized = custom_instructions.strip()
        if not sanitized:
            return ""
        
        return (
            "\nCREATOR DIRECTION:\n"
            f"{sanitized}\n"
            "Integrate this intent and tone while staying 100% faithful to the on-screen footage. "
            "Never invent scenes or dialogue that are not visible/heard.\n"
        )
    
    def _time_to_seconds(self, timestamp):
        """Convert a HH:MM:SS or MM:SS timestamp to seconds."""
        if timestamp is None:
            return None
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        try:
            time_str = str(timestamp).strip()
            if not time_str:
                return None
            parts = time_str.split(':')
            parts = [float(part) for part in parts]
            if len(parts) == 3:
                hours, minutes, seconds = parts
            elif len(parts) == 2:
                hours = 0.0
                minutes, seconds = parts
            elif len(parts) == 1:
                return float(parts[0])
            else:
                return None
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return None
    
    def _extract_response_text(self, response):
        """
        Normalize Gemini responses into plain text.
        
        The SDK may populate `text`, `output_text`, or embed text inside candidate parts.
        """
        if response is None:
            return ""
        
        for attr in ("text", "output_text"):
            value = getattr(response, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        
        segments = []
        try:
            candidates = getattr(response, "candidates", []) or []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None)
                if not parts:
                    continue
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        segments.append(part_text.strip())
                        continue
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and getattr(inline_data, "data", None):
                        try:
                            segments.append(inline_data.data.decode("utf-8").strip())
                        except Exception:
                            continue
        except Exception as e:
            logger.debug(f"Could not extract text from response candidates: {str(e)}", exc_info=True)
        
        combined = "\n".join(seg for seg in segments if seg)
        return combined.strip()
    
    def _execute_with_retry(self, func, description):
        """
        Execute a Gemini API call with retry handling for transient HTTP errors.
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    f"Gemini API network error during {description}: {exc}. "
                    f"Attempt {attempt}/{self.max_retries}"
                )
                if attempt >= self.max_retries:
                    break
                backoff = self.retry_backoff_seconds * attempt
                logger.info(f"Retrying {description} in {backoff}s...")
                time.sleep(backoff)
        raise RuntimeError(
            f"{description} failed after {self.max_retries} attempts due to API connectivity issues. "
            "Please try again once your network is stable."
        ) from last_error
    
    def generate_recap_script(self, movie_title, custom_instructions=None):
        """
        Generate a long-form movie recap script using Gemini with web grounding enabled.
        
        Args:
            movie_title: Title of the movie or series to recap
            custom_instructions: Optional stylistic guidance from the user
        
        Returns:
            Recap script text
        """
        try:
            if not movie_title:
                raise ValueError("Movie title is required to generate a recap script.")
            
            logger.info(f"Generating recap script for: {movie_title}")
            
            instruction_block = self._format_user_instructions(custom_instructions)
            
            # Respect rate limits ahead of the request
            self._wait_for_rate_limit()
            
            script_prompt = textwrap.dedent(f"""
                You are a seasoned storyteller creating a recap for the YouTube channel "Movie Recaps".
                Use Google Search to gather accurate, spoiler-friendly information about "{movie_title}" before writing.
                
                REQUIREMENTS:
                • Write a single continuous third-person narrative with no headings or bullet lists.
                • Match the energetic, descriptive tone used in Movie Recaps videos.
                • Break the plot down into sequential beats, but keep the output as one flowing script.
                • Include character motivations, twists, and cause-effect storytelling.
                • Do not invent events—ground every plot detail in the actual movie/series.
                • If the title cannot be verified, state that directly instead of guessing.
                • Keep the pacing engaging with natural sentence transitions (light contractions are fine).
                
                {instruction_block if instruction_block else ''}
                
                Return ONLY the final narrative script text with normal paragraph breaks. 
                Do not add markdown, headings, or commentary outside the story.
            """).strip()
            
            response = self._execute_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=[script_prompt],
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        top_p=0.95,
                        top_k=40,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                ),
                description="recap script generation"
            )
            
            script_text = self._extract_response_text(response)
            
            if not script_text:
                logger.error(f"Recap script response was empty. Raw response object: {response}")
                raise ValueError("Gemini returned an empty script.")
            
            logger.info(f"✓ Recap script generated ({len(script_text)} characters)")
            logger.debug(f"Recap script preview: {script_text[:400]}...")
            return script_text
        
        except Exception as e:
            logger.error(f"Error generating recap script: {str(e)}", exc_info=True)
            raise
    
    def align_script_to_video(self, video_path, script_text, custom_instructions=None):
        """
        Align a recap script to the uploaded video and produce timestamped segments.
        
        Args:
            video_path: Local path to the video file
            script_text: Full recap script to align
            custom_instructions: Optional stylistic guidance
        
        Returns:
            Dictionary with `scenes` array and optional notes.
        """
        try:
            if not script_text:
                raise ValueError("Cannot align script to video without script text.")
            
            logger.info("Uploading video for script alignment...")
            video_file = self.upload_video(video_path)
            
            instruction_block = self._format_user_instructions(custom_instructions)
            
            alignment_prompt = textwrap.dedent(f"""
                You are synchronizing a narrative recap script with the actual footage.
                Watch the entire video to understand the correct sequence before mapping narration segments.
                
                TASK:
                • Break the script into chronological segments that match what happens on-screen.
                • For each segment, provide the exact HH:MM:SS start and end timestamps from the video.
                • Include the corresponding narration text (verbatim or lightly smoothed) in the `narration` field.
                • Ensure the narration lines up with character actions and plot beats visible in that range.
                • CRITICAL: Watch the full movie first and understand it. Match the script with the exact moments they happen in this movie/tv series.
                • Timestamps provided MUST match perfectly with the time of the original video (e.g., 00:11 to 00:21 must match exactly on the main video).
                • Create quick, short cuts: aim for clips between 5 seconds and 15 seconds duration.
                
                {instruction_block if instruction_block else ''}
                
                SCRIPT TO ALIGN (verbatim):
                \"\"\"{script_text}\"\"\"
                
                Output JSON in this exact format:
                {{
                  "scenes": [
                    {{
                      "scene_number": 1,
                      "start_time": "HH:MM:SS",
                      "end_time": "HH:MM:SS",
                      "duration_seconds": 125.6,
                      "narration": "Narration text tied to this moment."
                    }}
                  ],
                  "notes": "Optional alignment notes for the editor."
                }}
                
                RULES:
                • Timecode format must be zero-padded HH:MM:SS (e.g., 00:05:12).
                • duration_seconds must be a positive float accurate to two decimals.
                • Ensure scene_number increases sequentially.
                • Do NOT return markdown, prose, or commentary outside the JSON.
            """).strip()
            
            # Respect rate limits before alignment call
            self._wait_for_rate_limit()
            
            file_uri = getattr(video_file, "uri", None)
            if not file_uri:
                logger.error("Uploaded video missing URI reference from Gemini")
                raise ValueError("Unable to reference uploaded video within Gemini response.")
            logger.info(f"Using Gemini file reference: {file_uri}")

            video_part = types.Part.from_uri(
                file_uri=file_uri,
                mime_type=video_file.mime_type
            )

            prompt_part = types.Part.from_text(text=alignment_prompt)

            user_content = types.Content(
                role="user",
                parts=[video_part, prompt_part]
            )

            response = self._execute_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=[user_content],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        top_p=0.9,
                        top_k=40,
                        media_resolution="MEDIA_RESOLUTION_HIGH"
                    )
                ),
                description="script-to-video alignment"
            )
            
            response_text = self._extract_response_text(response)
            
            # Clean potential markdown formatting
            if response_text.strip().startswith("```"):
                lines = response_text.strip().splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()
            
            logger.debug(f"Alignment raw response (cleaned): {response_text[:500]}...")
            
            if not response_text:
                logger.error(f"Alignment response was empty. Raw response object: {response}")
                # Check for safety blocking
                try:
                    if response.candidates and response.candidates[0].finish_reason != "STOP":
                        logger.error(f"Finish reason: {response.candidates[0].finish_reason}")
                except:
                    pass
                raise ValueError("Alignment response was empty or blocked.")
            
            try:
                alignment_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON. Raw text: {response_text}")
                raise
            
            if isinstance(alignment_data, list):
                alignment_data = {"scenes": alignment_data}
            
            scenes = alignment_data.get("scenes", [])
            if not scenes:
                raise ValueError("No scenes were returned during alignment.")
            
            for index, scene in enumerate(scenes, start=1):
                # Ensure mandatory fields exist
                scene['scene_number'] = scene.get('scene_number', index)
                
                narration_text = scene.get('narration') or scene.get('text') or ""
                scene['narration'] = narration_text.strip()
                
                start_time = scene.get('start_time')
                end_time = scene.get('end_time')
                
                if start_time and isinstance(start_time, str):
                    scene['start_time'] = start_time.strip()
                if end_time and isinstance(end_time, str):
                    scene['end_time'] = end_time.strip()
                
                # Calculate duration if missing or invalid
                duration = scene.get('duration_seconds')
                if duration in (None, "", 0):
                    start_seconds = self._time_to_seconds(scene.get('start_time'))
                    end_seconds = self._time_to_seconds(scene.get('end_time'))
                    if start_seconds is not None and end_seconds is not None:
                        computed = max(0.0, end_seconds - start_seconds)
                        scene['duration_seconds'] = round(computed, 2)
                else:
                    try:
                        scene['duration_seconds'] = round(float(duration), 2)
                    except Exception:
                        start_seconds = self._time_to_seconds(scene.get('start_time'))
                        end_seconds = self._time_to_seconds(scene.get('end_time'))
                        if start_seconds is not None and end_seconds is not None:
                            scene['duration_seconds'] = round(max(0.0, end_seconds - start_seconds), 2)
                
                # Attach original script excerpt for reference if missing
                if 'script_excerpt' not in scene:
                    scene['script_excerpt'] = scene['narration']
            
            logger.info(f"✓ Script alignment complete with {len(scenes)} segments")
            return alignment_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse alignment JSON: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error aligning script to video: {str(e)}", exc_info=True)
            raise
    
    def upload_video(self, video_path):
        """
        Upload video to Gemini
        
        Args:
            video_path: Path to video file
            
        Returns:
            Uploaded file object
        """
        try:
            logger.info(f"Uploading video to Gemini: {video_path}")
            
            # Upload the video file using the new API
            with open(video_path, 'rb') as video_file:
                uploaded_file = self.client.files.upload(
                    file=video_file,
                    config=types.UploadFileConfig(
                        mime_type='video/mp4',
                        display_name=Path(video_path).name
                    )
                )
            
            logger.info(f"Video uploaded successfully. File name: {uploaded_file.name}")
            logger.info(f"File URI: {uploaded_file.uri}")
            
            # Wait for the file to be processed
            logger.info("Waiting for video to be processed...")
            while uploaded_file.state == 'PROCESSING':
                time.sleep(2)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
                logger.debug(f"Video processing state: {uploaded_file.state}")
            
            if uploaded_file.state == 'FAILED':
                logger.error("Video processing failed")
                raise ValueError("Video processing failed")
            
            logger.info("Video processed and ready for analysis")
            return uploaded_file
            
        except Exception as e:
            logger.error(f"Error uploading video to Gemini: {str(e)}", exc_info=True)
            raise
    

    def process_video(self, video_path, movie_title=None, script_text=None, custom_instructions=None):
        """
        Complete workflow: generate recap (if needed) and align it to the video.
        
        Args:
            video_path: Path to video file
            movie_title: Title of the movie/series (required if script_text is None)
            script_text: Optional pre-generated script to align
            custom_instructions: Optional creator guidance
            
        Returns:
            Dictionary containing full script, scenes, and optional notes
        """
        try:
            logger.info(f"Starting complete video processing for: {video_path}")
            if custom_instructions:
                logger.info("Creator instructions supplied; embedding them in prompts.")
            
            if script_text is None:
                if not movie_title:
                    raise ValueError("movie_title is required when script_text is not provided.")
                script_text = self.generate_recap_script(movie_title, custom_instructions=custom_instructions)
            else:
                logger.info("Using pre-generated recap script for alignment.")
            
            alignment_data = self.align_script_to_video(
                video_path=video_path,
                script_text=script_text,
                custom_instructions=custom_instructions
            )
            
            alignment_data['full_script'] = script_text
            if movie_title:
                alignment_data['movie_title'] = movie_title
            
            logger.info("Video processing completed successfully")
            return alignment_data
            
        except Exception as e:
            logger.error(f"Error in video processing workflow: {str(e)}", exc_info=True)
            raise
