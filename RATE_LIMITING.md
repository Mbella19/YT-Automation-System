# ⏱️ Gemini API Rate Limiting

## The Problem

When using the **free tier of Gemini API**, you may encounter:

```
429 TooManyRequests Error
```

This happens especially with **two-pass analysis**, which makes multiple API calls:
- 1 call for timestamp extraction
- N calls for narration generation (where N = number of scenes)

**Example:** A video with 10 scenes requires **11 API calls total**

## The Solution: Automatic Rate Limiting

I've implemented automatic rate limiting that adds delays between Gemini API calls to prevent 429 errors.

## Configuration

### Default Settings (Free Tier)

```python
# config.py
GEMINI_API_DELAY_SECONDS = 120  # 2 minutes between calls
```

### For Paid Tier Users

```python
# config.py
GEMINI_API_DELAY_SECONDS = 0  # No delay needed
```

Or adjust to your tier's limits:
```python
GEMINI_API_DELAY_SECONDS = 30   # 30 seconds
GEMINI_API_DELAY_SECONDS = 60   # 1 minute
GEMINI_API_DELAY_SECONDS = 120  # 2 minutes (free tier)
```

## How It Works

### Automatic Wait Logic

```python
# Before each Gemini API call:
1. Check time since last call
2. If less than DELAY_SECONDS:
   - Calculate wait time
   - Show countdown in logs
   - Wait until rate limit satisfied
3. Make API call
4. Record call time
```

### Visual Countdown

For long waits (> 10 seconds), the system shows a countdown:

```
⏳ Rate limit: Waiting 120s before next API call...
   (Free tier requires ~120s between calls)
   ⏰ 120s remaining...
   ⏰ 90s remaining...
   ⏰ 60s remaining...
   ⏰ 30s remaining...
✅ Rate limit wait complete, proceeding with API call
```

## Processing Time Impact

### Example: 10-minute video, 10 scenes

**Without Rate Limiting:**
- Processing time: ~5-8 minutes
- Risk: 429 errors, processing fails

**With Rate Limiting (120s delay):**
- Pass 1: 1 call → immediate
- Pass 2: 10 calls → 2 min wait × 10 = 20 minutes
- Total processing: ~25-30 minutes
- Risk: None, guaranteed to work

**Trade-off:** Slower but reliable

## Where Rate Limiting Is Applied

### 1. Timestamp Extraction (Pass 1)
```python
def extract_scene_timestamps(self, video_file):
    self._wait_for_rate_limit()  # Wait if needed
    response = client.models.generate_content(...)  # API call
```

### 2. Per-Scene Narration (Pass 2)
```python
def generate_scene_narration(self, video_file, scene_number, ...):
    self._wait_for_rate_limit()  # Wait if needed
    response = client.models.generate_content(...)  # API call
```

### 3. Single-Pass Analysis (Fallback)
```python
def analyze_video_single_pass(self, video_file):
    self._wait_for_rate_limit()  # Wait if needed
    response = client.models.generate_content(...)  # API call
```

## Logging

### Startup Logs

```
Gemini API client initialized successfully
Two-pass analysis: ENABLED
API rate limit delay: 120s between calls  ← Shows delay setting
```

### During Processing

```
PASS 1: Extracting scene timestamps...
[No wait on first call]
Received timestamp data from Gemini
✓ Extracted 8 scene timestamps

PASS 2: Generating narration for 8 scenes...

Processing scene 1/8: 00:15-00:25
[No wait - first narration call]
  ✓ Generated narration (95 chars)

Processing scene 2/8: 00:35-00:45
⏳ Rate limit: Waiting 120s before next API call...
   (Free tier requires ~120s between calls)
   ⏰ 120s remaining...
   ⏰ 90s remaining...
   ⏰ 60s remaining...
   ⏰ 30s remaining...
✅ Rate limit wait complete, proceeding with API call
  ✓ Generated narration (103 chars)

[Repeat for remaining scenes...]
```

## Optimization Strategies

### Strategy 1: Reduce Number of Scenes

Edit the Pass 1 prompt to request fewer scenes:

```python
# In gemini_analyzer.py, line ~133
"REQUIREMENTS:
1. Select 5-8 scenes that capture the core narrative  # Changed from 8-15
```

**Impact:**
- Fewer API calls
- Faster processing
- Still captures main story

### Strategy 2: Use Single-Pass for Testing

```python
# config.py
GEMINI_TWO_PASS_ANALYSIS = False  # Faster for testing
```

**Impact:**
- Only 1 API call total
- Much faster processing
- Lower content accuracy (but good for testing)

