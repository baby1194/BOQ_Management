from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import logging
from pathlib import Path

from database.database import init_system_database, init_project_database
from database import project_registry
from routers import boq, concentration_sheets, file_import, pdf_export, search, calculation_sheets, project_info, contract_updates, subsections, systems, structures, auth, projects, non_boq_items

# Initialize project registry and databases
project_registry.migrate_legacy_db()
init_system_database()
for _project in project_registry.list_projects():
    init_project_database(_project["id"])

app = FastAPI(
    title="BOQ Management System",
    description="A modern web application for managing Bill of Quantities",
    version="1.0.0",
    redirect_slashes=False,
)

# CORS middleware (explicit origins required when using credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ],
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
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(non_boq_items.router, prefix="/api/non-boq-items", tags=["Non-BOQ Items"])

@app.get("/")
async def root():
    return {"message": "BOQ Management System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "BOQ Management System is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 