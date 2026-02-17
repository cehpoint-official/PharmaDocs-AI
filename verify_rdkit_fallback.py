
import sys
import os

# Add the current directory to sys.path to import services
sys.path.append(os.getcwd())

from services.chemical_structure_service import chemical_structure_generator

def test_fallback():
    print(f"RDKIT_AVAILABLE: {chemical_structure_generator.available}")
    
    # Test generation from SMILES (even if RDKit is missing)
    result = chemical_structure_generator.generate_structure_with_properties(
        "C1=CC=C(C=C1)C(=O)O", 
        input_type='smiles'
    )
    
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error')}")
    
    if result['image']:
        # Save the placeholder image to verify
        output_file = "test_placeholder.png"
        with open(output_file, "wb") as f:
            f.write(result['image'].getvalue())
        print(f"Placeholder image saved to {output_file}")
        return True
    else:
        print("Failed to generate even a placeholder image.")
        return False

if __name__ == "__main__":
    test_fallback()
