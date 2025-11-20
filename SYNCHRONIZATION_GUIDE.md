# 🎬 Audio-Video Synchronization Guide

## The Problem You Identified

You noticed that the **narration audio doesn't match the video clips**. For example:
- The voice might be talking about an accident
- But the video shows a scene that comes BEFORE or AFTER the accident
- This creates a confusing, out-of-sync experience

## Why This Was Happening

The original prompt wasn't explicit enough about synchronization. Gemini might:
1. Analyze the video and create a story flow
2. Generate narration that tells the story chronologically
3. But the narration for each timestamp might reference events that happen at different times
4. Result: Audio talks about Scene B while video shows Scene A

## The Solution Applied

### 1. **Completely Rewritten Gemini Prompt** ✅

The new prompt is **extremely explicit** about synchronization:

```
⚠️ CRITICAL REQUIREMENT - AUDIO-VISUAL SYNCHRONIZATION:
The narration you write for each timestamp MUST describe EXACTLY what is 
VISIBLE and HAPPENING on screen during that EXACT time period.
```

**Key improvements:**
- ✅ Explains WHY synchronization matters (audio plays over ONLY that clip)
- ✅ Provides step-by-step process for Gemini to follow
- ✅ Clear DO/DON'T rules with examples
- ✅ Example of correct vs wrong synchronization
- ✅ Emphasizes present tense for current action

**Example from prompt:**
```
If timestamp is 01:22-01:30 (showing a car crash):
✅ CORRECT: "A speeding car loses control and crashes into a barrier"
❌ WRONG: "After the argument at home, John drives away" 
          (argument happened BEFORE this timestamp)
❌ WRONG: "Paramedics will arrive soon"
          (paramedics arrive AFTER this timestamp)
```

### 2. **Lower Temperature for Consistency** ✅

Added configuration to make Gemini more focused:
```python
config=types.GenerateContentConfig(
    temperature=0.5,  # Lower = more consistent analysis
    top_p=0.95,
    top_k=40
)
```

### 3. **Enhanced Verification Logging** ✅

Added detailed logging so you can **verify synchronization** before processing:

```
================================================================================
SCENE ANALYSIS RESULTS - VERIFY SYNCHRONIZATION:
================================================================================

📍 Scene 1: 00:15 → 00:24 (9s)
🎬 Narration: [Full narration text shown here]
--------------------------------------------------------------------------------

📍 Scene 2: 00:45 → 00:53 (8s)
🎬 Narration: [Full narration text shown here]
--------------------------------------------------------------------------------

⚠️  IMPORTANT: Please verify that each narration matches the visual content
    at its specific timestamp.
```

## How to Verify Synchronization

### Method 1: Check the Logs

1. Run your video through the system
2. Look for the "SCENE ANALYSIS RESULTS" section in the logs
3. For each scene, verify:
   - Does the narration describe what's ACTUALLY in that timestamp?
   - Or does it reference earlier/later events?

### Method 2: Review the scenes.json File

The system saves `outputs/[session_id]/scenes.json` with all scene data:

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "00:15",
      "end_time": "00:24",
      "duration_seconds": 9,
      "narration": "Check if this matches 00:15-00:24 video content"
    }
  ]
}
```

**Review process:**
1. Open your original video
2. Jump to each timestamp (e.g., 00:15)
3. Watch that 8-10 second segment
4. Read the narration
5. Ask: Does the narration describe what I'm SEEING in this clip?

### Method 3: Test Individual Clips

After processing, the system creates individual clips:
- `outputs/[session_id]/clip_001.mp4`
- `outputs/[session_id]/clip_002.mp4`
- etc.

**Watch each clip:**
1. Play `clip_001.mp4`
2. Listen to the narration
3. Watch the video
4. Verify they match

## If Synchronization Still Has Issues

### Option 1: Manually Edit the JSON

1. After Gemini analyzes the video, the system saves `scenes.json`
2. Review the file
3. If any narration is out of sync, manually edit the `"narration"` field
4. Currently, you'd need to re-run just the TTS and video processing steps

### Option 2: Adjust Timestamps

If Gemini chose the wrong time range, you can:
1. Edit `scenes.json`
2. Adjust `"start_time"` and `"end_time"` to better match the narration
3. Re-run video processing

### Option 3: Re-run with Better Instructions

Sometimes being more specific helps. When uploading, you could add custom instructions about:
- Specific scenes to focus on
- Key moments you want captured
- Particular timestamp ranges to use

## Configuration Options

In `config.py`, you can adjust:

```python
# Lower temperature = more consistent analysis
GEMINI_TEMPERATURE = 0.5  # Range: 0.0 to 1.0

