"""
Gemini AI video analyzer using the new google-genai library
"""
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
import json
import re
import difflib
import time
import textwrap
from pathlib import Path
import httpx
from utils.logger import setup_logger

logger = setup_logger()

# HTTP status codes worth retrying (rate limit + transient server errors)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

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
                 model_name="gemini-3.5-flash",
                 api_version=None,
                 thinking_level="high",
                 clip_min=5, clip_max=20):
        """
        Initialize Gemini API client
        
        Args:
            api_key: Gemini API key
            api_delay_seconds: Delay between API calls to avoid rate limits (default: 60s for free tier)
        """
        self.api_key = api_key
        
        # Set HTTP options
        http_options = types.HttpOptions(
            api_version=api_version if api_version else None,
            timeout=600000  # 10 minutes in milliseconds
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
        self.clip_min = clip_min
        self.clip_max = clip_max
        
        logger.info("Gemini API client initialized successfully")
        logger.info(f"API rate limit delay: {api_delay_seconds}s between calls")
        logger.info(f"Narration temperature: {narration_temperature}")
        logger.info(f"Timestamp temperature: {timestamp_temperature}")
        logger.info(f"Model: {self.model_name}")
        if api_version:
            logger.info(f"API version override: {api_version}")
        logger.info(f"Thinking level: {self.thinking_level}")
    
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

    def _extract_json_from_response(self, response_text):
        """
        Robustly extract JSON from response text that might contain markdown or conversational text.
        """
        if not response_text:
            raise ValueError("Empty response text")

        # 1. Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # 2. Try to find markdown JSON block
        # Look for ```json ... ``` or just ``` ... ```
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. Try to find just the first { and last }
        # This handles cases where there are no code blocks but there is JSON-like content
        match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
                
        raise ValueError(f"Could not extract valid JSON from response: {response_text[:100]}...")
    
    def _execute_with_retry(self, func, description):
        """
        Execute a Gemini API call with retry handling for transient failures.

        Retries on network errors (httpx) AND on transient Gemini API errors
        (429 rate limit, 5xx). Non-transient API errors (400/401/403/404) are
        re-raised immediately so we don't waste retries on a bad request/key.

        NOTE: The google-genai SDK raises google.genai.errors.APIError, which is
        NOT an httpx error — the previous version only caught httpx and therefore
        never actually retried real rate-limit/server errors.
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except genai_errors.APIError as exc:
                status = getattr(exc, "code", None)
                if status is not None and status not in _RETRYABLE_STATUS:
                    logger.error(
                        f"Gemini API error during {description}: {status} {exc}. Not retryable."
                    )
                    raise
                last_error = exc
                logger.warning(
                    f"Gemini API transient error during {description}: {status} {exc}. "
                    f"Attempt {attempt}/{self.max_retries}"
                )
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    f"Gemini API network error during {description}: {exc}. "
                    f"Attempt {attempt}/{self.max_retries}"
                )

            if attempt >= self.max_retries:
                break
            # Exponential-ish backoff; give 429s extra room.
            backoff = self.retry_backoff_seconds * attempt
            if isinstance(last_error, genai_errors.APIError) and getattr(last_error, "code", None) == 429:
                backoff = max(backoff, self.retry_backoff_seconds * 4)
            logger.info(f"Retrying {description} in {backoff}s...")
            time.sleep(backoff)

        raise RuntimeError(
            f"{description} failed after {self.max_retries} attempts. Last error: {last_error}"
        ) from last_error

    def _build_generation_config(self, temperature):
        """
        Build a GenerateContentConfig that honors the configured thinking level
        and temperature. Previously temperature was hardcoded to 0.0 and the
        thinking level was never sent at all.
        """
        kwargs = dict(
            temperature=temperature,
            top_p=0.9,
            top_k=40,
            media_resolution="MEDIA_RESOLUTION_HIGH",
        )
        if self.thinking_level:
            try:
                kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=self.thinking_level
                )
            except Exception as exc:  # older SDKs / unsupported models
                logger.debug(f"thinking_config not applied: {exc}")
        return types.GenerateContentConfig(**kwargs)

    @staticmethod
    def _seconds_to_timestamp(total_seconds):
        """Format an absolute number of seconds as HH:MM:SS.mmm."""
        total_seconds = max(0.0, float(total_seconds))
        h = int(total_seconds // 3600)
        m = int((total_seconds % 3600) // 60)
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"

    def _delete_remote_file(self, video_file):
        """Best-effort deletion of an uploaded file to avoid quota buildup."""
        name = getattr(video_file, "name", None)
        if not name:
            return
        try:
            self.client.files.delete(name=name)
            logger.debug(f"Deleted uploaded Gemini file: {name}")
        except Exception as exc:
            logger.debug(f"Could not delete uploaded file {name}: {exc}")

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

    def _find_script_split_point(self, full_text, search_text):
        """
        Find the index in full_text where search_text ends, using fuzzy matching if needed.
        Returns -1 if not found.
        """
        if not full_text or not search_text:
            return -1
            
        # 1. Try exact match first (normalized)
        def normalize(text):
            return " ".join(text.split())
            
        # Exact search for the suffix of the search text. Use a FORWARD search
        # (first occurrence): because we trim the script front-to-back, the first
        # match of this narration's tail is the correct cut point. rfind() could
        # jump too far ahead when a phrase repeats, silently dropping script.
        suffix_len = min(len(search_text), 50)
        suffix = search_text[-suffix_len:]

        idx = full_text.find(suffix)
        if idx != -1:
            return idx + len(suffix)

        # 2. Fuzzy Matching
        # If exact match fails, use difflib to find the best matching block
        logger.info("Exact match failed, trying fuzzy matching...")
        
        # We only need to search in the first part of the script if we assume sequential processing,
        # but here we search the whole thing. To optimize, we could limit scope.
        
        matcher = difflib.SequenceMatcher(None, full_text, search_text)
        match = matcher.find_longest_match(0, len(full_text), 0, len(search_text))
        
        # Check if the match is "good enough"
        # We expect a significant portion of the search_text to match
        if match.size > len(search_text) * 0.6:  # Match at least 60%
            # The match gives us the start index in full_text. 
            # We want the END of the matching segment.
            # However, the match might be in the middle of search_text.
            
            # Let's try to align the END of search_text
            end_in_full = match.a + match.size
            
            # If we matched the END of search_text, we are good
            if match.b + match.size == len(search_text):
                return end_in_full
            
            # If we matched the START or MIDDLE, we need to project where the end would be
            # This is risky if the texts diverge. 
            # Instead, let's assume the match we found is the "anchor" and we cut there.
            # But better: let's try to find the match for the SUFFIX of search_text
            
            suffix_matcher = difflib.SequenceMatcher(None, full_text, suffix)
            suffix_match = suffix_matcher.find_longest_match(0, len(full_text), 0, len(suffix))
            
            if suffix_match.size > len(suffix) * 0.6:
                return suffix_match.a + suffix_match.size
                
            # Fallback: use the main match end
            return end_in_full
            
        return -1

    def _offset_and_clamp_scenes(self, scenes, chunk_index, chunk_seconds):
        """
        Convert chunk-relative timestamps to absolute video time, clamping to the
        chunk bounds so a hallucinated timestamp can't push a clip past EOF.
        Returns the list of scenes that had usable start < end after clamping.
        """
        chunk_offset_seconds = chunk_index * chunk_seconds
        cleaned = []
        for scene in scenes:
            start_rel = self._time_to_seconds(scene.get('start_time'))
            end_rel = self._time_to_seconds(scene.get('end_time'))

            if start_rel is None or end_rel is None:
                # Unparseable timestamp(s): blank them so downstream code can't crash
                # on a truthy-but-invalid value, and the app reports it as skipped
                # ("missing timestamps") rather than raising.
                scene['start_time'] = ''
                scene['end_time'] = ''
                cleaned.append(scene)
                continue

            # Clamp into [0, chunk_seconds] and enforce ordering.
            start_rel = min(max(start_rel, 0.0), chunk_seconds)
            end_rel = min(max(end_rel, 0.0), chunk_seconds)
            if end_rel <= start_rel:
                logger.warning(
                    f"Dropping scene with non-positive duration after clamping "
                    f"(start={start_rel:.2f}s end={end_rel:.2f}s)"
                )
                continue

            scene['start_time'] = self._seconds_to_timestamp(start_rel + chunk_offset_seconds)
            scene['end_time'] = self._seconds_to_timestamp(end_rel + chunk_offset_seconds)
            scene['duration_seconds'] = round(end_rel - start_rel, 2)
            cleaned.append(scene)
        return cleaned

    def analyze_video_chunks(self, video_chunks, script_text, custom_instructions=None,
                             chunk_seconds=600):
        """
        Analyze video chunks sequentially using independent sessions with dynamic
        script trimming. Aligns a provided script to the video timeline.

        Args:
            video_chunks: List of paths to video chunk files
            script_text: Full script text to align
            custom_instructions: Optional user instructions (kept separate from the script)
            chunk_seconds: Length of each chunk in seconds (for offset + clamping)

        Returns:
            Aggregated scenes data: {"scenes": [...]}
        """
        try:
            if not video_chunks:
                raise ValueError("No video chunks provided for analysis.")
            if not script_text:
                raise ValueError("Script text is required.")

            logger.info(f"Starting sequential analysis of {len(video_chunks)} chunks with dynamic script trimming...")

            all_scenes = []
            remaining_script = script_text

            for i, chunk_path in enumerate(video_chunks):
                chunk_num = i + 1
                logger.info(f"\n--- Processing Chunk {chunk_num}/{len(video_chunks)}: {chunk_path.name} ---")
                logger.info(f"Remaining script length: {len(remaining_script)} chars")

                if len(remaining_script.strip()) < 10:
                    logger.warning("Remaining script is too short, skipping remaining chunks.")
                    break

                max_chunk_retries = self.max_retries
                chunk_retry_count = 0
                chunk_success = False

                while chunk_retry_count < max_chunk_retries and not chunk_success:
                    if chunk_retry_count > 0:
                        logger.info(f"Retrying chunk {chunk_num} (Attempt {chunk_retry_count + 1}/{max_chunk_retries})...")
                        time.sleep(self.retry_backoff_seconds)

                    video_file = None
                    try:
                        # Fresh chat per chunk so each is analyzed independently.
                        chat = self.client.chats.create(model=self.model_name)

                        self._wait_for_rate_limit()
                        video_file = self.upload_video(chunk_path)

                        file_uri = getattr(video_file, "uri", None)
                        if not file_uri:
                            raise ValueError(f"Failed to get URI for chunk {chunk_num}")

                        video_part = types.Part.from_uri(
                            file_uri=file_uri,
                            mime_type=video_file.mime_type
                        )

                        # Construct prompt with the REMAINING script only.
                        prompt_text = textwrap.dedent(f"""
                            I will upload several cut versions of 1 movie each 10min long so its easy for you too understand, and i want you too watch each part of the movie and understand it end too end then match the script to the movie with corresponding timestamps. note use only the exact words in the script nothing out of it and also always end exactly the way the script ends dont add no continuation symbols or marks always end each section exactly the way it is in the script and also i want ot to be quick cuts about {self.clip_min}secs too {self.clip_max}secs per clip and also each narration per clip should be at least 10 words long and each clip should be not be a continuation of the previous meaning if scene 1 ends at 1:25 for example, scene 2 should not start from 1:25 or 1:26, there should be at least a 10sec difference. Output JSON in this exact format:
                            {{
                              "scenes": [
                                {{
                                  "scene_number": 1,
                                  "start_time": "MM:SS",
                                  "end_time": "MM:SS",
                                  "duration_seconds": 12.5,
                                  "narration": "Exact text from script"
                                }}
                              ]
                            }}

                            SCRIPT:
                            \"\"\"{remaining_script}\"\"\"
                        """).strip()

                        if custom_instructions:
                            prompt_text += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"

                        prompt_part = types.Part.from_text(text=prompt_text)

                        logger.info(f"Sending request to Gemini for chunk {chunk_num}...")
                        gen_config = self._build_generation_config(self.timestamp_temperature)
                        response = self._execute_with_retry(
                            lambda: chat.send_message(message=[video_part, prompt_part], config=gen_config),
                            description=f"analysis of chunk {chunk_num}"
                        )

                        response_text = self._extract_response_text(response)

                        if not response_text:
                            logger.warning(f"Empty response for chunk {chunk_num}, retrying...")
                            chunk_retry_count += 1
                            continue

                        chunk_data = self._extract_json_from_response(response_text)
                        scenes = chunk_data.get("scenes", [])

                        if not scenes:
                            logger.warning(f"No scenes returned for chunk {chunk_num}")
                            chunk_retry_count += 1
                            continue

                        # Offset + clamp timestamps for THIS attempt (not yet committed).
                        attempt_scenes = self._offset_and_clamp_scenes(scenes, i, chunk_seconds)
                        if not attempt_scenes:
                            logger.warning(f"No usable scenes after clamping for chunk {chunk_num}")
                            chunk_retry_count += 1
                            continue

                        # --- DYNAMIC SCRIPT TRIMMING ---
                        last_narration = (attempt_scenes[-1].get('narration') or '').strip()
                        split_index = -1
                        if last_narration:
                            logger.info(f"Looking for split point after: '{last_narration[:50]}...'")
                            split_index = self._find_script_split_point(remaining_script, last_narration)

                        if split_index != -1:
                            all_scenes.extend(attempt_scenes)
                            prev_len = len(remaining_script)
                            remaining_script = remaining_script[split_index:].strip()
                            logger.info(f"✓ Chunk {chunk_num}: {len(attempt_scenes)} scenes. "
                                        f"Trimmed {prev_len - len(remaining_script)} chars; {len(remaining_script)} left.")
                            chunk_success = True
                        elif chunk_retry_count < max_chunk_retries - 1:
                            # Discard this attempt's scenes and retry for a cleaner split.
                            logger.warning("Could not locate split point; retrying chunk for better alignment...")
                            chunk_retry_count += 1
                            continue
                        else:
                            # Final attempt: commit scenes AND advance the script by the
                            # approximate amount consumed, so the next chunk does NOT
                            # re-process the same script (which caused duplicate scenes).
                            all_scenes.extend(attempt_scenes)
                            consumed = sum(len(s.get('narration') or '') for s in attempt_scenes)
                            prev_len = len(remaining_script)
                            remaining_script = remaining_script[consumed:].strip()
                            logger.warning(f"✓ Chunk {chunk_num}: {len(attempt_scenes)} scenes (approx trim). "
                                           f"Advanced ~{prev_len - len(remaining_script)} chars to avoid re-processing.")
                            chunk_success = True

                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON for chunk {chunk_num}.")
                        chunk_retry_count += 1
                        continue
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_num}: {str(e)}")
                        chunk_retry_count += 1
                        continue
                    finally:
                        # Always remove the uploaded chunk from Gemini to avoid quota buildup.
                        self._delete_remote_file(video_file)

            # Renumber scenes sequentially
            for idx, scene in enumerate(all_scenes, 1):
                scene['scene_number'] = idx

            return {"scenes": all_scenes}

        except Exception as e:
            logger.error(f"Error in sequential video analysis: {str(e)}", exc_info=True)
            raise

    def generate_youtube_metadata(self, script_text, movie_title=None):
        """
        Generate YouTube title, description, and tags from the recap script.
        Text-only call (cheap). Returns a dict; falls back gracefully on failure
        so a metadata hiccup never blocks the upload.
        """
        fallback = {
            "title": (movie_title or "Movie Recap")[:100],
            "description": (script_text or "")[:4900],
            "tags": ["movie recap", "recap", "movie summary"],
        }
        if not script_text or not script_text.strip():
            return fallback

        title_hint = f'The movie/series is titled "{movie_title}". ' if movie_title else ""
        prompt = textwrap.dedent(f"""
            You are a YouTube growth expert for a movie-recap channel. {title_hint}
            Based on the recap narration below, produce clickable but non-clickbait
            metadata. Output ONLY JSON:
            {{
              "title": "compelling title, <= 90 characters",
              "description": "2-3 short paragraphs summarizing the recap, then a line of relevant hashtags",
              "tags": ["10-15", "relevant", "lowercase", "search", "tags"]
            }}

            RECAP NARRATION:
            \"\"\"{script_text[:8000]}\"\"\"
        """).strip()

        try:
            self._wait_for_rate_limit()
            gen_config = self._build_generation_config(self.narration_temperature)
            response = self._execute_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=gen_config,
                ),
                description="YouTube metadata generation",
            )
            data = self._extract_json_from_response(self._extract_response_text(response))
            return {
                "title": (data.get("title") or fallback["title"])[:100],
                "description": (data.get("description") or fallback["description"])[:5000],
                "tags": data.get("tags") or fallback["tags"],
            }
        except Exception as exc:
            logger.warning(f"Metadata generation failed, using fallback: {exc}")
            return fallback

    def generate_scenes_from_video(self, video_chunks, custom_instructions=None,
                                   chunk_seconds=600):
        """
        AUTONOMOUS MODE: watch the video and WRITE the recap narration directly,
        with timestamps — no pre-written script required.

        This is what makes the system hands-off: the model both selects the story
        beats and writes movie-recap-style narration for each, so the user does not
        have to paste a script. The assembled narration is returned as `full_script`.

        Args:
            video_chunks: List of paths to video chunk files
            custom_instructions: Optional creative direction (tone, focus, etc.)
            chunk_seconds: Length of each chunk in seconds (for offset + clamping)

        Returns:
            {"scenes": [...], "full_script": "..."}
        """
        if not video_chunks:
            raise ValueError("No video chunks provided for generation.")

        logger.info(f"AUTONOMOUS generation over {len(video_chunks)} chunk(s) — no script needed.")

        all_scenes = []

        for i, chunk_path in enumerate(video_chunks):
            chunk_num = i + 1
            logger.info(f"\n--- Generating recap for Chunk {chunk_num}/{len(video_chunks)}: {chunk_path.name} ---")

            max_chunk_retries = self.max_retries
            chunk_retry_count = 0
            chunk_success = False

            while chunk_retry_count < max_chunk_retries and not chunk_success:
                if chunk_retry_count > 0:
                    logger.info(f"Retrying chunk {chunk_num} (Attempt {chunk_retry_count + 1}/{max_chunk_retries})...")
                    time.sleep(self.retry_backoff_seconds)

                video_file = None
                try:
                    chat = self.client.chats.create(model=self.model_name)
                    self._wait_for_rate_limit()
                    video_file = self.upload_video(chunk_path)

                    file_uri = getattr(video_file, "uri", None)
                    if not file_uri:
                        raise ValueError(f"Failed to get URI for chunk {chunk_num}")

                    video_part = types.Part.from_uri(file_uri=file_uri, mime_type=video_file.mime_type)

                    prompt_text = textwrap.dedent(f"""
                        You are a professional YouTube movie-recap narrator (in the style of channels like
                        Mystery Recapped or Story Recapped). Watch this ~10-minute segment of a movie end to
                        end and WRITE the recap narration yourself — do not just describe what is on screen,
                        tell the STORY: what is happening in the plot, character names, motivations and beats.

                        Rules:
                        - Present tense, engaging, story-driven narration.
                        - Pick the most important story moments as separate clips.
                        - Each clip should be {self.clip_min}–{self.clip_max} seconds long.
                        - Each narration should be at least 10 words and read naturally when spoken aloud.
                        - Clips must NOT be back-to-back: leave at least a ~10 second gap between the end of
                          one clip and the start of the next.
                        - Narration for a clip must describe ONLY what happens within that clip's timestamps
                          (no foreshadowing or backstory from outside the window).
                        - Do not include any visual stage directions or camera notes in the narration text.

                        Output ONLY JSON in exactly this format:
                        {{
                          "scenes": [
                            {{
                              "scene_number": 1,
                              "start_time": "MM:SS",
                              "end_time": "MM:SS",
                              "duration_seconds": 12.5,
                              "narration": "The written recap narration for this clip."
                            }}
                          ]
                        }}
                    """).strip()

                    if custom_instructions:
                        prompt_text += f"\n\nADDITIONAL CREATIVE DIRECTION:\n{custom_instructions}"

                    prompt_part = types.Part.from_text(text=prompt_text)

                    logger.info(f"Sending generation request to Gemini for chunk {chunk_num}...")
                    gen_config = self._build_generation_config(self.narration_temperature)
                    response = self._execute_with_retry(
                        lambda: chat.send_message(message=[video_part, prompt_part], config=gen_config),
                        description=f"recap generation for chunk {chunk_num}"
                    )

                    response_text = self._extract_response_text(response)
                    if not response_text:
                        logger.warning(f"Empty response for chunk {chunk_num}, retrying...")
                        chunk_retry_count += 1
                        continue

                    chunk_data = self._extract_json_from_response(response_text)
                    scenes = chunk_data.get("scenes", [])
                    if not scenes:
                        logger.warning(f"No scenes generated for chunk {chunk_num}")
                        chunk_retry_count += 1
                        continue

                    attempt_scenes = self._offset_and_clamp_scenes(scenes, i, chunk_seconds)
                    if not attempt_scenes:
                        logger.warning(f"No usable scenes after clamping for chunk {chunk_num}")
                        chunk_retry_count += 1
                        continue

                    all_scenes.extend(attempt_scenes)
                    logger.info(f"✓ Chunk {chunk_num}: generated {len(attempt_scenes)} scenes")
                    chunk_success = True

                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON for chunk {chunk_num}.")
                    chunk_retry_count += 1
                    continue
                except Exception as e:
                    logger.error(f"Error generating chunk {chunk_num}: {str(e)}")
                    chunk_retry_count += 1
                    continue
                finally:
                    self._delete_remote_file(video_file)

        # Renumber and assemble the full narration script from the generated scenes.
        for idx, scene in enumerate(all_scenes, 1):
            scene['scene_number'] = idx

        full_script = "\n\n".join(
            (s.get('narration') or '').strip() for s in all_scenes if (s.get('narration') or '').strip()
        )
        return {"scenes": all_scenes, "full_script": full_script}
