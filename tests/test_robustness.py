
import os
import shutil
from pathlib import Path
import json

# Setup test environment
TEST_DIR = Path("test_robustness_output")
if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)
TEST_DIR.mkdir()

print(f"Created test directory: {TEST_DIR}")

# Simulate the logic in app.py
session_output_dir = TEST_DIR / "session_123"
session_output_dir.mkdir()
print(f"Created session directory: {session_output_dir}")

# Simulate "accidental deletion"
print("Simulating accidental deletion...")
shutil.rmtree(session_output_dir)
if not session_output_dir.exists():
    print("Session directory deleted.")

# Run the robustness code
print("Running robustness check...")
scenes_data = {"test": "data"}
scenes_json_path = session_output_dir / "scenes.json"

# Robustness: Ensure directory exists (in case it was deleted during processing)
if not session_output_dir.exists():
    print(f"Output directory missing, recreating: {session_output_dir}")
    session_output_dir.mkdir(parents=True, exist_ok=True)

try:
    with open(scenes_json_path, 'w', encoding='utf-8') as f:
        json.dump(scenes_data, f, indent=2)
    print("SUCCESS: File written successfully after directory recreation.")
except Exception as e:
    print(f"FAILED: {e}")

# Cleanup
shutil.rmtree(TEST_DIR)
