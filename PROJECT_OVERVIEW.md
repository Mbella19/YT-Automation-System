# Try On - Project Overview

## 📋 Project Summary

**Try On** is a mobile-first virtual fitting room application that uses Google's Gemini 2.5 Flash AI model to help users visualize how clothes look on them. Users can upload their photos and clothing items, then generate realistic virtual try-on images using cutting-edge AI technology.

### Key Technologies
- **Frontend**: React 18 + Vite + TailwindCSS
- **Backend**: Python Flask + SQLAlchemy + JWT
- **AI**: Google Gemini 2.5 Flash API
- **Database**: SQLite (PostgreSQL-ready)
- **Design**: Mobile-first, responsive, dark mode support

## 📂 Project Structure

```
Try on/
├── 📄 README.md                 # Main documentation
├── 📄 QUICKSTART.md             # 5-minute setup guide
├── 📄 FEATURES.md               # Feature list and roadmap
├── 📄 PROJECT_OVERVIEW.md       # This file
├── 🔧 setup.sh                  # One-command setup script
├── 🔧 start-backend.sh          # Backend startup script
├── 🔧 start-frontend.sh         # Frontend startup script
├── 🚫 .gitignore                # Git ignore rules
│
├── 📁 backend/                  # Python Flask API
│   ├── app.py                   # Main Flask application
│   ├── config.py                # Configuration management
│   ├── models.py                # Database models (User, Photo, Clothing, SavedLook)
│   ├── gemini_service.py        # Google Gemini AI integration
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Environment template
│   └── uploads/                 # User-uploaded files
│       ├── photos/              # User photos
│       ├── clothing/            # Clothing items
│       └── results/             # Generated try-on results
│
└── 📁 frontend/                 # React SPA
    ├── index.html               # HTML entry point
    ├── package.json             # Node dependencies
    ├── vite.config.js           # Vite configuration
    ├── tailwind.config.js       # Tailwind CSS config
    ├── postcss.config.js        # PostCSS config
    └── src/
        ├── main.jsx             # React entry point
        ├── App.jsx              # Main app component with routing
        ├── index.css            # Global styles
        ├── pages/               # Page components
        │   ├── Welcome.jsx      # Landing page
        │   ├── Auth.jsx         # Sign up / Login
        │   ├── Photos.jsx       # Photo management
        │   ├── Wardrobe.jsx     # Clothing wardrobe
        │   ├── TryOnStudio.jsx  # Virtual try-on interface
        │   └── SavedLooks.jsx   # Saved results gallery
        ├── services/
        │   └── api.js           # API client with axios
        └── store/
            └── authStore.js     # Authentication state (Zustand)
```

## 🎯 Core Features

### 1. Authentication System
- JWT-based authentication
- Password hashing with bcrypt
- Persistent sessions with localStorage
- Protected routes

### 2. Photo Management
- Upload personal photos
- Select photo for try-on
- Delete photos
- Visual feedback for selected photo

### 3. Wardrobe System
- Upload clothing items
- Categorize by type (tops, bottoms, dresses, outerwear, accessories)
- Filter by category
- Delete items

### 4. Virtual Try-On
- AI-powered image generation
- Realistic clothing fitting
- Result preview
- Automatic saving

### 5. Saved Looks Gallery
- View all generated looks
- Share functionality
- Delete saved looks
- Empty state handling

## 🔄 Data Flow

```
User Interface (React)
    ↓
API Requests (Axios)
    ↓
Flask Backend
    ↓
├─→ Database (SQLite)
│   ├─ Users
│   ├─ Photos
│   ├─ Clothing Items
│   └─ Saved Looks
│
└─→ Google Gemini API
    └─ Image Generation
```

## 🗄️ Database Schema

### Users Table
- id (Primary Key)
- full_name
- email (Unique)
- password_hash
- created_at

### Photos Table
- id (Primary Key)
- user_id (Foreign Key → Users)
- filename
- filepath
- is_selected
- uploaded_at

### Clothing Items Table
- id (Primary Key)
- user_id (Foreign Key → Users)
- filename
- filepath
- category
- uploaded_at

### Saved Looks Table
- id (Primary Key)
- user_id (Foreign Key → Users)
- photo_id (Foreign Key → Photos)
- clothing_id (Foreign Key → Clothing Items)
- result_filename
- result_filepath
- created_at

## 🔌 API Endpoints

### Authentication
```
POST   /api/auth/register     # Create new user account
POST   /api/auth/login        # Login with email/password
GET    /api/user/profile      # Get user profile (protected)
```

### Photos
```
GET    /api/photos            # Get all user photos (protected)
POST   /api/photos            # Upload new photo (protected)
DELETE /api/photos/:id        # Delete photo (protected)
PUT    /api/photos/:id/select # Select photo for try-on (protected)
```

### Clothing
```
GET    /api/clothing          # Get clothing items (protected)
POST   /api/clothing          # Upload clothing item (protected)
DELETE /api/clothing/:id      # Delete clothing item (protected)
```

### Virtual Try-On
```
POST   /api/tryon             # Generate virtual try-on (protected)
GET    /api/saved-looks       # Get saved looks (protected)
DELETE /api/saved-looks/:id   # Delete saved look (protected)
```

