# BOQ Management System - Setup Guide

This guide will help you set up and run the BOQ Management System on your local machine.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **npm**: 9.0 or higher

### Required Software

1. **Python 3.11+**: Download from [python.org](https://www.python.org/downloads/)
2. **Node.js 18+**: Download from [nodejs.org](https://nodejs.org/)
3. **Git**: Download from [git-scm.com](https://git-scm.com/)

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Python-React
```

### 2. Quick Start (Recommended)

Use the provided batch scripts for Windows:

1. **Start Both Servers**: Double-click `start_system.bat`
   - This will automatically install dependencies and start both servers
   - Backend will be available at: http://localhost:8000
   - Frontend will be available at: http://localhost:3000

### 3. Manual Setup (Alternative)

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm run dev
```

## Accessing the Application

### Web Interface

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Default Features

- **Dashboard**: Overview of BOQ items and statistics
- **BOQ Items**: Manage Bill of Quantities items
- **Concentration Sheets**: Detailed breakdown sheets for each item
- **Search & Filter**: Advanced search and filtering capabilities
- **File Import**: Import BOQ and calculation files
- **PDF Export**: Export concentration sheets and reports

## Sample Data Setup

### 1. Create Sample Excel Files

Follow the instructions in the `sample_data/` folder to create:

- `boq_sample.xlsx` - Sample BOQ items
- `calculation_sample.xlsx` - Sample calculation data

### 2. Import Sample Data

1. Go to the **File Import** page
2. Upload the `boq_sample.xlsx` file
3. Click **Create Concentration Sheets**
4. Import calculation files (if available)

## Configuration

### Environment Variables

Create a `.env` file in the backend directory for custom configuration:

```env
# Database
DATABASE_URL=sqlite:///./database/boq_system.db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=uploads
EXPORT_DIR=exports
```

### Database

The system uses SQLite by default. The database file will be created automatically at:
`backend/database/boq_system.db`

## Usage Guide

### 1. Importing BOQ Data

1. Prepare your Excel file according to the format in `EXCEL_FORMAT.md`
2. Go to **File Import** page
3. Upload your BOQ Excel file
4. Review import logs for any errors

### 2. Managing BOQ Items

1. Go to **BOQ Items** page
2. View, add, edit, or delete items
3. Use search functionality to find specific items
4. Filter by sub-chapters

### 3. Working with Concentration Sheets

1. Go to **Concentration Sheets** page
2. View detailed breakdowns for each BOQ item
3. Add manual entries if needed
4. Track estimate, submitted, PNIMI, and approved values

### 4. Exporting Reports

1. Go to **PDF Export** page
2. Select items to export
3. Choose columns to include/exclude
4. Generate and download PDF reports

## Troubleshooting

### Common Issues

#### Backend Issues

- **Port 8000 already in use**: Change the port in the uvicorn command
- **Python dependencies not found**: Run `pip install -r requirements.txt`
- **Database errors**: Delete `boq_system.db` and restart the server

#### Frontend Issues

- **Port 3000 already in use**: The system will automatically use the next available port
- **Node modules not found**: Run `npm install`
- **Build errors**: Clear npm cache with `npm cache clean --force`

#### Import Issues

- **File format not supported**: Ensure files are in .xlsx or .xls format
- **Column headers not found**: Check the exact column names in `EXCEL_FORMAT.md`
- **Data validation errors**: Review the data types and required fields

### Getting Help

1. Check the console output for error messages
2. Review the API documentation at http://localhost:8000/docs
3. Check the import logs for detailed error information
4. Verify file formats match the expected structure

## Development

### Project Structure

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
└── README.md
```

### Adding New Features

1. **Backend**: Add new models, schemas, and API endpoints
2. **Frontend**: Create new components and pages
3. **Database**: Run migrations if needed
4. **Testing**: Test with sample data

## Support

For technical support or questions:

1. Check the documentation in this repository
2. Review the API documentation
3. Check the console logs for error details
4. Ensure all prerequisites are installed correctly

## License

This project is licensed under the MIT License - see the LICENSE file for details.
