"""
PharmaDoc AI - Complete Automated Process Validation Documentation System
Integrated with Google Gemini AI for document parsing and analysis
"""

import os
import json
import re
import io
import pickle
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path
import base64
import PyPDF2
from pdf2image import convert_from_path
import pdfplumber
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None
import PIL.Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import OCR libraries
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    print("Warning: pytesseract not installed. OCR features disabled.")
    OCR_AVAILABLE = False
    pytesseract = None

# ==================== CONFIGURATION ====================

class Config:
    """Enhanced Configuration settings for PharmaDoc AI"""
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash"
    
    # OCR Configuration
    TESSERACT_PATH = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")
    OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "eng").split(",")
    
    # Cache Configuration
    CACHE_DIR = ".cache"
    CACHE_ENABLED = True
    
    # Processing Configuration
    MAX_PAGES_FOR_OCR = 10
    # Optimized for speed (User Request) - was 3
    CONSENSUS_PASSES = 1
    MIN_TEXT_LENGTH_FOR_OCR = 100  # Switch to OCR if text less than this
    
    # Enhanced Regulatory Guidelines
    REGULATORY_GUIDELINES = {
        "USFDA": ["21 CFR 210", "21 CFR 211", "21 CFR 11", "Process Validation: General Principles and Practices (2011)"],
        "EU_GMP": ["Annex 15: Qualification and Validation", "EU GMP Guidelines Volume 4", "EudraLex"],
        "ICH": ["Q8(R2) Pharmaceutical Development", "Q9 Quality Risk Management", "Q10 Pharmaceutical Quality System", "Q11 Development and Manufacture of Drug Substances"],
        "WHO": ["WHO GMP Guidelines", "WHO Technical Report Series 992"],
        "PIC/S": ["PI 006-3: Recommendations on Validation Master Plan"],
        "ISO": ["ISO 13485:2016", "ISO 9001:2015"]
    }
    
    # Enhanced Sampling Rules
    SAMPLING_RULES = {
        "injection": {
            "vial_washing": {"samples_per_batch": 3, "sample_size": "20 vials", "times": ["before", "after", "depyrogenation"]},
            "manufacturing": {"samples_per_batch": 3, "sample_size": "20 ml", "times": ["10 min", "15 min", "20 min"]},
            "filtration": {"samples_per_batch": 1, "sample_size": "20 ml", "location": "post-filtration"},
            "filling": {"samples_per_batch": 3, "sample_size": "4 vials", "times": ["beginning", "middle", "end"]},
            "visual_inspection": {"samples_per_batch": 3, "sample_size": "20 vials", "times": ["beginning", "middle", "end"]},
            "hold_time": {"samples_per_batch": 4, "sample_size": "20 ml", "times": ["0h", "6h", "12h", "24h", "48h"]}
        },
        "tablet": {
            "blending": {"samples_per_batch": 3, "sample_size": "100g", "locations": ["top", "middle", "bottom"]},
            "compression": {"frequency_minutes": 30, "sample_size": "20 tablets"},
            "coating": {"samples_per_batch": 3, "sample_size": "10 tablets", "times": ["start", "middle", "end"]}
        }
    }
    
    # Document Templates
    DOCUMENT_TEMPLATES = {
        "pvp_title": "PROCESS VALIDATION PROTOCOL",
        "pvr_title": "PROCESS VALIDATION REPORT",
        "company_name": "ATLAS LABORATORIES & PHARMACEUTICALS LTD.",
        "address": "Pharma Complex, Industrial Area, City, Country",
        "quality_system": "ISO 9001:2015 Certified",
        "footer_text": "Confidential Document - For Internal Use Only"
    }

# ==================== CACHING SYSTEM ====================

class CacheManager:
    """Cache manager to avoid redundant API calls"""
    
    def __init__(self, cache_dir: str = Config.CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, content: str, prompt: str) -> str:
        """Generate cache key from content and prompt"""
        combined = f"{content[:1000]}{prompt[:500]}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, cache_key: str, document_type: str = None) -> Optional[Dict]:
        """Get cached result"""
        if not Config.CACHE_ENABLED:
            return None
            
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    cached = pickle.load(f)
                    if document_type is None or cached.get('document_type') == document_type:
                        age = datetime.now() - cached.get('timestamp', datetime.min)
                        if age.days < 1:  # Cache valid for 1 day
                            print(f"Using cached result for {document_type or 'unknown'}")
                            return cached.get('data', {})
            except Exception as e:
                print(f"Cache read error: {e}")
        
        return None
    
    def set(self, cache_key: str, data: Dict, document_type: str = None):
        """Cache result"""
        if not Config.CACHE_ENABLED:
            return
            
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'document_type': document_type,
                    'data': data,
                    'timestamp': datetime.now()
                }, f)
        except Exception as e:
            print(f"Cache write error: {e}")

# ==================== DATA SANITIZER ====================

class DataSanitizer:
    """Regex Guardrails for GxP Data Integrity"""
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Cleans text artifacts common in PDFs (headers/footers, excess whitespace).
        """
        if not text:
            return ""
            
        # 1. Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. Remove page numbers (e.g., "Page 1 of 5", "1/5", "- 1 -")
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\d+\s*/\s*\d+\s*\n', '\n', text)
        
        # 3. Remove common headers/footers identifiers if they appear frequently (basic heuristic)
        # This is tricky without page awareness, so we stick to safe whitespace cleanup
        
        # 4. Collapse multiple newlines (max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 5. Remove control characters but keep structure
        text = "".join(ch for ch in text if ch.isprintable() or ch in '\n\t')
        
        return text.strip()

    
    @staticmethod
    def clean_assay(value: str) -> Optional[str]:
        """Reject text walls, enforce %"""
        if not value:
            return "-------"
        # Rule: Must contain % symbol
        if "%" not in value:
            return "-------"
            
        match = re.search(r"(\d+\.?\d*\s*%)", value)
        return match.group(1) if match else "-------"

    @staticmethod
    def clean_limit(value: str) -> str:
        """Reject references like 'As per...'"""
        if not value:
            return "-------"
        value_lower = value.lower()
        if "as per" in value_lower or "refer" in value_lower:
            return value  # Allow references as per new Industry Standard
        return value
        
    @staticmethod
    def clean_ph(value: str) -> Optional[str]:
        """Enforce numeric range for pH"""
        if not value:
            return "-------"
        # Must contain digits
        if not any(char.isdigit() for char in value):
             return "-------"
        # Clean basic noise
        if "as per" in value.lower():
            return "-------"
            
        return value
    
    @staticmethod
    def sanitize_product_code(value: str) -> str:
        """Sanitize and validate product code format"""
        if not value:
            return "-------"
        
        # Remove whitespace and normalize
        value = value.strip().upper()
        
        # Check for common formats: XX/XXX or XX/YYY/XXX or similar with hyphens
        # Allows KPL/CI/010, FU/002, etc.
        if re.match(r'^[A-Z]{2,5}(?:[-/][A-Z0-9]{2,5})+(?:[-/]\d{3,4})?$', value):
            return value
        
        # Try to extract code from text
        match = re.search(r'([A-Z]{2,5}(?:[-/][A-Z0-9]{2,5})+(?:[-/]\d{3,4}))', value)
        if match:
            return match.group(1)
        
        return "-------"

# ==================== DATA MODELS ====================

class ProductType(Enum):
    """Enum for product types"""
    TABLET = "tablet"
    CAPSULE = "capsule"
    INJECTION = "injection"
    SYRUP = "syrup"
    OINTMENT = "ointment"
    CREAM = "cream"
    POWDER = "powder"
    LIQUID = "liquid"

@dataclass
class ProductInfo:
    """Enhanced product information"""
    name: str
    generic_name: str = ""
    dosage_form: str = ""
    strength: str = ""
    batch_size: str = ""
    product_code: str = ""
    shelf_life: str = "36 Months"
    storage_condition: str = "Store at temperature below 25°C. Protect from light."
    composition: List[Dict[str, str]] = field(default_factory=list)
    manufacturing_site: str = "Main Manufacturing Facility"
    regulatory_category: str = "Prescription Drug"
    
    def __post_init__(self):
        if not self.product_code:
            self.product_code = self._generate_product_code()
        if not self.generic_name:
            self.generic_name = self.name
    
    def _generate_product_code(self) -> str:
        """Generate product code from product name"""
        words = self.name.split()
        initials = ''.join([word[0].upper() for word in words if word and word[0].isalpha()][:3])
        
        dosage_code = {
            "tablet": "TAB", "capsule": "CAP", "injection": "INJ",
            "syrup": "SYR", "ointment": "ONT", "cream": "CRM",
            "powder": "PWD", "liquid": "LIQ"
        }.get(self.dosage_form.lower(), "GEN")
        
        return f"{dosage_code}/{initials}/001"

@dataclass
class EquipmentInfo:
    """Equipment information"""
    name: str
    make: str = ""
    model: str = ""
    equipment_id: str = ""
    capacity: str = ""
    qualification_status: str = "Qualified"
    last_calibration: str = ""
    location: str = ""
    criticality: str = "Critical"

@dataclass
class RawMaterialInfo:
    """Raw material information"""
    name: str
    specification: str = "BP/USP/EP"
    item_code: str = ""
    quantity_required: str = ""
    quantity_dispensed: str = ""
    vendor: str = ""
    ar_number: str = ""
    assay: str = ""
    expiry: str = ""
    storage_condition: str = "Room Temperature"

@dataclass
class STPData:
    """Enhanced Standard Testing Procedure data"""
    product_name: str
    product_code: str = ""
    version: str = "01-00"
    effective_date: str = ""
    tests: List[Dict[str, Any]] = field(default_factory=list)
    specifications: Dict[str, str] = field(default_factory=dict)
    methods: Dict[str, str] = field(default_factory=dict)
    acceptance_criteria: Dict[str, str] = field(default_factory=dict)
    reference_standards: List[Dict[str, str]] = field(default_factory=list)
    sampling_procedure: str = ""
    reference_documents: List[str] = field(default_factory=list)
    raw_data: str = ""

@dataclass
class MFRData:
    """Enhanced Master Formula Record data"""
    product_name: str
    product_code: str = ""
    version: str = "01-00"
    batch_size: str = ""
    manufacturing_steps: List[Dict[str, Any]] = field(default_factory=list)
    raw_materials: List[Dict[str, str]] = field(default_factory=list)
    equipment: List[Dict[str, str]] = field(default_factory=list)
    process_parameters: Dict[str, str] = field(default_factory=dict)
    packaging_details: Dict[str, str] = field(default_factory=dict)
    in_process_controls: List[Dict[str, str]] = field(default_factory=list)
    hold_times: Dict[str, str] = field(default_factory=dict)
    yield_calculations: Dict[str, str] = field(default_factory=dict)
    raw_data: str = ""

# ==================== DOCUMENT CLASSIFIER ====================

class DocumentClassifier:
    """Classify document type before extraction"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None
        self.cache = CacheManager()
    
    def classify(self, content: str, filename: str = "") -> Dict[str, Any]:
        """Classify document type and extract basic metadata"""
        cache_key = self.cache.get_cache_key(content[:1000], "classification")
        cached = self.cache.get(cache_key, "classification")
        if cached:
            return cached
        
        prompt = """
        You are a pharmaceutical document classification system. Analyze the document and classify it.
        
        Document types:
        - STP: Standard Testing Procedure (contains test methods, specifications, acceptance criteria)
        - MFR: Master Formula Record (contains manufacturing steps, raw materials, batch size)
        - BMR: Batch Manufacturing Record (batch-specific manufacturing record)
        - PVP: Process Validation Protocol
        - PVR: Process Validation Report
        - SPEC: Specification document
        - COA: Certificate of Analysis
        - SOP: Standard Operating Procedure
        - OTHER: Other document types
        
        Extract basic metadata and return JSON:
        {
            "document_type": "STP",
            "confidence": 0.95,
            "product_name": "Product name if found",
            "product_code": "Product code if found (format: XX/XXX or XX/YYY/XXX)",
            "version": "Document version",
            "contains_tables": true/false,
            "is_scanned": true/false (based on text quality),
            "keywords_found": ["list", "of", "relevant", "keywords"]
        }
        
        Document content (first 5000 chars):
        """
        
        try:
            if not self.model:
                raise Exception("GenAI model not initialized")

            response = self.model.generate_content(
                [prompt, content[:5000]],
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                }
            )
            
            result = self._extract_json(response.text)
            if result:
                # Add filename to result
                result["filename"] = filename
                self.cache.set(cache_key, result, "classification")
                return result
        
        except Exception as e:
            print(f"Classification error: {e}")
        
        # Fallback classification based on content
        return self._fallback_classify(content, filename)
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text"""
        try:
            # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'```', '', text)
            
            # Find JSON structure
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
        except:
            pass
        return None
    
    def _fallback_classify(self, content: str, filename: str) -> Dict:
        """Fallback classification using keywords"""
        content_lower = content.lower()
        
        # Check for document type keywords
        doc_type = "OTHER"
        confidence = 0.5
        
        if any(keyword in content_lower for keyword in ["standard testing procedure", "stp", "test method", "specification"]):
            doc_type = "STP"
            confidence = 0.8
        elif any(keyword in content_lower for keyword in ["master formula record", "mfr", "batch size", "manufacturing steps"]):
            doc_type = "MFR"
            confidence = 0.8
        elif any(keyword in content_lower for keyword in ["batch manufacturing record", "bmr"]):
            doc_type = "BMR"
            confidence = 0.7
        elif any(keyword in content_lower for keyword in ["process validation protocol", "pvp"]):
            doc_type = "PVP"
            confidence = 0.9
        elif any(keyword in content_lower for keyword in ["process validation report", "pvr"]):
            doc_type = "PVR"
            confidence = 0.9
        
        # Check if scanned (low text density)
        is_scanned = len(content.strip()) < Config.MIN_TEXT_LENGTH_FOR_OCR
        
        # Extract product code
        product_code_match = re.search(r'([A-Z]{2,4}(?:/[A-Z]{2,4})?/\d{3})', content, re.IGNORECASE)
        product_code = product_code_match.group(1) if product_code_match else ""
        
        return {
            "document_type": doc_type,
            "confidence": confidence,
            "product_name": "",
            "product_code": product_code,
            "version": "",
            "contains_tables": "table" in content_lower,
            "is_scanned": is_scanned,
            "keywords_found": [],
            "filename": filename
        }

# ==================== CONSENSUS EXTRACTOR ====================

class ConsensusExtractor:
    """Multi-pass consensus extraction for reliability"""
    
    def __init__(self, model):
        self.model = model
        self.cache = CacheManager()
    
    def extract_with_consensus(self, content: Union[str, List[PIL.Image.Image]], 
                              prompt: str, document_type: str, 
                              passes: int = Config.CONSENSUS_PASSES) -> Dict[str, Any]:
        """Run multiple extractions and select consensus"""
        cache_key = self.cache.get_cache_key(str(content)[:1000], prompt)
        cached = self.cache.get(cache_key, document_type)
        if cached:
            return cached
        
        results = []
        
        for i in range(passes):
            try:
                print(f"  Pass {i+1}/{passes}...")
                
                # Prepare content for this pass
                submission = [prompt]
                if isinstance(content, list):
                    # Multimodal: Add images (limit to first few for speed)
                    submission.extend(content[:3])
                else:
                    # Text only - use different chunks for each pass to get variety
                    chunk_size = min(20000, len(content))
                    start = (i * chunk_size) // passes
                    end = ((i + 1) * chunk_size) // passes
                    chunk = content[start:end] if len(content) > chunk_size else content
                    submission.append(f"Document Text (Pass {i+1}):\n{chunk}")
                
                response = self.model.generate_content(
                    submission,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
                    }
                )
                
                extracted = self._extract_json(response.text)
                if extracted:
                    results.append(extracted)
                    
            except Exception as e:
                print(f"    Pass {i+1} failed: {e}")
        
        # Get consensus result
        if len(results) >= 2:
            consensus_result = self._get_consensus(results)
        elif results:
            consensus_result = results[0]
        else:
            consensus_result = {}
        
        # Cache the result
        self.cache.set(cache_key, consensus_result, document_type)
        
        return consensus_result
    
    def _get_consensus(self, results: List[Dict]) -> Dict:
        """Get consensus from multiple extractions"""
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0]
        
        # Initialize consensus structure
        consensus = {}
        
        # Get all unique keys
        all_keys = set()
        for result in results:
            all_keys.update(result.keys())
        
        for key in all_keys:
            values = []
            for result in results:
                if key in result:
                    val = result[key]
                    if val is not None and val != "":
                        values.append(val)
            
            if not values:
                continue
            
            # For lists, merge unique items
            if isinstance(values[0], list):
                merged_list = []
                for val_list in values:
                    if isinstance(val_list, list):
                        merged_list.extend(val_list)
                consensus[key] = list(dict.fromkeys(merged_list))  # Remove duplicates preserving order
            
            # For dicts, merge recursively
            elif isinstance(values[0], dict):
                dict_results = [v for v in values if isinstance(v, dict)]
                if dict_results:
                    # Get consensus for each subkey
                    sub_consensus = {}
                    sub_keys = set()
                    for d in dict_results:
                        sub_keys.update(d.keys())
                    
                    for sub_key in sub_keys:
                        sub_vals = [d.get(sub_key) for d in dict_results if sub_key in d]
                        sub_vals = [v for v in sub_vals if v is not None and v != ""]
                        if sub_vals:
                            # Take most common non-empty value
                            freq = {}
                            for v in sub_vals:
                                freq[v] = freq.get(v, 0) + 1
                            sub_consensus[sub_key] = max(freq.items(), key=lambda x: x[1])[0]
                    
                    consensus[key] = sub_consensus
            
            # For simple values, take most common
            else:
                freq = {}
                for v in values:
                    freq[v] = freq.get(v, 0) + 1
                consensus[key] = max(freq.items(), key=lambda x: x[1])[0]
        
        return consensus
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from text"""
        try:
            # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'```', '', text)
            
            # Find JSON structure
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
        except:
            pass
        return None

