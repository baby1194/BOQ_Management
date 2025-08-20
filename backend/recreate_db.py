#!/usr/bin/env python3
"""
Recreate database with new schema
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database.database import engine
    from models import models
    
    print("🗄️  Recreating database with new schema...")
    
    # Drop all tables
    models.Base.metadata.drop_all(bind=engine)
    print("✅ Dropped existing tables")
    
    # Create all tables with new schema
    models.Base.metadata.create_all(bind=engine)
    print("✅ Created new tables with updated schema")
    
    print("🎯 Database recreation complete!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Error recreating database: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}") 
 
 