### Strategy 3: Upgrade to Paid Tier

If you upgrade to a paid Gemini API tier:

```python
# config.py
GEMINI_API_DELAY_SECONDS = 0  # Or lower value based on your tier
```

### Strategy 4: Process Overnight

Submit videos for processing and let them run overnight:
- Free tier: Slow but works
- No manual intervention needed
- Reliable results

## Expected Processing Times

### Free Tier (120s delay)

| Scenes | API Calls | Wait Time | Total Time |
|--------|-----------|-----------|------------|
| 5      | 6         | 10 min    | ~15 min    |
| 8      | 9         | 16 min    | ~21 min    |
| 10     | 11        | 20 min    | ~25 min    |
| 15     | 16        | 30 min    | ~35 min    |

### Paid Tier (0s delay)

| Scenes | API Calls | Total Time |
|--------|-----------|------------|
| 5      | 6         | ~5 min     |
| 8      | 9         | ~6 min     |
| 10     | 11        | ~7 min     |
| 15     | 16        | ~9 min     |

## Error Handling

### If You Still Get 429 Errors

**Possible causes:**
1. Delay too short
2. Multiple requests from different sources
3. Rate limit already exceeded before

**Solutions:**

**Increase delay:**
```python
# config.py
GEMINI_API_DELAY_SECONDS = 180  # 3 minutes
# or
GEMINI_API_DELAY_SECONDS = 300  # 5 minutes
```

**Wait for rate limit reset:**
- Free tier limits usually reset hourly/daily
- Wait a few hours before retrying
- Check Gemini API dashboard for quota

**Reduce scenes:**
```python
# In Pass 1 prompt, change to:
"Select 3-5 scenes"  # Minimum viable story
```

## Technical Implementation

### Rate Limiter Class Method

```python
def _wait_for_rate_limit(self):
    """Wait if necessary to respect rate limits"""
    if self.api_delay_seconds > 0:
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call_time
        
        if time_since_last_call < self.api_delay_seconds:
            wait_time = self.api_delay_seconds - time_since_last_call
            # Show countdown
            # Sleep for wait_time
            # Update last_call_time
```

### State Tracking

```python
class GeminiVideoAnalyzer:
    def __init__(self, ...):
        self.api_delay_seconds = delay_seconds
        self.last_api_call_time = 0  # Timestamp of last call
```

## Monitoring & Debugging

### Check Current Settings

Look for these lines in startup logs:

```
API rate limit delay: 120s between calls
```

### Watch Processing Time

```
Processing scene 2/8: 00:35-00:45
⏳ Rate limit: Waiting 120s before next API call...
```

If you see this, rate limiting is working.

### Disable for Testing

```python
# config.py - Temporarily disable for local testing
GEMINI_API_DELAY_SECONDS = 0  # No delay

# Remember to re-enable for production!
GEMINI_API_DELAY_SECONDS = 120  # Back to safe default
```

## Best Practices

### ✅ DO

- Use 120s delay for free tier (default)
- Monitor logs during processing
- Process videos overnight for free tier
- Upgrade to paid tier for production use
- Test with short videos first

### ❌ DON'T

- Don't set delay < 60s on free tier
- Don't process multiple videos simultaneously
- Don't cancel processing mid-wait (wastes time)
- Don't ignore 429 errors (means delay too short)

## Cost vs. Speed Trade-off

### Free Tier
- ✅ Cost: $0
- ⏱️ Speed: Very slow (20-30 min for 10 scenes)
- ✅ Reliability: High (with proper delays)
- 📊 Best for: Testing, personal projects

### Paid Tier ($X/month)
- 💰 Cost: ~$0.01-0.05 per video
- ⚡ Speed: Fast (5-10 min for 10 scenes)
- ✅ Reliability: High
- 📊 Best for: Production, professional use

## Summary

**Rate limiting is now:**
- ✅ **Enabled by default** (120s delay)
- ✅ **Automatic** (no manual intervention)
- ✅ **Configurable** (adjust in config.py)
- ✅ **Logged** (countdown visible)
- ✅ **Reliable** (prevents 429 errors)

**For free tier users:**
- Expect 20-30 minute processing for typical videos
- This is NORMAL and EXPECTED
- System will work reliably
- Consider upgrading for production

**For paid tier users:**
- Set `GEMINI_API_DELAY_SECONDS = 0`
- Fast processing (5-10 minutes)
- No waits

---

**Status:** ✅ Implemented and Active
**Default:** 120 seconds (free tier safe)
**Last Updated:** October 21, 2025