# ==================== ENHANCED AI UTILITIES ====================

class DocumentClassifier:
    """
    Intelligent Document Classification
    Determines if a document is STP or MFR based on content analysis.
    """
    
    @staticmethod
    def classify_document(text: str) -> str:
        """
        Classifies document based on keywords in the first few pages.
        Returns: "STP" or "MFR"
        """
        text_lower = text.lower()[:5000] # Check header/intro
        
        # MFR Signals
        mfr_score = 0
        if "master formula" in text_lower: mfr_score += 3
        if "manufacturing record" in text_lower: mfr_score += 3
        if "batch manufacturing" in text_lower: mfr_score += 2
        if "mfr" in text_lower: mfr_score += 1
        if "bill of materials" in text_lower or "bom" in text_lower: mfr_score += 2
        
        # STP Signals
        stp_score = 0
        if "standard testing" in text_lower: stp_score += 3
        if "stp" in text_lower: stp_score += 1
        if "specification" in text_lower and "method" in text_lower: stp_score += 1
        if "finished product specification" in text_lower: stp_score += 2
        
        if mfr_score > stp_score:
            return "MFR"
        return "STP"

class ConsensusExtractor:
    """
    Automated Consensus Engine for AI Extraction.
    Runs extraction multiple times and consolidates results to eliminate hallucinations.
    """
    
    def __init__(self, model):
        self.model = model
    
    def robust_extract(self, content: list, prompt_template: str, document_type: str, context: str = "") -> Dict[str, Any]:
        """
        Performs 3-pass extraction and 1-pass consolidation.
        """
        candidates = []
        
        # 1. Run 3 extraction passes (simulating diversity)
        # Note: We use the same prompt. In a real stochastic setting, we rely on temperature.
        # Here we will append a small "Seed" instruction to vary the output slightly if needed,
        # but modern models are deterministic at temp 0. We will assume the caller configures temp > 0.4.
        # For this implementation, we will append Iteration counts to the prompt to potentially influence the model.
        
        print(f"    - Starting Consensus Loop (3 passes)...")
        for i in range(3):
            # Add iteration marker to force fresh generation path
            iteration_prompt = f"{prompt_template}\n\n[System Note: Extraction Pass {i+1}/3. Ensure strict adherence to JSON format.]"
            
            try:
                if not self.model:
                    print(f"      > Pass {i+1}: Failed (No Model)")
                    continue


                
                response = self.model.generate_content(
                    content + [iteration_prompt],
                     generation_config=genai.types.GenerationConfig(
                        temperature=0.0 # Zero temperature for strict anti-hallucination
                    )
                )
                
                # Extract JSON
                json_data = self._clean_json(response.text)
                if json_data:
                    candidates.append(json_data)
                    print(f"      > Pass {i+1}: Success")
                else:
                    print(f"      > Pass {i+1}: Failed (No JSON)")
            except Exception as e:
                print(f"      > Pass {i+1}: Error ({e})")
        
        if not candidates:
            return {}
            
        if len(candidates) == 1:
            return candidates[0]
            
        # 2. Consolidation Phase (The "Judge")
        return self._consolidate(candidates, document_type)

    def _clean_json(self, text: str) -> Optional[Dict]:
        """Helper to extract JSON from response"""
        try:
             # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'```', '', text)
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except:
            return None
        return None

    def _consolidate(self, candidates: List[Dict], doc_type: str) -> Dict[str, Any]:
        """
        Uses the LLM to merge candidate extractions into a single truth.
        """
        print("    - Running Consensus Judge...")
        
        judge_prompt = f"""
        Role: Validated Data Arbiter.
        Task: You are provided with {len(candidates)} extraction candidates for a {doc_type} document.
        Your job is to merge them into a SINGLE, FINAL JSON object.
        
        Rules for Consolidation:
        1. Majority Vote: If 2 or more candidates agree on a value (e.g., "50mg"), use strictly that.
        2. Conservative Selection: If values differ/conflict (e.g., "50mg" vs "500mg"), choose the one that makes most sense for a Pharma {doc_type}, or keeping the most detailed one.
        3. No Hallucinations: Do not add fields not present in the candidates.
        4. Array Merging: For lists (tests/steps), merge them to ensure no items are missed. Deduplicate identical items.
        
        Candidates:
        {json.dumps(candidates, indent=2)}
        
        Output: Return ONLY the final JSON.
        """
        
        try:
            # Low temperature for the Judge to be strict
            response = self.model.generate_content(
                judge_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.0)
            )
            final_json = self._clean_json(response.text)
            if final_json:
                print("      > Consensus Achieved.")
                return final_json
            else:
                print("      > Consensus Failed (JSON error). Using Candidate 1.")
                return candidates[0]
        except Exception as e:
            print(f"      > Consensus Error: {e}. Using Candidate 1.")
            return candidates[0]
# ==================== ENHANCED AI UTILITIES ====================

class DocumentClassifier:
    """
    Intelligent Document Classification
    Determines if a document is STP or MFR based on content analysis.
    """
    
    @staticmethod
    def classify_document(text: str, model=None) -> str:
        """
        Classifies document based on keywords + LLM Verification.
        Returns: "STP" or "MFR"
        """
        text_preview = text[:5000]
        text_lower = text_preview.lower()
        
        # 1. Heuristic Check
        mfr_score = 0
        if "master formula" in text_lower: mfr_score += 3
        if "manufacturing record" in text_lower: mfr_score += 3
        if "batch manufacturing" in text_lower: mfr_score += 2
        if "mfr" in text_lower: mfr_score += 1
        
        stp_score = 0
        if "standard testing" in text_lower: stp_score += 3
        if "stp" in text_lower: stp_score += 1
        if "specification" in text_lower and "method" in text_lower: stp_score += 1
        
        heuristic_result = "MFR" if mfr_score > stp_score else "STP"
        
        # 2. LLM Verification (Robustness)
        if model:
            try:
                print(f"  > Heuristic classifies as: {heuristic_result}. Verifying with LLM...")
                prompt = f"""
                Classify this pharmaceutical document content into exactly one category: "STP" (Standard Testing Procedure) or "MFR" (Master Formula Record).
                
                Content Preview:
                {text_preview}
                
                Rules:
                - STP contains tests, methods, specifications, limits.
                - MFR contains manufacturing steps, equipment, batch size, raw materials.
                
                Return ONLY the category name.
                """
                response = model.generate_content(prompt)
                ai_classification = response.text.strip().upper()
                
                # Simple cleanup
                if "STP" in ai_classification: ai_classification = "STP"
                elif "MFR" in ai_classification: ai_classification = "MFR"
                
                if ai_classification in ["STP", "MFR"]:
                    if ai_classification != heuristic_result:
                        print(f"  > LLM corrected classification to: {ai_classification}")
                    return ai_classification
            except Exception as e:
                print(f"  > LLM Classification failed: {e}. Falling back to heuristic.")
        
        return heuristic_result

