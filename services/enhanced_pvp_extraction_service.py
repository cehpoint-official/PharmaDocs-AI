"""
Enhanced PVP AI Extraction Service
Extracts comprehensive data from Process Validation Protocol PDFs using AI
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
import pdfplumber
import google.generativeai as genai

# Configure logging
logger = logging.getLogger(__name__)
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    logger.warning("Gemini API key not found. Using regex-only extraction.")


class EnhancedPVPExtractor:
    """Extract comprehensive data from PVP documents"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.full_text = ""
        self.product_type = None
        
    def extract_all(self) -> Dict:
        """Main extraction method - extracts everything from PVP"""
        
        logger.info(f"Starting extraction from: {self.pdf_path}")
        
        # Extract full text from PDF
        self.full_text = self._extract_text_from_pdf()
        
        if not self.full_text:
            logger.error("Failed to extract text from PDF")
            return self._empty_result()
        
        logger.info(f"Extracted {len(self.full_text)} characters from PDF")
        
        # Extract all data
        result = {
            'product_info': self._extract_product_info(),
            'product_type': self._detect_product_type(),
            'equipment': self._extract_equipment(),
            'materials': self._extract_materials(),
            'stages': self._extract_stages(),
            'test_criteria': self._extract_test_criteria()
        }
        
        self.product_type = result['product_type']
        
        logger.info(f"Extraction complete. Product: {result['product_info'].get('product_name')}, Type: {result['product_type']}")
        
        return result
    
    def _extract_text_from_pdf(self) -> str:
        """Extract all text from PDF"""
        try:
            text = ""
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def _extract_product_info(self) -> Dict:
        """Extract basic product information"""
        
        if model:
            return self._extract_product_info_with_ai()
        else:
            return self._extract_product_info_with_regex()
    
    def _extract_product_info_with_ai(self) -> Dict:
        """Extract product info using Gemini AI"""
        
        try:
            prompt = f"""
Extract the following product information from this Process Validation Protocol:

Text:
{self.full_text[:3000]}

Extract and return ONLY a JSON object with these fields:
{{
    "product_name": "full product name",
    "strength": "e.g., 50mg/ml",
    "dosage_form": "e.g., Injection, Tablet, Capsule, Syrup",
    "batch_size": "e.g., 10,000 vials",
    "pack_size": "e.g., 10ml vial",
    "manufacturing_site": "site name if mentioned"
}}

Return only the JSON, no other text.
"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean up response
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            product_info = json.loads(result_text)
            logger.info(f"AI extracted product info: {product_info.get('product_name')}")
            return product_info
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return self._extract_product_info_with_regex()
    
    def _extract_product_info_with_regex(self) -> Dict:
        """Extract product info using regex patterns"""
        
        product_info = {
            'product_name': '',
            'strength': '',
            'dosage_form': '',
            'batch_size': '',
            'pack_size': '',
            'manufacturing_site': ''
        }
        
        # Extract product name (first line often contains it)
        lines = self.full_text.split('\n')
        for line in lines[:20]:
            if any(word in line.lower() for word in ['injection', 'tablet', 'capsule', 'syrup', 'suspension']):
                product_info['product_name'] = line.strip()
                break
        
        # Extract strength
        strength_pattern = r'(\d+(?:\.\d+)?)\s*(?:mg|g|ml|mcg|%|IU)(?:/(?:ml|g|tablet|capsule))?'
        match = re.search(strength_pattern, self.full_text, re.IGNORECASE)
        if match:
            product_info['strength'] = match.group(0)
        
        # Extract batch size
        batch_pattern = r'batch\s*size[:\s]+(\d+(?:,\d+)?)\s*(?:vials|tablets|capsules|bottles|units)?'
        match = re.search(batch_pattern, self.full_text, re.IGNORECASE)
        if match:
            product_info['batch_size'] = match.group(0)
        
        return product_info
    
    def _detect_product_type(self) -> str:
        """Detect product type from text"""
        
        text_lower = self.full_text.lower()
        
        # Keywords for each type
        injectable_keywords = ['injection', 'injectable', 'vial', 'ampoule', 'sterile', 'aseptic', 'filtration']
        tablet_keywords = ['tablet', 'compression', 'granulation', 'coating', 'punch', 'die']
        capsule_keywords = ['capsule', 'gelatin', 'filling', 'shell', 'banding']
        liquid_keywords = ['syrup', 'suspension', 'solution', 'liquid', 'bottle filling']
        
        # Count matches
        scores = {
            'Injectable': sum(1 for k in injectable_keywords if k in text_lower),
            'Tablet': sum(1 for k in tablet_keywords if k in text_lower),
            'Capsule': sum(1 for k in capsule_keywords if k in text_lower),
            'Oral_Liquid': sum(1 for k in liquid_keywords if k in text_lower)
        }
        
        # Return type with highest score
        detected_type = max(scores, key=scores.get)
        logger.info(f"Detected product type: {detected_type} (scores: {scores})")
        
        return detected_type
    
    def _extract_equipment(self) -> List[Dict]:
        """Extract equipment list"""
        
        if model:
            return self._extract_equipment_with_ai()
        else:
            return self._extract_equipment_with_regex()
    
    def _extract_equipment_with_ai(self) -> List[Dict]:
        """Extract equipment using AI"""
        
        try:
            prompt = f"""
