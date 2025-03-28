# 🚀 WebAutoDash Startup Guide

## Quick Start

### Method 1: Using the Startup Script (Recommended)
```bash
# From anywhere, run:
cd ~/Projects/WebAutoDash
./start_webautodash.sh
```

### Method 2: Using NPM from Frontend Directory
```bash
cd ~/Projects/WebAutoDash/frontend
npm run dev
```

### Method 3: Start Components Separately
```bash
# Terminal 1 - Backend
cd ~/Projects/WebAutoDash/backend
conda activate medimind
python app.py

# Terminal 2 - Frontend
cd ~/Projects/WebAutoDash/frontend
npm start
```

## 🔧 Troubleshooting

### Problem: Slow Dashboard Loading
**Solution**: The system now uses caching and reduced polling intervals to improve performance:
- Dashboard refreshes every 15 seconds (reduced from 10s)
- Navigation bar updates every 10 seconds (reduced from 5s)
- API responses are cached for 5 seconds to prevent redundant calls

### Problem: "npm run" doesn't start backend
**Solution**: Use the correct commands:
- ✅ `npm run dev` - Starts both backend and frontend
- ✅ `npm run start` - Starts only frontend
- ✅ `npm run backend` - Starts only backend
- ❌ `npm run` - Does nothing (no default script)

### Problem: Port Already in Use
The startup script will detect if ports 5005 (backend) or 3008 (frontend) are already in use and offer to:
1. Kill existing processes and restart
2. Use existing processes

### Problem: Backend Won't Start
Check that:
1. You're in the correct conda environment: `conda activate medimind`
2. Flask dependencies are installed: `pip install flask flask-sqlalchemy flask-cors`
3. Port 5005 is available

### Problem: Frontend Won't Start
Check that:
1. Node.js dependencies are installed: `npm install`
2. Port 3008 is available
3. You're in the frontend directory

## 📍 Access URLs

Once started successfully:
- **Frontend (Main UI)**: http://localhost:3008
- **Backend API**: http://localhost:5005/api
- **API Health Check**: http://localhost:5005/

## 🎯 Available NPM Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start both backend and frontend |
| `npm run start` | Start only frontend (React) |
| `npm run backend` | Start only backend (Flask) |
| `npm run start-full` | Alias for `npm run dev` |
| `npm run backend-only` | Alternative backend startup |
| `npm run frontend-only` | Alias for `npm run start` |

## 🔄 Performance Optimizations Applied

1. **Reduced API Polling**:
   - Dashboard: 15-second intervals
   - Navigation: 10-second intervals

2. **Response Caching**:
   - API responses cached for 5 seconds
   - Prevents redundant calls during rapid navigation

3. **Smart Startup**:
   - Detects running processes
   - Offers restart options
   - Validates directory structure

## 🐛 Known Issues & Solutions

1. **Slow Initial Load**: Normal behavior as the system fetches all data for the first time
2. **Multiple API Calls**: Now optimized with caching
3. **Backend Script Path**: Fixed with improved shell handling

## 💡 Tips for Best Performance

1. Keep the system running - stopping and restarting causes the initial load delay
2. Use the startup script for consistent launches
3. If you need to restart, use the script's restart option rather than manual killing
4. Clear browser cache if you experience UI issues after updates 