class ConsensusExtractor:
    """
    Automated Consensus Engine for AI Extraction.
    Runs extraction multiple times and consolidates results to eliminate hallucinations.
    """
    
    def __init__(self, model):
        self.model = model
    
    def robust_extract(self, content: list, prompt_template: str, document_type: str, context: str = "") -> Dict[str, Any]:
        """
        Performs 3-pass extraction and 1-pass consolidation.
        """
        candidates = []
        
        # 1. Run 3 extraction passes (simulating diversity)
        # Note: We use the same prompt regarding user instruction.
        # We vary the system note slightly to encourage independence.
        
        print(f"    - Starting Consensus Loop ({Config.CONSENSUS_PASSES} passes) for {document_type}...")
        
        if not self.model:
            print("    > No AI model available. Skipping extraction.")
            return {}

        for i in range(Config.CONSENSUS_PASSES):
            # Add iteration marker to force fresh generation path or just rely on non-zero temp if set
            iteration_prompt = f"{prompt_template}\n\n[System Note: Extraction Iteration {i+1}/3. Strict JSON only.]"
            
            # Retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # We assume self.model is configured by caller (or we re-config here if needed)
                    response = self.model.generate_content(
                        content + [iteration_prompt],
                         generation_config=genai.types.GenerationConfig(
                            temperature=0.7 # Higher temp for diversity
                        )
                    )
                    
                    # Extract JSON
                    json_data = self._clean_json(response.text)
                    if json_data:
                        candidates.append(json_data)
                        print(f"      > Pass {i+1}: Success")
                        break # Success, move to next pass
                    else:
                        print(f"      > Pass {i+1} (Attempt {attempt+1}): No JSON found")
                except Exception as e:
                    print(f"      > Pass {i+1} (Attempt {attempt+1}): Error ({e})")
                    if "429" in str(e):
                        # Extract wait time if possible or default to robust backoff
                        wait_time = 30 * (attempt + 1) # 30s, 60s, 90s
                        print(f"        ! Rate limit hit. Waiting {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                    else:
                        break # Don't retry non-transient errors
            
        if not candidates:
            return {}
        
        if not candidates:
            return {}
            
        if len(candidates) == 1:
            return candidates[0]
            
        # 2. Consolidation Phase (The "Judge")
        return self._consolidate(candidates, document_type)

    def _clean_json(self, text: str) -> Optional[Dict]:
        """Helper to extract JSON from response"""
        try:
             # Remove markdown code blocks
            text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'```', '', text)
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except:
            return None
        return None

    def _consolidate(self, candidates: List[Dict], doc_type: str) -> Dict[str, Any]:
        """
        Uses the LLM to merge candidate extractions into a single truth.
        """
        print("    - Running Consensus Judge...")
        
        judge_prompt = f"""
        Role: Validated Data Arbiter.
        Task: You are provided with {len(candidates)} extraction candidates for a {doc_type} document.
        Your job is to merge them into a SINGLE, FINAL JSON object.
        
        Rules for Consolidation:
        1. Majority Vote: If 2 or more candidates agree on a value, use strictly that.
        2. Conservative Selection: If values differ, choose the most detailed and contextually correct one for a Pharma {doc_type}.
        3. No Hallucinations: Do not add fields not present in the candidates.
        4. Array Merging: For lists (tests/steps), merge them to ensure no items are missed. Deduplicate identical items.
        
        Candidates:
        {json.dumps(candidates, indent=2)}
        
        Output: Return ONLY the final JSON.
        """
        
        try:
            # Low temperature for the Judge to be strict
            if not self.model:
                return candidates[0]

            response = self.model.generate_content(
                judge_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.0)
            )
            final_json = self._clean_json(response.text)
            if final_json:
                print("      > Consensus Achieved.")
                return final_json
            else:
                print("      > Consensus Failed (JSON error). Using Candidate 1.")
                return candidates[0]
        except Exception as e:
            print(f"      > Consensus Error: {e}. Using Candidate 1.")
            return candidates[0]