Extract all equipment/instruments mentioned in this validation protocol.

Text:
{self.full_text[:5000]}

Return ONLY a JSON array of equipment objects:
[
    {{
        "equipment_name": "Balance",
        "equipment_id": "BAL-001",
        "location": "Dispensing Area",
        "calibration_status": "Valid"
    }}
]

Return only the JSON array, no other text.
"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            equipment = json.loads(result_text)
            logger.info(f"AI extracted {len(equipment)} equipment items")
            return equipment
            
        except Exception as e:
            logger.error(f"AI equipment extraction failed: {e}")
            return self._extract_equipment_with_regex()
    
    def _extract_equipment_with_regex(self) -> List[Dict]:
        """Extract equipment using regex"""
        
        equipment = []
        
        # Look for equipment patterns
        equipment_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\(?([A-Z]{2,}-\d+)\)?',  # Balance (BAL-001)
            r'Equipment:\s*([A-Za-z\s]+)',
            r'Instrument:\s*([A-Za-z\s]+)'
        ]
        
        for pattern in equipment_patterns:
            matches = re.finditer(pattern, self.full_text, re.MULTILINE)
            for match in matches:
                equipment.append({
                    'equipment_name': match.group(1).strip(),
                    'equipment_id': match.group(2) if len(match.groups()) > 1 else '',
                    'location': '',
                    'calibration_status': 'Valid'
                })
        
        logger.info(f"Regex extracted {len(equipment)} equipment items")
        return equipment[:20]  # Limit to 20 items
    
    def _extract_materials(self) -> List[Dict]:
        """Extract materials (API, excipients, packaging)"""
        
        if model:
            return self._extract_materials_with_ai()
        else:
            return self._extract_materials_with_regex()
    
    def _extract_materials_with_ai(self) -> List[Dict]:
        """Extract materials using AI"""
        
        try:
            prompt = f"""
Extract all materials from this validation protocol. Categorize as API, Excipient, or Packaging.

Text:
{self.full_text[:5000]}

Return ONLY a JSON array:
[
    {{
        "material_type": "API",
        "material_name": "Fluorouracil",
        "specification": "USP",
        "quantity": "500 mg"
    }}
]

Return only the JSON array, no other text.
"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            materials = json.loads(result_text)
            logger.info(f"AI extracted {len(materials)} materials")
            return materials
            
        except Exception as e:
            logger.error(f"AI materials extraction failed: {e}")
            return self._extract_materials_with_regex()
    
    def _extract_materials_with_regex(self) -> List[Dict]:
        """Extract materials using regex"""
        
        materials = []
        
        # Common pharmaceutical materials
        api_keywords = ['api', 'active ingredient', 'drug substance']
        excipient_keywords = ['excipient', 'sodium hydroxide', 'water for injection', 'preservative']
        
        text_lower = self.full_text.lower()
        
        # Simple extraction
        for keyword in api_keywords:
            if keyword in text_lower:
                materials.append({
                    'material_type': 'API',
                    'material_name': keyword.title(),
                    'specification': 'USP',
                    'quantity': ''
                })
        
        logger.info(f"Regex extracted {len(materials)} materials")
        return materials
    
    def _extract_stages(self) -> List[Dict]:
        """Extract manufacturing stages mentioned in PVP"""
        
        if model:
            return self._extract_stages_with_ai()
        else:
            return self._extract_stages_with_regex()
    
    def _extract_stages_with_ai(self) -> List[Dict]:
        """Extract stages using AI"""
        
        try:
            # Get stage template for detected product type
            stage_names = self._get_stage_template_names()
            
            prompt = f"""
