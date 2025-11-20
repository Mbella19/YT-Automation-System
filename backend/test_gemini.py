import os
import sys
from dotenv import load_dotenv
from gemini_service import GeminiService
from PIL import Image

# Load environment variables
load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env")
    sys.exit(1)

print(f"✓ Found API Key: {api_key[:5]}...")

try:
    service = GeminiService(api_key)
    print("✓ GeminiService initialized")
    
    # Paths
    person_path = "/Users/gervaciusjr/.gemini/antigravity/brain/b4b763f2-92e1-46ee-bf77-724bfb7f588f/uploaded_image_1763621375335.png"
    clothing_path = "/Users/gervaciusjr/Desktop/Try on/backend/uploads/clothing/2d9d8297-8605-455a-b1fe-d3829aa5fe14.png"
    
    if not os.path.exists(person_path):
        print(f"❌ Person image not found at {person_path}")
        sys.exit(1)
        
    if not os.path.exists(clothing_path):
        print(f"❌ Clothing image not found at {clothing_path}")
        sys.exit(1)
        
    print("🤖 Testing virtual_tryon...")
    result = service.virtual_tryon(person_path, clothing_path)
    
    if result:
        print("✓ virtual_tryon successful!")
        result.save("test_result.png")
        print("✓ Saved result to test_result.png")
    else:
        print("❌ virtual_tryon returned None")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