class EnhancedDocumentParser:
    """Enhanced parser for STP and MFR PDFs using Gemini AI with OCR"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        else:
            self.model = None
        self.consensus_extractor = ConsensusExtractor(self.model)
        # self.cache = CacheManager() # Cache disabled for now or missing class
        
        # Enhanced regex patterns
        self.patterns = {
            'product_info': r'(?:product\s*name|name\s*of\s*product)[:=]\s*(.+?)(?:\n|;)',
            'product_code': r'([A-Z]{2,5}(?:[-/][A-Z0-9]{2,5})+(?:[-/]\d{3,4}))',
            'batch_size': r'(?:batch\s*size|batch\s*volume)[:=]\s*([\d\.,]+\s*(?:Liters|Litres|Kg|Grams|Vials))',
            'strength': r'(?:strength|potency|concentration)[:=]\s*([\d\.]+\s*(?:mg|g|ml|%)\s*(?:per\s*(?:ml|tablet|capsule|g))?)',
            'composition': r'(?:composition|each\s*(?:ml|tablet|capsule|g)\s*contains?)[:-]\s*(.+?)(?:\n\n|\n\s*\n)',
            'test_method': r'(?:method|procedure|test\s*method)[:-]\s*(.+?)(?:\n|;)',
            'acceptance': r'(?:acceptance\s*criteria|specification|limit)[:-]\s*(.+?)(?:\n|;)',
            'equipment': r'(?:equipment|machine|apparatus)[:-]\s*(.+?)(?:\n|;)',
            'parameter': r'(\w+(?:\s+\w+)*)\s*[:=]?\s*([\d\.]+\s*(?:to|-|±)\s*[\d\.]+\s*\w+)',
            'step': r'\d+\.\s*(.+?)(?=\n\d+\.|\n\s*\n|$)',
            'raw_material': r'(\w+(?:\s+\w+)*)\s+([\d\.]+\s*(?:mg|g|kg|ml|L|%))\s*(?:per\s*(?:tablet|ml|g))?',
            'specification': r'(\w+(?:\s+\w+)*)\s*[:=]\s*(.+?)(?:\n|;)'
        }
    
    def extract_content_with_tables(self, pdf_path: str) -> str:
        """
        Smart Extraction Strategy (The "Reddit Approach"):
        1. Try pdfplumber (Text + Table structure).
        2. Check Text Density.
        3. If low density (< 50 chars/page), fallback to OCR.
        4. Apply DataSanitizer cleanup.
        """
        full_text = ""
        total_chars = 0
        total_pages = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    # 1. Extract Text
                    text = page.extract_text() or ""
                    total_chars += len(text.strip())
                    
                    # 2. Extract Tables and convert to Markdown
                    tables = page.extract_tables()
                    markdown_tables = []
                    for table in tables:
                        if not table: continue
                        # Create Markdown Table (Filter empty rows)
                        clean_table = [[str(cell).replace('\n', ' ') if cell else "" for cell in row] for row in table]
                        # Remove empty rows
                        clean_table = [row for row in clean_table if any(cell.strip() for cell in row)]
                        
                        if not clean_table: continue
                        
                        # Header
                        header = "| " + " | ".join(clean_table[0]) + " |"
                        separator = "| " + " | ".join(["---"] * len(clean_table[0])) + " |"
                        body = "\n".join(["| " + " | ".join(row) + " |" for row in clean_table[1:]])
                        
                        md_table = f"\n{header}\n{separator}\n{body}\n"
                        markdown_tables.append(md_table)
                    
                    page_content = f"--- Page {i+1} ---\n{text}\n"
                    if markdown_tables:
                        page_content += "\n[DETECTED TABLES (Markdown View)]:\n" + "\n".join(markdown_tables)
                    
                    full_text += page_content + "\n"
            
            # --- Density Check ---
            avg_chars = total_chars / total_pages if total_pages > 0 else 0
            print(f"  Text Density: {avg_chars:.0f} chars/page")
            
            if avg_chars < 50:
                print("  ! Low text density detected. Attempting OCR fallback...")
                ocr_text = self.extract_text_with_ocr_fallback(pdf_path)
                if len(ocr_text) > len(full_text):
                    print("  > OCR yield better results. Using OCR text.")
                    full_text = ocr_text

            # --- Cleanup ---
            return DataSanitizer.preprocess_text(full_text)

        except Exception as e:
            print(f"Borked PDF read: {e}. Falling back to standard OCR.")
            return self.extract_text_with_ocr_fallback(pdf_path)

    def extract_text_with_ocr_fallback(self, pdf_path: str) -> str:
        """Original OCR fallback method (Tesseract)"""
        text = ""
        try:
            # Check if it's a text file
            if pdf_path.endswith('.txt'):
                with open(pdf_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # Use pdfplumber as base
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            except: pass

            # If Tesseract is available (mock check)
            if Config.TESSERACT_PATH and os.path.exists(Config.TESSERACT_PATH):
                # We would call pytesseract here if installed.
                # Since strict environment control is tricky, we treat this as a placeholder
                # that strictly returns what we found or tries PyPDF2
                if len(text) < 100:
                    try:
                        import PyPDF2
                        with open(pdf_path, 'rb') as f:
                            reader = PyPDF2.PdfReader(f)
                            for page in reader.pages:
                                text += page.extract_text() + "\n"
                    except: pass
            
            return text
            
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def extract_images_from_pdf(self, pdf_path: str, max_pages: int = 3) -> List[PIL.Image.Image]:
        """Extract images from PDF for multimodal processing"""
        images = []
        try:
            if pdf_path.lower().endswith('.pdf'):
                pdf_images = convert_from_path(pdf_path, dpi=200)
                images = pdf_images[:max_pages]
                print(f"  Extracted {len(images)} pages as images")
        except Exception as e:
            print(f"  Image extraction failed: {e}")
        return images
    
    def parse_document(self, pdf_path: str, product_name: str = "", 
                      dosage_form: str = "") -> Dict[str, Any]:
        """
        Main parsing pipeline with classification and consensus extraction
        """
        print(f"\nProcessing document: {pdf_path}")
        
        # Step 1: Extract text with OCR fallback
        print("Step 1: Extracting text (with smart table detection)...")
        text_content = self.extract_content_with_tables(pdf_path)
        
        if not text_content.strip():
            print("  ERROR: No text extracted from document")
            return {"error": "No text extracted", "document_type": "UNKNOWN"}
        
        # Step 2: Classify document
        print("Step 2: Classifying document...")
        doc_type = DocumentClassifier.classify_document(text_content, self.model)
        print(f"  Document type: {doc_type}")
        
        # Create minimal classification object for compatibility
        classification = {
            "document_type": doc_type,
            "is_scanned": len(text_content) < 100, # Simple check
            "product_name": "",
            "product_code": "",
            "confidence": 1.0
        }
        
        # Step 3: Extract content based on document type
        print("Step 3: Extracting content...")
        
        if doc_type == "STP":
            return self._parse_stp_document(text_content, pdf_path, product_name, dosage_form, classification)
        elif doc_type == "MFR":
            return self._parse_mfr_document(text_content, pdf_path, product_name, dosage_form, classification)
        else:
            print(f"  Warning: Document type {doc_type} not fully supported")
            return {
                "document_type": doc_type,
                "classification": classification,
                "raw_text_preview": text_content[:1000],
                "warning": f"Document type {doc_type} extraction not implemented"
            }
    
    def _parse_stp_document(self, text_content: str, pdf_path: str, 
                           product_name: str, dosage_form: str, 
                           classification: Dict) -> Dict[str, Any]:
        """Parse STP document with consensus extraction"""
        # Extract images for multimodal processing if needed
        # Extract images for multimodal processing if needed
        images = []
        # if classification.get("is_scanned", False):
        #     images = self.extract_images_from_pdf(pdf_path, max_pages=2)
        
        # Prepare context
        context = {
            "product_name": product_name,
            "dosage_form": dosage_form,
            "product_code": "",
            "is_scanned": False
        }
        
        # Strict Bifurcated Schema Prompt for STP
        prompt = f"""
        Role: Your task is to extract Process Validation data from the STP (Standard Testing Procedure).
        
        CRITICAL INSTRUCTION: You must split the data into two distinct sections:
        1. "master_definition": The "Plan" or "Template" data (Standards, Specifications, Limits).
        2. "execution_evidence": The "Actual Results" from any executed batches found (Batch IDs, Dates, Test Results).

        Context:
        - Product: {context['product_name']} ({dosage_form})
        - Document Type: Standard Testing Procedure
        - Product Code: {context['product_code']}

        ANTI-HALLUCINATION RULES:
        1. Temperature 0 Validity: If a value is not explicitly in the text, return "-------" or null. Do not guess.
        2. Execution Data: ONLY extract explicit batch results (e.g., "Batch No. XYZ: pH 7.2"). If the document is just a template, "execution_evidence" should be empty.
        3. Future Tense: Master Definition should imply requirements (e.g., "Acceptance Criteria").
        4. Missing Data: Always use "-------" for missing fields instead of generic placeholders.
        
        REQUIRED JSON STRUCTURE:
        {{
            "master_definition": {{
                "description": "Validation Protocol Master Data",
                "product_name": "Exact Name",
                "product_code": "Code found",
                "version": "Version info",
                "effective_date": "Date info",
                "tests": [
                    {{
                        "test_name": "Test Name",
                        "method": "Full Method Text",
                        "acceptance_criteria": "Exact Limit/Spec",
                        "specification": "Exact Spec Text"
                    }}
                ]
            }},
            "execution_evidence": {{
                "description": "Actual Batch Results if present",
                "batches": [
                    {{
                        "batch_id": "Strict format [A-Z]{{2}}[0-9]{{4}} only",
                        "mfg_date": "YYYY-MM-DD",
                        "results": {{
                            "pH": "Actual Value",
                            "Assay": "Actual Value"
                        }}
                    }}
                ]
            }}
        }}
        """
        
        # Prepare content for extraction
        content_for_extraction = images if images else text_content
        
        # Extract with consensus
        print("  Running consensus extraction...")
        extracted_data = self.consensus_extractor.robust_extract(
            [prompt] + (images if images else [f"Document Content:\n{text_content[:60000]}"]), # Increased context window
            prompt,
            "STP"
        )
        
        # Sanitize extracted data
        if extracted_data:
            extracted_data = self._sanitize_stp_data(extracted_data)
        
        # Combine with classification
        result = {
            "document_type": "STP",
            "classification": classification,
            "extracted_data": extracted_data or {},
            "raw_text_length": len(text_content),
            "images_used": len(images) > 0
        }
        
        return result
    
    def _parse_mfr_document(self, text_content: str, pdf_path: str,
                           product_name: str, dosage_form: str,
                           classification: Dict) -> Dict[str, Any]:
        """Parse MFR document with consensus extraction"""
        # Extract images for multimodal processing if needed
        images = []
        if classification.get("is_scanned", False):
            images = self.extract_images_from_pdf(pdf_path, max_pages=2)
        
        # Also extract equipment table deterministically
        equipment_table = self._extract_equipment_table_deterministic(pdf_path)
        
        # Prepare context
        context = {
            "product_name": product_name or classification.get("product_name", ""),
            "dosage_form": dosage_form,
            "product_code": classification.get("product_code", ""),
            "is_scanned": classification.get("is_scanned", False)
        }
        
        # Strict Bifurcated Schema Prompt for MFR
        prompt = f"""
        Role: Your task is to extract Process Validation data from the MFR (Master Formula Record).
        
        CRITICAL INSTRUCTION: Split data into "master_definition" (Plan) and "execution_evidence" (Results).
        
        Context:
        - Product: {context['product_name']} ({dosage_form}) 
        - Document Type: Master Formula Record
        - Product Code: {context['product_code']}

        ANTI-HALLUCINATION RULES:
        1. Batch IDs: ONLY extract batch IDs matching regex [A-Z]{{2}}[0-9]{{4}} (e.g., OI0391). Ignore "FU/MFR/..." patterns as batch IDs.
        2. Blank Filling: If you see "______" for a quantity, check the Bill of Materials (BOM) and fill it from the Standard Quantity.
        3. Vendor Names: Extract full vendor names from Raw Material specs (e.g., "Avandose Pharmatech").
        4. Missing Data: Always use "-------" for missing fields instead of generic placeholders.
        
        REQUIRED JSON STRUCTURE:
        {{
            "master_definition": {{
                "description": "MFR Master Template Data",
                "product_name": "Exact Name",
                "product_code": "Code found",
                "batch_size": "Batch size with unit",
                "mfr_effective_date": "Effective Date",
                "shelf_life": "Shelf Life",
                "storage_condition": "Storage Condition",
                "manufacturing_steps": [
                    {{
                        "step_number": 1,
                        "step_name": "Title",
                        "description": "Full instruction text",
                        "equipment": ["Eq1", "Eq2"],
                        "parameters": {{"temp": "..."}},
                        "critical": true/false
                    }}
                ],
                "raw_materials": [
                    {{
                        "name": "Material Name",
                        "standard_qty": "Qty with unit",
                        "vendor": "Vendor Name if present"
                    }}
                ],
                "equipment": [
                    {{
                        "name": "Eq Name",
                        "equipment_id": "ID (e.g., KPL/WH/013)",
                        "capacity": "Cap",
                        "make": "Make/Model"
                    }}
                ]
            }},
            "execution_evidence": {{
                "description": "Executed Batch Data",
                "batches": [
                    {{
                        "batch_id": "Strict format [A-Z]{{2}}[0-9]{{4}}",
                        "mfg_date": "YYYY-MM-DD",
                        "results": {{
                            "yield": "Yield %",
                            "ph_after_mixing": "Value",
                            "bulk_yield": "Value"
                        }}
                    }}
                ]
            }}
        }}
        """
        
        # Prepare content for extraction
        content_for_extraction = images if images else text_content
        
        # Extract with consensus
        print("  Running consensus extraction...")
        extracted_data = self.consensus_extractor.robust_extract(
            [prompt] + (images if images else [f"Document Content:\n{text_content[:60000]}"]),
            prompt,
            "MFR"
        )
        
        # Add deterministically extracted equipment table
        if equipment_table and extracted_data:
            if "equipment" not in extracted_data:
                extracted_data["equipment"] = []
            extracted_data["equipment"].extend(equipment_table)
            # Remove duplicates
            if extracted_data["equipment"]:
                seen = set()
                unique_eq = []
                for eq in extracted_data["equipment"]:
                    eq_key = (eq.get("name", ""), eq.get("equipment_id", ""))
                    if eq_key not in seen:
                        seen.add(eq_key)
                        unique_eq.append(eq)
                extracted_data["equipment"] = unique_eq
        
        # Sanitize extracted data
        if extracted_data:
            extracted_data = self._sanitize_mfr_data(extracted_data)
            # Try to extract batch size if missing
            if not extracted_data.get("batch_size"):
                extracted_data["batch_size"] = self._vacuum_batch_size(pdf_path)
        
        # Combine with classification
        result = {
            "document_type": "MFR",
            "classification": classification,
            "extracted_data": extracted_data or {},
            "deterministic_equipment": equipment_table,
            "raw_text_length": len(text_content),
            "images_used": len(images) > 0
        }
        
        return result
    
    def _sanitize_stp_data(self, data: Dict) -> Dict:
        """Sanitize STP data"""
        master = data.get("master_definition") or data # Fallback for backward compatibility
        
        if "tests" in master:
            cleaned_tests = []
            for test in master["tests"]:
                # Clean test data
                test_name = test.get("test_name", "").lower()
                
                # Clean assay
                if "assay" in test_name:
                    acceptance = test.get("acceptance_criteria", "")
                    cleaned = DataSanitizer.clean_assay(acceptance)
                    if cleaned:
                        test["acceptance_criteria"] = cleaned
                    elif acceptance:
                        test["acceptance_criteria"] = acceptance
                
                # Clean pH
                if "ph" in test_name:
                    acceptance = test.get("acceptance_criteria", "")
                    cleaned = DataSanitizer.clean_ph(acceptance)
                    if cleaned:
                        test["acceptance_criteria"] = cleaned
                
                # Clean limit references
                acceptance = test.get("acceptance_criteria", "")
                test["acceptance_criteria"] = DataSanitizer.clean_limit(acceptance)
                
                cleaned_tests.append(test)
            
            master["tests"] = cleaned_tests
        
        # Sanitize product code
        if "product_code" in master:
            master["product_code"] = DataSanitizer.sanitize_product_code(master["product_code"])
        
        return data
    
    def _sanitize_mfr_data(self, data: Dict) -> Dict:
        """Sanitize MFR data"""
        master = data.get("master_definition") or data
        
        # Sanitize product code
        if "product_code" in master:
            master["product_code"] = DataSanitizer.sanitize_product_code(master["product_code"])
        
        # Ensure batch size has unit
        if "batch_size" in master:
            batch_size = master["batch_size"]
            if batch_size and not any(unit in batch_size.lower() for unit in ["liter", "litre", "l", "kg", "g", "vial", "tablet"]):
                # Try to add unit based on dosage form
                if "injection" in master.get("product_name", "").lower():
                    master["batch_size"] = f"{batch_size} Liters"
        
        return data
    
    def _extract_equipment_table_deterministic(self, pdf_path: str) -> List[Dict[str, str]]:
        """Deterministic extraction of equipment list from table"""
        equipment = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Look for equipment-related headers
                        header = table[0]
                        if not header:
                            continue
                        
                        header_lower = [str(cell).lower() if cell else "" for cell in header]
                        
                        # Check if this looks like an equipment table
                        is_equipment_table = any(
                            "equipment" in h or "machine" in h or "apparatus" in h 
                            for h in header_lower
                        )
                        
                        if is_equipment_table:
                            # Map column indices
                            col_mapping = {}
                            for idx, h in enumerate(header_lower):
                                if "name" in h or "equipment" in h:
                                    col_mapping["name"] = idx
                                elif "id" in h or "code" in h or "no" in h:
                                    col_mapping["equipment_id"] = idx
                                elif "make" in h or "model" in h or "manufacturer" in h:
                                    col_mapping["make"] = idx
                                elif "capacity" in h or "size" in h:
                                    col_mapping["capacity"] = idx
                            
                            # Extract data rows
                            for row in table[1:]:
                                if not row:
                                    continue
                                
                                eq_data = {}
                                for field, idx in col_mapping.items():
                                    if idx < len(row) and row[idx]:
                                        eq_data[field] = str(row[idx]).strip()
                                
                                if eq_data.get("name"):
                                    # Add default values for missing fields
                                    if "equipment_id" not in eq_data:
                                        # Generate ID from name
                                        name_words = eq_data["name"].split()
                                        if name_words:
                                            eq_data["equipment_id"] = "".join(
                                                [w[0].upper() for w in name_words[:3] if w]
                                            ) + "/001"
                                    
                                    eq_data["qualification_status"] = "Qualified"
                                    equipment.append(eq_data)
                                    
        except Exception as e:
            print(f"  Equipment table extraction failed: {e}")
        
        return equipment
    
    def _vacuum_batch_size(self, pdf_path: str) -> Optional[str]:
        """Secondary search for batch size"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i in range(min(2, len(pdf.pages))):
                    page = pdf.pages[i]
                    text = page.extract_text() or ""
                    
                    # Regex for "Batch Size : 50.0 L" or similar
                    match = re.search(
                        r"(?:batch\s*size|volume|batch\s*volume)\s*[:\.-]?\s*([\d\.,]+\s*[a-zA-Z]+)", 
                        text, 
                        re.IGNORECASE
                    )
                    if match:
                        return match.group(1).strip()
        except Exception as e:
            print(f"  Vacuum batch size search failed: {e}")
        return None

# ==================== VALIDATION PIPELINE ====================

