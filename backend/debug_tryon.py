import os
import sys
from flask import Flask
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add current dir to path
sys.path.insert(0, os.getcwd())

from app import create_app, db
from models import User, Photo, ClothingItem
from gemini_service import GeminiService

app = create_app()

def debug_tryon():
    with app.app_context():
        print("--- Starting Debug ---")
        
        # Check API Key
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return
        print(f"✅ API Key found: {api_key[:5]}...")
        
        # Get Data
        user_id = 4
        photo_id = 2
        clothing_id = 24
        
        print(f"Fetching User {user_id}, Photo {photo_id}, Clothing {clothing_id}")
        
        photo = Photo.query.get(photo_id)
        clothing = ClothingItem.query.get(clothing_id)
        
        if not photo:
            print("❌ Photo not found")
            return
        if not clothing:
            print("❌ Clothing not found")
            return
            
        print(f"Photo DB filepath: {photo.filepath}")
        print(f"Clothing DB filepath: {clothing.filepath}")
        
        # Simulate Path Construction (Current Logic)
        upload_folder = app.config['UPLOAD_FOLDER']
        print(f"UPLOAD_FOLDER: {upload_folder}")
        
        # Photo Path
        if not os.path.isabs(photo.filepath):
            photo_rel = photo.filepath.replace('uploads/', '', 1) if photo.filepath.startswith('uploads/') else photo.filepath
            photo_path = os.path.join(upload_folder, photo_rel)
        else:
            photo_path = photo.filepath
            
        # Clothing Path
        if not os.path.isabs(clothing.filepath):
            clothing_rel = clothing.filepath.replace('uploads/', '', 1) if clothing.filepath.startswith('uploads/') else clothing.filepath
            clothing_path = os.path.join(upload_folder, clothing_rel)
        else:
            clothing_path = clothing.filepath
            
        print(f"Constructed Photo Path: {photo_path}")
        print(f"Exists? {os.path.exists(photo_path)}")
        
        print(f"Constructed Clothing Path: {clothing_path}")
        print(f"Exists? {os.path.exists(clothing_path)}")
        
        if not os.path.exists(photo_path) or not os.path.exists(clothing_path):
            print("❌ Files missing, cannot proceed to Gemini")
            return

        # Initialize Service
        gemini_service = GeminiService(api_key)
        
        # Call Virtual Tryon
        print("\n--- Calling Gemini Service ---")
        try:
            result_image = gemini_service.virtual_tryon(photo_path, clothing_path)
            print("✅ Success! Image generated.")
            
            # Simulate Save
            import uuid
            from models import SavedLook
            
            result_filename = f"{uuid.uuid4()}.png"
            result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'results', result_filename)
            print(f"Saving result to: {result_filepath}")
            result_image.save(result_filepath)
            
            ai_analysis = getattr(gemini_service, 'last_analysis', None)
            
            saved_look = SavedLook(
                user_id=user_id,
                photo_id=photo_id,
                clothing_id=clothing_id,
                result_filename=result_filename,
                result_filepath=result_filepath,
                ai_analysis=ai_analysis
            )
            
            print("Attempting DB commit...")
            db.session.add(saved_look)
            db.session.commit()
            print("✅ DB Commit Successful!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_tryon()
