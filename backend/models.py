from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New fields for Monetization & Retention
    credits = db.Column(db.Integer, default=5)
    last_daily_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    photos = db.relationship('Photo', backref='user', lazy=True, cascade='all, delete-orphan')
    clothing_items = db.relationship('ClothingItem', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_looks = db.relationship('SavedLook', backref='user', lazy=True, cascade='all, delete-orphan')
    challenge_entries = db.relationship('ChallengeEntry', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Verify the user's password"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'credits': self.credits,
            'created_at': self.created_at.isoformat()
        }

class Photo(db.Model):
    """User photos for virtual try-on"""
    __tablename__ = 'photos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    is_selected = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert photo to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': f"uploads/photos/{self.filename}",
            'is_selected': self.is_selected,
            'uploaded_at': self.uploaded_at.isoformat()
        }

class ClothingItem(db.Model):
    """Clothing items in user's wardrobe"""
    __tablename__ = 'clothing_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # tops, bottoms, dresses, outerwear, accessories
    
    # New fields for Utility
    price = db.Column(db.Float, default=0.0)
    wear_count = db.Column(db.Integer, default=0)
    is_generated = db.Column(db.Boolean, default=False)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert clothing item to dictionary"""
        cpw = 0
        if self.wear_count > 0:
            cpw = self.price / self.wear_count
        elif self.price > 0:
            cpw = self.price

        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': f"uploads/clothing/{self.filename}",
            'category': self.category,
            'price': self.price,
            'wear_count': self.wear_count,
            'cost_per_wear': round(cpw, 2),
            'uploaded_at': self.uploaded_at.isoformat()
        }

class SavedLook(db.Model):
    """Saved virtual try-on results"""
    __tablename__ = 'saved_looks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey('photos.id'), nullable=True)
    clothing_id = db.Column(db.Integer, db.ForeignKey('clothing_items.id'), nullable=True)
    result_filename = db.Column(db.String(255), nullable=False)
    result_filepath = db.Column(db.String(500), nullable=False)
    ai_analysis = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert saved look to dictionary"""
        return {
            'id': self.id,
            'photo_id': self.photo_id,
            'clothing_id': self.clothing_id,
            'result_filename': self.result_filename,
            'result_filepath': f"uploads/results/{self.result_filename}",
            'ai_analysis': self.ai_analysis,
            'created_at': self.created_at.isoformat()
        }

class Challenge(db.Model):
    """Daily Fashion Challenges"""
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    
    entries = db.relationship('ChallengeEntry', backref='challenge', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'theme': self.theme,
            'description': self.description,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'entry_count': len(self.entries)
        }

class ChallengeEntry(db.Model):
    """User entries to challenges"""
    __tablename__ = 'challenge_entries'

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    saved_look_id = db.Column(db.Integer, db.ForeignKey('saved_looks.id'), nullable=False)
    votes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    saved_look = db.relationship('SavedLook')

    def to_dict(self):
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name,
            'saved_look_url': f"/uploads/results/{self.saved_look.result_filename}",
            'votes': self.votes,
            'created_at': self.created_at.isoformat()
        }

