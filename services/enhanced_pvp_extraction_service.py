"""
Enhanced PVP AI Extraction Service
Extracts comprehensive data from Process Validation Protocol PDFs using AI
"""

# enhanced_pvp_extraction_service.py
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
        # Replace comma thousand separators
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
    return {'mean': round(mean, 6), 'std': round(std, 6), 'rsd': round(rsd, 4) if rsd is not None else None, 'count': len(vals)}

def normalize_header(h: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', str(h).lower()).strip()

def ensure_df(table):
    """Return a pandas DataFrame for a camelot table or None if empty."""
    if table is None:
        return None
    df = getattr(table, 'df', None)
    if df is None:
        return None
    # some camelot df objects are already DataFrame-like
    try:
        df = pd.DataFrame(df)
    except Exception:
        pass
    if df is None or df.shape[0] == 0:
        return None
    return df

# New cleaning helper to avoid DB truncation errors
def _clean_text_val(v: Optional[str], max_len: int = 190) -> str:
    """Normalize whitespace, remove control chars, truncate to max_len."""
    if v is None:
        return ''
    s = str(v)
    # remove common page header/footer markers like 'Page 1 of 23' (optional)
    s = s.replace('\r', ' ').replace('\n', ' ').strip()
    # collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    # remove non-printable control characters
    s = ''.join(ch for ch in s if ch.isprintable())
    # trim
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
        'cover', 'acknowledgement', 'references', 'appendix'
    )
    for p in skip_prefixes:
        if low.startswith(p):
            return True
    # headers that are very short numeric headings or single characters
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
        self.tables = []  # camelot Table objects
        self.tables_df: List[pd.DataFrame] = []  # DataFrames converted from tables
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
        # Convert tables to DataFrames for easier processing
        self.tables_df = []
        for t in self.tables:
            df = ensure_df(t)
            if df is not None:
                # If first row seems like header, keep it but we'll use normalized header logic in readers
                self.tables_df.append(df)

        logger.info(f"Extracted {len(self.tables_df)} usable tables from PDF")

        # Build result
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
            'batch_details': self._extract_batch_details(),
            'raw_text_length': len(self.full_text)
        }

        self.product_type = result['product_type']
        logger.info("Extraction complete: product=%s, type=%s", result['product_info'].get('product_name'), result['product_type'])
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
                    # If text is short or empty assume scanned and try OCR
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
            # try lattice first, then stream
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

            # camelot Table objects may leave temp files - attempt close if supported
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
    # Product info extraction (AI guarded + regex fallback)
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
            # extract JSON substring
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
        # heuristics: pick first lines, search for dosage forms, strengths, batch size
        lines = [l.strip() for l in self.full_text.splitlines() if l.strip()]
        # product name: look at first non-empty lines for keywords
        for line in lines[:30]:
            if any(k in line.lower() for k in ['injection', 'tablet', 'capsule', 'syrup', 'suspension', 'vial']):
                product_info['product_name'] = line
                break
        # strength
        m = re.search(r'(\d+(?:\.\d+)?)\s*(mg|g|ml|mcg|%|iu)(?:\s*/\s*(ml|g|tablet|capsule))?', self.full_text, re.I)
        if m:
            product_info['strength'] = m.group(0)
        # batch size
        m = re.search(r'batch\s*size[:\s]*([\d, ]+\s*(?:vials|tablets|capsules|bottles|units)?)', self.full_text, re.I)
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
    # Equipment extraction
    # -----------------------
    def _extract_equipment(self) -> List[Dict]:
        # try table-based extraction first
        eq_from_tables = self._extract_equipment_from_tables()
        if eq_from_tables:
            return eq_from_tables
        # fallback to text block search
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
        """Robustly extract equipment from tables: normalize headers, drop junk rows, dedupe."""
        equipment = []
        seen = set()

        def is_junk_cell(text: str) -> bool:
            if not text:
                return True
            t = str(text).strip().lower()
            # common junk lines found in your PDFs - extend this list as needed
            junk_starts = ('format no', 'process validation protocol', 'page', 'effective date', 'product name:', 'protocol no', 'no change is permitted', 'rev no')
            if len(t) < 2:
                return True
            if any(t.startswith(js) for js in junk_starts):
                return True
            # too short or only punctuation/digits
            if re.fullmatch(r'[\W\d]+', t):
                return True
            return False

        for df in self.tables_df:
            try:
                # normalize header row
                headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            except Exception:
                continue
            if not headers:
                continue

            # fuzzy header-to-index mapping
            def find_idx(possibles):
                for p in possibles:
                    for idx, h in enumerate(headers):
                        if p in h:
                            return idx
                return None

            name_idx = find_idx(['equipment name', 'equipment', 'name'])
            id_idx = find_idx(['equipment id', 'equipment id no', 'id', 'no'])
            loc_idx = find_idx(['location', 'place', 'dept'])
            cal_idx = find_idx(['calibration', 'status'])

            # fallback: assume first column is name if not found
            if name_idx is None:
                name_idx = 0

            # limit how many candidate rows we accept per table to avoid massive junk
            max_rows_per_table = max(200, df.shape[0])

            for ridx in range(1, min(df.shape[0], max_rows_per_table)):
                try:
                    row = df.iloc[ridx].tolist()
                except Exception:
                    continue

                # quickly join row cells to detect junk rows (repeated headers, footers)
                row_text = " ".join([str(x) for x in row if str(x).strip() != '']).strip()
                if not row_text:
                    continue
                if any(h in row_text.lower() for h in ['equipment name', 'sr no', 's.no', 'format no', 'page no', 'product name', 'protocol no']):
                    continue
                if is_junk_cell(row_text):
                    continue

                # read raw cells safely
                eq_name_raw = str(row[name_idx]).strip() if name_idx is not None and name_idx < len(row) else ''
                eq_id_raw = str(row[id_idx]).strip() if id_idx is not None and id_idx < len(row) else ''
                location_raw = str(row[loc_idx]).strip() if loc_idx is not None and loc_idx < len(row) else ''
                cal_status_raw = str(row[cal_idx]).strip() if cal_idx is not None and cal_idx < len(row) else ''

                # try fallback to find a good name cell if eq_name looks invalid
                if not eq_name_raw or re.fullmatch(r'[\W\d]+', eq_name_raw):
                    for cell in row:
                        c = str(cell).strip()
                        if c and not re.fullmatch(r'[\W\d]+', c):
                            eq_name_raw = c
                            break
                    if not eq_name_raw:
                        continue

                # Clean and truncate
                eq_name = _clean_text_val(eq_name_raw, max_len=190)
                eq_id = _clean_text_val(eq_id_raw, max_len=100)
                location = _clean_text_val(location_raw, max_len=100)
                cal_status = _clean_text_val(cal_status_raw, max_len=100)

                # skip obvious headings or short garbage
                if not eq_name or len(eq_name) < 2 or _is_obvious_heading(eq_name):
                    continue

                key = (eq_name.lower(), (eq_id or '').lower())
                if key in seen:
                    continue
                seen.add(key)

                equipment.append({
                    'equipment_name': eq_name,
                    'equipment_id': eq_id if eq_id else 'N/A',
                    'location': location if location else 'N/A',
                    'calibration_status': cal_status if cal_status else 'N/A'
                })
        return equipment

    # -----------------------
    # Materials extraction
    # -----------------------
    def _extract_materials(self) -> List[Dict]:
        # try AI if available
        if model:
            try:
                return self._extract_materials_with_ai()
            except Exception as e:
                logger.debug("AI materials failed: %s", e)
        return self._extract_materials_with_regex()
    def _extract_materials_with_ai(self) -> List[Dict]:
        """Extract materials using AI"""
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
            logger.error("AI materials extraction failed: {e}")
        return self._extract_materials_with_regex()

    def _extract_materials_with_regex(self) -> List[Dict]:
        materials = []
        # table-first
        mats_from_tables = self._extract_materials_from_tables()
        if mats_from_tables:
            materials.extend(mats_from_tables)
        # keyword heuristics
        text = (self.full_text or "").lower()
        apis = ['api', 'active ingredient', 'acetaminophen', 'paracetamol', 'ibuprofen', 'fluorouracil']
        excips = ['excipient', 'sodium hydroxide', 'water for injection', 'sodium chloride', 'preservative']
        for k in apis:
            if k in text and not any(k in m.get('material_name','').lower() for m in materials):
                materials.append({'material_type': 'API', 'material_name': k.title(), 'specification': '', 'quantity': ''})
        for k in excips:
            if k in text and not any(k in m.get('material_name','').lower() for m in materials):
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
            name_idx = find_idx(['material name', 'name'])
            type_idx = find_idx(['material type', 'type'])
            spec_idx = find_idx(['specification', 'spec'])
            qty_idx = find_idx(['quantity', 'qty', 'amount'])
            if name_idx is not None:
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    name = str(row[name_idx]).strip() if name_idx < len(row) else ''
                    if name and name.upper() != 'N/A':
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
            # typical batch headers
            batch_keys = ['batch no', 'batch number', 'batch', 'lot', 'mfg date', 'manufacture', 'expiry', 'exp date']
            if any(any(k in h for h in headers) for k in batch_keys):
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    row_dict = {}
                    for i, h in enumerate(headers):
                        row_dict[h] = str(row[i]).strip() if i < len(row) else ''
                    batches.append(row_dict)
        return batches

    # -----------------------
    # Stages extraction
    # -----------------------
    def _extract_stages(self) -> List[Dict]:
        if model:
            try:
                return self._extract_stages_with_ai()
            except Exception as e:
                logger.debug("AI stages failed: %s", e)
        return self._extract_stages_with_regex()

    def _extract_stages_with_ai(self) -> List[Dict]:
        # guarded AI call - fallback to regex
        prompt = f"Extract manufacturing stages and return JSON array from the text:\n{self.full_text[:8000]}"
        try:
            response = model.generate_content(prompt)
            text = getattr(response, 'text', str(response)).strip()
            jstart = text.find('[')
            jend = text.rfind(']')
            if jstart != -1 and jend != -1 and jend > jstart:
                arr = json.loads(text[jstart:jend+1])
                return arr
        except Exception as e:
            logger.debug("AI stages parse failed: %s", e)
        return self._extract_stages_with_regex()

    def _extract_stages_with_regex(self) -> List[Dict]:
        stages = []
        major_process_headings = [
            ('Dispensing', r'dispensing'),
            ('Filtration', r'filtration'),
            ('Filling', r'filling'),
            ('Lyophilization', r'lyophilization'),
            ('Visual Inspection', r'visual inspection'),
            ('Sealing/Capping', r'seal|cap|capping'),
            ('Packaging', r'packaging'),
        ]
        for name, patt in major_process_headings:
            m = re.search(patt, self.full_text, re.I)
            if m:
                # capture small context
                idx = m.start()
                context = self.full_text[max(0, idx - 200): idx + 400]
                stages.append({
                    'stage_number': len(stages) + 1,
                    'stage_name': name,
                    'equipment_used': '',
                    'parameters': context.strip()[:400],
                    'acceptance_criteria': ''
                })
        # also try tables
        tbl_stages = self._extract_stages_from_tables()
        for s in tbl_stages:
            if not any(s['stage_name'].lower() in ex['stage_name'].lower() for ex in stages):
                stages.append(s)
        # re-number
        for i, st in enumerate(stages):
            st['stage_number'] = i + 1
        return stages

    def _extract_stages_from_tables(self) -> List[Dict]:
        stages = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            stage_keywords = ['stage', 'step', 'process', 'operation']
            if any(any(k in h for h in headers) for k in stage_keywords):
                # try to map columns
                def idx_of(poss):
                    for p in poss:
                        for i, h in enumerate(headers):
                            if p in h:
                                return i
                    return None
                name_idx = idx_of(['stage', 'step', 'process', 'activity'])
                eq_idx = idx_of(['equipment', 'machine'])
                param_idx = idx_of(['parameter', 'condition'])
                crit_idx = idx_of(['criteria', 'acceptance', 'limit'])
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    name = str(row[name_idx]).strip() if name_idx is not None and name_idx < len(row) else ''
                    if name:
                        stages.append({
                            'stage_number': ridx,
                            'stage_name': _clean_text_val(name, max_len=200),
                            'equipment_used': _clean_text_val(str(row[eq_idx]).strip() if eq_idx is not None and eq_idx < len(row) else '', max_len=200),
                            'parameters': _clean_text_val(str(row[param_idx]).strip() if param_idx is not None and param_idx < len(row) else '', max_len=400),
                            'acceptance_criteria': _clean_text_val(str(row[crit_idx]).strip() if crit_idx is not None and crit_idx < len(row) else '', max_len=400)
                        })
        return stages

    # -----------------------
    # Test preparations & calculations
    # -----------------------
    def _extract_test_preparations(self) -> List[Dict]:
        preparations = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            if any('preparation' in h or 'absorbance' in h or 'area' in h for h in headers):
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    preparations.append({
                        'test_name': _clean_text_val(str(row[0]).strip() if len(row) > 0 else '', max_len=200),
                        'preparation': _clean_text_val(str(row[1]).strip() if len(row) > 1 else '', max_len=400),
                        'area': _clean_text_val(str(row[2]).strip() if len(row) > 2 else '', max_len=100),
                        'absorbance': _clean_text_val(str(row[3]).strip() if len(row) > 3 else '', max_len=100)
                    })
        return preparations

    def _extract_calculation_sheet(self) -> List[Dict]:
        calculations = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            if any(k in ' '.join(headers) for k in ['mean', 'sd', 'rsd', 'calculation', 'result']):
                # try to extract numeric columns for stats
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    calculations.append({
                        'parameter': _clean_text_val(str(row[0]).strip() if len(row) > 0 else '', max_len=200),
                        'mean': _clean_text_val(str(row[1]).strip() if len(row) > 1 else '', max_len=100),
                        'sd': _clean_text_val(str(row[2]).strip() if len(row) > 2 else '', max_len=100),
                        'rsd': _clean_text_val(str(row[3]).strip() if len(row) > 3 else '', max_len=100),
                        'formula': _clean_text_val(str(row[4]).strip() if len(row) > 4 else '', max_len=400)
                    })
        return calculations

    # -----------------------
    # Observations, signatures, protocol summary
    # -----------------------
    def _extract_observations(self) -> str:
        m = re.search(r'(observations|remarks|deviations)[:\s]*\n?(.{0,800})', self.full_text, re.I)
        return m.group(2).strip() if m else ''

    def _extract_signatures(self) -> Dict:
        sigs = {}
        for role in ['performed by', 'checked by', 'approved by']:
            m = re.search(fr'{role}[:\s]*([A-Za-z ,\.\-]+)', self.full_text, re.I)
            if m:
                sigs[role.replace(' ', '_')] = m.group(1).strip()
        # capture first date occurrence
        m = re.search(r'(\d{2}/\d{2}/\d{4})', self.full_text)
        if m:
            sigs['date'] = m.group(1)
        return sigs

    def _extract_protocol_summary(self) -> str:
        start = re.search(r'(methodology|protocol|procedure)[:\s]*\n', self.full_text, re.I)
        if not start:
            return ''
        start_idx = start.start()
        # find next major heading
        end = re.search(r'(calculations|results|observations|conclusion|references)[:\s]*\n', self.full_text[start_idx:], re.I)
        if end:
            return self.full_text[start_idx:start_idx + end.start()].strip()
        return self.full_text[start_idx:].strip()

    # -----------------------
    # Test criteria extraction
    # -----------------------
    def _extract_test_criteria(self) -> List[Dict]:
        crits = []
        # tables first
        ct_from_tables = self._extract_test_criteria_from_tables()
        crits.extend(ct_from_tables)
        # text heuristics
        patterns = [
            (r'pH[:\s]*([0-9\.]+)\s*(?:-|to|–)\s*([0-9\.]+)', 'pH'),
            (r'Assay[:\s]*([0-9\.]+)\s*(?:-|to|–)\s*([0-9\.]+)%', 'Assay'),
            (r'Volume[:\s]*([0-9\.]+)\s*ml', 'Volume')
        ]
        for patt, name in patterns:
            for m in re.finditer(patt, self.full_text, re.I):
                crits.append({'test_id': f'test_{len(crits)+1}', 'test_name': name, 'acceptance_criteria': m.group(0)})
        return crits

    def _extract_test_criteria_from_tables(self) -> List[Dict]:
        criteria = []
        for df in self.tables_df:
            headers = [normalize_header(h) for h in df.iloc[0].tolist()] if df.shape[0] > 0 else []
            if not headers:
                continue
            # determine if this is a test spec table
            if any(k in h for h in headers for k in ['test', 'parameter', 'specification', 'acceptance', 'limit']):
                # find cols
                def idx_of_poss(poss):
                    for p in poss:
                        for i, h in enumerate(headers):
                            if p in h:
                                return i
                    return None
                test_idx = idx_of_poss(['test', 'parameter', 'name'])
                crit_idx = idx_of_poss(['acceptance', 'criteria', 'limit', 'specification', 'range'])
                for ridx in range(1, df.shape[0]):
                    row = df.iloc[ridx].tolist()
                    if test_idx is not None and test_idx < len(row) and str(row[test_idx]).strip():
                        criteria.append({
                            'test_id': f'test_{len(criteria)+1}',
                            'test_name': _clean_text_val(str(row[test_idx]).strip(), max_len=200),
                            'acceptance_criteria': _clean_text_val(str(row[crit_idx]).strip() if crit_idx is not None and crit_idx < len(row) else '', max_len=400)
                        })
        return criteria

    # -----------------------
    # Template normalizer & docx generation
    # -----------------------
    def normalize_for_template(self, extracted: Dict) -> Dict:
        """Produce the JSON structure expected by templates/view_pvr.html"""
        out = {}
        out['meta'] = extracted.get('product_info', {})
        batches = extracted.get('batch_details', [])
        # normalize batch list to have 'batch_number' key
        normalized_batches = []
        for b in batches:
            # pick best-known keys if present
            bn = b.get('batch no') or b.get('batch number') or b.get('batch') or b.get('lot') or ''
            if not bn:
                # try to pick first non-empty value
                for v in b.values():
                    if str(v).strip():
                        bn = str(v).strip()
                        break
            normalized_batches.append({'batch_number': bn, **b})
        out['batches'] = normalized_batches
        # build test_ids & data from test_criteria (best-effort) and calculation sheet
        test_ids = []
        data_rows = []
        for t in extracted.get('test_criteria', []):
            tid = t.get('test_id') or f"test_{len(test_ids)+1}"
            test_ids.append(tid)
            # produce a placeholder row per batch
            for b in normalized_batches:
                data_rows.append({'test_id': tid, 'batch_number': b.get('batch_number'), 'test_result': t.get('acceptance_criteria', '')})
        out['test_ids'] = test_ids
        out['data'] = data_rows
        # materials/equipment tables in view-friendly format: list of lists (header row + rows)
        mats = extracted.get('materials', [])
        if mats:
            headers = list(mats[0].keys())
            rows = [[m.get(h, '') for h in headers] for m in mats]
            out['materials_tables'] = [ [headers] + rows ]
        else:
            out['materials_tables'] = []
        eqs = extracted.get('equipment', [])
        if eqs:
            headers = list(eqs[0].keys())
            rows = [[e.get(h, '') for h in headers] for e in eqs]
            out['equipment_tables'] = [ [headers] + rows ]
        else:
            out['equipment_tables'] = []
        out['calculations'] = extracted.get('calculation_sheet', [])
        out['calculated'] = {}  # place for summary stats if you compute later
        out['extracted'] = extracted
        # for compatibility with existing view_pvr.html fields
        out['generated_filepath'] = ''
        return out

    def generate_docx_from_extracted(self, extracted: Dict, out_path: str) -> Optional[str]:
        """Simple docx generator - requires python-docx"""
        if Document is None:
            logger.warning("python-docx not installed, skipping DOCX generation")
            return None
        doc = Document()
        meta = extracted.get('product_info', {})
        title = meta.get('product_name') or "Process Validation Report"
        doc.add_heading(title, level=1)
        doc.add_paragraph(f"Protocol / Product info: {json.dumps(meta, ensure_ascii=False)}")
        # Batches table
        batches = extracted.get('batch_details', [])
        doc.add_heading("Batch Details", level=2)
        if batches:
            keys = list(batches[0].keys())
            table = doc.add_table(rows=1, cols=len(keys))
            for i, k in enumerate(keys):
                table.rows[0].cells[i].text = str(k)
            for b in batches:
                r = table.add_row().cells
                for i, k in enumerate(keys):
                    r[i].text = str(b.get(k, ''))
        else:
            doc.add_paragraph("No batch details parsed.")
        # Materials
        doc.add_heading("Materials / Reagents", level=2)
        mats = extracted.get('materials', [])
        if mats:
            for m in mats:
                doc.add_paragraph(f"{m.get('material_type','')}: {m.get('material_name','')} - {m.get('quantity','')}")
        else:
            doc.add_paragraph("No materials parsed.")
        # Equipment
        doc.add_heading("Equipment", level=2)
        eqs = extracted.get('equipment', [])
        if eqs:
            for e in eqs:
                doc.add_paragraph(f"{e.get('equipment_name','')} (ID: {e.get('equipment_id','')})")
        else:
            doc.add_paragraph("No equipment parsed.")
        # Calculations & criteria
        doc.add_heading("Test Criteria", level=2)
        for t in extracted.get('test_criteria', []):
            doc.add_paragraph(f"{t.get('test_name','')}: {t.get('acceptance_criteria','')}")
        # Observations and signatures
        doc.add_heading("Observations", level=2)
        doc.add_paragraph(extracted.get('observations','') or "-")
        doc.add_heading("Signatures", level=2)
        doc.add_paragraph(json.dumps(extracted.get('signatures', {}), ensure_ascii=False))
        # Save
        try:
            doc.save(out_path)
            logger.info("DOCX saved to %s", out_path)
            return out_path
        except Exception as e:
            logger.error("Failed to write DOCX: %s", e)
            return None


    # -----------------------
    # Helper: empty structure
    # -----------------------
    def _empty_result(self) -> Dict:
        return {
            'product_info': {},
            'product_type': 'Injectable',
            'equipment': [],
            'materials': [],
            'stages': [],
            'test_criteria': [],
            'batch_details': []
        }


