# BOQ Management System

A modern web application for managing Bill of Quantities (BOQ) with interactive search, concentration sheets, and automated data processing.

## 🚀 Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd Python-React
   ```

2. **Start the system** (Windows)

   ```bash
   # Double-click start_system.bat
   # Or run manually:
   start_system.bat
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## ✨ Features

- **📊 Interactive BOQ Management**: Search and filter items by code or description
- **📋 Concentration Sheets**: Individual sheets for each BOQ item with navigation
- **📁 External File Integration**: Import data from Excel calculation files
- **📄 PDF Export**: Export and merge concentration sheets to PDF
- **🛡️ Manual Data Protection**: Preserve user entries during imports
- **📈 Sub-chapter Summaries**: Aggregate totals by item groups
- **⚡ Real-time Updates**: Automatic calculation of line totals and summaries
- **🔍 Advanced Search**: Multi-criteria search and filtering
- **📤 File Import/Export**: Excel file processing with error handling
- **📊 Dashboard Analytics**: Overview statistics and quick actions

## 🛠️ Tech Stack

### Frontend

- **React 18** + **TypeScript** + **Tailwind CSS**
- **Vite** for fast development and building
- **React Router DOM** for navigation
- **React Query** for data fetching
- **React Hook Form** + **Zod** for form validation
- **Lucide React** for icons
- **React Hot Toast** for notifications

### Backend

- **FastAPI** + **Python 3.11+**
- **SQLAlchemy** for database ORM
- **Pydantic** for data validation
- **Uvicorn** as ASGI server
- **SQLite** database

### File Processing

- **openpyxl** for Excel file handling
- **pandas** for data manipulation
- **reportlab** for PDF generation

## 📁 Project Structure

```
Python-React/
├── backend/                 # FastAPI backend
│   ├── database/           # Database configuration
│   ├── models/             # SQLAlchemy models
│   ├── routers/            # API endpoints
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── main.py            # FastAPI application
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── utils/          # Utility functions
│   └── package.json
├── sample_data/            # Sample Excel files
├── start_system.bat        # Quick start script
└── README.md
```

## 📖 Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Complete installation and setup instructions
- **[Excel Format Guide](EXCEL_FORMAT.md)** - File format specifications for imports
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)

## 🎯 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### Installation Options

#### Option 1: Quick Start (Recommended)

```bash
# Windows
start_system.bat

# Manual (any OS)
./start_system.bat
```

#### Option 2: Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

## 🔧 Configuration

The system uses sensible defaults but can be customized:

- **Database**: SQLite (configurable via environment variables)
- **File Upload**: 10MB limit (configurable)
- **Ports**: Backend 8000, Frontend 3000 (auto-detected if busy)

## 📊 Sample Data

Create sample Excel files using the templates in `sample_data/`:

- `boq_sample.xlsx` - Sample BOQ items
- `calculation_sample.xlsx` - Sample calculation data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
