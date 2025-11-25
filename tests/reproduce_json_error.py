
import json
import re

def extract_json_old(response_text):
    # This mimics the logic currently in gemini_analyzer.py
    if response_text.strip().startswith("```"):
        lines = response_text.strip().splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        response_text = "\n".join(lines).strip()
    return json.loads(response_text)

def extract_json_new(response_text):
    # This will be the new logic
    try:
        # First try direct parsing
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    
    # Try to find just the first { and last }
    match = re.search(r'(\{.*\})', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
        
    raise ValueError("No JSON found")

problematic_response = """Based on the provided script and the video footage, here is the matched scene list. The script provided in the prompt starts with the "runt" storyline, which corresponds to events starting around the 4-minute mark of the video. The scenes have been reordered to match the narrative flow of the script.

```json
{
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "04:55",
      "end_time": "05:05",
      "duration_seconds": 10,
      "narration": "Most runts don't make it through their first season."
    }
  ]
}
```"""

print("Testing OLD logic:")
try:
    result = extract_json_old(problematic_response)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")

print("\nTesting NEW logic:")
try:
    result = extract_json_new(problematic_response)
    print("SUCCESS")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"FAILED: {e}")