# ------------ Top-level convenience function ------------
def extract_from_pvp(pdf_path: str, output_dir: Optional[str] = None) -> Dict:
    """
    Convenience wrapper to run extraction and optionally create a DOCX.
    Returns a dict: {'extracted': {...}, 'docx_path': ..., 'template_payload': {...}}
    """
    extractor = EnhancedPVPExtractor(pdf_path)
    extracted = extractor.extract_all()
    template_payload = extractor.normalize_for_template(extracted)
    docx_path = None
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_docx = os.path.join(output_dir, f"generated_pvr_{timestamp}.docx")
        docx_path = extractor.generate_docx_from_extracted(extracted, out_docx)
        # update template payload with generated file path
        template_payload['generated_filepath'] = docx_path or ''
    return {'extracted': extracted, 'docx_path': docx_path, 'template_payload': template_payload}


# -----------------------
# Example run (edit path as needed)
# -----------------------
if __name__ == "__main__":
    # Example PVP already uploaded in your environment
    sample_pdf = "/mnt/data/b1e84de0-8225-4168-b62f-74fc2862c880.pdf"
    outdir = "/mnt/data/pvr_generated_output"
    print("Running extractor on:", sample_pdf)
    res = extract_from_pvp(sample_pdf, output_dir=outdir)
    print("Extraction keys:", list(res['extracted'].keys()))
    print("DOCX:", res['docx_path'])
    # Save template JSON for UI preview
    preview_path = os.path.join(outdir, "template_payload.json")
    with open(preview_path, "w", encoding="utf-8") as fh:
        json.dump(res['template_payload'], fh, indent=2)
    print("Preview JSON written to:", preview_path)
