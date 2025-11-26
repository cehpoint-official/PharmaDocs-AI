"""
Enhanced PVP AI Extraction Service
Extracts comprehensive data from Process Validation Protocol PDFs using AI
"""

import os
import re
import json
import math
import logging
import datetime
from typing import Dict, List, Optional
from pathlib import Path

import pdfplumber
import pandas as pd

# Optional AI + OCR + PDF rendering
try:
    import camelot
except Exception:
    camelot = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

try:
    from docx import Document
    from docx.shared import Pt, Inches
except Exception:
    Document = None

try:
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML
except Exception:
    Environment = None
    HTML = None

logger = logging.getLogger(__name__)
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)

# Configure Gemini (optional)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY and genai:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        logger.warning("Failed to configure Gemini model: %s", e)
        model = None
else:
    model = None
    logger.info("Gemini API key not found or SDK not available. Using regex-only extraction.")


# -----------------------
# Utility helpers
# -----------------------
def _to_float(x):
    try:
        s = str(x)
        s = s.replace(',', '')
        v = re.search(r'-?\d+(\.\d+)?', s)
        return float(v.group(0)) if v else None
    except Exception:
        return None


def compute_stats(values):
    vals = [v for v in (_to_float(x) for x in values) if v is not None]
    if not vals:
        return {}
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    std = math.sqrt(var)
    rsd = (std / mean * 100) if mean != 0 else None
    return {
        'mean': round(mean, 6),
        'std': round(std, 6),
        'rsd': round(rsd, 4) if rsd is not None else None,
        'count': len(vals)
    }


