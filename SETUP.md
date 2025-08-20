# BOQ Management System - Setup Instructions

## Prerequisites

- **Python 3.11+** - Download from [python.org](https://python.org)
- **Node.js 18+** - Download from [nodejs.org](https://nodejs.org)
- **Git** - Download from [git-scm.com](https://git-scm.com)

## Quick Start (Windows)

1. **Clone or download the project**

   ```bash
   git clone <repository-url>
   cd Python-React
   ```

2. **Start the entire system**

   - Double-click `start_system.bat`
   - This will start both backend and frontend servers automatically

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Manual Setup

### Backend Setup

1. **Navigate to backend directory**

   ```bash
   cd backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**

   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Start the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**

   ```bash
   cd frontend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

## Features

### Core Functionality

- **BOQ Items Management**: Create, read, update, delete BOQ items
- **Concentration Sheets**: Manage detailed breakdowns for each BOQ item
- **Search & Filter**: Advanced search with multiple criteria
- **File Import**: Import BOQ and calculation files from Excel
- **PDF Export**: Generate concentration sheets and summary reports
- **Sub-chapter Summaries**: Automatic aggregation by item groups

### Technical Features

- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Automatic calculation of totals
- **Data Protection**: Preserves manual entries during imports
- **PDF Generation**: Professional reports with customizable columns
- **File Management**: Automatic cleanup of old files

## API Endpoints

### BOQ Items

- `GET /api/boq` - List all BOQ items
- `POST /api/boq` - Create new BOQ item
- `PUT /api/boq/{id}` - Update BOQ item
- `DELETE /api/boq/{id}` - Delete BOQ item

### Search & Filter

- `GET /api/search` - Search BOQ items
- `GET /api/search/summary` - Get sub-chapter summary
- `GET /api/search/subchapters` - List all sub-chapters

### Concentration Sheets

- `GET /api/concentration` - List concentration sheets
- `POST /api/concentration` - Create concentration sheet
- `GET /api/concentration/{id}/entries` - Get sheet entries

### File Import

- `POST /api/import/boq` - Import BOQ Excel file
- `POST /api/import/calculation-files` - Import calculation files
- `GET /api/import/logs` - View import history

### PDF Export

- `POST /api/export/concentration-sheets` - Export concentration sheets
- `POST /api/export/summary` - Export summary report
- `GET /api/export/download/{filename}` - Download PDF

## Database Schema

### BOQ Items

- Item code, description, unit
- Contract quantity, unit price, line total
- Sub-chapter classification
- Price columns (estimate, submitted, PNIMI, approved)

### Concentration Sheets

- Linked to BOQ items
- Automatic total calculations
- Entry management

### Concentration Entries

- Job descriptions and references
- Price breakdowns
- Manual entry protection

## File Structure

```
Python-React/
├── backend/
│   ├── database/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── README.md
├── SETUP.md
└── start_system.bat
```

## Troubleshooting

### Common Issues

1. **Port already in use**

   - Backend: Change port in `uvicorn` command
   - Frontend: Change port in `vite.config.ts`

2. **Python dependencies not found**

   - Ensure virtual environment is activated
   - Reinstall requirements: `pip install -r requirements.txt`

3. **Node modules not found**

   - Delete `node_modules` and reinstall: `npm install`

4. **Database errors**
   - Delete `backend/database/boq_system.db` to reset
   - Restart the backend server

### Development Tips

1. **Backend Development**

   - Use `--reload` flag for auto-restart on changes
   - Check logs in terminal for errors
   - Use FastAPI docs at `/docs` for API testing

2. **Frontend Development**

   - Use browser dev tools for debugging
   - Check console for JavaScript errors
   - Use React Query dev tools for data debugging

3. **Database Changes**
   - Update models in `backend/models/models.py`
   - Update schemas in `backend/schemas/schemas.py`
   - Restart backend to apply changes

## Production Deployment

### Backend

1. Use production WSGI server (Gunicorn)
2. Set up proper database (PostgreSQL recommended)
3. Configure environment variables
4. Set up reverse proxy (Nginx)

### Frontend

1. Build for production: `npm run build`
2. Serve static files with web server
3. Configure API proxy
4. Set up HTTPS

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check browser console for frontend errors
4. Check backend logs for server errors

## License

This project is created for educational and commercial use.
