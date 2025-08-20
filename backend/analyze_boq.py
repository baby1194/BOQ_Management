#!/usr/bin/env python3
"""
Analyze BOQ.xlsx file structure to understand the data format
"""
import pandas as pd
import os
from pathlib import Path

def analyze_boq_file():
    """Analyze the BOQ.xlsx file structure"""
    
    # Path to BOQ.xlsx in root directory
    boq_file = Path("BOQ.xlsx")
    
    if not boq_file.exists():
        print(f"❌ BOQ.xlsx not found at: {boq_file.absolute()}")
        return
    
    print(f"📊 Analyzing BOQ file: {boq_file.absolute()}")
    
    try:
        # Read the Excel file
        df = pd.read_excel(boq_file)
        
        print(f"\n📋 File Structure:")
        print(f"  - Total rows: {len(df)}")
        print(f"  - Total columns: {len(df.columns)}")
        
        print(f"\n📝 Column Names:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")
        
        print(f"\n🔍 Sample Data (first 5 rows):")
        print(df.head().to_string())
        
        # Check for Section Number column
        if 'Section Number' in df.columns:
            print(f"\n🎯 Section Number Analysis:")
            section_numbers = df['Section Number'].dropna()
            print(f"  - Total section numbers: {len(section_numbers)}")
            print(f"  - Sample section numbers:")
            for i, section in section_numbers.head(10).items():
                print(f"    {section}")
            
            # Analyze subsection extraction
            print(f"\n📂 Subsection Analysis:")
            subsections = set()
            for section in section_numbers:
                if pd.notna(section) and str(section).strip():
                    parts = str(section).split('.')
                    if len(parts) >= 3:
                        subsection = '.'.join(parts[:3])  # First 3 parts
                        subsections.add(subsection)
            
            print(f"  - Unique subsections found: {len(subsections)}")
            print(f"  - Sample subsections:")
            for subsection in sorted(list(subsections))[:10]:
                print(f"    {subsection}")
        
        # Check for other important columns
        print(f"\n📊 Column Data Types:")
        for col in df.columns:
            non_null_count = df[col].count()
            data_type = df[col].dtype
            print(f"  - {col}: {data_type} ({non_null_count} non-null values)")
        
        return df
        
    except Exception as e:
        print(f"❌ Error analyzing file: {str(e)}")
        return None

if __name__ == "__main__":
    analyze_boq_file() 