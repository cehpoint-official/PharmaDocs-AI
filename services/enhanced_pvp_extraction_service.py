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
import camelot
import pandas as pd
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
        self.tables = []  # Store extracted tables
        
    def extract_all(self) -> Dict:
        """Main extraction method - extracts everything from PVP"""
        logger.info(f"Starting extraction from: {self.pdf_path}")
        # Extract full text from PDF
        self.full_text = self._extract_text_from_pdf()
        if not self.full_text:
            logger.error("Failed to extract text from PDF")
            return self._empty_result()
        logger.info(f"Extracted {len(self.full_text)} characters from PDF")
        # Extract tables from PDF
        self.tables = self._extract_tables_from_pdf()
        logger.info(f"Extracted {len(self.tables)} tables from PDF")
        # Extract all data
        result = {
            'product_info': self._extract_product_info(),
            'product_type': self._detect_product_type(),
            'equipment': self._extract_equipment(),
            'materials': self._extract_materials(),
            'stages': self._extract_stages(),
            'test_criteria': self._extract_test_criteria(),
            'test_preparations': self._extract_test_preparations(),
            'calculation_sheet': self._extract_calculation_sheet(),
            'observations': self._extract_observations(),
            'signatures': self._extract_signatures(),
            'protocol_summary': self._extract_protocol_summary(),
            'batch_details': self._extract_batch_details()
        }
        self.product_type = result['product_type']
        logger.info(f"Extraction complete. Product: {result['product_info'].get('product_name')}, Type: {result['product_type']}")
        return result
        return result
    def _extract_test_preparations(self) -> list:
        """Extract test preparation details and area/absorbance values from tables and text"""
        preparations = []
        for table in self.tables:
            df = table.df
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            prep_keywords = ['preparation', 'test', 'sample', 'area', 'absorbance']
            is_prep_table = any(any(k in str(h) for k in prep_keywords) for h in headers)
            if is_prep_table:
                for idx in range(1, len(df)):
                    row = df.iloc[idx]
                    preparations.append({
                        'test_name': str(row[0]).strip(),
                        'preparation': str(row[1]).strip() if len(row) > 1 else '',
                        'area': str(row[2]).strip() if len(row) > 2 else '',
                        'absorbance': str(row[3]).strip() if len(row) > 3 else ''
                    })
        return preparations

    def _extract_calculation_sheet(self) -> list:
        """Extract calculation formulas and results from tables"""
        calculations = []
        for table in self.tables:
            df = table.df
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            calc_keywords = ['mean', 'sd', 'rsd', 'calculation', 'result']
            is_calc_table = any(any(k in str(h) for k in calc_keywords) for h in headers)
            if is_calc_table:
                for idx in range(1, len(df)):
                    row = df.iloc[idx]
                    calculations.append({
                        'parameter': str(row[0]).strip(),
                        'mean': str(row[1]).strip() if len(row) > 1 else '',
                        'sd': str(row[2]).strip() if len(row) > 2 else '',
                        'rsd': str(row[3]).strip() if len(row) > 3 else '',
                        'formula': str(row[4]).strip() if len(row) > 4 else ''
                    })
        return calculations

    def _extract_observations(self) -> str:
        """Extract observations, remarks, deviations from text"""
        obs_pattern = r'(observations|remarks|deviations)[:\s]+([^\n]{0,500})'
        match = re.search(obs_pattern, self.full_text, re.IGNORECASE)
        return match.group(2).strip() if match else ''

    def _extract_signatures(self) -> dict:
        """Extract performed by, checked by, approved by, and dates"""
        sig_pattern = r'(performed by|checked by|approved by)[:\s]+([^\n]+)'
        matches = re.findall(sig_pattern, self.full_text, re.IGNORECASE)
        signatures = {}
        for role, name in matches:
            signatures[role.lower().replace(' ', '_')] = name.strip()
        date_pattern = r'(\d{2}/\d{2}/\d{4})'
        dates = re.findall(date_pattern, self.full_text)
        if dates:
            signatures['date'] = dates[0]
        return signatures

    def _extract_protocol_summary(self) -> str:
        """Extract full methodology/protocol section from text"""
        # Find start of methodology/protocol/procedure section
        start_pattern = r'(methodology|protocol|procedure)[:\s]*\n?'
        end_pattern = r'^(?:calculations?|results?|observations?|conclusion|references?)[:\s]*$'
        lines = self.full_text.splitlines()
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if re.match(start_pattern, line.strip(), re.IGNORECASE):
                start_idx = i
                break
        if start_idx is not None:
            for j in range(start_idx + 1, len(lines)):
                if re.match(end_pattern, lines[j].strip(), re.IGNORECASE):
                    end_idx = j
                    break
            # Extract all lines between start and end
            section = lines[start_idx:end_idx] if end_idx else lines[start_idx:]
            return '\n'.join(section).strip()
        return ''
    
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
    
    def _extract_tables_from_pdf(self) -> List:
        """Extract all tables from PDF using camelot, ensuring temp files are closed"""
        try:
            # Extract tables using camelot (lattice method for bordered tables)
            tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='lattice')
            logger.info(f"Camelot lattice found {len(tables)} tables")

            # If no tables found with lattice, try stream method for non-bordered tables
            if len(tables) == 0:
                tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='stream')
                logger.info(f"Camelot stream found {len(tables)} tables")

            # Explicitly close temp files if possible
            for table in tables:
                if hasattr(table, 'temp_dir') and table.temp_dir:
                    try:
                        table._close_temp_files()
                    except Exception:
                        pass
            return tables
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            return []
    
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
        """Extract equipment using tables and regex"""
        
        equipment = []
        
        # First, try to extract from tables
        equipment_from_tables = self._extract_equipment_from_tables()
        if equipment_from_tables:
            equipment.extend(equipment_from_tables)
            logger.info(f"Extracted {len(equipment_from_tables)} equipment from tables")
        
        # Extract from text - look for equipment section
        equipment_section_pattern = r'(?:equipment and machinery list|production equipment)(.*?)(?:engineering equipment|raw material|quality control|$)'
        match = re.search(equipment_section_pattern, self.full_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            equipment_text = match.group(1)
            # Look for equipment entries with IDs
            # Pattern: equipment name followed by ID code
            lines = equipment_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 5 and not line.lower().startswith('s.no'):
                    # Skip headers and short lines
                    equipment.append({
                        'equipment_name': line[:50],  # First 50 chars as name
                        'equipment_id': '',
                        'location': '',
                        'calibration_status': 'Valid'
                    })
        
        logger.info(f"Total extracted {len(equipment)} equipment items")
        return equipment[:50]  # Limit to 50 items
    
    def _extract_equipment_from_tables(self) -> List[Dict]:
        """Extract equipment from tables in the PDF, capturing all columns"""
        equipment = []
        for idx, table in enumerate(self.tables):
            df = table.df
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            equipment_keywords = ['equipment', 'instrument', 'machine', 'apparatus', 'balance', 'item']
            is_equipment_table = any(
                any(keyword in str(header).lower() for keyword in equipment_keywords)
                for header in headers
            )
            if is_equipment_table:
                for idx in range(1, len(df)):
                    row = df.iloc[idx]
                    equipment.append({h: str(row[i]).strip() if i < len(row) else '' for i, h in enumerate(headers)})
        return equipment
    
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
        """Extract materials using tables and regex"""
        
        materials = []
        
        # First, try to extract from tables
        materials_from_tables = self._extract_materials_from_tables()
        if materials_from_tables:
            materials.extend(materials_from_tables)
            logger.info(f"Extracted {len(materials_from_tables)} materials from tables")
        
        # Also try regex patterns as backup
        # Common pharmaceutical materials
        api_keywords = ['api', 'active ingredient', 'drug substance', 'fluorouracil', 'paracetamol', 'ibuprofen']
        excipient_keywords = ['excipient', 'sodium hydroxide', 'water for injection', 'preservative', 'sodium chloride']
        
        text_lower = self.full_text.lower()
        
        # Simple extraction
        for keyword in api_keywords:
            if keyword in text_lower:
                # Avoid duplicates
                if not any(m['material_name'].lower() == keyword for m in materials):
                    materials.append({
                        'material_type': 'API',
                        'material_name': keyword.title(),
                        'specification': 'USP',
                        'quantity': ''
                    })
        
        for keyword in excipient_keywords:
            if keyword in text_lower:
                # Avoid duplicates
                if not any(m['material_name'].lower() == keyword for m in materials):
                    materials.append({
                        'material_type': 'Excipient',
                        'material_name': keyword.title(),
                        'specification': 'USP',
                        'quantity': ''
                    })
        
        logger.info(f"Total extracted {len(materials)} materials")
        return materials[:50]  # Limit to 50 items
    
    def _extract_materials_from_tables(self) -> List[Dict]:
        """Extract materials from tables in the PDF, capturing all columns"""
        materials = []
        for table in self.tables:
            df = table.df
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            material_keywords = ['material', 'ingredient', 'component', 'item', 'api', 'excipient']
            is_material_table = any(
                any(keyword in str(header).lower() for keyword in material_keywords)
                for header in headers
            )
            if is_material_table:
                for idx in range(1, len(df)):
                    row = df.iloc[idx]
                    materials.append({h: str(row[i]).strip() if i < len(row) else '' for i, h in enumerate(headers)})
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
        """Extract stages using regex, templates, and table matching"""
        
        stages = []
        
        # Method 1: Extract major process headings (Dispensing, Filling, Lyophilization, etc.)
        # These become the main stage headings
        major_process_headings = [
            ('Dispensing of Raw Material', r'dispensing\s+of\s+raw\s+material'),
            ('Manufacturing Process', r'manufacturing\s*process'),
            ('Filtration', r'filtration|aseptic\s+filtration'),
            ('Filling & Partial Plugging', r'filling\s*(?:&|and)\s*partial\s+plugging'),
            ('Lyophilization Process', r'lyophilization\s*process'),
            ('Visual Inspection', r'visual\s+inspection'),
            ('Sealing', r'sealing|capping'),
            ('Packaging', r'packaging|packing'),
            ('Labeling', r'labeling|labelling'),
        ]
        
        for stage_name, pattern in major_process_headings:
            if re.search(pattern, self.full_text, re.IGNORECASE):
                # Find the section text for this stage
                section_pattern = rf'{pattern}[:\s]*([^\n]{{0,500}})'
                match = re.search(section_pattern, self.full_text, re.IGNORECASE | re.DOTALL)
                
                parameters = ''
                if match and match.group(1):
                    parameters = match.group(1).strip()[:200]
                
                stages.append({
                    'stage_number': len(stages) + 1,
                    'stage_name': stage_name,
                    'equipment_used': '',
                    'parameters': parameters,
                    'acceptance_criteria': ''
                })
        
        # Method 2: Try table extraction
        stages_from_tables = self._extract_stages_from_tables()
        if stages_from_tables:
            # Add table stages if not already present
            for table_stage in stages_from_tables:
                if not any(table_stage['stage_name'].lower() in s['stage_name'].lower() for s in stages):
                    stages.append(table_stage)
            logger.info(f"Extracted {len(stages_from_tables)} stages from tables")
        
        # Remove duplicates and re-number
        unique_stages = []
        seen_names = set()
        for stage in stages:
            name_lower = stage['stage_name'].lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                stage['stage_number'] = len(unique_stages) + 1
                unique_stages.append(stage)
        
        logger.info(f"Total extracted {len(unique_stages)} unique stages")
        return unique_stages[:30]
    
    def _extract_stages_from_tables(self) -> List[Dict]:
        """Extract manufacturing stages from tables"""
        stages = []
        
        for idx, table in enumerate(self.tables):
            df = table.df
            
            # Check if this table contains stage/process data
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            
            # DEBUG: Log table info
            logger.info(f"Table {idx} has {len(df)} rows, headers: {list(headers)}")
            
            stage_keywords = ['stage', 'step', 'process', 'operation', 'activity', 'procedure']
            
            # Check if this is a stages table
            is_stage_table = any(
                any(keyword in str(header).lower() for keyword in stage_keywords)
                for header in headers
            )
            
            if is_stage_table:
                # Find column indices
                stage_col = None
                name_col = None
                equipment_col = None
                params_col = None
                criteria_col = None
                
                for i, header in enumerate(headers):
                    header_lower = str(header).lower()
                    if 'no' in header_lower or 'number' in header_lower or '#' in header_lower:
                        stage_col = i
                    elif any(kw in header_lower for kw in stage_keywords):
                        name_col = i
                    elif 'equipment' in header_lower or 'machine' in header_lower:
                        equipment_col = i
                    elif 'parameter' in header_lower or 'condition' in header_lower:
                        params_col = i
                    elif 'criteria' in header_lower or 'acceptance' in header_lower or 'limit' in header_lower:
                        criteria_col = i
                
                # Extract stage rows
                for idx in range(1, len(df)):  # Skip header row
                    row = df.iloc[idx]
                    
                    # Get stage number
                    stage_num = idx
                    if stage_col is not None and pd.notna(row[stage_col]):
                        try:
                            stage_num = int(re.search(r'\d+', str(row[stage_col])).group())
                        except:
                            stage_num = idx
                    
                    # Get stage name
                    stage_name = ''
                    if name_col is not None and pd.notna(row[name_col]):
                        stage_name = str(row[name_col]).strip()
                    
                    if stage_name:
                        stages.append({
                            'stage_number': stage_num,
                            'stage_name': stage_name,
                            'equipment_used': str(row[equipment_col]).strip() if equipment_col is not None and pd.notna(row[equipment_col]) else '',
                            'parameters': str(row[params_col]).strip() if params_col is not None and pd.notna(row[params_col]) else '',
                            'acceptance_criteria': str(row[criteria_col]).strip() if criteria_col is not None and pd.notna(row[criteria_col]) else ''
                        })
        
        return stages
    
    def _extract_test_criteria(self) -> List[Dict]:
        """Extract test criteria and acceptance limits from tables and text"""
        
        criteria = []
        
        # Method 1: Extract from tables first
        criteria_from_tables = self._extract_test_criteria_from_tables()
        if criteria_from_tables:
            criteria.extend(criteria_from_tables)
            logger.info(f"Extracted {len(criteria_from_tables)} test criteria from tables")
        
        # Method 2: Common test patterns from text
        test_patterns = [
            (r'pH[:\s]+(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)', 'pH Test'),
            (r'Assay[:\s]+(\d+\.?\d*)\s*[-–to]\s*(\d+\.?\d*)%', 'Assay'),
            (r'Volume[:\s]+(\d+\.?\d*)\s*(?:ml|ML)', 'Volume'),
            (r'Weight[:\s]+(\d+\.?\d*)\s*(?:g|kg|mg)', 'Weight'),
            (r'Particulate\s+Matter', 'Particulate Matter'),
            (r'Sterility\s+Test', 'Sterility Test'),
            (r'Endotoxin[:\s]+(<\s*\d+\.?\d*)', 'Endotoxin Test'),
        ]
        
        for pattern, test_name in test_patterns:
            matches = re.finditer(pattern, self.full_text, re.IGNORECASE)
            for match in matches:
                # Avoid duplicates
                if not any(c['test_name'].lower() == test_name.lower() for c in criteria):
                    criteria.append({
                        'test_id': f'test_{len(criteria)+1}',
                        'test_name': test_name,
                        'acceptance_criteria': match.group(0)
                    })
        
        logger.info(f"Total extracted {len(criteria)} test criteria")
        return criteria[:50]  # Limit to 50
    
    def _extract_test_criteria_from_tables(self) -> List[Dict]:
        """Extract test criteria from tables"""
        criteria = []
        
        for table in self.tables:
            df = table.df
            
            # Check if this table contains test/quality criteria
            headers = df.iloc[0].str.lower() if len(df) > 0 else []
            
            test_keywords = ['test', 'parameter', 'specification', 'quality', 'analysis', 'examination']
            criteria_keywords = ['criteria', 'acceptance', 'limit', 'specification', 'range']
            
            # Check if this is a test criteria table
            is_test_table = (
                any(any(keyword in str(header).lower() for keyword in test_keywords) for header in headers) and
                any(any(keyword in str(header).lower() for keyword in criteria_keywords) for header in headers)
            )
            
            if is_test_table:
                # Find column indices
                test_col = None
                criteria_col = None
                method_col = None
                
                for i, header in enumerate(headers):
                    header_lower = str(header).lower()
                    if any(kw in header_lower for kw in test_keywords):
                        test_col = i
                    elif any(kw in header_lower for kw in criteria_keywords):
                        criteria_col = i
                    elif 'method' in header_lower or 'procedure' in header_lower:
                        method_col = i
                
                # Extract test criteria rows
                for idx in range(1, len(df)):  # Skip header row
                    row = df.iloc[idx]
                    
                    if test_col is not None and pd.notna(row[test_col]) and str(row[test_col]).strip():
                        test_name = str(row[test_col]).strip()
                        acceptance = str(row[criteria_col]).strip() if criteria_col is not None and pd.notna(row[criteria_col]) else ''
                        
                        criteria.append({
                            'test_id': f'test_{len(criteria)+1}',
                            'test_name': test_name,
                            'acceptance_criteria': acceptance
                        })
        
        return criteria
    
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