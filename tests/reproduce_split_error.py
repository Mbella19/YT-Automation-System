
from utils.gemini_analyzer import GeminiVideoAnalyzer
import difflib

# Mock analyzer to access the helper method
class MockAnalyzer(GeminiVideoAnalyzer):
    def __init__(self):
        pass

analyzer = MockAnalyzer()

# Original script text
full_script = """
The robot learns to be gentle, to comfort, to play.
She builds him a nest, then a proper home when he outgrows it.
She teaches him to find food, to recognize danger, and to navigate the forest.
But as Brightbill becomes aware of the world around him, he also becomes aware that he's different.
These encounters wound Brightbill deeply, and he begins to question his place in the world.
He struggles with the realization that his mother is a "monster" in the eyes of others.
"""

def test_split(name, search_text, expected_found=True):
    print(f"\n--- Case: {name} ---")
    print(f"Search: '{search_text}'")
    idx = analyzer._find_script_split_point(full_script, search_text)
    
    if idx != -1:
        print(f"SUCCESS: Found at index {idx}")
        print(f"Context: ...{full_script[idx-10:idx]} [CUT] {full_script[idx:idx+10]}...")
        return True
    else:
        print("FAILED: Not found")
        return False

# Case 1: Exact match
test_split("Exact Match", "These encounters wound Brightbill deeply, and he begins to question his place in the world.")

# Case 2: Slight mismatch (AI hallucination/typo)
# "wound" -> "hurt", removed comma
test_split("Slight Mismatch", "These encounters hurt Brightbill deeply and he begins to question his place in the world.")

# Case 3: Truncated output (The log showed '...and he b...')
test_split("Truncated/Partial", "These encounters wound Brightbill deeply, and he b")

# Case 4: Completely wrong (Should fail)
test_split("Completely Wrong", "The robot decides to fly to the moon.", expected_found=False)
