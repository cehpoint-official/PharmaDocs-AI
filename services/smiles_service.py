# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

"""
SMILES Generation Service using PubChem API
This service generates SMILES notation from chemical ingredient names
"""

import requests
import logging
from typing import Optional, Dict, Any

class SMILESGenerator:
    """Generate SMILES notation from chemical ingredient names using PubChem API"""
    
    def __init__(self):
        self.base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"
        self.timeout = 10  # seconds
        
    def get_smiles_from_name(self, name: str) -> Optional[str]:
        """
        Get SMILES notation from chemical name using PubChem API
        
        Args:
            name (str): Chemical ingredient name
            
        Returns:
            Optional[str]: SMILES notation if found, None otherwise
        """
        if not name or not name.strip():
            return None
            
        try:
            # Clean the name
            clean_name = name.strip()
            
            # Make API request to PubChem
            url = f"{self.base_url}/{clean_name}/property/SMILES,IsomericSMILES,CanonicalSMILES/JSON"
            
            logging.info(f"Requesting SMILES for: {clean_name}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract SMILES from response with fallback priority
                if "PropertyTable" in data and "Properties" in data["PropertyTable"]:
                    properties = data["PropertyTable"]["Properties"]
                    if properties and len(properties) > 0:
                        prop = properties[0]
                        isomeric_smiles = prop.get("IsomericSMILES", "")
                        canonical_smiles = prop.get("CanonicalSMILES", "")
                        basic_smiles = prop.get("SMILES", "")
                        
                        # Try in order of preference
                        smiles = (isomeric_smiles if isomeric_smiles and isomeric_smiles.strip()
                                else canonical_smiles if canonical_smiles and canonical_smiles.strip()
                                else basic_smiles)
                        
                        if smiles and smiles.strip():
                            logging.info(f"Successfully retrieved SMILES for {clean_name}: {smiles}")
                            return smiles
                
                logging.warning(f"No SMILES found for {clean_name}")
                return None
            else:
                logging.warning(f"PubChem API returned status {response.status_code} for {clean_name}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout while requesting SMILES for {clean_name}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error while getting SMILES for {clean_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while getting SMILES for {clean_name}: {e}")
            return None
    
    def get_chemical_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive chemical information including SMILES, molecular formula, and molecular weight
        
        Args:
            name (str): Chemical ingredient name
            
        Returns:
            Optional[Dict[str, Any]]: Chemical information if found, None otherwise
        """
        if not name or not name.strip():
            return None
            
        try:
            clean_name = name.strip()
            
            # Request multiple properties
            url = f"{self.base_url}/{clean_name}/property/MolecularFormula,MolecularWeight,SMILES,IsomericSMILES,CanonicalSMILES/JSON"
            
            logging.info(f"Requesting chemical info for: {clean_name}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if "PropertyTable" in data and "Properties" in data["PropertyTable"]:
                    properties = data["PropertyTable"]["Properties"]
                    if properties and len(properties) > 0:
                        prop = properties[0]
                        
                        # Get SMILES with fallback priority: IsomericSMILES > CanonicalSMILES > SMILES
                        isomeric_smiles = prop.get('IsomericSMILES', '')
                        canonical_smiles = prop.get('CanonicalSMILES', '')
                        basic_smiles = prop.get('SMILES', '')
                        
                        smiles = (isomeric_smiles if isomeric_smiles and isomeric_smiles.strip() 
                                else canonical_smiles if canonical_smiles and canonical_smiles.strip()
                                else basic_smiles)
                        
                        chemical_info = {
                            'name': clean_name,
                            'molecular_formula': prop.get('MolecularFormula', ''),
                            'molecular_weight': prop.get('MolecularWeight', 0),
                            'isomeric_smiles': isomeric_smiles,
                            'canonical_smiles': canonical_smiles,
                            'basic_smiles': basic_smiles,
                            'smiles': smiles
                        }
                        
                        logging.info(f"Successfully retrieved chemical info for {clean_name}")
                        return chemical_info
                
                logging.warning(f"No chemical info found for {clean_name}")
                return None
            else:
                logging.warning(f"PubChem API returned status {response.status_code} for {clean_name}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout while requesting chemical info for {clean_name}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error while getting chemical info for {clean_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while getting chemical info for {clean_name}: {e}")
            return None
    
    def search_chemical_alternatives(self, name: str) -> Optional[list]:
        """
        Search for alternative names or similar compounds
        
        Args:
            name (str): Chemical ingredient name
            
        Returns:
            Optional[list]: List of alternative names if found, None otherwise
        """
        if not name or not name.strip():
            return None
            
        try:
            clean_name = name.strip()
            
            # Search for compounds with similar names
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{clean_name}/synonyms/JSON"
            
            logging.info(f"Searching alternatives for: {clean_name}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                if "InformationList" in data and "Information" in data["InformationList"]:
                    info = data["InformationList"]["Information"]
                    if info and len(info) > 0:
                        synonyms = info[0].get("Synonym", [])
                        if synonyms:
                            logging.info(f"Found {len(synonyms)} alternatives for {clean_name}")
                            return synonyms[:10]  # Return first 10 alternatives
                
                logging.warning(f"No alternatives found for {clean_name}")
                return None
            else:
                logging.warning(f"PubChem API returned status {response.status_code} for {clean_name}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout while searching alternatives for {clean_name}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error while searching alternatives for {clean_name}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while searching alternatives for {clean_name}: {e}")
            return None

# Global instance
smiles_generator = SMILESGenerator()
