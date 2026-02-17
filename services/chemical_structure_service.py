# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

"""
Chemical Structure Generation Service using RDKit
This service generates chemical structure images from SMILES, InChI, or chemical names
"""

import os
import tempfile
from io import BytesIO
from PIL import Image
import logging

try:
    from rdkit import Chem
    from rdkit.Chem import Draw
    from rdkit.Chem import Descriptors
    from rdkit.Chem import rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    logging.warning("RDKit not available. Chemical structure generation will be disabled.")

class ChemicalStructureGenerator:
    """Generate chemical structure images using RDKit"""
    
    def __init__(self):
        self.available = RDKIT_AVAILABLE
        
    def _generate_placeholder_image(self, text="Structure Unavailable", subtext="RDKit Not Found", width=400, height=300):
        """Generate a placeholder image using PIL when RDKit is not available"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # Create a light gray background
            img = Image.new('RGB', (width, height), color=(245, 247, 250))
            draw = ImageDraw.Draw(img)
            
            # Draw a border
            draw.rectangle([0, 0, width-1, height-1], outline=(203, 213, 224), width=2)
            
            # Use default font
            try:
                # Try to get a nicer font if possible, otherwise fallback
                font = ImageFont.load_default()
            except:
                font = None

            # Draw text (Centered roughly)
            draw.text((width//2 - 60, height//2 - 20), text, fill=(74, 85, 104))
            draw.text((width//2 - 50, height//2 + 10), subtext, fill=(160, 174, 192))
            
            # Convert to BytesIO
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            return img_bytes
        except Exception as e:
            logging.error(f"Error generating placeholder image: {e}")
            return None
        
    def generate_structure_from_smiles(self, smiles, width=400, height=300):
        """
        Generate chemical structure image from SMILES string
        
        Args:
            smiles (str): SMILES string
            width (int): Image width in pixels
            height (int): Image height in pixels
            
        Returns:
            BytesIO: Image data as BytesIO object
        """
        if not self.available:
            return self._generate_placeholder_image(f"SMILES: {smiles[:15]}...")
            
        try:
            # Create molecule from SMILES
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logging.error(f"Invalid SMILES string: {smiles}")
                return None
            
            # Generate image
            img = Draw.MolToImage(mol, size=(width, height))
            
            # Convert to BytesIO
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logging.error(f"Error generating structure from SMILES: {e}")
            return None
    
    def generate_structure_from_inchi(self, inchi, width=400, height=300):
        """
        Generate chemical structure image from InChI string
        
        Args:
            inchi (str): InChI string
            width (int): Image width in pixels
            height (int): Image height in pixels
            
        Returns:
            BytesIO: Image data as BytesIO object
        """
        if not self.available:
            return self._generate_placeholder_image(f"InChI: {inchi[:15]}...")
            
        try:
            # Create molecule from InChI
            mol = Chem.MolFromInchi(inchi)
            if mol is None:
                logging.error(f"Invalid InChI string: {inchi}")
                return None
            
            # Generate image
            img = Draw.MolToImage(mol, size=(width, height))
            
            # Convert to BytesIO
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logging.error(f"Error generating structure from InChI: {e}")
            return None
    
    def generate_structure_from_name(self, name, width=400, height=300):
        """
        Generate chemical structure image from chemical name
        
        Args:
            name (str): Chemical name
            width (int): Image width in pixels
            height (int): Image height in pixels
            
        Returns:
            BytesIO: Image data as BytesIO object
        """
        if not self.available:
            return self._generate_placeholder_image(f"Name: {name[:15]}...")
            
        try:
            # Try to create molecule from name
            mol = Chem.MolFromSmiles(name)
            if mol is None:
                # Try alternative approach
                mol = Chem.MolFromMolBlock(name)
            
            if mol is None:
                logging.error(f"Could not generate structure from name: {name}")
                return None
            
            # Generate image
            img = Draw.MolToImage(mol, size=(width, height))
            
            # Convert to BytesIO
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logging.error(f"Error generating structure from name: {e}")
            return None
    
    def get_molecular_properties(self, smiles):
        """
        Get molecular properties from SMILES string
        
        Args:
            smiles (str): SMILES string
            
        Returns:
            dict: Molecular properties
        """
        if not self.available:
            return {}
            
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {}
            
            properties = {
                'molecular_weight': round(Descriptors.MolWt(mol), 2),
                'molecular_formula': rdMolDescriptors.CalcMolFormula(mol),
                'logp': round(Descriptors.MolLogP(mol), 2),
                'hbd': Descriptors.NumHDonors(mol),
                'hba': Descriptors.NumHAcceptors(mol),
                'tpsa': round(Descriptors.TPSA(mol), 2),
                'rotatable_bonds': Descriptors.NumRotatableBonds(mol),
                'aromatic_rings': Descriptors.NumAromaticRings(mol)
            }
            
            return properties
            
        except Exception as e:
            logging.error(f"Error calculating molecular properties: {e}")
            return {}
    
    def generate_structure_with_properties(self, chemical_input, input_type='smiles', width=400, height=300):
        """
        Generate chemical structure and properties
        
        Args:
            chemical_input (str): Chemical input (SMILES, InChI, or name)
            input_type (str): Type of input ('smiles', 'inchi', 'name')
            width (int): Image width in pixels
            height (int): Image height in pixels
            
        Returns:
            dict: Structure image and properties
        """
        result = {
            'image': None,
            'properties': {},
            'success': False,
            'error': None
        }
        
        if not self.available:
            result['image'] = self._generate_placeholder_image("RDKit Required", "Python 3.14 Compatibility")
            result['success'] = True # Return success so UI shows the placeholder instead of error
            result['error'] = 'RDKit not available'
            return result
        
        try:
            # Generate structure image
            if input_type == 'smiles':
                result['image'] = self.generate_structure_from_smiles(chemical_input, width, height)
                if result['image']:
                    result['properties'] = self.get_molecular_properties(chemical_input)
            elif input_type == 'inchi':
                result['image'] = self.generate_structure_from_inchi(chemical_input, width, height)
            elif input_type == 'name':
                result['image'] = self.generate_structure_from_name(chemical_input, width, height)
            else:
                result['error'] = f'Unsupported input type: {input_type}'
                return result
            
            if result['image']:
                result['success'] = True
            else:
                result['error'] = f'Could not generate structure from {input_type}'
                
        except Exception as e:
            result['error'] = str(e)
            logging.error(f"Error in generate_structure_with_properties: {e}")
        
        return result

# Global instance
chemical_structure_generator = ChemicalStructureGenerator()