Extract manufacturing stages from this validation protocol.

Expected stages for {self.product_type}:
{', '.join(stage_names[:10])}

Text:
{self.full_text[:8000]}

For each stage found, return JSON:
[
    {{
        "stage_number": 1,
        "stage_name": "Dispensing",
        "equipment_used": "Balance BAL-001",
        "parameters": "Weight accuracy ±0.1%",
        "acceptance_criteria": "±0.5% of target weight"
    }}
]

Return only the JSON array, no other text.
"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            stages = json.loads(result_text)
            logger.info(f"AI extracted {len(stages)} stages")
            return stages
            
        except Exception as e:
            logger.error(f"AI stages extraction failed: {e}")
            return self._extract_stages_with_regex()
    
    def _extract_stages_with_regex(self) -> List[Dict]:
        """Extract stages using regex and template matching"""
        
        stages = []
        stage_names = self._get_stage_template_names()
        
        # Search for each stage name in text
        for i, stage_name in enumerate(stage_names, 1):
            # Clean stage name for searching
            search_term = stage_name.lower().replace('(if applicable)', '').strip()
            
            if search_term in self.full_text.lower():
                stages.append({
                    'stage_number': i,
                    'stage_name': stage_name,
                    'equipment_used': '',
                    'parameters': '',
                    'acceptance_criteria': ''
                })
        
        logger.info(f"Regex extracted {len(stages)} stages")
        return stages
    
    def _extract_test_criteria(self) -> List[Dict]:
        """Extract test criteria and acceptance limits"""
        
        criteria = []
        
        # Common test patterns
        test_patterns = [
            r'pH[:\s]+(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)',
            r'Assay[:\s]+(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)%',
            r'Volume[:\s]+(\d+\.?\d*)\s*ml',
        ]
        
        for pattern in test_patterns:
            matches = re.finditer(pattern, self.full_text, re.IGNORECASE)
            for match in matches:
                criteria.append({
                    'test_id': f'test_{len(criteria)+1}',
                    'test_name': match.group(0).split(':')[0].strip(),
                    'acceptance_criteria': match.group(0)
                })
        
        logger.info(f"Extracted {len(criteria)} test criteria")
        return criteria[:20]  # Limit to 20
    
    def _get_stage_template_names(self) -> List[str]:
        """Get stage names from database template"""
        
        try:
            from app import app, db
            from models import PV_Stage_Template
            
            with app.app_context():
                templates = PV_Stage_Template.query.filter_by(
                    product_type=self.product_type
                ).order_by(PV_Stage_Template.stage_number).all()
                
                return [t.stage_name for t in templates]
        except Exception as e:
            logger.error(f"Error loading stage templates: {e}")
            return []
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'product_info': {},
            'product_type': 'Injectable',
            'equipment': [],
            'materials': [],
            'stages': [],
            'test_criteria': []
        }


def extract_from_pvp(pdf_path: str) -> Dict:
    """
    Main function to extract all data from PVP
    
    Args:
        pdf_path: Path to PVP PDF file
        
    Returns:
        Dictionary with all extracted data
    """
    extractor = EnhancedPVPExtractor(pdf_path)
    return extractor.extract_all()