### Static Files
```
GET    /uploads/:path         # Serve uploaded files
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Google API Key for Gemini

### Setup (3 Steps)
1. Run `./setup.sh` to install dependencies
2. Add your Google API key to `backend/.env`
3. Start both servers:
   - Terminal 1: `./start-backend.sh`
   - Terminal 2: `./start-frontend.sh`

### Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## 🎨 Design System

### Colors
- **Primary**: #13a4ec (Blue)
- **Secondary**: #FF7043 (Orange)
- **Background Light**: #f6f7f8
- **Background Dark**: #101c22

### Typography
- **Font Family**: Plus Jakarta Sans
- **Icon Set**: Material Symbols Outlined

### Components
- Mobile-first responsive design
- Touch-optimized interactions
- Smooth animations and transitions
- Dark mode support

## 📦 Dependencies

### Backend (Python)
- Flask 3.0.0 - Web framework
- Flask-CORS 4.0.0 - Cross-origin support
- Flask-SQLAlchemy 3.1.1 - Database ORM
- Flask-Bcrypt 1.0.1 - Password hashing
- Flask-JWT-Extended 4.6.0 - JWT authentication
- google-generativeai 0.3.2 - Gemini API client
- Pillow 10.2.0 - Image processing

### Frontend (Node.js)
- react 18.2.0 - UI library
- react-router-dom 6.20.1 - Routing
- vite 5.0.8 - Build tool
- tailwindcss 3.3.6 - CSS framework
- zustand 4.4.7 - State management
- axios 1.6.2 - HTTP client

## 🔧 Configuration

### Backend Environment Variables
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///tryon.db
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
GOOGLE_API_KEY=your-gemini-api-key
CORS_ORIGINS=http://localhost:3000
```

### Frontend Configuration
```env
VITE_API_URL=http://localhost:5000/api
```

## 🧪 Testing

### Manual Testing Checklist
- [ ] User registration
- [ ] User login
- [ ] Photo upload
- [ ] Photo selection
- [ ] Photo deletion
- [ ] Clothing upload with category
- [ ] Clothing deletion
- [ ] Virtual try-on generation
- [ ] Saved looks viewing
- [ ] Saved look deletion
- [ ] Dark mode toggle
- [ ] Mobile responsiveness

### Future Testing
- Unit tests (pytest for backend, Jest for frontend)
- Integration tests
- E2E tests (Playwright)
- Performance testing
- Security testing

## 📱 Mobile Optimization

### Features
- Touch-friendly UI elements
- Swipeable carousels
- Optimized image loading
- Responsive grid layouts
- Mobile camera integration
- Gesture support

### Performance
- Lazy loading images
- Code splitting
- Minified assets
- Compressed images
- Service worker (planned)

## 🔒 Security Measures

### Implemented
- Password hashing with bcrypt
- JWT token authentication
- CORS configuration
- File type validation
- File size limits

### Planned
- Rate limiting
- CSRF protection
- XSS prevention
- SQL injection prevention
- Content Security Policy
- HTTPS enforcement

## 📈 Scalability Considerations

### Current Setup
- SQLite database (suitable for < 100 users)
- Local file storage
- Single server deployment

### Production Recommendations
- PostgreSQL database
- Cloud storage (AWS S3, Cloudflare R2)
- CDN for static assets
- Redis for caching
- Load balancer
- Background job queue
- Horizontal scaling

## 🚀 Deployment Guide

### Backend Options
- **Railway** - Easy deployment, free tier
- **Render** - Good for Python apps
- **Heroku** - Classic PaaS
- **AWS/GCP** - Full control
- **DigitalOcean** - VPS option

### Frontend Options
- **Vercel** - Optimized for React
- **Netlify** - Simple deployment
- **Cloudflare Pages** - Fast CDN
- **GitHub Pages** - Free static hosting

### Database Options
- **Supabase** - PostgreSQL with auth
- **Railway** - Managed PostgreSQL
- **AWS RDS** - Scalable database
- **Render** - PostgreSQL hosting

## 🔮 Future Enhancements

### Short Term
- Email verification
- Password reset
- Profile editing
- Image cropping
- Batch uploads

### Medium Term
- Social features
- Collections/outfits
- Advanced AI options
- Mobile apps (React Native)
- API versioning

### Long Term
- AR camera try-on
- Video try-on
- 3D model generation
- E-commerce integration
- Marketplace

## 📚 Resources

### Documentation
- [README.md](README.md) - Full documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [FEATURES.md](FEATURES.md) - Feature roadmap

### External Links
- [Google Gemini API](https://ai.google.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [TailwindCSS](https://tailwindcss.com/)

## 🤝 Contributing

Interested in contributing? Here's how:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📄 License

This project is open source under the MIT License.

## 👨‍💻 Development Team

- **Project Type**: Full-stack web application
- **Development Time**: Built with AI assistance
- **Maintenance**: Community-driven

## 🙏 Acknowledgments

- Google Gemini for AI technology
- React community for excellent tools
- Flask community for robust framework
- TailwindCSS for beautiful styling
- All open source contributors

---

**Need Help?**
- Check [QUICKSTART.md](QUICKSTART.md) for setup
- Read [README.md](README.md) for details
- Check [FEATURES.md](FEATURES.md) for roadmap
- Open an issue on GitHub

**Happy Coding! 🎉**

