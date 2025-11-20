import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

from config import config
from models import db, bcrypt, User, Photo, ClothingItem, SavedLook, Challenge, ChallengeEntry
from gemini_service import GeminiService
from weather_service import WeatherService
import requests
from bs4 import BeautifulSoup
from sqlalchemy.sql.expression import func
from rembg import remove
from PIL import Image
from io import BytesIO

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({'error': 'Missing or invalid authorization token'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({'error': 'Invalid authorization token'}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    # Create upload directories
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'clothing'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'results'), exist_ok=True)
    
    # Initialize Gemini service
    gemini_service = GeminiService(app.config['GOOGLE_API_KEY'])
    
    # Initialize Weather service
    weather_service = WeatherService()
    
    # Helper functions
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def save_uploaded_file(file, folder):
        """Save uploaded file and return filepath"""
        if file and allowed_file(file.filename):
            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
            file.save(filepath)
            return filename, filepath
        return None, None
    
    # Routes
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'message': 'Try On API is running'}), 200
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """Register a new user"""
        try:
            data = request.get_json()
            
            # Validate input
            if not data or not data.get('email') or not data.get('password') or not data.get('full_name'):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Check if user exists
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Create new user
            user = User(
                full_name=data['full_name'],
                email=data['email']
            )
            user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            
            # Generate access token
            access_token = create_access_token(identity=str(user.id))
            
            return jsonify({
                'message': 'User registered successfully',
                'access_token': access_token,
                'user': user.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Login user"""
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Missing email or password'}), 400
            
            # Find user
            user = User.query.filter_by(email=data['email']).first()
            
            if not user or not user.check_password(data['password']):
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Generate access token
            access_token = create_access_token(identity=str(user.id))
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': user.to_dict()
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/user/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """Get user profile"""
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify(user.to_dict()), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/photos', methods=['GET'])
    @jwt_required()
    def get_photos():
        """Get all user photos"""
        try:
            user_id = int(get_jwt_identity())
            photos = Photo.query.filter_by(user_id=user_id).order_by(Photo.uploaded_at.desc()).all()
            
            return jsonify({
                'photos': [photo.to_dict() for photo in photos]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/photos', methods=['POST'])
    @jwt_required()
    def upload_photo():
        """Upload a new photo"""
        try:
            user_id = int(get_jwt_identity())
            
            if 'photo' not in request.files:
                return jsonify({'error': 'No photo provided'}), 400
            
            file = request.files['photo']
            filename, filepath = save_uploaded_file(file, 'photos')
            
            if not filename:
                return jsonify({'error': 'Invalid file type'}), 400
            
            # Create photo record
            photo = Photo(
                user_id=user_id,
                filename=filename,
                filepath=filepath
            )
            
            db.session.add(photo)
            db.session.commit()
            
            return jsonify({
                'message': 'Photo uploaded successfully',
                'photo': photo.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/photos/<int:photo_id>', methods=['DELETE'])
    @jwt_required()
    def delete_photo(photo_id):
        """Delete a photo"""
        try:
            user_id = int(get_jwt_identity())
            photo = Photo.query.filter_by(id=photo_id, user_id=user_id).first()
            
            if not photo:
                return jsonify({'error': 'Photo not found'}), 404
            
            # Delete file
            if not os.path.isabs(photo.filepath):
                photo_rel = photo.filepath.replace('uploads/', '', 1) if photo.filepath.startswith('uploads/') else photo.filepath
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_rel)
            else:
                photo_path = photo.filepath
            if os.path.exists(photo_path):
                os.remove(photo_path)
            
            db.session.delete(photo)
            db.session.commit()
            
            return jsonify({'message': 'Photo deleted successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/photos/<int:photo_id>/select', methods=['PUT'])
    @jwt_required()
    def select_photo(photo_id):
        """Select a photo for try-on"""
        try:
            user_id = int(get_jwt_identity())
            
            # Deselect all photos
            Photo.query.filter_by(user_id=user_id).update({'is_selected': False})
            
            # Select this photo
            photo = Photo.query.filter_by(id=photo_id, user_id=user_id).first()
            if not photo:
                return jsonify({'error': 'Photo not found'}), 404
            
            photo.is_selected = True
            db.session.commit()
            
            return jsonify({
                'message': 'Photo selected successfully',
                'photo': photo.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clothing', methods=['GET'])
    @jwt_required()
    def get_clothing():
        """Get all clothing items"""
        try:
            user_id = int(get_jwt_identity())
            category = request.args.get('category')
            
            query = ClothingItem.query.filter_by(user_id=user_id)
            if category and category != 'all':
                query = query.filter_by(category=category)
            
            items = query.order_by(ClothingItem.uploaded_at.desc()).all()
            
            return jsonify({
                'items': [item.to_dict() for item in items]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clothing', methods=['POST'])
    @jwt_required()
    def upload_clothing():
        """Upload clothing item(s)"""
        try:
            user_id = int(get_jwt_identity())
            
            if 'clothing' not in request.files:
                return jsonify({'error': 'No clothing image provided'}), 400
            
            files = request.files.getlist('clothing')
            category = request.form.get('category', 'tops')
            try:
                price = float(request.form.get('price', 0.0))
            except ValueError:
                price = 0.0
            
            uploaded_items = []
            
            for file in files:
                if not file or not allowed_file(file.filename):
                    continue
                    
                # Generate unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4()}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', filename)
                
                # Process with rembg
                try:
                    input_image = Image.open(file.stream)
                    output_image = remove(input_image)
                    output_image.save(filepath)
                except Exception as e:
                    print(f"⚠️ Background removal failed for {file.filename}: {e}")
                    # Fallback to original
                    file.seek(0)
                    file.save(filepath)
                
                # Create clothing item record
                item = ClothingItem(
                    user_id=user_id,
                    filename=filename,
                    filepath=filepath,
                    category=category,
                    price=price
                )
                
                db.session.add(item)
                uploaded_items.append(item)
            
            db.session.commit()
            
            return jsonify({
                'message': f'{len(uploaded_items)} clothing items uploaded successfully',
                'items': [item.to_dict() for item in uploaded_items]
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clothing/<int:item_id>', methods=['DELETE'])
    @jwt_required()
    def delete_clothing(item_id):
        """Delete a clothing item"""
        try:
            user_id = int(get_jwt_identity())
            item = ClothingItem.query.filter_by(id=item_id, user_id=user_id).first()
            
            if not item:
                return jsonify({'error': 'Clothing item not found'}), 404
            
            # Delete file
            if not os.path.isabs(item.filepath):
                item_rel = item.filepath.replace('uploads/', '', 1) if item.filepath.startswith('uploads/') else item.filepath
                item_path = os.path.join(app.config['UPLOAD_FOLDER'], item_rel)
            else:
                item_path = item.filepath
            if os.path.exists(item_path):
                os.remove(item_path)
            
            db.session.delete(item)
            db.session.commit()
            
            return jsonify({'message': 'Clothing item deleted successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/tryon', methods=['POST'])
    @jwt_required()
    def virtual_tryon():
        """Generate virtual try-on"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            photo_id = data.get('photo_id')
            clothing_id = data.get('clothing_id')
            
            if not photo_id or not clothing_id:
                return jsonify({'error': 'Photo ID and Clothing ID required'}), 400
            
            # Check user credits
            user = User.query.get(user_id)
            if user.credits < 1:
                return jsonify({'error': 'Insufficient credits. Watch an ad or upgrade to continue.'}), 402

            # Get photo and clothing
            photo = Photo.query.filter_by(id=photo_id, user_id=user_id).first()
            clothing = ClothingItem.query.filter_by(id=clothing_id, user_id=user_id).first()
            
            if not photo or not clothing:
                return jsonify({'error': 'Photo or clothing not found'}), 404
            
            # Construct absolute paths (handle both relative and absolute paths in DB)
            # If relative path starts with 'uploads/', strip it since UPLOAD_FOLDER already points to uploads dir
            if not os.path.isabs(photo.filepath):
                photo_rel = photo.filepath.replace('uploads/', '', 1) if photo.filepath.startswith('uploads/') else photo.filepath
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_rel)
            else:
                photo_path = photo.filepath
                
            if not os.path.isabs(clothing.filepath):
                clothing_rel = clothing.filepath.replace('uploads/', '', 1) if clothing.filepath.startswith('uploads/') else clothing.filepath
                clothing_path = os.path.join(app.config['UPLOAD_FOLDER'], clothing_rel)
            else:
                clothing_path = clothing.filepath
            
            # Generate try-on using Gemini
            clothing_desc = f"{clothing.category} ({os.path.splitext(clothing.filename)[0].replace('_', ' ')})"
            prompt = (
                f"Take the {clothing_desc} from the first image "
                "and let the person from the second image wear it. "
                "Generate a realistic, full-body shot of the person wearing the clothes, "
                "preserving their identity and facial features exactly."
            )
            
            result_image = gemini_service.virtual_tryon(photo_path, clothing_path, prompt=prompt)
            
            # Save result
            result_filename = f"{uuid.uuid4()}.png"
            result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'results', result_filename)
            result_image.save(result_filepath)
            
            # Get AI analysis from Gemini service
            ai_analysis = getattr(gemini_service, 'last_analysis', None)
            
            # Save to database
            saved_look = SavedLook(
                user_id=user_id,
                photo_id=photo_id,
                clothing_id=clothing_id,
                result_filename=result_filename,
                result_filepath=result_filepath,
                ai_analysis=ai_analysis
            )
            
            # Update stats
            user.credits -= 1
            clothing.wear_count += 1
            
            db.session.add(saved_look)
            db.session.commit()
            
            return jsonify({
                'message': 'Virtual try-on generated successfully',
                'result': saved_look.to_dict(),
                'credits_remaining': user.credits
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/style-me', methods=['POST'])
    @jwt_required()
    def style_me():
        """AI Stylist - Generate outfit recommendations based on occasion and weather"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            
            occasion = data.get('occasion', '')
            location = data.get('location', '')
            time = data.get('time', '')
            consider_weather = data.get('consider_weather', True)
            
            if not occasion or not location:
                return jsonify({'error': 'Occasion and location required'}), 400
            
            # Get user's wardrobe
            clothing_items = ClothingItem.query.filter_by(user_id=user_id).all()
            if len(clothing_items) == 0:
                return jsonify({'error': 'No clothing items in wardrobe'}), 400
            
            clothing_lookup = {item.id: item for item in clothing_items}
            
            # Ensure a base photo is selected for visualization output
            base_photo = Photo.query.filter_by(user_id=user_id, is_selected=True).first()
            if not base_photo:
                base_photo = Photo.query.filter_by(user_id=user_id).order_by(Photo.uploaded_at.desc()).first()
            if not base_photo:
                return jsonify({'error': 'Please upload and select a photo before generating a style.'}), 400
            
            # Get weather if requested
            weather_info = None
            if consider_weather:
                weather_info = weather_service.get_weather(location)
            
            # Build styling prompt for Gemini selections
            weather_context = "Weather data not considered."
            if weather_info:
                weather_context = f"Temperature: {weather_info['temperature']}°{weather_info['temperature_unit']}, Conditions: {weather_info['conditions']}"
            
            wardrobe_lines = []
            for item in clothing_items:
                display_name = os.path.splitext(item.filename)[0].replace('_', ' ')
                wardrobe_lines.append(f"{item.id}: Category={item.category}, Name={display_name}")
            wardrobe_text = "\n".join(wardrobe_lines)
            
            styling_prompt = f"""
You are an expert fashion stylist. Using the wardrobe inventory provided, build 2-3 complete outfits that fit the user request.

User Context:
- Occasion: {occasion}
- Time: {time}
- Location: {location}
- Weather: {weather_context}

Wardrobe Inventory (each item has a unique numeric id):
{wardrobe_text}

Rules:
1. Only reference item ids that exist in the wardrobe inventory.
2. Combine items into cohesive outfits that suit the occasion, location, and weather.
3. Provide a short descriptive name and explain why the outfit works.

Respond strictly in JSON with this structure:
{{
  "outfits": [
    {{
      "name": "string",
      "description": "string",
      "item_ids": [1, 2]
    }}
  ]
}}
Ensure each outfit lists at least one item id.
"""
            
            print(f"🎨 Styling request: {occasion} at {time}")
            print(f"📍 Location: {location}")
            if weather_info:
                print(f"🌡️  Weather: {weather_info['temperature']}°{weather_info['temperature_unit']}, {weather_info['conditions']}")
            
            recommendation_payload = gemini_service.recommend_outfits(styling_prompt)
            outfits = recommendation_payload.get('outfits', [])
            
            if not outfits:
                return jsonify({'error': 'Gemini did not return any outfit selections'}), 502
            
            generated_outfits = []
            for outfit in outfits:
                raw_ids = outfit.get('item_ids') or []
                try:
                    item_ids = [int(i) for i in raw_ids]
                except (TypeError, ValueError):
                    print(f"⚠️  Skipping outfit due to invalid item ids: {raw_ids}")
                    continue
                
                selected_items = []
                for item_id in item_ids:
                    item = clothing_lookup.get(item_id)
                    if item:
                        selected_items.append(item)
                    else:
                        print(f"⚠️  Item id {item_id} not found in wardrobe; skipping outfit segment.")
                
                if len(selected_items) == 0:
                    continue
                
                try:
                    prompt_items = ", ".join(
                        f"{item.category} ({os.path.splitext(item.filename)[0].replace('_', ' ')})"
                        for item in selected_items
                    )
                    image_prompt = (
                        f"Take the {prompt_items} from the clothing images "
                        "and let the person from the final image wear them. "
                        "Generate a realistic, full-body shot of the person wearing the clothes, "
                        "preserving their identity and facial features exactly."
                    )
                    
                    
                    # Construct absolute paths
                    if not os.path.isabs(base_photo.filepath):
                        base_photo_rel = base_photo.filepath.replace('uploads/', '', 1) if base_photo.filepath.startswith('uploads/') else base_photo.filepath
                        base_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], base_photo_rel)
                    else:
                        base_photo_path = base_photo.filepath
                        
                    item_paths = []
                    for item in selected_items:
                        if not os.path.isabs(item.filepath):
                            item_rel = item.filepath.replace('uploads/', '', 1) if item.filepath.startswith('uploads/') else item.filepath
                            item_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], item_rel))
                        else:
                            item_paths.append(item.filepath)
                    
                    result_image = gemini_service.virtual_tryon(
                        base_photo_path,
                        item_paths,
                        prompt=image_prompt
                    )
                    
                    result_filename = f"{uuid.uuid4()}.png"
                    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'results', result_filename)
                    result_image.save(result_filepath)
                    
                    generated_outfits.append({
                        'name': outfit.get('name') or 'Outfit',
                        'description': outfit.get('description'),
                        'item_ids': item_ids,
                        'items': [
                            {
                                'id': item.id,
                                'category': item.category,
                                'filename': item.filename,
                                'display_name': os.path.splitext(item.filename)[0].replace('_', ' ')
                            }
                            for item in selected_items
                        ],
                        'image_url': f"/uploads/results/{result_filename}",
                        'analysis': getattr(gemini_service, 'last_analysis', None)
                    })
                except Exception as outfit_error:
                    print(f"⚠️  Failed to generate visualization for outfit: {outfit_error}")
                    continue
            
            if len(generated_outfits) == 0:
                return jsonify({'error': 'Unable to generate visual outfits. Please try again.'}), 500
            
            return jsonify({
                'message': 'Outfit recommendations generated',
                'outfits': generated_outfits,
                'weather': weather_info,
                'wardrobe_items': len(clothing_items)
            }), 200
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/saved-looks', methods=['GET'])
    @jwt_required()
    def get_saved_looks():
        """Get all saved looks"""
        try:
            user_id = int(get_jwt_identity())
            looks = SavedLook.query.filter_by(user_id=user_id).order_by(SavedLook.created_at.desc()).all()
            
            return jsonify({
                'looks': [look.to_dict() for look in looks]
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/saved-looks/<int:look_id>', methods=['DELETE'])
    @jwt_required()
    def delete_saved_look(look_id):
        """Delete a saved look"""
        try:
            user_id = int(get_jwt_identity())
            look = SavedLook.query.filter_by(id=look_id, user_id=user_id).first()
            
            if not look:
                return jsonify({'error': 'Saved look not found'}), 404
            
            # Delete file
            if not os.path.isabs(look.result_filepath):
                result_rel = look.result_filepath.replace('uploads/', '', 1) if look.result_filepath.startswith('uploads/') else look.result_filepath
                result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_rel)
            else:
                result_path = look.result_filepath
            if os.path.exists(result_path):
                os.remove(result_path)
            
            db.session.delete(look)
            db.session.commit()
            
            return jsonify({'message': 'Saved look deleted successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        """Serve uploaded files"""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # --- Virality Features (Style Duels) ---
    
    @app.route('/api/challenges', methods=['GET'])
    @jwt_required()
    def get_challenges():
        """Get active challenges"""
        try:
            now = datetime.utcnow()
            # For demo, if no active challenge, create one
            active = Challenge.query.filter(Challenge.end_date > now).first()
            
            if not active:
                themes = ["Rainy Day in London", "Date Night", "Streetwear Sunday", "Office Chic", "Summer Vibes"]
                import random
                theme = random.choice(themes)
                active = Challenge(
                    theme=theme,
                    description=f"Create the best look for {theme}!",
                    end_date=now.replace(hour=23, minute=59, second=59)
                )
                db.session.add(active)
                db.session.commit()
            
            return jsonify({'challenge': active.to_dict()}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/challenges/<int:challenge_id>/enter', methods=['POST'])
    @jwt_required()
    def enter_challenge(challenge_id):
        """Enter a challenge with a saved look"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            saved_look_id = data.get('saved_look_id')
            
            if not saved_look_id:
                return jsonify({'error': 'Saved look ID required'}), 400
            
            # Check if already entered
            existing = ChallengeEntry.query.filter_by(challenge_id=challenge_id, user_id=user_id).first()
            if existing:
                return jsonify({'error': 'You have already entered this challenge'}), 400
            
            entry = ChallengeEntry(
                challenge_id=challenge_id,
                user_id=user_id,
                saved_look_id=saved_look_id
            )
            db.session.add(entry)
            db.session.commit()
            
            return jsonify({'message': 'Entered challenge successfully', 'entry': entry.to_dict()}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/challenges/<int:challenge_id>/entries', methods=['GET'])
    @jwt_required()
    def get_challenge_entries(challenge_id):
        """Get entries for a challenge to vote on"""
        try:
            user_id = int(get_jwt_identity())
            # Get entries not by current user
            entries = ChallengeEntry.query.filter(
                ChallengeEntry.challenge_id == challenge_id,
                ChallengeEntry.user_id != user_id
            ).order_by(func.random()).limit(10).all()
            
            return jsonify({'entries': [e.to_dict() for e in entries]}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/challenges/vote', methods=['POST'])
    @jwt_required()
    def vote_entry():
        """Vote for an entry"""
        try:
            data = request.get_json()
            entry_id = data.get('entry_id')
            
            entry = ChallengeEntry.query.get(entry_id)
            if not entry:
                return jsonify({'error': 'Entry not found'}), 404
            
            entry.votes += 1
            db.session.commit()
            
            return jsonify({'message': 'Vote recorded'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # --- Monetization Features ---

    @app.route('/api/credits/ad-reward', methods=['POST'])
    @jwt_required()
    def ad_reward():
        """Reward user with credit for watching ad"""
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            user.credits += 1
            db.session.commit()
            return jsonify({'message': 'Credit added', 'credits': user.credits}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # --- Retention Features ---

    @app.route('/api/daily-briefing', methods=['GET'])
    @jwt_required()
    def daily_briefing():
        """Get daily weather and style tip"""
        try:
            location = request.args.get('location', 'London')
            weather = weather_service.get_weather(location)
            
            # Simple logic for tip
            temp = weather['temperature']
            condition = weather['conditions'].lower()
            
            tip = "It's a great day to dress up!"
            if 'rain' in condition:
                tip = "Don't forget your waterproofs or umbrella!"
            elif temp < 10:
                tip = "Bundle up! It's chilly out there."
            elif temp > 25:
                tip = "Stay cool with light fabrics today."
                
            return jsonify({
                'weather': weather,
                'tip': tip
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # --- Expansion Features ---

    @app.route('/api/clothing/generate', methods=['POST'])
    @jwt_required()
    def generate_clothing():
        """Generate clothing item from text"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            description = data.get('description')
            category = data.get('category', 'tops')
            
            if not description:
                return jsonify({'error': 'Description required'}), 400
                
            image = gemini_service.generate_clothing_image(description)
            
            # Save image to temp folder first
            filename = f"temp_{uuid.uuid4()}.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', filename)
            image.save(filepath)
            
            return jsonify({
                'message': 'Preview generated',
                'temp_image_url': f"/uploads/clothing/{filename}",
                'filename': filename
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/clothing/refine', methods=['POST'])
    @jwt_required()
    def refine_clothing():
        """Refine a generated clothing item"""
        try:
            data = request.get_json()
            filename = data.get('filename')
            refinement_prompt = data.get('refinement_prompt')
            
            if not filename or not refinement_prompt:
                return jsonify({'error': 'Filename and refinement prompt required'}), 400
                
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', filename)
            if not os.path.exists(filepath):
                return jsonify({'error': 'Original image not found'}), 404
                
            image = gemini_service.refine_clothing_image(filepath, refinement_prompt)
            
            # Overwrite or create new temp file? Let's create new to allow undo if we wanted, 
            # but for now simple flow: new file
            new_filename = f"temp_{uuid.uuid4()}.png"
            new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', new_filename)
            image.save(new_filepath)
            
            # Clean up old temp file
            try:
                os.remove(filepath)
            except:
                pass
            
            return jsonify({
                'message': 'Image refined',
                'temp_image_url': f"/uploads/clothing/{new_filename}",
                'filename': new_filename
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/clothing/save-generated', methods=['POST'])
    @jwt_required()
    def save_generated_clothing():
        """Save a temporary generated item to wardrobe"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            filename = data.get('filename')
            category = data.get('category', 'tops')
            
            if not filename:
                return jsonify({'error': 'Filename required'}), 400
                
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', filename)
            if not os.path.exists(temp_filepath):
                return jsonify({'error': 'Image file not found'}), 404
                
            # Rename/Move to permanent (remove temp_ prefix if we want, or just keep unique name)
            # The filename is already unique UUID, just has temp_ prefix. That's fine.
            
            # Create item
            item = ClothingItem(
                user_id=user_id,
                category=category,
                filename=filename,
                filepath=temp_filepath,
                is_generated=True
            )
            db.session.add(item)
            db.session.commit()
            
            return jsonify({'message': 'Item added to wardrobe', 'item': item.to_dict()}), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/clothing/import', methods=['POST'])
    @jwt_required()
    def import_clothing():
        """Import clothing from URL"""
        try:
            user_id = int(get_jwt_identity())
            data = request.get_json()
            url = data.get('url')
            category = data.get('category', 'tops')
            
            if not url:
                return jsonify({'error': 'URL required'}), 400
            
            # Validate URL format
            if not url.startswith('http'):
                return jsonify({'error': 'Please enter a valid URL starting with http:// or https://'}), 400
            
            # Scraping with multiple strategies
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            img_url = None
            
            # Strategy 1: OpenGraph image
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                img_url = og_image['content']
            
            # Strategy 2: Twitter card image
            if not img_url:
                twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
                if twitter_image and twitter_image.get('content'):
                    img_url = twitter_image['content']
            
            # Strategy 3: Look for product image in common class names
            if not img_url:
                for class_name in ['product-image', 'main-image', 'primary-image', 'product-img']:
                    img_tag = soup.find('img', class_=lambda x: x and class_name in x.lower())
                    if img_tag and img_tag.get('src'):
                        img_url = img_tag['src']
                        break
            
            # Strategy 4: Find largest image
            if not img_url:
                all_imgs = soup.find_all('img', src=True)
                if all_imgs:
                    img_url = all_imgs[0].get('src')  # Take first image as fallback
            
            if not img_url:
                return jsonify({'error': 'Could not find product image on this page'}), 400
            
            # Handle relative URLs
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                from urllib.parse import urljoin
                img_url = urljoin(url, img_url)
                
            # Download image
            img_response = requests.get(img_url, headers=headers, timeout=10)
            img_response.raise_for_status()
            
            # Process image with background removal
            image = Image.open(BytesIO(img_response.content))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Apply background removal
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            output = remove(img_byte_arr)
            
            # Save processed image
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'clothing', filename)
            
            with open(filepath, 'wb') as f:
                f.write(output)
            
            item = ClothingItem(
                user_id=user_id,
                filename=filename,
                filepath=filepath,
                category=category,
                price=0.0
            )
            db.session.add(item)
            db.session.commit()
            
            return jsonify({'message': 'Clothing imported successfully', 'item': item.to_dict()}), 201
            
        except requests.RequestException as e:
            return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Import failed: {str(e)}'}), 500
    
    # Database initialization
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
