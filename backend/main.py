from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import logging
from pathlib import Path

from database.database import engine, get_db
from models import models
from routers import boq, concentration_sheets, file_import, pdf_export, search, calculation_sheets, project_info, contract_updates, subsections, systems, structures, auth
from services.excel_service import ExcelService
from services.pdf_service import PDFService

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BOQ Management System",
    description="A modern web application for managing Bill of Quantities",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)
os.makedirs("database", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()  # Also log to console
    ]
)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/exports", StaticFiles(directory="exports"), name="exports")

# Include routers
app.include_router(boq.router, prefix="/api/boq", tags=["BOQ"])
app.include_router(concentration_sheets.router, prefix="/api/concentration", tags=["Concentration Sheets"])
app.include_router(calculation_sheets.router, prefix="/api/calculation-sheets", tags=["Calculation Sheets"])
app.include_router(file_import.router, prefix="/api", tags=["File Import"])
app.include_router(pdf_export.router, prefix="/api/export", tags=["PDF Export"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(project_info.router, prefix="/api/project-info", tags=["Project Info"])
app.include_router(contract_updates.router, prefix="/api/contract-updates", tags=["Contract Updates"])
app.include_router(subsections.router, prefix="/api/subsections", tags=["Subsections"])
app.include_router(systems.router, prefix="/api/systems", tags=["Systems"])
app.include_router(structures.router, prefix="/api/structures", tags=["Structures"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {"message": "BOQ Management System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "BOQ Management System is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 