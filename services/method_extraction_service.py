"""
Method Extraction Service for AMV Documents
Extracts analytical method parameters from uploaded PDF files using AI
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
import PyPDF2
import io

logger = logging.getLogger(__name__)

class MethodExtractionService:
    """Service for extracting analytical method parameters from PDF files"""
    
    def __init__(self):
        self.instrument_patterns = {
            'hplc': {
                'wavelength': r'(?:wavelength|λ|nm|detection)[\s:]*(\d{3,4})',
                'flow_rate': r'(?:flow rate|flowrate|flow)[\s:]*(\d+\.?\d*)\s*(?:ml/min|ml/min|mL/min)',
                'injection_volume': r'(?:injection volume|inject|injection)[\s:]*(\d+\.?\d*)\s*(?:μl|μL|ul|UL)',
                'column': r'(?:column|stationary phase|packing)[\s:]*([^,\n\r]+)',
                'mobile_phase': r'(?:mobile phase|eluent|solvent)[\s:]*([^,\n\r]+)',
                'detection': r'(?:detection|detector|detect)[\s:]*([^,\n\r]+)',
                'temperature': r'(?:temperature|temp|column temp)[\s:]*(\d+\.?\d*)\s*(?:°C|C)',
                'pressure': r'(?:pressure)[\s:]*(\d+\.?\d*)\s*(?:bar|psi|MPa)',
                'reference_area_standard': r'(?:reference area|area of standard|standard area)[\s:]*(\d+\.?\d*)',
                'retention_time': r'(?:retention time|rt)[\s:]*(\d+\.?\d*)\s*(?:min|minutes)',
                'resolution': r'(?:resolution|rs)[\s:]*(\d+\.?\d*)',
                'tailing_factor': r'(?:tailing factor|tf)[\s:]*(\d+\.?\d*)',
                'theoretical_plates': r'(?:theoretical plates|n)[\s:]*(\d+\.?\d*)'
            },
            'uv': {
                'wavelength': r'(?:wavelength|λ|nm|detection)[\s:]*(\d{3,4})',
                'absorbance': r'(?:absorbance|abs|A)[\s:]*(\d+\.?\d*)',
                'reference_absorbance_standard': r'(?:reference absorbance|absorbance of standard|standard absorbance)[\s:]*(\d+\.?\d*)',
                'path_length': r'(?:path length|cell|cuvette)[\s:]*(\d+\.?\d*)\s*(?:cm|mm)',
                'reference': r'(?:reference|blank)[\s:]*([^,\n\r]+)',
                'scan_range': r'(?:scan range|range)[\s:]*(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*(?:nm)',
                'bandwidth': r'(?:bandwidth|slit width)[\s:]*(\d+\.?\d*)\s*(?:nm)'
            },
            'titration': {
                'indicator': r'(?:indicator)[\s:]*([^,\n\r]+)',
                'titrant': r'(?:titrant|standard|reagent)[\s:]*([^,\n\r]+)',
                'endpoint': r'(?:endpoint|end point|equivalence)[\s:]*([^,\n\r]+)',
                'volume': r'(?:volume|consumption)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
                'standard_factor': r'(?:each\s+ml.*?equivalent\s+to\s+)(\d+\.?\d*)\s*(?:mg|g)',
                'reference_volume': r'(?:reference\s+volume|volume)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
                'weight_sample_gm': r'(?:weigh.*?containing\s+)(\d+\.?\d*)\s*(?:g|gm)',
                'molarity': r'(?:molarity|molar concentration)[\s:]*(\d+\.?\d*)\s*(?:M|mol/L)',
                'normality': r'(?:normality|normal concentration)[\s:]*(\d+\.?\d*)\s*(?:N|eq/L)'
            },
            'aas': {
                'wavelength': r'(?:wavelength|λ|nm|detection)[\s:]*(\d{3,4})',
                'absorbance': r'(?:absorbance|abs|A)[\s:]*(\d+\.?\d*)',
                'reference_absorbance_standard': r'(?:reference absorbance|absorbance of standard|standard absorbance)[\s:]*(\d+\.?\d*)',
                'path_length': r'(?:path length|cell|cuvette)[\s:]*(\d+\.?\d*)\s*(?:cm|mm)',
                'reference': r'(?:reference|blank)[\s:]*([^,\n\r]+)',
                'lamp_current': r'(?:lamp current|current)[\s:]*(\d+\.?\d*)\s*(?:mA)',
                'slit_width': r'(?:slit width|bandwidth)[\s:]*(\d+\.?\d*)\s*(?:nm)',
                'burner_height': r'(?:burner height|height)[\s:]*(\d+\.?\d*)\s*(?:mm)',
                'gas_flow': r'(?:gas flow|flow rate)[\s:]*(\d+\.?\d*)\s*(?:L/min)'
            },
            'gc': {
                'column': r'(?:column|stationary phase|packing)[\s:]*([^,\n\r]+)',
                'carrier_gas': r'(?:carrier gas|gas)[\s:]*([^,\n\r]+)',
                'flow_rate': r'(?:flow rate|flowrate|flow)[\s:]*(\d+\.?\d*)\s*(?:ml/min|ml/min|mL/min)',
                'injection_volume': r'(?:injection volume|inject|injection)[\s:]*(\d+\.?\d*)\s*(?:μl|μL|ul|UL)',
                'temperature': r'(?:temperature|temp|column temp)[\s:]*(\d+\.?\d*)\s*(?:°C|C)',
                'detection': r'(?:detection|detector|detect)[\s:]*([^,\n\r]+)',
                'split_ratio': r'(?:split ratio|split)[\s:]*(\d+:\d+)',
                'retention_time': r'(?:retention time|rt)[\s:]*(\d+\.?\d*)\s*(?:min|minutes)'
            }
        }
        
        self.concentration_patterns = {
            'weight_standard': r'(?:weight|wt|mass)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
            'weight_sample': r'(?:sample weight|sample wt|sample mass|weight of sample)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
            'final_concentration_standard': r'(?:final concentration|concentration|conc|strength)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL)',
            'final_concentration_sample': r'(?:sample concentration|sample conc|sample strength)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|μg/ml|mg/mL|μg/mL)',
            'dilution': r'(?:dilute|dilution|dilute to)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
            'volume': r'(?:volume|vol|final volume)[\s:]*(\d+\.?\d*)\s*(?:ml|mL)',
            'potency': r'(?:potency|assay|purity)[\s:]*(\d+\.?\d*)\s*%?',
            'label_claim': r'(?:label claim|claim|strength)[\s:]*(\d+\.?\d*)\s*(?:mg|g|%)',
            'average_weight': r'(?:average weight|mean weight|weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
            'weight_per_ml': r'(?:weight per ml|weight/ml|density)[\s:]*(\d+\.?\d*)\s*(?:mg/ml|g/ml)',
            'wavelength': r'(?:wavelength|λ|nm|detection)[\s:]*(\d{3,4})',
            'molecular_weight': r'(?:molecular weight|mol wt|MW)[\s:]*(\d+\.?\d*)\s*(?:g/mol|Da)',
            'molecular_formula': r'(?:molecular formula|formula)[\s:]*([A-Za-z0-9]+)'
        }
        
        self.validation_patterns = {
            'precision': r'(?:precision|RSD|%CV)[\s:]*(\d+\.?\d*)%?',
            'linearity': r'(?:linearity|correlation|r²)[\s:]*(\d+\.?\d*)',
            'accuracy': r'(?:accuracy|recovery)[\s:]*(\d+\.?\d*)%?',
            'specificity': r'(?:specificity|selectivity)',
            'robustness': r'(?:robustness|ruggedness)'
        }
        
        # Instrument type detection patterns
        self.instrument_type_patterns = {
            'HPLC': [
                r'(?:hplc|high performance liquid chromatography|high-pressure liquid chromatography)',
                r'(?:liquid chromatography|lc)',
                r'(?:column chromatography)',
                r'(?:mobile phase|eluent)',
                r'(?:flow rate|injection volume)',
                r'(?:retention time|rt)',
                r'(?:uv detector|pda detector|mass spectrometer)'
            ],
            'UPLC': [
                r'(?:uplc|ultra performance liquid chromatography|ultra-pressure liquid chromatography)',
                r'(?:ultra high performance liquid chromatography)',
                r'(?:waters acquity|waters uplc)',
                r'(?:sub-2.*?micron|sub-2.*?μm)'
            ],
            'GC': [
                r'(?:gc|gas chromatography|gas chromatograph)',
                r'(?:headspace|hs-gc)',
                r'(?:carrier gas|helium|nitrogen)',
                r'(?:split ratio|splitless)',
                r'(?:fid detector|ecd detector|ms detector)'
            ],
            'UV-Vis': [
                r'(?:uv-vis|uv/vis|ultraviolet-visible|uv-visible)',
                r'(?:spectrophotometer|spectrophotometric)',
                r'(?:wavelength.*?nm|λ.*?nm)',
                r'(?:absorbance|optical density)',
                r'(?:by uv|uv method|uv spectroscopy)'
            ],
            'AAS': [
                r'(?:aas|atomic absorption|atomic absorption spectroscopy)',
                r'(?:flame atomic absorption|flame aas)',
                r'(?:graphite furnace|gf-aas)',
                r'(?:hollow cathode lamp|hcl)',
                r'(?:by aas|aas method)'
            ],
            'Titration': [
                r'(?:by titration|titration method|titrimetric)',
                r'(?:weigh.*?titrate|titrate.*?with)',
                r'(?:indicator|methyl orange|phenolphthalein)',
                r'(?:endpoint|equivalence point)',
                r'(?:each ml.*?equivalent|equivalent to)',
                r'(?:vs|volumetric solution)',
                r'(?:hydrochloric acid|sodium hydroxide|sulfuric acid)'
            ]
        }

    def extract_method_parameters(self, pdf_content: bytes, instrument_type: str) -> Dict[str, any]:
        """
        Extract analytical method parameters from PDF content
        
        Args:
            pdf_content: PDF file content as bytes
            instrument_type: Type of instrument (hplc, uv, titration, etc.)
            
        Returns:
            Dictionary containing extracted parameters
        """
        try:
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(pdf_content)
            
            if not text_content:
                logger.warning("No text content extracted from PDF")
                return {
                    'error': 'No text content could be extracted from the PDF file. Please ensure the PDF contains readable text.',
                    'raw_text_length': 0
                }
            
            # Extract parameters based on instrument type
            extracted_params = {}
            
            if instrument_type in self.instrument_patterns:
                extracted_params.update(self._extract_instrument_params(text_content, instrument_type))
            
            # Extract common parameters
            extracted_params.update(self._extract_common_params(text_content))
            
            # Extract validation parameters
            extracted_params.update(self._extract_validation_params(text_content))
            
            # Detect instrument type from content
            detected_instrument_type = self._detect_instrument_type(text_content)
            if detected_instrument_type:
                extracted_params['detected_instrument_type'] = detected_instrument_type
            
            # Add metadata
            extracted_params['raw_text_length'] = len(text_content)
            extracted_params['text_preview'] = text_content[:500] + "..." if len(text_content) > 500 else text_content
            
            logger.info(f"Extracted {len(extracted_params)} parameters from PDF")
            return extracted_params
            
        except Exception as e:
            logger.error(f"Error extracting method parameters: {str(e)}")
            return {
                'error': f'Error processing PDF: {str(e)}',
                'raw_text_length': 0
            }

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text content from PDF bytes"""
        try:
            # First try PyPDF2 for actual PDF files
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text_content = ""
            
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            return text_content
        except Exception as e:
            # If PyPDF2 fails, try to decode as plain text
            try:
                text_content = pdf_content.decode('utf-8')
                logger.info("Decoded content as plain text")
                return text_content
            except UnicodeDecodeError:
                logger.error(f"Error extracting text from PDF: {str(e)}")
                return ""

    def _extract_instrument_params(self, text: str, instrument_type: str) -> Dict[str, any]:
        """Extract instrument-specific parameters"""
        params = {}
        patterns = self.instrument_patterns.get(instrument_type, {})
        
        for param_name, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Take the first match and convert to appropriate type
                value = matches[0]
                if param_name in ['wavelength', 'flow_rate', 'injection_volume']:
                    try:
                        params[param_name] = float(value)
                    except ValueError:
                        params[param_name] = value
                else:
                    params[param_name] = value
        
        return params

    def _extract_common_params(self, text: str) -> Dict[str, any]:
        """Extract common analytical parameters"""
        params = {}
        
        for param_name, pattern in self.concentration_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Handle multiple matches by taking the first one
                    value = matches[0] if isinstance(matches[0], str) else matches[0]
                    if param_name in ['weight_standard', 'weight_sample', 'final_concentration_standard', 
                                    'final_concentration_sample', 'potency', 'average_weight', 'weight_per_ml',
                                    'wavelength', 'molecular_weight']:
                        params[param_name] = float(value)
                    else:
                        params[param_name] = value
                except ValueError:
                    params[param_name] = matches[0]
        
        # Add smart defaults for missing parameters
        params = self._add_smart_defaults(params, text)
        
        return params

    def _add_smart_defaults(self, params: Dict[str, any], text: str) -> Dict[str, any]:
        """Add smart defaults for missing parameters based on context"""
        
        # Smart defaults for common parameters
        if 'weight_standard' not in params:
            # Look for standard weight in different formats
            standard_weight_patterns = [
                r'(?:weigh\s+)(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:standard.*?weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:reference.*?weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)'
            ]
            for pattern in standard_weight_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        params['weight_standard'] = float(match.group(1))
                        break
                    except ValueError:
                        continue
        
        if 'weight_sample' not in params:
            # Look for sample weight in different formats
            sample_weight_patterns = [
                r'(?:sample.*?weigh\s+)(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:weigh.*?sample)[\s:]*(\d+\.?\d*)\s*(?:mg|g)',
                r'(?:test.*?weight)[\s:]*(\d+\.?\d*)\s*(?:mg|g)'
            ]
            for pattern in sample_weight_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        params['weight_sample'] = float(match.group(1))
                        break
                    except ValueError:
                        continue
        
        # Calculate concentrations if weights are available
        if 'weight_standard' in params and 'final_concentration_standard' not in params:
            # Try to calculate from volume information
            volume_match = re.search(r'(?:dilute.*?to\s+)(\d+\.?\d*)\s*(?:ml|mL)', text, re.IGNORECASE)
            if volume_match:
                try:
                    volume = float(volume_match.group(1))
                    if volume > 0:
                        params['final_concentration_standard'] = params['weight_standard'] / volume
                except ValueError:
                    pass
        
        if 'weight_sample' in params and 'final_concentration_sample' not in params:
            # Try to calculate from volume information
            volume_match = re.search(r'(?:dilute.*?to\s+)(\d+\.?\d*)\s*(?:ml|mL)', text, re.IGNORECASE)
            if volume_match:
                try:
                    volume = float(volume_match.group(1))
                    if volume > 0:
                        params['final_concentration_sample'] = params['weight_sample'] / volume
                except ValueError:
                    pass
        
        # Default wavelength based on instrument type
        if 'wavelength' not in params:
            if re.search(r'(?:hplc|hplc-uv|uv detection)', text, re.IGNORECASE):
                params['wavelength'] = 254.0  # Common UV wavelength
            elif re.search(r'(?:visible|vis)', text, re.IGNORECASE):
                params['wavelength'] = 450.0  # Visible range
            elif re.search(r'(?:fluorescence|fl)', text, re.IGNORECASE):
                params['wavelength'] = 280.0  # Common fluorescence wavelength
        
        # Default flow rate for HPLC
        if 'flow_rate' not in params and re.search(r'(?:hplc|hplc-uv)', text, re.IGNORECASE):
            params['flow_rate'] = 1.0  # Common HPLC flow rate
        
        # Default injection volume for HPLC
        if 'injection_volume' not in params and re.search(r'(?:hplc|hplc-uv)', text, re.IGNORECASE):
            params['injection_volume'] = 20.0  # Common injection volume
        
        # Default potency if not found
        if 'potency' not in params:
            potency_match = re.search(r'(?:assay|purity|potency)[\s:]*(\d+\.?\d*)\s*%?', text, re.IGNORECASE)
            if potency_match:
                try:
                    params['potency'] = float(potency_match.group(1))
                except ValueError:
                    pass
        
        return params

    def _detect_instrument_type(self, text: str) -> Optional[str]:
        """Detect instrument type from PDF content"""
        text_lower = text.lower()
        
        # Score each instrument type based on pattern matches
        instrument_scores = {}
        
        for instrument_type, patterns in self.instrument_type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                score += len(matches)
            
            # Special scoring for titration (very specific patterns)
            if instrument_type == 'Titration':
                # Look for specific titration keywords
                titration_keywords = [
                    r'(?:by titration)',
                    r'(?:weigh.*?titrate)',
                    r'(?:each ml.*?equivalent)',
                    r'(?:vs|volumetric solution)',
                    r'(?:indicator)',
                    r'(?:endpoint)'
                ]
                for keyword in titration_keywords:
                    if re.search(keyword, text_lower):
                        score += 2  # Higher weight for titration-specific terms
            
            instrument_scores[instrument_type] = score
        
        # Return the instrument type with the highest score
        if instrument_scores:
            best_match = max(instrument_scores, key=instrument_scores.get)
            if instrument_scores[best_match] > 0:
                return best_match
        
        return None

    def _extract_validation_params(self, text: str) -> Dict[str, any]:
        """Extract validation parameters"""
        params = {}
        
        for param_name, pattern in self.validation_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                params[param_name] = True
                
                # Try to extract numeric values for quantitative parameters
                if param_name in ['precision', 'linearity', 'accuracy']:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        try:
                            params[f"{param_name}_value"] = float(matches[0])
                        except ValueError:
                            pass
        
        return params

    def suggest_validation_parameters(self, extracted_params: Dict[str, any], 
                                    parameters_to_validate: List[str]) -> List[str]:
        """
        Suggest validation parameters based on extracted method parameters
        
        Args:
            extracted_params: Extracted method parameters
            parameters_to_validate: Selected parameters to validate
            
        Returns:
            List of suggested validation parameters
        """
        suggestions = []
        
        # Basic validation parameters for all methods
        suggestions.extend(['specificity', 'system_suitability', 'precision', 'linearity'])
        
        # Method-specific suggestions
        if 'assay' in parameters_to_validate:
            suggestions.extend(['accuracy', 'robustness', 'range'])
        
        if 'dissolution' in parameters_to_validate:
            suggestions.extend(['accuracy', 'robustness'])
        
        if any(param in parameters_to_validate for param in ['related_substances', 'organic_impurities']):
            suggestions.extend(['lod_loq', 'lod_loq_precision'])
        
        # Remove duplicates and return
        return list(set(suggestions))

    def generate_method_summary(self, extracted_params: Dict[str, any]) -> str:
        """
        Generate a summary of the extracted method parameters
        
        Args:
            extracted_params: Extracted method parameters
            
        Returns:
            Formatted summary string
        """
        if not extracted_params:
            return "No parameters extracted from the method document."
        
        # Check for errors first
        if 'error' in extracted_params:
            return f"Error: {extracted_params['error']}"
        
        summary_parts = []
        
        # Instrument parameters
        if 'wavelength' in extracted_params:
            summary_parts.append(f"Wavelength: {extracted_params['wavelength']} nm")
        
        if 'flow_rate' in extracted_params:
            summary_parts.append(f"Flow Rate: {extracted_params['flow_rate']} ml/min")
        
        if 'injection_volume' in extracted_params:
            summary_parts.append(f"Injection Volume: {extracted_params['injection_volume']} μL")
        
        if 'temperature' in extracted_params:
            summary_parts.append(f"Temperature: {extracted_params['temperature']} °C")
        
        if 'column' in extracted_params:
            summary_parts.append(f"Column: {extracted_params['column']}")
        
        if 'mobile_phase' in extracted_params:
            summary_parts.append(f"Mobile Phase: {extracted_params['mobile_phase']}")
        
        # Concentration parameters
        if 'weight_standard' in extracted_params:
            summary_parts.append(f"Standard Weight: {extracted_params['weight_standard']} mg")
        
        if 'weight_sample' in extracted_params:
            summary_parts.append(f"Sample Weight: {extracted_params['weight_sample']} mg")
        
        if 'concentration' in extracted_params:
            summary_parts.append(f"Concentration: {extracted_params['concentration']} mg/ml")
        
        if 'potency' in extracted_params:
            summary_parts.append(f"Potency: {extracted_params['potency']}%")
        
        # Validation parameters
        validation_params = [k for k in extracted_params.keys() if k in self.validation_patterns]
        if validation_params:
            summary_parts.append(f"Validation Parameters: {', '.join(validation_params)}")
        
        # Add text preview if available
        if 'text_preview' in extracted_params:
            summary_parts.append(f"\nText Preview (first 500 chars):\n{extracted_params['text_preview']}")
        
        if summary_parts:
            return "✅ Extracted Parameters:\n" + "\n".join(f"• {part}" for part in summary_parts)
        else:
            return "⚠️ No specific parameters found, but text was extracted. Please check the method document format."

# Global instance
method_extraction_service = MethodExtractionService()