def normalize_header(h: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', str(h).lower()).strip()


def ensure_df(table):
    """Return a pandas DataFrame for a camelot table or None if empty."""
    if table is None:
        return None
    df = getattr(table, 'df', None)
    if df is None:
        return None
    try:
        df = pd.DataFrame(df)
    except Exception:
        pass
    if df is None or df.shape[0] == 0:
        return None
    return df


def _clean_text_val(v: Optional[str], max_len: int = 190) -> str:
    """Normalize whitespace, remove control chars, truncate to max_len."""
    if v is None:
        return ''
    s = str(v)
    s = s.replace('\r', ' ').replace('\n', ' ').strip()
    s = re.sub(r'\s+', ' ', s)
    s = ''.join(ch for ch in s if ch.isprintable())
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip()
    return s


def _is_obvious_heading(s: str) -> bool:
    if not s:
        return False
    low = s.lower()
    skip_prefixes = (
        'cover page', 'table of contents', 'protocol approval', 'objective',
        'scope', 'validation approach', 'reason for validation', 'revalidation',
        'index', 'page', 'product standard', 'stability protocol', 'contents',
        'cover', 'acknowledgement', 'references', 'appendix', 'format no',
        'effective date', 'supersedes'
    )
    for p in skip_prefixes:
        if low.startswith(p):
            return True
    if re.fullmatch(r'[0-9\.\-]{1,4}', low):
        return True
    return False


# -----------------------
# Main extractor
# -----------------------
class EnhancedPVPExtractor:
    """Extract comprehensive data from PVP documents"""
    
    def __init__(self, pdf_path: str, tesseract_cmd: Optional[str] = None):
        self.pdf_path = str(pdf_path)
        self.full_text: str = ""
        self.product_type: Optional[str] = None
        self.tables = []
        self.tables_df: List[pd.DataFrame] = []
        if tesseract_cmd:
            os.environ['TESSERACT_CMD'] = tesseract_cmd

    # -----------------------
    # Public runner
    # -----------------------
    def extract_all(self) -> Dict:
        """Main extraction method - extracts everything from PVP"""
        logger.info(f"Starting extraction from: {self.pdf_path}")
        
        # Extract full text from PDF (with OCR fallback)
        self.full_text = self._extract_text_from_pdf()
        if not self.full_text or len(self.full_text.strip()) == 0:
            logger.error("Failed to extract text from PDF or it's empty")
            return self._empty_result()
        logger.info(f"Extracted text length: {len(self.full_text)}")

        # Extract tables
        self.tables = self._extract_tables_from_pdf()
        self.tables_df = []
        for t in self.tables:
            df = ensure_df(t)
            if df is not None:
                self.tables_df.append(df)

        logger.info(f"Extracted {len(self.tables_df)} usable tables from PDF")

        # Build result with ALL sections
        result = {
            'product_info': self._extract_product_info(),
            'product_type': self._detect_product_type(),
            'equipment': self._extract_equipment(),
            'materials': self._extract_materials(),
            'stages': self._extract_stages(),
            'test_criteria': self._extract_test_criteria(),
            'test_preparations': self._extract_test_preparations(),
            'calculation_sheet': self._extract_calculation_sheet(),
            'batch_details': self._extract_batch_details(),
            
            # NEW SECTIONS
            'hold_time_study': self._extract_hold_time_study(),
            'bioburden_bet': self._extract_bioburden_bet(),
            'qc_final_product': self._extract_qc_final_product(),
            'water_quality': self._extract_water_quality(),
            'vial_sterility': self._extract_vial_sterility(),
            'manufacturing_params': self._extract_manufacturing_params(),
            
            'observations': self._extract_observations(),
            'signatures': self._extract_signatures(),
            'protocol_summary': self._extract_protocol_summary(),
            'raw_text_length': len(self.full_text)
        }

        # Calculate statistics
        result['statistics'] = self._calculate_statistics_from_criteria(result['test_criteria'])

        self.product_type = result['product_type']
        logger.info("Extraction complete: product=%s, type=%s", 
                   result['product_info'].get('product_name'), result['product_type'])
        return result

    # -----------------------
    # Text extraction with OCR fallback
    # -----------------------
    def _extract_text_from_pdf(self) -> str:
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = page.extract_text() or ""
                    except Exception:
                        page_text = ""
                    
                    # If text is short or empty, try OCR
                    if not page_text or len(page_text.strip()) < 60:
                        if pytesseract:
                            try:
                                pil_img = page.to_image(resolution=200).original
                                ocr_text = pytesseract.image_to_string(pil_img)
                                page_text = (page_text or "") + "\n" + ocr_text
                                logger.debug("OCR used on page %d, extracted %d chars", page_num, len(ocr_text))
                            except Exception as e:
                                logger.debug("OCR failed on page %d: %s", page_num, e)
                        else:
                            logger.debug("No pytesseract available; skipping OCR")
                    
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error("Error reading PDF via pdfplumber: %s", e)
            return ""
        return text

    # -----------------------
    # Table extraction (camelot)
    # -----------------------
    def _extract_tables_from_pdf(self) -> List:
        try:
            tables = []
            try:
                if camelot:
                    tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='lattice')
                    logger.info("Camelot lattice found %d tables", len(tables))
                else:
                    logger.debug("Camelot not available")
            except Exception as e:
                logger.debug("Camelot lattice failed: %s", e)

            if not tables and camelot:
                try:
                    tables = camelot.read_pdf(self.pdf_path, pages='all', flavor='stream')
                    logger.info("Camelot stream found %d tables", len(tables))
                except Exception as e:
                    logger.debug("Camelot stream failed: %s", e)

            for table in tables:
                try:
                    if hasattr(table, '_close_temp_files'):
                        table._close_temp_files()
                except Exception:
                    pass

            return tables or []
        except Exception as e:
            logger.error("Error extracting tables: %s", e)
            return []

    # -----------------------
    # Product info extraction
    # -----------------------
    def _extract_product_info(self) -> Dict:
        if model:
            return self._extract_product_info_with_ai()
        return self._extract_product_info_with_regex()

    def _extract_product_info_with_ai(self) -> Dict:
        try:
            prompt = f"""
Extract the following product information from this Process Validation Protocol:

Text:
{self.full_text[:4000]}

Return ONLY a JSON object with the fields:
{{"product_name": "...", "strength": "...", "dosage_form": "...", "batch_size": "...", "pack_size":"...", "manufacturing_site":"..."}}
"""
            response = model.generate_content(prompt)
            result_text = getattr(response, 'text', str(response)).strip()
            jstart = result_text.find('{')
            jend = result_text.rfind('}')
            if jstart != -1 and jend != -1 and jend > jstart:
                candidate = result_text[jstart:jend+1]
                try:
                    product_info = json.loads(candidate)
                    return product_info
                except Exception as e:
                    logger.error("AI returned non-JSON or parse failed: %s", e)
            logger.warning("AI did not return valid JSON, falling back to regex")
            return self._extract_product_info_with_regex()
        except Exception as e:
            logger.error("AI extraction failed: %s", e)
            return self._extract_product_info_with_regex()

    def _extract_product_info_with_regex(self) -> Dict:
        product_info = {
            'product_name': '',
            'strength': '',
            'dosage_form': '',
            'batch_size': '',
            'pack_size': '',
            'manufacturing_site': ''
        }
        
        lines = [l.strip() for l in self.full_text.splitlines() if l.strip()]
        
        # Product name
        for line in lines[:30]:
            if any(k in line.lower() for k in ['injection', 'tablet', 'capsule', 'syrup', 'suspension', 'vial']):
                product_info['product_name'] = line
                break
        
        # Strength
        m = re.search(r'(\d+(?:\.\d+)?)\s*(mg|g|ml|mcg|%|iu)(?:\s*/\s*(ml|g|tablet|capsule))?', self.full_text, re.I)
        if m:
            product_info['strength'] = m.group(0)
        
        # Batch size
        m = re.search(r'batch\s*size[:\s]*([\d, ]+\s*(?:vials|tablets|capsules|bottles|units|liters|litres)?)', self.full_text, re.I)
        if m:
            product_info['batch_size'] = m.group(1).strip()
        
        return product_info

    # -----------------------
    # Product type detection
    # -----------------------
    def _detect_product_type(self) -> str:
        text = (self.full_text or "").lower()
        injectable = sum(k in text for k in ['injection', 'injectable', 'vial', 'ampoule', 'aseptic'])
        tablet = sum(k in text for k in ['tablet', 'compression', 'granulation', 'coating'])
        capsule = sum(k in text for k in ['capsule', 'gelatin', 'shell'])
        oral = sum(k in text for k in ['syrup', 'suspension', 'solution', 'bottle filling'])
        scores = {'Injectable': injectable, 'Tablet': tablet, 'Capsule': capsule, 'Oral_Liquid': oral}
        return max(scores, key=scores.get)

    # -----------------------
    # Equipment extraction (FIXED)
    # -----------------------
    def _extract_equipment(self) -> List[Dict]:
        eq_from_tables = self._extract_equipment_from_tables()
        if eq_from_tables:
            return eq_from_tables
        
        # Fallback to text
        equipment = []
        pat = r'(?:equipment and machinery list|production equipment|equipment list)(.*?)(?:raw material|materials|quality control|$)'
        m = re.search(pat, self.full_text, re.I | re.S)
        if m:
            lines = [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]
            for ln in lines:
                if len(ln) > 4 and not ln.lower().startswith('s.no') and not _is_obvious_heading(ln):
                    equipment.append({
                        'equipment_name': _clean_text_val(ln, max_len=190),
                        'equipment_id': '',
                        'location': '',
                        'calibration_status': ''
                    })
        return equipment

    def _extract_equipment_from_tables(self) -> List[Dict]:
        """FIXED: Simpler, less aggressive filtering"""
        equipment = []
        seen = set()

        for df in self.tables_df:
            # Check if this looks like equipment table
            try:
                first_row_text = ' '.join([str(x).lower() for x in df.iloc[0].tolist()])
            except:
                continue
            
            if 'equipment' not in first_row_text and 'machine' not in first_row_text:
                continue
            
            logger.info(f"Found equipment table with {df.shape[0]} rows")
            
            # Process all rows
            for ridx in range(1, df.shape[0]):
                try:
                    row = df.iloc[ridx].tolist()
                    
                    # Get equipment name (usually first column)
                    eq_name = str(row[0]).strip() if len(row) > 0 else ''
                    
                    # Skip empty or obvious headers
                    if not eq_name or len(eq_name) < 3:
                        continue
                    
                    if any(x in eq_name.lower() for x in ['equipment name', 'sr.no', 's.no', 'sr no', 'equipment', 'format no', 'page']):
                        continue
                    
                    # Get ID (usually second or third column)
                    eq_id = ''
                    if len(row) > 2:
                        eq_id = str(row[2]).strip()
                    elif len(row) > 1:
                        eq_id = str(row[1]).strip()
                    
                    # Clean and add
                    eq_name_clean = _clean_text_val(eq_name, 190)
                    eq_id_clean = _clean_text_val(eq_id, 100)
                    
                    # Skip if too short or obvious junk
                    if len(eq_name_clean) < 3 or _is_obvious_heading(eq_name_clean):
                        continue
                    
                    key = (eq_name_clean.lower(), eq_id_clean.lower())
                    if key not in seen:
                        seen.add(key)
                        equipment.append({
                            'equipment_name': eq_name_clean,
                            'equipment_id': eq_id_clean if eq_id_clean else 'N/A',
                            'location': 'N/A',
                            'calibration_status': 'N/A'
                        })
                        
                except Exception as e:
                    logger.debug(f"Error processing equipment row {ridx}: {e}")
                    continue
            
        logger.info(f"Extracted {len(equipment)} equipment items")
        return equipment

    # -----------------------
    # Materials extraction
    # -----------------------
    def _extract_materials(self) -> List[Dict]:
        if model:
            try:
                return self._extract_materials_with_ai()
            except Exception as e:
                logger.debug("AI materials failed: %s", e)
        return self._extract_materials_with_regex()

    def _extract_materials_with_ai(self) -> List[Dict]:
        try:
            prompt = (
                "Extract all materials from this validation protocol. "
                "Categorize as API, Excipient, or Packaging.\n\n"
                "Text:\n"
                f"{self.full_text[:5000]}\n\n"
                "Return ONLY a JSON array like this:\n"
                '[\n'
                '  {\n'
                '    "material_type": "API",\n'
                '    "material_name": "Fluorouracil",\n'
                '    "specification": "USP",\n'
                '    "quantity": "500 mg"\n'
                '  }\n'
                ']\n\n'
                "Return only the JSON array, no other text."
            )
            response = model.generate_content(prompt)
            result_text = getattr(response, 'text', str(response)).strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            jstart = result_text.find('[')
            jend = result_text.rfind(']')
            if jstart != -1 and jend != -1 and jend > jstart:
                materials = json.loads(result_text[jstart:jend+1])
                logger.info(f"AI extracted {len(materials)} materials")
                return materials
        except Exception as e:
            logger.error(f"AI materials extraction failed: {e}")
        return self._extract_materials_with_regex()

    def _extract_materials_with_regex(self) -> List[Dict]:
        materials = []
        mats_from_tables = self._extract_materials_from_tables()
        if mats_from_tables:
            materials.extend(mats_from_tables)
        
        # Keyword heuristics
        text = (self.full_text or "").lower()
        apis = ['api', 'active ingredient', 'acetaminophen', 'paracetamol', 'ibuprofen', 'fluorouracil']
        excips = ['excipient', 'sodium hydroxide', 'water for injection', 'sodium chloride', 'preservative', 'tromethamine', 'disodium edetate']
        
        for k in apis:
            if k in text and not any(k in m.get('material_name', '').lower() for m in materials):
                materials.append({'material_type': 'API', 'material_name': k.title(), 'specification': '', 'quantity': ''})
        
        for k in excips:
            if k in text and not any(k in m.get('material_name', '').lower() for m in materials):
                materials.append({'material_type': 'Excipient', 'material_name': k.title(), 'specification': '', 'quantity': ''})
        
        return materials[:200]

    def _extract_materials_from_tables(self) -> List[Dict]:
        materials = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            if not headers:
                continue
            
            def find_idx(possibles):
                for p in possibles:
                    for i, h in enumerate(headers):
                        if p in h:
                            return i
                return None
            
            name_idx = find_idx(['material name', 'name', 'ingredient'])
            type_idx = find_idx(['material type', 'type'])
            spec_idx = find_idx(['specification', 'spec'])
            qty_idx = find_idx(['quantity', 'qty', 'amount'])
            
            if name_idx is not None:
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    name = str(row[name_idx]).strip() if name_idx < len(row) else ''
                    if name and name.upper() != 'N/A' and len(name) > 2:
                        materials.append({
                            'material_type': str(row[type_idx]).strip() if type_idx is not None and type_idx < len(row) else '',
                            'material_name': _clean_text_val(name, max_len=190),
                            'specification': str(row[spec_idx]).strip() if spec_idx is not None and spec_idx < len(row) else '',
                            'quantity': str(row[qty_idx]).strip() if qty_idx is not None and qty_idx < len(row) else ''
                        })
        return materials

    # -----------------------
    # Batch details extraction
    # -----------------------
    def _extract_batch_details(self) -> List[Dict]:
        batches = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            if not headers:
                continue
            
            batch_keys = ['batch no', 'batch number', 'batch', 'lot', 'mfg date', 'manufacture', 'expiry', 'exp date']
            if any(any(k in h for h in headers) for k in batch_keys):
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    row_dict = {}
                    for i, h in enumerate(headers):
                        row_dict[h] = str(row[i]).strip() if i < len(row) else ''
                    if row_dict:
                        batches.append(row_dict)
        return batches

    # -----------------------
    # NEW: Hold Time Study Extraction
    # -----------------------
    def _extract_hold_time_study(self) -> Dict:
        """Extract hold time study data (before/after filtration)"""
        hold_time = {
            'before_filtration': [],
            'after_filtration': []
        }
        
        for df in self.tables_df:
            try:
                text = ' '.join([str(x).lower() for x in df.iloc[0].tolist()])
            except:
                continue
            
            # Look for hold time indicators
            if 'hold' in text or any(x in text for x in ['0 hour', '6 hour', '12 hour', '24 hour', '48 hour']):
                logger.info("Found hold time study table")
                
                for ridx in range(1, df.shape[0]):
                    try:
                        row = df.iloc[ridx].tolist()
                        
                        # Extract data
                        time = str(row[0]).strip() if len(row) > 0 else ''
                        if not time or 'hour' not in time.lower():
                            continue
                        
                        entry = {
                            'time': time,
                            'description': str(row[1]).strip() if len(row) > 1 else '',
                            'pH': str(row[2]).strip() if len(row) > 2 else '',
                            'assay': str(row[3]).strip() if len(row) > 3 else '',
                            'bioburden': str(row[4]).strip() if len(row) > 4 else '',
                            'sterility': str(row[5]).strip() if len(row) > 5 else ''
                        }
                        
                        # Determine if before or after filtration
                        if 'before' in text or 'manufacturing tank' in text:
                            hold_time['before_filtration'].append(entry)
                        else:
                            hold_time['after_filtration'].append(entry)
                            
                    except Exception as e:
                        logger.debug(f"Error processing hold time row: {e}")
                        continue
        
        return hold_time

    # -----------------------
    # NEW: Bioburden & BET Extraction
    # -----------------------
    def _extract_bioburden_bet(self) -> List[Dict]:
        """Extract bioburden and BET test results"""
        results = []
        
        for df in self.tables_df:
            try:
                text = ' '.join([str(x).lower() for x in df.iloc[0].tolist()])
            except:
                continue
            
            if any(k in text for k in ['bioburden', 'bet', 'endotoxin', 'bacterial']):
                logger.info("Found bioburden/BET table")
                
                for ridx in range(1, df.shape[0]):
                    try:
                        row = df.iloc[ridx].tolist()
                        
                        results.append({
                            'stage': _clean_text_val(str(row[0]).strip() if len(row) > 0 else '', 200),
                            'test': _clean_text_val(str(row[1]).strip() if len(row) > 1 else '', 100),
                            'specification': _clean_text_val(str(row[2]).strip() if len(row) > 2 else '', 200),
                            'result': _clean_text_val(str(row[3]).strip() if len(row) > 3 else '', 200)
                        })
                    except:
                        continue
        
        return results

    # -----------------------
    # NEW: Quality Control Final Product
    # -----------------------
    def _extract_qc_final_product(self) -> List[Dict]:
        """Extract final product quality control results"""
        qc_results = []
        
        # Search for QC section in text
        match = re.search(
            r'quality control.*?finish.*?product(.*?)(?:conclusion|deviation|summary|$)',
            self.full_text,
            re.I | re.S
        )
        
        if match:
            section = match.group(1)
            
            # Extract key tests
            tests_patterns = [
                ('Description', r'description[:\s]+(.*?)(?:\n|$)'),
                ('pH', r'ph[:\s]+([\d\.\-\s]+)'),
                ('Assay', r'assay[:\s]+([\d\.\-%\s]+)'),
                ('Sterility', r'sterility[:\s]+(.*?)(?:\n|$)'),
                ('BET', r'bet[:\s]+(.*?)(?:\n|$)'),
                ('Bacterial Endotoxins', r'bacterial endotoxins[:\s]+(.*?)(?:\n|$)'),
                ('Particulate Matter', r'particulate matter[:\s]+(.*?)(?:\n|$)'),
                ('Extractable Volume', r'extractable volume[:\s]+(.*?)(?:\n|$)')
            ]
            
            for test_name, pattern in tests_patterns:
                m = re.search(pattern, section, re.I)
                if m:
                    qc_results.append({
                        'test_name': test_name,
                        'result': _clean_text_val(m.group(1).strip(), 200)
                    })
        
        # Also check tables
        for df in self.tables_df:
            try:
                text = ' '.join([str(x).lower() for x in df.iloc[0].tolist()])
            except:
                continue
            
            if 'quality' in text or 'finish' in text or 'specification' in text:
                for ridx in range(1, min(df.shape[0], 30)):
                    try:
                        row = df.iloc[ridx].tolist()
                        test_name = str(row[0]).strip() if len(row) > 0 else ''
                        result = str(row[1]).strip() if len(row) > 1 else ''
                        
                        if test_name and result and len(test_name) > 2:
                            qc_results.append({
                                'test_name': _clean_text_val(test_name, 200),
                                'result': _clean_text_val(result, 200)
                            })
                    except:
                        continue
        
        return qc_results

    # -----------------------
    # NEW: Water Quality Extraction
    # -----------------------
    def _extract_water_quality(self) -> List[Dict]:
        """Extract water quality test results (purified water, WFI)"""
        water_tests = []
        
        for df in self.tables_df:
            try:
                text = ' '.join([str(x).lower() for x in df.iloc[0].tolist()])
            except:
                continue
            
            if any(k in text for k in ['water', 'wfi', 'purified', 'conductivity']):
                logger.info("Found water quality table")
                
                for ridx in range(1, df.shape[0]):
                    try:
                        row = df.iloc[ridx].tolist()
                        
                        water_tests.append({
                            'type': _clean_text_val(str(row[0]).strip() if len(row) > 0 else '', 100),
                            'test': _clean_text_val(str(row[1]).strip() if len(row) > 1 else '', 100),
                            'specification': _clean_text_val(str(row[2]).strip() if len(row) > 2 else '', 100),
                            '