# Clip duration
CLIP_DURATION_MIN = 5  # seconds
CLIP_DURATION_MAX = 20  # seconds

# Enable detailed logging
VERBOSE_LOGGING = True
```

## Best Practices for Good Synchronization

1. **Use high-quality source videos**
   - Clear scenes with distinct actions
   - Good lighting and visibility
   - Clear scene transitions

2. **Ideal video structure**
   - Videos with clear story beats
   - Distinct scenes (not continuous action)
   - Each scene has unique visual content

3. **Check the logs after analysis**
   - Always review the scene analysis results
   - Verify timestamps make sense
   - Check narration matches before processing

4. **Start with shorter videos**
   - Test with 2-3 minute videos first
   - Verify synchronization quality
   - Then move to longer content

## Technical Details

### How It Works Now

1. **Gemini receives explicit instructions** about synchronization
2. **Lower temperature (0.5)** makes analysis more focused and literal
3. **Detailed logging** shows you exactly what will be narrated for each clip
4. **System processes** each clip independently:
   ```
   For Scene 1 (00:15-00:24):
   - Extract 00:15-00:24 from video
   - Generate TTS for Scene 1 narration
   - Mute original audio
   - Add Scene 1 TTS audio
   - Result: Audio matches video for this 9-second clip
   ```

### Why This Should Work Better

- **Explicit prompt** makes Gemini understand the constraint
- **Lower temperature** reduces creative interpretation
- **Examples in prompt** show correct vs wrong approach
- **Step-by-step instructions** guide Gemini's analysis process
- **Verification logging** lets you catch issues before processing

## Troubleshooting

### Issue: Narration still out of sync

**Possible causes:**
1. Video has complex storytelling (flashbacks, parallel plots)
2. Gemini is interpreting implied context
3. Timestamps chosen span multiple sub-scenes

**Solutions:**
- Try a simpler, more linear video first
- Manually review and edit scenes.json before processing
- Use shorter clips (6-7 seconds instead of 8-10)

### Issue: Timestamps don't capture key moments

**Solution:**
- Gemini 2.5 Pro should identify key moments well
- If not, you could implement a manual scene selection UI
- Or pre-process video to identify scene changes

### Issue: Too many/too few scenes

**Current behavior:**
- Gemini decides how many scenes to extract
- Aims for 8-10 second clips

**To control:**
- You could add parameters to the prompt like "Extract exactly 10 scenes"
- Or "Extract one scene every 30 seconds"

## Future Improvements

Potential enhancements for even better sync:

1. **Two-pass analysis**
   - Pass 1: Identify scene timestamps
   - Pass 2: Generate narration for specific timestamps

2. **Visual verification**
   - Extract keyframes from each timestamp
   - Show user thumbnails with proposed narration
   - Allow approval/editing before processing

3. **Scene detection**
   - Use OpenCV or similar to detect scene changes
   - Use these as candidate timestamps
   - Ask Gemini to narrate pre-selected scenes

4. **Interactive mode**
   - User reviews scenes.json
   - Can edit timestamps and narration
   - Re-process only edited clips

## Summary

✅ **Problem identified:** Audio-video synchronization mismatch  
✅ **Root cause:** Narration referencing wrong timeframes  
✅ **Solution applied:** 
   - Completely rewritten explicit prompt
   - Lower temperature for consistency
   - Enhanced verification logging
   
✅ **How to verify:** Check logs and scenes.json before processing  
✅ **Result:** Audio should now match visual content in each clip

---

**Last Updated:** October 20, 2025  
**Status:** Fixed with enhanced prompt and validation

