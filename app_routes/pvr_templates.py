"""
PVR Templates - Pre-defined data for different product types
"""

LIQUID_INJECTION_TEMPLATE = {
    'name': 'Liquid Injection Template',
    'dosage_form': 'Liquid Injection',
    
    # Equipment List (54 items from your PVP)
    'equipment': [
        {'sr': 1, 'name': 'Sampling & Dispensing Isolator', 'make': 'Klenzide', 'id': 'KPL/WH/013'},
        {'sr': 2, 'name': 'Reverse Laminar Air Flow', 'make': 'New Brehz Engineering Works', 'id': 'KPL/WH/005'},
        {'sr': 3, 'name': 'Weighing Balance', 'make': 'A & D company Limited', 'id': 'KPL/WH/006'},
        {'sr': 4, 'name': 'Vial washing machine', 'make': 'Kailas machine tools', 'id': 'KPL/CI/010'},
        {'sr': 5, 'name': 'Bung Washing Machine', 'make': 'Parth Engineering', 'id': 'KPL/CI/011'},
        {'sr': 6, 'name': 'Homogenizer', 'make': 'IKA', 'id': 'KPL/CI/017'},
        {'sr': 7, 'name': 'Pressure Vessel –I', 'make': '-', 'id': 'KPL/CI/018'},
        {'sr': 8, 'name': 'Pressure Vessel –II', 'make': '-', 'id': 'KPL/CI/019'},
        {'sr': 9, 'name': 'Pressure Vessel –III(Jacketed)', 'make': '-', 'id': 'KPL/CI/020'},
        {'sr': 10, 'name': 'Pressure Vessel –IV', 'make': '-', 'id': 'KPL/CI/021'},
        {'sr': 11, 'name': 'SS 316 Membrane Holder-I', 'make': '-', 'id': 'KPL/CI/022'},
        {'sr': 12, 'name': 'SS 316 Membrane Holder-II', 'make': '-', 'id': 'KPL/CI/023'},
        {'sr': 13, 'name': 'SS 316 Membrane Holder-III', 'make': '-', 'id': 'KPL/CI/024'},
        {'sr': 14, 'name': 'Automatic Vial Filling Machine', 'make': 'Keshav Pharmapack', 'id': 'KPL/CI/025'},
        {'sr': 15, 'name': 'Sealing machine', 'make': 'Keshav Pharmapack', 'id': 'KPL/CI/026'},
        {'sr': 16, 'name': 'Rotary Evaporator', 'make': 'IKA', 'id': 'KPL/CI/027'},
        {'sr': 17, 'name': 'Cold Room', 'make': 'Blue Star', 'id': 'KPL/CI/028'},
        {'sr': 18, 'name': 'Bubble point tester', 'make': 'Pall life science', 'id': 'KPL/CI/029'},
        {'sr': 19, 'name': 'Compounding Isolator', 'make': 'Klenzaids', 'id': 'KPL/CI/030'},
        {'sr': 20, 'name': 'Lyophilizer-I', 'make': 'Lyophilization System India', 'id': 'KPL/CI/031'},
        {'sr': 21, 'name': 'Lyophilizer-II', 'make': 'Lyophilization System India', 'id': 'KPL/CI/032'},
        {'sr': 22, 'name': 'Manufacturing Tank –I', 'make': 'Komal', 'id': 'KPL/CI/033'},
        {'sr': 23, 'name': 'Manufacturing Tank –II', 'make': 'Komal', 'id': 'KPL/CI/034'},
        {'sr': 24, 'name': 'Fogger', 'make': '-', 'id': 'KPL/CI/035'},
        {'sr': 25, 'name': 'Three bucket system', 'make': '-', 'id': 'KPL/CI/036'},
        {'sr': 26, 'name': 'Vacuum pump', 'make': '-', 'id': 'KPL/CI/039'},
        {'sr': 27, 'name': 'Closer Processing System Cum HPHV', 'make': 'Machin Fabrik', 'id': 'KPL/CI/040'},
        {'sr': 28, 'name': 'Dynamic Pass Box –I', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/041'},
        {'sr': 29, 'name': 'Dynamic Pass Box –II', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/042'},
        {'sr': 30, 'name': 'Dynamic Pass Box –III', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/043'},
        {'sr': 31, 'name': 'Dynamic Pass Box –IV', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/044'},
        {'sr': 32, 'name': 'Dynamic Pass Box –V', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/045'},
        {'sr': 33, 'name': 'Dynamic Pass Box –VI', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/046'},
        {'sr': 34, 'name': 'Dynamic Pass Box –VII', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/047'},
        {'sr': 35, 'name': 'Dynamic Pass Box –VIII', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/048'},
        {'sr': 36, 'name': 'Mobile Trolley- I', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/049'},
        {'sr': 37, 'name': 'Mobile Trolley-II', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/050'},
        {'sr': 38, 'name': 'Sterile garments cubicle -I', 'make': '-', 'id': 'KPL/CI/051'},
        {'sr': 39, 'name': 'Sterile garments cubicle -II', 'make': '-', 'id': 'KPL/CI/052'},
        {'sr': 40, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/053'},
        {'sr': 41, 'name': 'Particle Counter', 'make': 'Shreedhar instruments', 'id': 'KPL/CI/054'},
        {'sr': 42, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/055'},
        {'sr': 43, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/056'},
        {'sr': 44, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/057'},
        {'sr': 45, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/058'},
        {'sr': 46, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/059'},
        {'sr': 47, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/060'},
        {'sr': 48, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/061'},
        {'sr': 49, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/062'},
        {'sr': 50, 'name': 'SS Membrane holder', 'make': '-', 'id': 'KPL/CI/066'},
        {'sr': 51, 'name': 'Housing filter', 'make': '-', 'id': 'KPL/CI/067'},
        {'sr': 52, 'name': 'Table Mount LAF', 'make': '-', 'id': 'KPL/CI/074'},
        {'sr': 53, 'name': 'Laminar Air Flow', 'make': 'P.S. Air Technology', 'id': 'KPL/CI/075'},
        {'sr': 54, 'name': 'Dry Heat Sterilizer', 'make': 'Machine Fabrik', 'id': 'KPL/CI/076'},
        {'sr': 55, 'name': 'Purified Water system', 'make': 'Komal', 'id': 'KPL/ENG/014'},
        {'sr': 56, 'name': 'Water for Injection System', 'make': 'Komal', 'id': 'KPL/ENG/015'},
        {'sr': 57, 'name': 'Pure steam System', 'make': 'Komal', 'id': 'KPL/ENG/016'},
        {'sr': 58, 'name': 'Compressed Air System', 'make': 'Ingersoll Rand', 'id': 'KPL/ENG/001'},
        {'sr': 59, 'name': 'Nitrogen System', 'make': 'Allied Air and gas Engineers', 'id': 'KPL/ENG/007'},
        {'sr': 60, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/001'},
        {'sr': 61, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/004'},
        {'sr': 62, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/005'},
        {'sr': 63, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/006'},
        {'sr': 64, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/007'},
        {'sr': 65, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/008'},
        {'sr': 66, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/009'},
        {'sr': 67, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/010'},
        {'sr': 68, 'name': 'Air Handling Unit', 'make': 'ZECO', 'id': 'AHU/HAC02/CI/011'},
        {'sr': 69, 'name': 'HPLC', 'make': 'Shimadzu LC', 'id': 'KPL/QC/117'},
        {'sr': 70, 'name': 'HPLC', 'make': 'Shimadzu', 'id': 'KPL/QC/118'},
        {'sr': 71, 'name': 'Weighing Balance', 'make': 'Shimadzu', 'id': 'KPL/QC/054'},
    ],
    
    # Process Steps
    'process_steps': [
        'Take freshly collected Water for Injection in dry and cleaned sterile S.S. manufacturing tank and cool at temperature between 30°C - 40°C with continuous nitrogen purging throughout the compounding process.',
        'Transfer Disodium edetate in manufacturing tank with continuous stirring until a clear solution is obtained and check the clarity of the solution.',
        'Add Tromethamine in manufacturing tank with continuous stirring and clear the solution.',
        'Stir the solution for 20 minutes and check the complete dissolution and clarity of the solution.',
        'Add Fluorouracil in manufacturing tank and continue stirring to disperse it completely.',
        'Add Sodium Hydroxide slowly in manufacturing tank under continuous stirring and stir the solution to obtain clear solution.',
        'Check the pH of the solution between 8.5-9.1. If required, adjust the pH of solution with Sodium Hydroxide.',
        'Make up the final batch volume with Water for Injection.',
        'Send the sample to QC for chemical analysis. If results are within limits, proceed with further processing.'
    ],
    
    # Acceptance Criteria
    'acceptance_criteria': [
        {'parameter': 'pH', 'specification': '8.5 to 9.1'},
        {'parameter': 'Assay', 'specification': '90.0% to 110.0%'},
        {'parameter': 'Clarity and Appearance', 'specification': 'Clear, colourless solution'},
        {'parameter': 'Average Fill Volume', 'specification': 'NLT 20 ml'},
        {'parameter': 'Extractable Volume', 'specification': 'NLT 20 ml'},
        {'parameter': 'Sterility', 'specification': 'No growth should be observed'},
        {'parameter': 'Bacterial Endotoxins', 'specification': 'NMT 0.33 EU/mg'},
        {'parameter': 'Particulate Matter (10-25 μm)', 'specification': 'NMT 6000 particles'},
        {'parameter': 'Particulate Matter (≥25 μm)', 'specification': 'NMT 600 particles'},
        {'parameter': 'Filtration Time', 'specification': 'Within 15 minutes'},
        {'parameter': 'Container Content', 'specification': 'NLT 20 ml'},
    ]
}

# Template registry
TEMPLATES = {
    'liquid_injection': LIQUID_INJECTION_TEMPLATE,
    # Add more templates later
}

def get_template(template_type):
    """Get template by type"""
    return TEMPLATES.get(template_type, None)