# Try On - Virtual Fitting Room

A mobile-first virtual try-on web application powered by Google's Gemini 2.5 Flash AI model. Users can upload their photos and clothing items, then use AI to visualize how clothes look on them.

![Try On App](https://img.shields.io/badge/Status-Active-success) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![React](https://img.shields.io/badge/React-18+-61dafb)

## ✨ Features

- 🔐 **User Authentication** - Secure sign up/login with JWT tokens
- 📸 **Photo Management** - Upload and manage personal photos
- 👔 **Wardrobe System** - Organize clothing items by category (tops, bottoms, dresses, outerwear, accessories)
- 🤖 **AI-Powered Virtual Try-On** - Generate realistic try-on images using Google Gemini 2.5 Flash
- 💾 **Saved Looks** - Save and manage your favorite try-on results
- 📱 **Mobile-First Design** - Optimized for mobile devices with responsive layout
- 🌓 **Dark Mode Support** - Beautiful UI in both light and dark themes

## 🏗️ Tech Stack

### Backend
- **Flask** - Python web framework
- **SQLAlchemy** - Database ORM
- **Flask-JWT-Extended** - JWT authentication
- **Google Generative AI** - Gemini 2.5 Flash for virtual try-on
- **Pillow** - Image processing
- **SQLite** - Database (easily swappable with PostgreSQL)

### Frontend
- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Zustand** - State management
- **Axios** - HTTP client

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn
- Google API Key (for Gemini API)

## 🚀 Getting Started

### 1. Clone the Repository

```bash
cd "/Users/gervaciusjr/Desktop/Try on"
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Google API key
# GOOGLE_API_KEY=your-actual-api-key-here
```

**Get Your Google API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

### 3. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install

# The frontend is pre-configured to proxy API requests to the backend
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python app.py
```
Backend will run on `http://localhost:5000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Frontend will run on `http://localhost:3000`

### 5. Open the App

Visit `http://localhost:3000` in your mobile browser or use responsive mode in your desktop browser.

## 📱 Usage Guide

### First Time Setup

1. **Create Account**
   - Open the app and click "Try It Now"
   - Sign up with your name, email, and password
   - Or log in if you already have an account

2. **Upload Your Photo**
   - Navigate to "My Photos"
   - Click "Upload Photo"
   - Select a well-lit photo with your face clearly visible
   - The photo will be automatically selected for try-on

3. **Add Clothing Items**
   - Go to "My Wardrobe"
   - Click the "+" button
   - Select category (tops, bottoms, dresses, etc.)
   - Upload clothing item images

4. **Try On Clothes**
   - Navigate to "Try On Studio"
   - Your selected photo will appear
   - Browse and select a clothing item from your wardrobe
   - Click "Try On" to generate the virtual try-on
   - Wait for AI to process (may take 10-30 seconds)

5. **View Saved Looks**
   - All generated try-ons are automatically saved
   - Visit "My Looks" to see your collection
   - Share or delete looks as needed

## 🔧 Configuration

### Backend Environment Variables

Edit `backend/.env`:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production

# Database
DATABASE_URL=sqlite:///tryon.db

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB

# Google Gemini API
GOOGLE_API_KEY=your-google-gemini-api-key-here

# CORS (for production)
CORS_ORIGINS=http://localhost:3000
```

### Frontend Configuration

Create `frontend/.env` (optional):

```env
VITE_API_URL=http://localhost:5000/api
```

## 📁 Project Structure

```
Try on/
├── backend/
│   ├── app.py              # Flask application
│   ├── config.py           # Configuration
│   ├── models.py           # Database models
│   ├── gemini_service.py   # Gemini AI integration
│   ├── requirements.txt    # Python dependencies
│   └── uploads/            # Uploaded files storage
│       ├── photos/
│       ├── clothing/
│       └── results/
├── frontend/
│   ├── src/
│   │   ├── pages/          # React page components
│   │   │   ├── Welcome.jsx
│   │   │   ├── Auth.jsx
│   │   │   ├── Photos.jsx
│   │   │   ├── Wardrobe.jsx
│   │   │   ├── TryOnStudio.jsx
│   │   │   └── SavedLooks.jsx
│   │   ├── store/          # State management
│   │   │   └── authStore.js
│   │   ├── services/       # API services
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 🔐 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/user/profile` - Get user profile (protected)

### Photos
- `GET /api/photos` - Get all user photos (protected)
- `POST /api/photos` - Upload photo (protected)
- `DELETE /api/photos/:id` - Delete photo (protected)
- `PUT /api/photos/:id/select` - Select photo for try-on (protected)

### Clothing
- `GET /api/clothing?category=all` - Get clothing items (protected)
- `POST /api/clothing` - Upload clothing item (protected)
- `DELETE /api/clothing/:id` - Delete clothing item (protected)

### Virtual Try-On
- `POST /api/tryon` - Generate virtual try-on (protected)
- `GET /api/saved-looks` - Get saved looks (protected)
- `DELETE /api/saved-looks/:id` - Delete saved look (protected)

## 🎨 Design Inspiration

- **Sephora Virtual Artist** - Intuitive photo upload flow
- **ASOS See My Fit** - Clean result displays
- **Mobile-first approach** - Optimized for touch interactions

## 🐛 Troubleshooting

### Backend Issues

**Error: No module named 'flask'**
```bash
# Make sure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Error: Google API key not found**
- Check that `.env` file exists in backend directory
- Verify `GOOGLE_API_KEY` is set correctly
- Restart the backend server after updating `.env`

**Database errors**
```bash
# Delete database and restart (will lose data)
rm backend/tryon.db
python backend/app.py
```

### Frontend Issues

**Port 3000 already in use**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
# Or change port in vite.config.js
```

**API requests failing**
- Ensure backend is running on port 5000
- Check browser console for CORS errors
- Verify proxy settings in `vite.config.js`

### Gemini API Issues

**Virtual try-on not generating**
- Check that your API key has Gemini 2.5 Flash access
- Verify you have API quota remaining
- Check backend logs for detailed error messages
- Try with smaller image files (< 5MB)

## 🚀 Production Deployment

### Backend (Flask)

1. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. Use PostgreSQL instead of SQLite:
```env
DATABASE_URL=postgresql://user:password@localhost/tryon
```

3. Set secure secret keys and disable debug mode

### Frontend (React)

```bash
cd frontend
npm run build
# Serve the dist/ folder with nginx or any static hosting
```

### Recommended Hosting

- **Backend**: Railway, Render, Heroku, or AWS
- **Frontend**: Vercel, Netlify, or Cloudflare Pages
- **Database**: Render PostgreSQL, Supabase, or AWS RDS

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review existing GitHub issues
3. Create a new issue with detailed information

## 🙏 Acknowledgments

- Google Gemini AI for powering the virtual try-on
- Tailwind CSS for the beautiful UI components
- The React and Flask communities

---

**Built with ❤️ for fashion enthusiasts**

Enjoy your virtual fitting room! 👔👗

