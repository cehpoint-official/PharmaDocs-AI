# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import pdfplumber
import re
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

import os
from dotenv import load_dotenv
import logging

#disable debug logging
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

load_dotenv()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY and GENAI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)


def extract_text_from_pdf(pdf_path):
    """
    Extract all text from PDF file
    """
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2)
                if text:
                    full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def extract_with_ai(pdf_text):
    """
    Use Gemini AI to extract test criteria from PVP text
    """
    try:
        if not GENAI_AVAILABLE:
            print("⚠️ Gemini AI not available (module missing)")
            return []
            
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
You are an expert pharmaceutical documentation analyst. Analyze this Process Validation Protocol (PVP) document and extract ALL test parameters and their acceptance criteria.

Extract information in this EXACT JSON format:
[
  {{
    "test_id": "unique_snake_case_id",
    "test_name": "Descriptive Test Name",
    "acceptance_criteria": "Exact acceptance criteria text"
  }}
]

DOCUMENT TEXT:
{pdf_text[:15000]}

EXTRACT:
1. Manufacturing process parameters (pH, temperature, mixing time, assay, etc.)
2. In-process control tests
3. Final product quality control tests
4. Critical process parameters
5. Acceptance criteria for each test

Return ONLY valid JSON array, no explanation.
"""
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean JSON response
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.startswith('```'):
            result_text = result_text[3:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        
        result_text = result_text.strip()
        
        # Parse JSON
        import json
        criteria = json.loads(result_text)
        
        return criteria
        
    except Exception as e:
        print(f"AI extraction error: {e}")
        return []


def extract_with_regex(pdf_text):
    """
    Fallback: Extract criteria using regex patterns
    """
    extracted = []
    
    # Pattern 1: pH tests
    ph_pattern = r'(?:pH|PH).*?(\d\.\d+\s*(?:to|-)\s*\d\.\d+)'
    for match in re.finditer(ph_pattern, pdf_text, re.IGNORECASE):
        extracted.append({
            'test_id': 'ph_test',
            'test_name': 'pH Test',
            'acceptance_criteria': match.group(1)
        })
        break  # Take first match
    
    # Pattern 2: Assay tests
    assay_pattern = r'Assay.*?(\d{2,3}\.?\d?\s*%?\s*(?:to|-)\s*\d{2,3}\.?\d?\s*%?)'
    for match in re.finditer(assay_pattern, pdf_text, re.IGNORECASE):
        extracted.append({
            'test_id': 'assay_test',
            'test_name': 'Assay Test',
            'acceptance_criteria': match.group(1)
        })
        break
    
    # Pattern 3: Temperature
    temp_pattern = r'Temperature.*?(\d+\s*°C?\s*(?:to|±|-)\s*\d+\s*°C?)'
    for match in re.finditer(temp_pattern, pdf_text, re.IGNORECASE):
        extracted.append({
            'test_id': 'temperature',
            'test_name': 'Temperature',
            'acceptance_criteria': match.group(1)
        })
        break
    
    # Pattern 4: Volume
    vol_pattern = r'(?:Volume|Extractable Volume).*?(NLT\s+\d+\.?\d?\s*ml)'
    for match in re.finditer(vol_pattern, pdf_text, re.IGNORECASE):
        extracted.append({
            'test_id': 'volume',
            'test_name': 'Extractable Volume',
            'acceptance_criteria': match.group(1)
        })
        break
    
    return extracted


def extract_pvp_criteria(pdf_path):
    """
    Main function to extract PVP criteria
    Uses AI first, falls back to regex if AI fails
    """
    print(f"📖 Extracting text from: {pdf_path}")
    pdf_text = extract_text_from_pdf(pdf_path)
    
    if not pdf_text:
        print("❌ No text extracted from PDF")
        return []
    
    print(f"✅ Extracted {len(pdf_text)} characters")
    
    # Try AI extraction first
    # Try AI extraction first
    if GEMINI_API_KEY and GENAI_AVAILABLE:
        print("🤖 Using Gemini AI for extraction...")
        criteria = extract_with_ai(pdf_text)
        if criteria:
            print(f"✅ AI extracted {len(criteria)} criteria")
            return criteria
    
    # Fallback to regex
    print("🔄 Falling back to regex extraction...")
    criteria = extract_with_regex(pdf_text)
    print(f"✅ Regex extracted {len(criteria)} criteria")
    
    return criteria