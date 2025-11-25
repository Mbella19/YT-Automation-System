"""
Gemini AI video analyzer using the new google-genai library
"""
from google import genai
from google.genai import types
import json
import re
import difflib
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
            
        search_norm = normalize(search_text)
        full_norm = normalize(full_text)
        
        try:
            # Try finding the exact normalized string
            norm_index = full_norm.rindex(search_norm)
            # Map back to original text is hard, so we fall back to a simpler exact search in original text
            # if the normalized one works, it gives us confidence it's there.
        except ValueError:
            pass

        # Try exact search in original text ignoring whitespace differences
        # We'll search for the last 20 chars of the search text
        suffix_len = min(len(search_text), 50)
        suffix = search_text[-suffix_len:]
        
        # Simple exact search for suffix
        idx = full_text.rfind(suffix)
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

    def analyze_video_chunks(self, video_chunks, script_text, custom_instructions=None):
        """
        Analyze video chunks sequentially using independent sessions with dynamic script trimming.
        
        Args:
            video_chunks: List of paths to video chunk files
            script_text: Full script text to align
            custom_instructions: Optional user instructions
            
        Returns:
            Aggregated scenes data
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
                
                # Create a FRESH chat session for each chunk to avoid memory pollution
                # We want each chunk to be treated independently with just the remaining script
                
                max_chunk_retries = 3
                chunk_retry_count = 0
                chunk_success = False
                
                while chunk_retry_count < max_chunk_retries and not chunk_success:
                    if chunk_retry_count > 0:
                        logger.info(f"Retrying chunk {chunk_num} (Attempt {chunk_retry_count + 1}/{max_chunk_retries})...")
                        time.sleep(5) # Wait a bit before retry
                    
                    try:
                        chat = self.client.chats.create(model=self.model_name)
                        
                        # Upload chunk
                        self._wait_for_rate_limit()
                        # If we already uploaded, we could reuse, but let's be safe and re-upload or just re-use if we had a way to check
                        # For simplicity, we re-upload or rely on the fact that upload_video might handle it (it doesn't cache currently)
                        # To avoid re-uploading every retry, we could move upload outside loop, but if upload failed, we need it inside.
                        # Let's assume upload is stable and focus on analysis retry.
                        
                        video_file = self.upload_video(chunk_path)
                        
                        file_uri = getattr(video_file, "uri", None)
                        if not file_uri:
                            raise ValueError(f"Failed to get URI for chunk {chunk_num}")
                        
                        video_part = types.Part.from_uri(
                            file_uri=file_uri,
                            mime_type=video_file.mime_type
                        )
                        
                        # Construct prompt with the REMAINING script
                        prompt_text = textwrap.dedent(f"""
                            I will upload several cut versions of 1 movie each 10min long so its easy for you too understand, and i want you too watch each part of the movie and understand it end too end then match the script to the movie with corresponding timestamps. note use only the exact words in the script nothing out of it and also always end exactly the way the script ends dont add no continuation symbols or marks always end each section exactly the way it is in the script and also i want ot to be quick cuts about 5secs too 20secs per clip and also each narration per clip should be at least 10 words long and each clip should be not be a continuation of the previous meaning if scene 1 ends at 1:25 for example, scene 2 should not start from 1:25 or 1:26, there should be at least a 10sec difference. Output JSON in this exact format:
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
                        
                        # Send message
                        logger.info(f"Sending request to Gemini for chunk {chunk_num}...")
                        response = self._execute_with_retry(
                            lambda: chat.send_message(
                                message=[video_part, prompt_part],
                                config=types.GenerateContentConfig(
                                    temperature=0.0,
                                    top_p=0.9,
                                    top_k=40,
                                    media_resolution="MEDIA_RESOLUTION_HIGH"
                                )
                            ),
                            description=f"analysis of chunk {chunk_num}"
                        )
                        
                        response_text = self._extract_response_text(response)
                        
                        # Retry if response is empty
                        if not response_text:
                            logger.warning(f"Empty response for chunk {chunk_num}, retrying...")
                            chunk_retry_count += 1
                            continue
                        
                        # Parse JSON
                        try:
                            chunk_data = self._extract_json_from_response(response_text)
                            scenes = chunk_data.get("scenes", [])
                            
                            if not scenes:
                                logger.warning(f"No scenes returned for chunk {chunk_num}")
                                chunk_retry_count += 1
                                continue
                                
                            # Adjust timestamps for chunk offset
                            chunk_offset_seconds = i * 600  # 10 minutes per chunk
                            
                            for scene in scenes:
                                # Parse relative times
                                start_rel = self._time_to_seconds(scene.get('start_time'))
                                end_rel = self._time_to_seconds(scene.get('end_time'))
                                
                                if start_rel is not None:
                                    start_abs = start_rel + chunk_offset_seconds
                                    # Format back to HH:MM:SS
                                    h = int(start_abs // 3600)
                                    m = int((start_abs % 3600) // 60)
                                    s = start_abs % 60
                                    scene['start_time'] = f"{h:02d}:{m:02d}:{s:06.3f}"
                                    
                                if end_rel is not None:
                                    end_abs = end_rel + chunk_offset_seconds
                                    h = int(end_abs // 3600)
                                    m = int((end_abs % 3600) // 60)
                                    s = end_abs % 60
                                    scene['end_time'] = f"{h:02d}:{m:02d}:{s:06.3f}"
                                    
                                # Recalculate duration
                                if start_rel is not None and end_rel is not None:
                                    scene['duration_seconds'] = round(end_rel - start_rel, 2)
                                    
                                all_scenes.append(scene)
                                
                            logger.info(f"✓ Chunk {chunk_num} processed: {len(scenes)} scenes found")
                            
                            # --- DYNAMIC SCRIPT TRIMMING ---
                            # Find the last narration in this chunk to know where to cut the script
                            last_scene = scenes[-1]
                            last_narration = last_scene.get('narration', '').strip()
                            
                            if last_narration:
                                logger.info(f"Looking for split point after: '{last_narration[:50]}...'")
                                split_index = self._find_script_split_point(remaining_script, last_narration)
                                
                                if split_index != -1:
                                    # Cut the script from this point onward
                                    prev_len = len(remaining_script)
                                    remaining_script = remaining_script[split_index:].strip()
                                    new_len = len(remaining_script)
                                    logger.info(f"✓ Script trimmed. Cut {prev_len - new_len} chars. New length: {new_len}")
                                    chunk_success = True # Success!
                                else:
                                    logger.warning("Could not find exact match for last narration to trim script.")
                                    # RETRY LOGIC for script splitting failure
                                    if chunk_retry_count < max_chunk_retries - 1:
                                        logger.warning("Retrying chunk analysis to get better script alignment...")
                                        chunk_retry_count += 1
                                        # Remove scenes from this failed attempt
                                        all_scenes = all_scenes[:-len(scenes)]
                                        continue
                                    else:
                                        logger.warning("Max retries reached. Using full remaining script for next chunk.")
                                        chunk_success = True # Accept it even if split failed, to move on
                            else:
                                logger.warning("Last scene had no narration, cannot trim script.")
                                chunk_success = True
                            
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON for chunk {chunk_num}. Response: {response_text}")
                            chunk_retry_count += 1
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_num}: {str(e)}")
                        chunk_retry_count += 1
                        continue
            
            # Renumber scenes sequentially
            for idx, scene in enumerate(all_scenes, 1):
                scene['scene_number'] = idx
                
            return {"scenes": all_scenes}
            
        except Exception as e:
            logger.error(f"Error in sequential video analysis: {str(e)}", exc_info=True)
            raise