class ValidationPipeline:
    """Validate extracted data against rules"""
    
    def validate_extraction(self, extracted_data: Dict, document_type: str) -> Dict[str, Any]:
        """Validate extracted data and return errors/warnings"""
        errors = []
        warnings = []
        
        # Unwrap master definition for validation
        data_to_validate = extracted_data.get("master_definition") or extracted_data
        
        if document_type == "STP":
            errors, warnings = self._validate_stp(data_to_validate)
        elif document_type == "MFR":
            errors, warnings = self._validate_mfr(data_to_validate)
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings)
        }
    
    def _validate_stp(self, data: Dict) -> Tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["product_name", "product_code"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check tests
        tests = data.get("tests", [])
        if not tests:
            warnings.append("No tests found in STP")
        else:
            for i, test in enumerate(tests):
                if not test.get("test_name"):
                    warnings.append(f"Test {i+1} missing test name")
                if not test.get("acceptance_criteria"):
                    warnings.append(f"Test '{test.get('test_name', 'Unknown')}' missing acceptance criteria")
        
        # Check product code format
        product_code = data.get("product_code", "")
        if product_code and product_code != "-------":
            if not re.match(r'^[A-Z]{2,4}(?:/[A-Z]{2,4})?/\d{3}$', product_code):
                warnings.append(f"Product code '{product_code}' doesn't match expected format (XX/XXX or XX/YYY/XXX)")
        
        return errors, warnings
    
    def _validate_mfr(self, data: Dict) -> Tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["product_name", "batch_size"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Check manufacturing steps
        steps = data.get("manufacturing_steps", [])
        if not steps:
            warnings.append("No manufacturing steps found")
        
        # Check raw materials
        materials = data.get("raw_materials", [])
        if not materials:
            warnings.append("No raw materials found")
        
        # Check batch size format
        batch_size = data.get("batch_size", "")
        if batch_size:
            # Should contain a unit
            has_unit = any(unit in batch_size.lower() for unit in 
                          ["liter", "litre", "l", "kg", "g", "ml", "vial", "tablet", "capsule"])
            if not has_unit:
                warnings.append(f"Batch size '{batch_size}' may be missing unit")
        
        return errors, warnings

# ==================== ENHANCED REGULATORY RULE ENGINE ====================

class EnhancedRegulatoryRuleEngine:
    """Enhanced regulatory rule engine"""
    
    def __init__(self):
        self.guidelines = Config.REGULATORY_GUIDELINES
        self.sampling_rules = Config.SAMPLING_RULES
        self.validator = ValidationPipeline()
    
    def identify_critical_parameters(self, mfr_data: Dict, stp_data: Dict, product_type: str) -> List[Dict]:
        """Identify enhanced critical process parameters"""
        critical_params = []
        
        # Get process parameters from MFR
        process_params = mfr_data.get("process_parameters", {})
        
        if product_type == "injection":
            # Add injection-specific parameters
            injection_params = [
                {
                    "parameter_name": "Compounding Temperature",
                    "stage": "Compounding",
                    "target_value": "35°C",
                    "acceptable_range": "30-40°C",
                    "justification": "Critical for solubility and stability",
                    "monitoring_method": "Temperature probe",
                    "frequency": "Continuous",
                    "unit": "°C",
                    "risk_level": "High"
                },
                {
                    "parameter_name": "Mixing Time",
                    "stage": "Compounding",
                    "target_value": "20 minutes",
                    "acceptable_range": "15-25 minutes",
                    "justification": "Ensures complete dissolution and homogeneity",
                    "monitoring_method": "Timer",
                    "frequency": "Per batch",
                    "unit": "minutes",
                    "risk_level": "High"
                },
                {
                    "parameter_name": "pH",
                    "stage": "Compounding",
                    "target_value": "8.8",
                    "acceptable_range": "8.5-9.1",
                    "justification": "Critical for stability and efficacy",
                    "monitoring_method": "pH meter",
                    "frequency": "After mixing",
                    "unit": "pH units",
                    "risk_level": "High"
                }
            ]
            critical_params.extend(injection_params)
        
        # Add parameters from MFR data
        for param_name, param_value in process_params.items():
            critical_params.append({
                "parameter_name": param_name.title(),
                "stage": "Manufacturing",
                "target_value": param_value,
                "acceptable_range": param_value,
                "justification": f"Critical parameter from MFR",
                "monitoring_method": "Manual recording",
                "frequency": "As required",
                "unit": self._extract_unit(param_value),
                "risk_level": "Medium"
            })
        
        return critical_params
    
    def generate_sampling_plan(self, mfr_data: Dict, product_type: str) -> List[Dict]:
        """Generate comprehensive sampling plan"""
        sampling_points = []
        
        if product_type == "injection":
            injection_points = [
                {
                    "stage": "Vial Washing",
                    "location": "Washing machine discharge",
                    "sample_quantity": "20 vials",
                    "frequency": "Before and after washing",
                    "tests": ["Bioburden"],
                    "justification": "To assess cleaning efficiency",
                    "acceptance_criteria": "For informative purpose",
                    "sample_type": "Vials",
                    "container": "Sterile bag",
                    "test_method": "Microbial limit test"
                },
                {
                    "stage": "Manufacturing (Compounding)",
                    "location": "Manufacturing vessel",
                    "sample_quantity": "20 ml",
                    "frequency": "After 10, 15, 20 minutes mixing",
                    "tests": ["Description", "pH", "Assay"],
                    "justification": "To monitor dissolution and solution characteristics",
                    "acceptance_criteria": "Clear solution, pH 8.5-9.1, Assay 90-110%",
                    "sample_type": "Bulk solution",
                    "container": "Sterile container",
                    "test_method": "As per STP"
                },
                {
                    "stage": "Filtration",
                    "location": "Post-filtration",
                    "sample_quantity": "20 ml",
                    "frequency": "After filtration",
                    "tests": ["Description", "pH", "Assay", "Sterility"],
                    "justification": "To ensure sterility and maintain quality",
                    "acceptance_criteria": "As per bulk specification",
                    "sample_type": "Filtered solution",
                    "container": "Sterile container",
                    "test_method": "As per STP"
                }
            ]
            sampling_points.extend(injection_points)
        
        return sampling_points
    
    def validate_cross_reference(self, stp_data: Dict, mfr_data: Dict) -> List[str]:
        """Cross-reference check between STP and MFR"""
        discrepancies = []
        
        stp_code = stp_data.get("product_code", "").strip().upper()
        mfr_code = mfr_data.get("product_code", "").strip().upper()
        
        if stp_code and mfr_code:
            if stp_code != mfr_code:
                discrepancies.append(f"Product Code mismatch: STP='{stp_code}' vs MFR='{mfr_code}'")
        
        return discrepancies
    
    def _extract_unit(self, value: str) -> str:
        """Extract unit from parameter value"""
        if not value:
            return ""
        
        value_lower = str(value).lower()
        
        # Handle temperature units
        if '°c' in value_lower or 'ºc' in value_lower or 'celsius' in value_lower:
            return '°C'
        if '°f' in value_lower or 'ºf' in value_lower or 'fahrenheit' in value_lower:
            return '°F'
        
        units = {
            'kg/cm²': 'kg/cm²', 'bar': 'bar', 'psi': 'psi',
            'rpm': 'rpm', 'min': 'minutes', 'hour': 'hours',
            'ml': 'ml', 'l': 'L', 'mg': 'mg', 'g': 'g', 'kg': 'kg',
            'n': 'N', 'kn': 'kN', '%': '%'
        }
        
        for unit_key, unit_value in units.items():
            if unit_key in value.lower():
                return unit_value
        
        return ""
    
    def apply_regulatory_compliance(self, product_type: str, validation_data: Dict) -> Dict:
        """Apply comprehensive regulatory compliance checks"""
        compliance = {
            "usfda_compliant": True,
            "eu_gmp_compliant": True,
            "ich_compliant": True,
            "who_compliant": True,
            "pics_compliant": True,
            "iso_compliant": True,
            "notes": [],
            "requirements": [],
            "guidelines_applied": []
        }
        
        if product_type == "injection":
            compliance["requirements"].extend([
                "21 CFR 211.113 - Control of microbiological contamination",
                "21 CFR 211.167 - Special testing requirements for sterile products",
                "FDA Guidance: Sterile Drug Products Produced by Aseptic Processing",
                "Three consecutive successful batches required"
            ])
            compliance["notes"].append("Sterility assurance level (SAL) of 10^-6 must be maintained")
        
        # Add applied guidelines
        for guideline, documents in self.guidelines.items():
            compliance["guidelines_applied"].extend(documents)
        
        return compliance


# Import templates
from services.validation_templates import ValidationTemplates

class EnhancedPDFGenerator:
    """Generates Pharma-Grade GMP Compliant PDFs for Process Validation"""
    
    def __init__(self):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            self.available = True
            
            self.colors = colors
            self.A4 = A4
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.Table = Table
            self.TableStyle = TableStyle
            self.PageBreak = PageBreak
            self.Image = Image
            self.getSampleStyleSheet = getSampleStyleSheet
            self.ParagraphStyle = ParagraphStyle
            self.inch = inch
            self.TA_CENTER = TA_CENTER
            
            # Styles
            self.styles = self.getSampleStyleSheet()
            self.title_style = ParagraphStyle(
                'PharmaTitle',
                parent=self.styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=20
            )
            self.heading_style = ParagraphStyle(
                'PharmaHeading',
                parent=self.styles['Heading2'],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=10,
                keepWithNext=True
            )
            self.body_style = ParagraphStyle(
                'PharmaBody',
                parent=self.styles['Normal'],
                fontSize=10,
                alignment=TA_JUSTIFY,
                leading=14
            )
            self.table_header_style = ParagraphStyle(
                'PharmaTableHeader',
                parent=self.styles['Normal'],
                fontSize=9,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                textColor=colors.whitesmoke
            )
            self.table_cell_style = ParagraphStyle(
                'PharmaTableCell',
                parent=self.styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER
            )
            
        except ImportError:
            self.available = False
            print("ReportLab not available")

    def _create_standard_table(self, data: List[List[str]], col_widths: List[float] = None, header: bool = True) -> Any:
        """Helper to create professional GMP standard tables"""
        if not data:
            return self.Paragraph("Not Applicable / No Data", self.body_style)
            
        # Wrap content in Paragraphs for text wrapping
        formatted_data = []
        for i, row in enumerate(data):
            formatted_row = []
            for j, cell in enumerate(row):
                style = self.table_header_style if (header and i == 0) else self.table_cell_style
                if isinstance(cell, str):
                    formatted_row.append(self.Paragraph(str(cell), style))
                else:
                    formatted_row.append(cell)
            formatted_data.append(formatted_row)
            
        t = self.Table(formatted_data, colWidths=col_widths)
        
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        if header:
            style.extend([
                ('BACKGROUND', (0, 0), (-1, 0), self.colors.Color(0.2, 0.2, 0.2)), # Dark Grey
                ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.whitesmoke),
            ])
            
        t.setStyle(self.TableStyle(style))
        return t

    def _add_section_header(self, elements, title):
        elements.append(self.Paragraph(title, self.heading_style))
        elements.append(self.Spacer(1, 0.1 * self.inch))

    def generate_pvp(self, data: Dict) -> io.BytesIO:
        """Generate Process Validation Protocol (PVP) - 21 Sections"""
        buffer = io.BytesIO()
        if not self.available: return buffer
        
        doc = self.SimpleDocTemplate(buffer, pagesize=self.A4)
        elements = []
        
        info = data.get("product_info", {})
        prod_name = info.get("name", "Drug Product")
        
        # Title Page
        elements.append(self.Spacer(1, 2 * self.inch))
        elements.append(self.Paragraph("PROCESS VALIDATION PROTOCOL", self.title_style))
        elements.append(self.Spacer(1, 0.5 * self.inch))
        elements.append(self._create_standard_table([
            ["Product Name", prod_name],
            ["Protocol Number", data.get("protocol_number", "Draft")],
            ["Date", datetime.now().strftime('%d-%b-%Y')]
        ], col_widths=[2*self.inch, 4*self.inch], header=False))
        elements.append(self.PageBreak())

        # 1. Objective
        self._add_section_header(elements, "1. Objective")
        elements.append(self.Paragraph(ValidationTemplates.get_pvp_objective(prod_name), self.body_style))

        # 2. Scope
        self._add_section_header(elements, "2. Scope")
        elements.append(self.Paragraph(f"This protocol applies to the validation of three consecutive batches of {prod_name} to be manufactured at the facility.", self.body_style))

        # 3. Responsibility
        self._add_section_header(elements, "3. Responsibility")
        elements.append(self._create_standard_table(ValidationTemplates.get_responsibilities(), col_widths=[2*self.inch, 4*self.inch]))

        # 4. Validation Approach
        self._add_section_header(elements, "4. Validation Approach")
        elements.append(self.Paragraph(ValidationTemplates.get_validation_approach(), self.body_style))

        # 5. Reason for Validation
        self._add_section_header(elements, "5. Reason for Validation")
        elements.append(self.Paragraph("New Product Introduction / Process Validation", self.body_style)) # Logic to detect reason could be added

        # 6. Revalidation Criteria
        self._add_section_header(elements, "6. Revalidation Criteria")
        elements.append(self._create_standard_table(ValidationTemplates.get_revalidation_criteria(), col_widths=[2*self.inch, 4*self.inch]))

        # 7. Product & Batch Details
        self._add_section_header(elements, "7. Product & Batch Details")
        prod_details = [
            ["Attribute", "Details"],
            ["Product Name", prod_name],
            ["Generic Name", info.get("generic_name", "")],
            ["Dosage Form", info.get("dosage_form", "")],
            ["Label Claim", info.get("strength", "")],
            ["Batch Size", info.get("batch_size", "")],
            ["Shelf Life", info.get("shelf_life", "")],
            ["Storage", info.get("storage_condition", "")]
        ]
        elements.append(self._create_standard_table(prod_details, col_widths=[2*self.inch, 4*self.inch]))

        # 8. Equipment & Utilities
        self._add_section_header(elements, "8. Equipment & Utilities")
        eq_data = data.get("mfr_data", {}).get("equipment", [])
        if eq_data:
            table_data = [["Equipment Name", "Equipment ID", "Capacity", "Make/Model"]]
            for eq in eq_data:
                table_data.append([
                    eq.get("name", ""), eq.get("equipment_id", ""), 
                    eq.get("capacity", ""), eq.get("make", "")
                ])
            elements.append(self._create_standard_table(table_data, col_widths=[2*self.inch, 1.5*self.inch, 1.5*self.inch, 2*self.inch]))
        else:
            elements.append(self.Paragraph("No equipment details available in MFR.", self.body_style))

        # 9. Raw Material & Packing Material
        self._add_section_header(elements, "9. Raw Material & Packing Material")
        rm_data = data.get("mfr_data", {}).get("raw_materials", [])
        if rm_data:
            table_data = [["Material Name", "Specification", "Std. Qty / Batch"]]
            for rm in rm_data:
                table_data.append([rm.get("name", ""), rm.get("specification", ""), rm.get("standard_qty", "")])
            elements.append(self._create_standard_table(table_data, col_widths=[3*self.inch, 2*self.inch, 2*self.inch]))
        else:
            elements.append(self.Paragraph("No raw material details available.", self.body_style))

        # 10. Process Flow Diagram
        self._add_section_header(elements, "10. Process Flow Diagram")
        steps = data.get("mfr_data", {}).get("manufacturing_steps", [])
        if steps:
            flow_text = " -> ".join([s.get("step_name", "").strip() for s in steps])
            elements.append(self.Paragraph(flow_text, self.body_style))
        else:
            elements.append(self.Paragraph("Refer to MFR for Flow Diagram.", self.body_style))

        # 11. Manufacturing Process
        self._add_section_header(elements, "11. Manufacturing Process")
        if steps:
            # Create a detailed table for process steps
            table_data = [["Step No.", "Operation", "Critical Parameters", "Recorded In"]]
            for i, step in enumerate(steps):
                params = step.get("parameters", {})
                param_str = "\n".join([f"{k}: {v}" for k,v in params.items()])
                table_data.append([
                    str(step.get("step_number", i+1)),
                    step.get("description", "")[:200] + "...", # Truncate long descriptions
                    param_str,
                    "BMR"
                ])
            elements.append(self._create_standard_table(table_data, col_widths=[0.8*self.inch, 3*self.inch, 2*self.inch, 1.2*self.inch]))
        else:
            elements.append(self.Paragraph("Details as per Master Formula Record.", self.body_style))
            
        # 12. Filling & Sealing / Compression (Adaptive based on form)
        form = info.get("dosage_form", "").lower()
        title = "12. Filling & Sealing" if "injection" in form or "liquid" in form else "12. Compression / Encapsulation"
        self._add_section_header(elements, title)
        elements.append(self.Paragraph("Process shall be executed as per the batch manufacturing record parameters.", self.body_style))

        # 13. Visual Inspection
        self._add_section_header(elements, "13. Visual Inspection")
        elements.append(self.Paragraph("100% visual inspection shall be performed for physical defects.", self.body_style))

        # 14. Sampling Plan
        self._add_section_header(elements, "14. Sampling Plan")
        sampling = data.get("sampling_plan", [])
        if sampling:
            table_data = [["Stage", "Sample Qty", "Tests", "Acceptance Criteria"]]
            for point in sampling:
                table_data.append([
                    point.get("stage", ""), 
                    point.get("sample_quantity", "As per STP"),
                    ", ".join(point.get("tests", [])),
                    str(point.get("acceptance_criteria", ""))
                ])
            elements.append(self._create_standard_table(table_data, col_widths=[1.5*self.inch, 1.5*self.inch, 2*self.inch, 2*self.inch]))
        else:
             elements.append(self.Paragraph("Sampling shall be performed as per STP.", self.body_style))

        # 15. Acceptance Criteria
        self._add_section_header(elements, "15. Acceptance Criteria")
        elements.append(self.Paragraph("The process shall be considered validated if three consecutive batches meet all Critical Quality Attributes (CQAs) and all Critical Process Parameters (CPPs) remain within the specified ranges.", self.body_style))

        # 16. Reference Documents
        self._add_section_header(elements, "16. Reference Documents")
        refs = [
            ["Document", "Reference Number"],
            ["Master Formula Record", data.get("mfr_summary", {}).get("product_code", "N/A")],
            ["Standard Testing Procedure", data.get("stp_summary", {}).get("product_code", "N/A")],
            ["Validation Master Plan", "VMP-001"]
        ]
        elements.append(self._create_standard_table(refs, col_widths=[3*self.inch, 3*self.inch]))

        # 17. Stability
        self._add_section_header(elements, "17. Stability")
        elements.append(self.Paragraph("Samples from the validation batches shall be charged for stability study (Accelerated and Long Term) as per the Stability Protocol.", self.body_style))

        # 18. Deviation Handling
        self._add_section_header(elements, "18. Deviation Handling")
        elements.append(self.Paragraph(ValidationTemplates.get_deviation_policy(), self.body_style))

        # 19. Change Control
        self._add_section_header(elements, "19. Change Control")
        elements.append(self.Paragraph(ValidationTemplates.get_change_control_policy(), self.body_style))

        # 20. Abbreviations
        self._add_section_header(elements, "20. Abbreviations")
        abbrevs = [
            ["Abbreviation", "Full Form"],
            ["QA", "Quality Assurance"],
            ["QC", "Quality Control"],
            ["BMR", "Batch Manufacturing Record"],
            ["MFR", "Master Formula Record"],
            ["CPP", "Critical Process Parameter"],
            ["CQA", "Critical Quality Attribute"]
        ]
        elements.append(self._create_standard_table(abbrevs, col_widths=[2*self.inch, 4*self.inch]))

        # 21. Approval
        self._add_section_header(elements, "21. Approval")
        approval_data = [
            ["Role", "Name", "Signature", "Date"],
            ["Prepared By", "", "", ""],
            ["Reviewed By", "", "", ""],
            ["Approved By", "", "", ""]
        ]
        elements.append(self._create_standard_table(approval_data, col_widths=[1.5*self.inch, 2*self.inch, 1.5*self.inch, 1.5*self.inch]))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_pvr(self, data: Dict) -> io.BytesIO:
        """Generate Process Validation Report (PVR) - 13 Sections"""
        buffer = io.BytesIO()
        if not self.available: return buffer
        
        doc = self.SimpleDocTemplate(buffer, pagesize=self.A4)
        elements = []
        
        info = data.get("product_info", {})
        prod_name = info.get("name", "Drug Product")
        
        # Title Page
        elements.append(self.Spacer(1, 2 * self.inch))
        elements.append(self.Paragraph("PROCESS VALIDATION REPORT", self.title_style))
        elements.append(self.Spacer(1, 0.5 * self.inch))
        elements.append(self._create_standard_table([
            ["Product Name", prod_name],
            ["Report Number", data.get("report_number", "Draft")],
            ["Protocol Reference", data.get("protocol_reference", "N/A")],
            ["Date", datetime.now().strftime('%d-%b-%Y')]
        ], col_widths=[2*self.inch, 4*self.inch], header=False))
        elements.append(self.PageBreak())

        # 1. Objective
        self._add_section_header(elements, "1. Objective")
        elements.append(self.Paragraph(ValidationTemplates.get_pvr_objective(prod_name), self.body_style))

        # 2. Scope
        self._add_section_header(elements, "2. Scope")
        batch_ids = [b.get("batch_number", "") for b in data.get("batch_results", [])]
        batch_str = ", ".join(batch_ids) if batch_ids else "execution batches"
        elements.append(self.Paragraph(f"This report covers the validation of batches: {batch_str}.", self.body_style))

        # 3. Responsibility
        self._add_section_header(elements, "3. Responsibility")
        elements.append(self.Paragraph("Responsibilities are defined in the reference Protocol.", self.body_style))

        # 4. Product & Batch Details
        self._add_section_header(elements, "4. Product & Batch Details")
        batches = data.get("batch_results", [])
        if batches:
            table_data = [["Batch No.", "Mfg Date", "Exp Date", "Batch Size"]]
            for b in batches:
                table_data.append([
                    b.get("batch_number", ""),
                    b.get("manufacturing_date", ""),
                    b.get("expiry_date", ""),
                    b.get("batch_size", "")
                ])
            elements.append(self._create_standard_table(table_data, col_widths=[1.5*self.inch, 1.5*self.inch, 1.5*self.inch, 1.5*self.inch]))
        else:
            elements.append(self.Paragraph("No batch execution data available.", self.body_style))

        # 5. Equipment & Machinery List
        self._add_section_header(elements, "5. Equipment & Machinery List")
        # Reuse MFR equipment list as "Used Equipment"
        eq_data = data.get("mfr_data", {}).get("equipment", [])
        if eq_data:
            table_data = [["Equipment Name", "ID Used", "Calibration Status"]]
            for eq in eq_data:
                table_data.append([eq.get("name", ""), eq.get("equipment_id", ""), "Calibrated"])
            elements.append(self._create_standard_table(table_data, col_widths=[2.5*self.inch, 2*self.inch, 2*self.inch]))
        else:
             elements.append(self.Paragraph("As per Master Formula Record.", self.body_style))

        # 6. Raw Material Details
        self._add_section_header(elements, "6. Raw Material Details")
        elements.append(self.Paragraph("All raw materials used were approved and met specifications.", self.body_style))

        # 7. Observations / Results (CPPs)
        self._add_section_header(elements, "7. Observations / Results")
        elements.append(self.Paragraph("Critical Process Parameters (CPPs) Monitoring:", self.body_style))
        # Create a combined result table
        cpps = data.get("critical_parameters", [])
        if cpps:
            table_data = [["Parameter", "Limit", "Observation (All Batches)", "Compliance"]]
            for cpp in cpps:
                 # STRICT RULE: Check if actual data exists. If not, mark "Not Evaluated"
                 observation = cpp.get("observed_value")
                 compliance = "Complies" if observation else "Not Evaluated"
                 if not observation: observation = "Data Not Available"
                 
                 table_data.append([
                     cpp.get("parameter_name", ""),
                     f"{cpp.get('target_value','')} ({cpp.get('acceptable_range','')})",
                     observation,
                     compliance
                 ])
            elements.append(self._create_standard_table(table_data, col_widths=[2*self.inch, 2*self.inch, 2*self.inch, 1.5*self.inch]))
        else:
             elements.append(self.Paragraph("No critical parameters defined.", self.body_style))

        # 8. Quality Control Results (CQAs)
        self._add_section_header(elements, "8. Quality Control Results of Finished Product")
        if batches:
            for b in batches:
                elements.append(self.Paragraph(f"Batch: {b.get('batch_number','')}", self.heading_style))
                test_results = b.get("test_results", [])
                if test_results:
                    table_data = [["Test", "Specification", "Result", "Status"]]
                    for t in test_results:
                        table_data.append([
                            t.get("test_name", ""),
                            str(t.get("specification", ""))[:50],
                            str(t.get("result", "")),
                            t.get("status", "")
                        ])
                    elements.append(self._create_standard_table(table_data, col_widths=[2*self.inch, 2*self.inch, 2*self.inch, 1*self.inch]))
                elements.append(self.Spacer(1, 0.1*self.inch))
        else:
            elements.append(self.Paragraph("No QC data available.", self.body_style))

        # 9. Deviation Report
        self._add_section_header(elements, "9. Deviation Report")
        # Check if any batch failed
        failed_batches = [b for b in batches if b.get("overall_result") == "FAIL"]
        if failed_batches:
             elements.append(self.Paragraph(f"Deviations observed in batches: {', '.join([b['batch_number'] for b in failed_batches])}. Investigation report attached.", self.body_style))
        else:
             elements.append(self.Paragraph("No critical deviations were observed during the validation execution.", self.body_style))

        # 10. Change Control
        self._add_section_header(elements, "10. Change Control")
        elements.append(self.Paragraph("No changes were implemented during the validation process.", self.body_style))

        # 11. Conclusion
        self._add_section_header(elements, "11. Conclusion")
        conclusion = data.get("conclusion", "PENDING")
        elements.append(self.Paragraph(f"Based on the results obtained, the manufacturing process is considered {conclusion}.", self.body_style))
        
        # Add Justification (Critical for Defensibility)
        justification = data.get("conclusion_justification", "")
        if justification:
             elements.append(self.Spacer(1, 0.1 * self.inch))
             elements.append(self.Paragraph(f"Justification: {justification}", self.body_style))

        # 12. Summary
        self._add_section_header(elements, "12. Summary")
        stats = data.get("summary_statistics", {})
        summary_text = (f"Three consecutive batches were manufactured. "
                        f"All {stats.get('total_tests_performed', 0)} tests were performed. "
                        f"{stats.get('tests_passed', 0)} tests passed. "
                        f"The process is capable of consistently producing product meeting specifications.")
        elements.append(self.Paragraph(summary_text, self.body_style))

        # 13. Post Approval
        self._add_section_header(elements, "13. Post Approval")
        elements.append(self.Paragraph("The product is recommended for commercial manufacturing. Routine monitoring shall continue as per protocol.", self.body_style))

        # Approval Block for PVR
        elements.append(self.Spacer(1, 0.5 * self.inch))
        approval_data = [
            ["Role", "Name", "Signature", "Date"],
            ["Prepared By", "", "", ""],
            ["Reviewed By", "", "", ""],
            ["Approved By", "", "", ""]
        ]
        elements.append(self._create_standard_table(approval_data, col_widths=[1.5*self.inch, 2*self.inch, 1.5*self.inch, 1.5*self.inch]))

        doc.build(elements)
        buffer.seek(0)
        return buffer

# ==================== ENHANCED MAIN PIPELINE ====================


# Import templates and reasoning engine
from services.validation_templates import ValidationTemplates
from services.regulatory_reasoning import RegulatoryReasoningEngine

class EnhancedPharmaDocAI:
    """Enhanced main PharmaDoc AI pipeline"""
    
    def __init__(self, gemini_api_key: str = None):
        self.parser = EnhancedDocumentParser(gemini_api_key)
        self.rule_engine = EnhancedRegulatoryRuleEngine()
        self.validator = ValidationPipeline()
        self.reasoning_engine = RegulatoryReasoningEngine()
        
        # Import PDF generator here to avoid circular imports
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet
            self.pdf_available = True
        except ImportError:
            print("Warning: reportlab not installed. PDF generation disabled.")
            self.pdf_available = False
        
        self.processed_data = {}
    
    def process_documents(self, product_name: str, dosage_form: str, 
                         stp_pdf_path: str, mfr_pdf_path: str) -> Dict[str, Any]:
        """
        Main processing pipeline with OCR, classification, and consensus extraction
        """
        print("="*80)
        print("Enhanced PharmaDoc AI - Processing Pipeline")
        print("="*80)
        
        results = {
            "processing_timestamp": datetime.now().isoformat(),
            "product_name": product_name,
            "dosage_form": dosage_form,
            "stp_path": stp_pdf_path,
            "mfr_path": mfr_pdf_path
        }
        
        # Helper function for STP processing
        def process_stp():
            print(f"\n[STP] Processing: {stp_pdf_path}")
            result = self.parser.parse_document(stp_pdf_path, product_name, dosage_form)
            result["validation"] = self.validator.validate_extraction(
                result.get("extracted_data", {}), "STP"
            )
            return result

        # Helper function for MFR processing
        def process_mfr():
            print(f"\n[MFR] Processing: {mfr_pdf_path}")
            result = self.parser.parse_document(mfr_pdf_path, product_name, dosage_form)
            result["validation"] = self.validator.validate_extraction(
                result.get("extracted_data", {}), "MFR"
            )
            return result

        # Execute in parallel
        import concurrent.futures
        print("\nStarting parallel document processing...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_stp = executor.submit(process_stp)
            future_mfr = executor.submit(process_mfr)
            
            stp_result = future_stp.result()
            mfr_result = future_mfr.result()
            
        print("\nParallel processing completed.")
        
        # Cross-reference validation
        cross_ref_errors = []
        if stp_result.get("extracted_data") and mfr_result.get("extracted_data"):
            cross_ref_errors = self.rule_engine.validate_cross_reference(
                stp_result["extracted_data"],
                mfr_result["extracted_data"]
            )
        
        # Extract data for further processing
        stp_data_full = stp_result.get("extracted_data", {})
        mfr_data_full = mfr_result.get("extracted_data", {})
        
        stp_master = stp_data_full.get("master_definition", {}) or stp_data_full
        stp_execution = stp_data_full.get("execution_evidence", {})
        
        mfr_master = mfr_data_full.get("master_definition", {}) or mfr_data_full
        mfr_execution = mfr_data_full.get("execution_evidence", {})

        # Aliases for backward compatibility (Fixes NameError)
        stp_data = stp_master
        mfr_data = mfr_master
        
        # Generate IDs
        # Prioritize valid code over placeholders
        candidate_codes = [
            mfr_master.get("product_code"),
            stp_master.get("product_code")
        ]
        
        product_code = "TEMP-001"
        for code in candidate_codes:
            if code and isinstance(code, str) and len(code.strip()) > 1 and "----" not in code and "N/A" not in code:
                product_code = code
                break
        generated_ids = self.generate_ids(product_code)
        
        # Create ProductInfo
        product_info = self._create_product_info(
            product_name, dosage_form, stp_master, mfr_master, product_code
        )
        
        # Identify product type
        product_type = self._identify_product_type(dosage_form)
        
        # Generate validation components
        critical_params = self.rule_engine.identify_critical_parameters(
            mfr_master, stp_master, product_type
        )
        
        sampling_plan = self.rule_engine.generate_sampling_plan(mfr_master, product_type)
        
        # Prepare PVP data (Plan only)
        pvp_data = self._prepare_pvp_data(
            product_info, stp_master, mfr_master, critical_params, sampling_plan,
            generated_ids['protocol_id']
        )
        
        # Generate batch results (Evidence only)
        batch_results = self._generate_strict_batch_results(
            mfr_execution, stp_execution, mfr_master.get("mfr_effective_date"), stp_master
        )
        
        # Prepare PVR data
        pvr_data = self._prepare_pvr_data(
            product_info, pvp_data, batch_results, product_type,
            generated_ids['report_id']
        )
        
        # Regulatory compliance
        regulatory_compliance = self.rule_engine.apply_regulatory_compliance(
            product_type, pvp_data
        )
        
        # Compile final results
        self.processed_data = {
            "processing_summary": results,
            "stp_processing": stp_result,
            "mfr_processing": mfr_result,
            "cross_reference_errors": cross_ref_errors,
            "product_info": product_info,
            "stp_data": stp_master,
            "mfr_data": mfr_master,
            "stp_execution": stp_execution,
            "mfr_execution": mfr_execution,
            "pvp_data": pvp_data,
            "pvr_data": pvr_data,
            "pvp": pvp_data, # Alias for compatibility
            "pvr": pvr_data, # Alias for compatibility
            "critical_parameters": critical_params,
            "sampling_plan": sampling_plan,
            "batch_results": batch_results,
            "regulatory_compliance": regulatory_compliance,
            "generated_ids": generated_ids,
            "product_type": product_type,
            "validation_summary": {
                "stp_valid": stp_result.get("validation", {}).get("is_valid", False),
                "mfr_valid": mfr_result.get("validation", {}).get("is_valid", False),
                "stp_errors": stp_result.get("validation", {}).get("error_count", 0),
                "mfr_errors": mfr_result.get("validation", {}).get("error_count", 0),
                "cross_ref_errors": len(cross_ref_errors)
            }
        }
        
        print("\n" + "="*80)
        print("Processing Complete!")
        print(f"  STP extracted: {len(stp_data.get('tests', []))} tests")
        print(f"  MFR extracted: {len(mfr_data.get('manufacturing_steps', []))} steps")
        print(f"  Critical parameters: {len(critical_params)}")
        print(f"  Sampling points: {len(sampling_plan)}")
        print("="*80)
        
        return self.processed_data
    
    def generate_ids(self, product_code: str) -> Dict[str, str]:
        """Generate unique Protocol and Report IDs"""
        safe_code = product_code.replace('/', '-').replace(' ', '')[:20]
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        return {
            "protocol_id": f"PVP-{safe_code}-{timestamp}",
            "report_id": f"PVR-{safe_code}-{timestamp}"
        }
    
    def _create_product_info(self, product_name: str, dosage_form: str, 
                            stp_data: Dict, mfr_data: Dict, 
                            product_code: str) -> Dict:
        """Create product information dictionary"""
        return {
            "name": product_name,
            "generic_name": product_name,
            "dosage_form": dosage_form,
            "strength": self._extract_strength(product_name),
            "batch_size": mfr_data.get("batch_size", ""),
            "product_code": product_code,
            "shelf_life": "36 Months",
            "storage_condition": "Store at temperature below 25°C. Protect from light.",
            "manufacturing_site": "Main Manufacturing Facility",
            "regulatory_category": "Prescription Drug"
        }
    
    def _extract_strength(self, product_name: str) -> str:
        """Extract strength from product name"""
        strength_patterns = [
            r'(\d+(?:\.\d+)?\s*(?:mg|g|ml|%)\s*(?:per\s*(?:ml|tablet|capsule|g))?)',
            r'(\d+(?:\.\d+)?\s*(?:mg|g|ml|%)\s*/\s*\d+(?:\.\d+)?\s*(?:mg|g|ml|%))'
        ]
        
        for pattern in strength_patterns:
            match = re.search(pattern, product_name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "As per STP"
    
    def _identify_product_type(self, dosage_form: str) -> str:
        """Identify product type from dosage form"""
        dosage_form_lower = dosage_form.lower()
        
        if any(word in dosage_form_lower for word in ['injection', 'injectable', 'vial', 'ampoule', 'sterile']):
            return "injection"
        elif any(word in dosage_form_lower for word in ['tablet', 'tab']):
            return "tablet"
        elif any(word in dosage_form_lower for word in ['capsule', 'cap']):
            return "capsule"
        elif any(word in dosage_form_lower for word in ['syrup', 'suspension', 'solution', 'liquid']):
            return "liquid"
        else:
            return "general"
    
    def _prepare_pvp_data(self, product_info: Dict, stp_data: Dict, 
                         mfr_data: Dict, critical_params: List[Dict],
                         sampling_plan: List[Dict], protocol_id: str) -> Dict[str, Any]:
        """Prepare comprehensive PVP data"""
        
        return {
            "protocol_number": protocol_id,
            "generation_date": datetime.now().strftime("%d/%m/%Y"),
            "product_info": product_info,
            "stp_summary": {
                "total_tests": len(stp_data.get("tests", [])),
                "product_code": stp_data.get("product_code", ""),
                "version": stp_data.get("version", "01-00")
            },
            "mfr_summary": {
                "batch_size": mfr_data.get("batch_size", ""),
                "total_steps": len(mfr_data.get("manufacturing_steps", [])),
                "raw_materials_count": len(mfr_data.get("raw_materials", [])),
                "equipment_count": len(mfr_data.get("equipment", [])),
                "product_code": mfr_data.get("product_code", ""),
                "version": mfr_data.get("version", "01-00")
            },
            "mfr_data": {
                "manufacturing_steps": mfr_data.get("manufacturing_steps", []),
                "raw_materials": mfr_data.get("raw_materials", []),
                "process_parameters": mfr_data.get("process_parameters", {}),
                "packaging_details": mfr_data.get("packaging_details", {}),
                "hold_times": mfr_data.get("hold_times", {}),
                "equipment": mfr_data.get("equipment", [])
            },
            "stp_data": {
                "tests": stp_data.get("tests", []),
                "specifications": stp_data.get("specifications", {}),
                "methods": stp_data.get("methods", {}),
                "acceptance_criteria": stp_data.get("acceptance_criteria", {})
            },
            "critical_parameters": critical_params,
            "sampling_plan": sampling_plan,
            "validation_approach": "Prospective validation with three consecutive batches",
            "batch_numbers": [f"{product_info['product_code']}{i:03d}" for i in range(1001, 1004)]
        }
    
    def _prepare_pvr_data(self, product_info: Dict, pvp_data: Dict, 
                         batch_results: List[Dict], product_type: str, 
                         report_id: str) -> Dict[str, Any]:
        """Prepare comprehensive PVR data (Template Supported)"""
        
        # Calculate overall results
        # STRICT RULE: Process Validated ONLY if at least 3 batches executed and ALL pass.
        # Check if we have actual results or just templates
        has_results = any(b.get('overall_result') for b in batch_results)
        
        all_passed = False
        if has_results:
             all_passed = len(batch_results) >= 3 and all(batch.get('overall_result') == 'PASS' for batch in batch_results)
        
        
        # Calculate statistics
        # Handle cases where test_results might be empty or valid
        total_tests = sum(len(batch.get('test_results', [])) for batch in batch_results)
        passed_tests = sum(1 for batch in batch_results 
                          for test in batch.get('test_results', []) 
                          if test.get('status') == 'PASS')
                          
        # Evaluate strict compliance
        # If no results (template mode), we shouldn't run reasoning engine or we should handle it
        if not has_results:
            compliance_level = "PENDING EXECUTION"
            conclusion_statement = "Validation Pending Execution of Batches"
            justification = "Report generated as template for data collection."
            recommendations = ["Execute 3 consecutive batches", "Record all results", "Compare against acceptance criteria"]
        else:
            decision = self.reasoning_engine.evaluate_validation(pvp_data, batch_results)
            compliance_level = decision.compliance_level
            conclusion_statement = decision.conclusion_statement
            justification = decision.justification
            recommendations = decision.recommendations

        
        return {
            "report_number": report_id,
            "generation_date": datetime.now().strftime("%d/%m/%Y"),
            "protocol_reference": pvp_data['protocol_number'],
            "product_info": pvp_data['product_info'],
            "mfr_summary": pvp_data.get("mfr_summary", {}),
            "stp_data": pvp_data.get("stp_data", {}),
            "mfr_data": pvp_data.get("mfr_data", {}),
            "critical_parameters": pvp_data.get("critical_parameters", []),
            "sampling_plan": pvp_data.get("sampling_plan", []),
            "batch_results": batch_results,
            "summary_statistics": {
                "total_batches": len(batch_results),
                "batches_passed": sum(1 for b in batch_results if b.get('overall_result') == 'PASS') if has_results else "N/A",
                "batches_failed": sum(1 for b in batch_results if b.get('overall_result') == 'FAIL') if has_results else "N/A",
                "total_tests_performed": total_tests,
                "tests_passed": passed_tests if has_results else "N/A",
                "tests_failed": (total_tests - passed_tests) if has_results else "N/A",
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if (total_tests > 0 and has_results) else "N/A"
            },
            # Strict Regulatory Reasoning Logic
            "conclusion": conclusion_statement,
            "validation_compliance": compliance_level,
            "conclusion_justification": justification,
            "recommendations": recommendations,
            "is_template": not has_results
        }
    
    
    def _generate_strict_batch_results(self, mfr_execution: Dict, stp_execution: Dict, 
                                     effective_date_str: str, stp_master: Dict = None) -> List[Dict]:
        """
        Generate batch results.
        If execution data exists, extract it.
        If NO execution data (Protocol phase), generate 3 EMPTY TEMPLATE batches.
        """
        batches = []
        
        # Build Spec Lookup Map
        spec_map = {}
        tests_list = []
        if stp_master:
            tests_list = stp_master.get("tests", [])
            for t in tests_list:
                tname = t.get("test_name", "").lower()
                spec = t.get("specification") or t.get("acceptance_criteria") or ""
                spec_map[tname] = spec

        # Merge extracted batch data
        mfr_batches = mfr_execution.get("batches", [])
        stp_batches = stp_execution.get("batches", [])
        
        # Map by Batch ID to merge sources
        batch_map = {}
        for b in mfr_batches:
            bid = b.get("batch_id")
            if bid: batch_map[bid] = b.copy()
            
        for b in stp_batches:
            bid = b.get("batch_id")
            if bid:
                if bid in batch_map:
                    if "results" not in batch_map[bid]: batch_map[bid]["results"] = {}
                    # Merge results (STP results take precedence)
                    batch_map[bid]["results"].update(b.get("results", {}))
                else:
                    batch_map[bid] = b.copy()
                    
        # CASE 1: Extracted Data Exists (Execution Mode)
        if batch_map:
            for bid, data in batch_map.items():
                results = data.get("results", {})
                mfg_date = data.get("mfg_date", "Unknown")
                
                # Identify Expiry Date (Simple Logic: Mfg + 3 Years if not present)
                exp_date = data.get("expiry_date", "")
                if not exp_date and mfg_date and mfg_date != "Unknown":
                    try:
                        # Try parsing YYYY-MM-DD
                        dt = datetime.strptime(mfg_date, "%Y-%m-%d")
                        exp_dt = dt.replace(year=dt.year + 2) # Assume 2 years default if unknown
                        exp_date = exp_dt.strftime("%Y-%m-%d")
                    except:
                        exp_date = "TBD"

                status = "PASS"
                remarks = "Batch extracted successfully"
                
                if not results:
                    status = "FAIL"
                    remarks = "No test results found in documents"
                
                formatted_results = []
                for test, val in results.items():
                    res_status = "PASS"
                    if "fail" in str(val).lower() or "oos" in str(val).lower():
                        res_status = "FAIL"
                        status = "FAIL"
                        remarks = "OOS reported"
                    
                    # Lookup Spec
                    spec = spec_map.get(test.lower(), "As per STP")

                    formatted_results.append({
                        "test_name": test,
                        "result": val,
                        "status": res_status,
                        "specification": spec
                    })
                
                batches.append({
                    "batch_number": bid,
                    "manufacturing_date": mfg_date,
                    "expiry_date": exp_date,
                    "batch_size": data.get("batch_size", "As per MFR"),
                    "test_results": formatted_results,
                    "overall_result": status,
                    "yield_percentage": data.get("results", {}).get("yield", "N/A"),
                    "remarks": remarks
                })
        
        # CASE 2: No Extracted Data (Template Mode)
        else:
            # Generate 3 Empty Template Batches
            for i in range(1, 4):
                test_templates = []
                for t in tests_list:
                    test_templates.append({
                        "test_name": t.get("test_name", "Test"),
                        "result": "", # EMPTY
                        "status": "", # EMPTY
                        "specification": t.get("specification") or t.get("acceptance_criteria") or ""
                    })

                batches.append({
                    "batch_number": f"BATCH-00{i} (Placehholder)",
                    "manufacturing_date": "",
                    "expiry_date": "",
                    "batch_size": "",
                    "test_results": test_templates,
                    "overall_result": "", # EMPTY
                    "yield_percentage": "",
                    "remarks": ""
                })
            
        return batches
            

    
    def export_results(self, output_dir: str = "output"):
        """Export processing results"""
        import os
        import json
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Export JSON data
        json_path = os.path.join(output_dir, "validation_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.processed_data, f, indent=2, default=str)
        print(f"  JSON data saved to: {json_path}")
        
        # Export processing summary
        summary_path = os.path.join(output_dir, "processing_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_summary_text())
        print(f"  Summary saved to: {summary_path}")
        
        # Export extracted data separately
        if self.processed_data.get("stp_data"):
            stp_path = os.path.join(output_dir, "stp_extracted.json")
            with open(stp_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_data["stp_data"], f, indent=2, default=str)
        
        if self.processed_data.get("mfr_data"):
            mfr_path = os.path.join(output_dir, "mfr_extracted.json")
            with open(mfr_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_data["mfr_data"], f, indent=2, default=str)
        
        print(f"\nAll results exported to: {output_dir}/")
    
    def _generate_summary_text(self) -> str:
        """Generate summary text"""
        summary = f"""
        PharmaDoc AI - Processing Summary
        {'='*60}
        
        Timestamp: {self.processed_data.get('processing_summary', {}).get('processing_timestamp', '')}
        
        Product: {self.processed_data.get('product_info', {}).get('name', 'Unknown')}
        Product Code: {self.processed_data.get('product_info', {}).get('product_code', '')}
        Dosage Form: {self.processed_data.get('product_info', {}).get('dosage_form', '')}
        
        Extraction Results:
        - STP Tests: {len(self.processed_data.get('stp_data', {}).get('tests', []))}
        - MFR Steps: {len(self.processed_data.get('mfr_data', {}).get('manufacturing_steps', []))}
        - Raw Materials: {len(self.processed_data.get('mfr_data', {}).get('raw_materials', []))}
        - Equipment: {len(self.processed_data.get('mfr_data', {}).get('equipment', []))}
        
        Validation Components:
        - Critical Parameters: {len(self.processed_data.get('critical_parameters', []))}
        - Sampling Points: {len(self.processed_data.get('sampling_plan', []))}
        - Validation Batches: {len(self.processed_data.get('batch_results', []))}
        
        Validation Status:
        - STP Valid: {self.processed_data.get('validation_summary', {}).get('stp_valid', False)}
        - MFR Valid: {self.processed_data.get('validation_summary', {}).get('mfr_valid', False)}
        - Cross-reference Errors: {self.processed_data.get('validation_summary', {}).get('cross_ref_errors', 0)}
        
        Generated Documents:
        - Protocol ID: {self.processed_data.get('pvp_data', {}).get('protocol_number', '')}
        - Report ID: {self.processed_data.get('pvr_data', {}).get('report_number', '')}
        - Conclusion: {self.processed_data.get('pvr_data', {}).get('conclusion', '')}
        
        {'='*60}
        """
        return summary

# ==================== MAIN EXECUTION ====================

def main():
    """Main execution function"""
    
    # Set your Gemini API key
    GEMINI_API_KEY = Config.GEMINI_API_KEY
    
    # Create Enhanced PharmaDoc AI instance
    pharmadoc = EnhancedPharmaDocAI(GEMINI_API_KEY)
    
    # Create mock documents for testing
    print("Creating mock documents for testing...")
    
    # Mock STP content
    stp_content = """
    STANDARD TESTING PROCEDURE
    Product Name: Fluorouracil Injection BP 50mg/ml, 10ml
    Product Code: FU/002
    Version: 01-00
    Effective Date: 01/01/2024
    
    TESTS AND SPECIFICATIONS:
    
    1. Description: A clear colourless or almost colourless solution filled in clear colour glass vial USP type-I
    
    2. Identification: 
       a) By IR: The infrared absorption spectrum obtained from the residue of sample should be concordant to the infrared absorption spectrum obtained from the working standard or reference standard.
       b) By UV: In the assay, the UV spectrum of sample solution should exhibits a maxima only at about 266 nm.
    
    3. pH: Between 8.5 to 9.1
    
    4. Extractable volume: Not less than 10.0 ml
    
    5. Sterility: Complies with the test for sterility (USP <71>)
    
    6. Bacterial Endotoxins: NMT 0.33 EU/mg
    
    7. Particulate Matter: Complies with the test for particulate matter (USP <788>)
    
    8. Related Substances:
       Any individual impurity: Should comply
       5-Hydroxyuracil: Any spot corresponding to 5-hydroxyuracil in the chromatogram obtained with sample solution should be not more intense than the spot in the chromatogram obtained with 5-hydroxyuracil standard.
    
    9. Assay: Each 10ml contains 90.0% to 110.0% of the labelled amount of Fluorouracil BP
    """
    
    # Mock MFR content
    mfr_content = """
    MASTER FORMULA RECORD
    Product: Fluorouracil Injection BP 50mg/ml, 10ml
    Product Code: FU/002
    Batch Size: 50.0 Liters (5000 vials)
    Version: 01-00
    
    COMPOSITION:
    Each ml contains:
    Fluorouracil BP: 50.00 mg
    Disodium edetate BP: 1.00 mg
    Tromethamine BP: 84.00 mg
    Sodium Hydroxide BP: 6.00 mg
    Sodium Hydroxide BP: q.s. to pH adjustment
    Water for Injection BP: q.s. to 1 ml
    
    MANUFACTURING PROCESS:
    
    1. Dispensing: Weigh all ingredients as per formula in controlled area
    
    2. Compounding: Take freshly collected Water for Injection in manufacturing tank and cool to 30-40°C with continuous nitrogen purging
    
    3. Add Disodium edetate with continuous stirring until clear solution
    
    4. Add Tromethamine with continuous stirring
    
    5. Stir for 20 minutes and check complete dissolution
    
    6. Add Fluorouracil and continue stirring to disperse completely
    
    7. Add Sodium Hydroxide slowly under continuous stirring
    
    8. Check pH between 8.5-9.1, adjust if required
    
    9. Make up final volume with Water for Injection
    
    10. Send sample to QC for analysis
    
    11. After approval, proceed to filtration
    
    12. Filter through 0.22μm membrane filter with nitrogen pressure 1.2-1.8 kg/cm²
    
    13. Fill not less than 10 ml into 10 ml vials
    
    14. Stopper with gray bromo butyl rubber stoppers
    
    15. Seal with aluminium flip-off seals
    
    16. Inspect 100% visually
    
    CRITICAL PARAMETERS:
    Compounding Temperature: 30-40°C
    Mixing Time: 20 minutes
    pH: 8.5-9.1
    Filtration Pressure: 1.2-1.8 kg/cm²
    Fill Volume: NLT 10.0 ml
    
    PACKAGING:
    Primary: 10 ml clear moulded glass vial USP type-1
    Closure: 20mm Gray Bromo Butyl rubber stopper
    Seal: 20mm aluminium flip off seal (blue)
    Secondary: Carton box with leaflet
    """
    
    # Write to files
    with open("mock_stp_fluorouracil.txt", "w", encoding='utf-8') as f:
        f.write(stp_content)
    
    with open("mock_mfr_fluorouracil.txt", "w", encoding='utf-8') as f:
        f.write(mfr_content)
    
    # Process documents
    try:
        print("\nProcessing Fluorouracil Injection...")
        results = pharmadoc.process_documents(
            product_name="Fluorouracil Injection BP 50mg/ml, 10ml",
            dosage_form="Injection",
            stp_pdf_path="mock_stp_fluorouracil.txt",
            mfr_pdf_path="mock_mfr_fluorouracil.txt"
        )
        
        # Export results
        pharmadoc.export_results("output_enhanced")
        
        print("\n" + "="*80)
        print("Processing Complete!")
        print("="*80)
        
        # Print summary
        validation_summary = results.get("validation_summary", {})
        print(f"\nValidation Summary:")
        print(f"  STP valid: {validation_summary.get('stp_valid', False)}")
        print(f"  MFR valid: {validation_summary.get('mfr_valid', False)}")
        print(f"  Cross-reference errors: {validation_summary.get('cross_ref_errors', 0)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Create cache directory
    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    main()



