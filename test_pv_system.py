"""
Test Script for PV System - Complete Workflow Test
Tests: PVP Upload → Extraction → PVR Generation
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from models import (
    PVP_Template, PVP_Equipment, PVP_Material, PVP_Extracted_Stage,
    PVP_Criteria, PVR_Report, PVR_Data, User
)
from services.enhanced_pvp_extraction_service import EnhancedPVPExtractor
from services.comprehensive_pvr_generator import ComprehensivePVRGenerator
from services.comprehensive_pvr_word_generator import ComprehensivePVRWordGenerator

def test_complete_workflow():
    """Test complete PV workflow"""
    
    print("\n" + "="*80)
    print("🧪 TESTING COMPLETE PV SYSTEM WORKFLOW")
    print("="*80 + "\n")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Step 1: Check if test user exists
            print("📌 Step 1: Setting up test user...")
            test_user = User.query.filter_by(email='test@pharmadocs.com').first()
            if not test_user:
                print("⚠️  No test user found. Creating one...")
                test_user = User(
                    firebase_uid='test_user_123',
                    email='test@pharmadocs.com',
                    name='Test User',
                    is_admin=False
                )
                test_user.set_password('test123')
                db.session.add(test_user)
                db.session.commit()
                print("✅ Test user created")
            else:
                print(f"✅ Found test user: {test_user.name}")
            
            # Step 2: Check for PVP file
            print("\n📌 Step 2: Checking for PVP file...")
            pvp_file = r"C:\Users\Admin\OneDrive\Desktop\Fluorouracil injection 50mg per ml Process Validation Protocol.pdf"
            
            if not os.path.exists(pvp_file):
                print(f"❌ PVP file not found at: {pvp_file}")
                print("Please provide the correct path to your PVP PDF file.")
                return
            
            print(f"✅ Found PVP file: {pvp_file}")
            
            # Step 3: Extract data from PVP
            print("\n📌 Step 3: Extracting data from PVP...")
            extractor = EnhancedPVPExtractor(pvp_file)
            extracted_data = extractor.extract_all()
            
            print(f"✅ Extraction complete!")
            print(f"   - Product: {extracted_data['product_info'].get('product_name', 'N/A')}")
            print(f"   - Type: {extracted_data['product_type']}")
            print(f"   - Equipment: {len(extracted_data.get('equipment', []))} items")
            print(f"   - Materials: {len(extracted_data.get('materials', []))} items")
            print(f"   - Stages: {len(extracted_data.get('stages', []))} stages")
            print(f"   - Test Criteria: {len(extracted_data.get('test_criteria', []))} tests")
            
            # Step 4: Save to database
            print("\n📌 Step 4: Saving to database...")
            
            product_name = extracted_data['product_info'].get('product_name', 'Test Product')
            product_type = extracted_data['product_type']
            batch_size = extracted_data['product_info'].get('batch_size', '10000 tablets')
            
            pvp_template = PVP_Template(
                product_name=product_name,
                product_type=product_type,
                batch_size=batch_size,
                filepath=pvp_file,
                user_id=test_user.id
            )
            db.session.add(pvp_template)
            db.session.flush()
            
            # Save equipment
            for eq_data in extracted_data.get('equipment', []):
                equipment = PVP_Equipment(
                    pvp_template_id=pvp_template.id,
                    equipment_name=eq_data.get('equipment_name', ''),
                    equipment_id=eq_data.get('equipment_id', ''),
                    location=eq_data.get('location', ''),
                    calibration_status=eq_data.get('calibration_status', 'Valid')
                )
                db.session.add(equipment)
            
            # Save materials
            for mat_data in extracted_data.get('materials', []):
                material = PVP_Material(
                    pvp_template_id=pvp_template.id,
                    material_type=mat_data.get('material_type', 'Excipient'),
                    material_name=mat_data.get('material_name', ''),
                    specification=mat_data.get('specification', ''),
                    quantity=mat_data.get('quantity', '')
                )
                db.session.add(material)
            
            # Save stages
            for stage_data in extracted_data.get('stages', []):
                stage = PVP_Extracted_Stage(
                    pvp_template_id=pvp_template.id,
                    stage_number=stage_data.get('stage_number', 0),
                    stage_name=stage_data.get('stage_name', ''),
                    equipment_used=stage_data.get('equipment_used', ''),
                    specific_parameters=stage_data.get('parameters', ''),
                    acceptance_criteria=stage_data.get('acceptance_criteria', '')
                )
                db.session.add(stage)
            
            # Save test criteria
            for crit_data in extracted_data.get('test_criteria', []):
                criteria = PVP_Criteria(
                    pvp_template_id=pvp_template.id,
                    test_id=crit_data.get('test_id', ''),
                    test_name=crit_data.get('test_name', ''),
                    acceptance_criteria=crit_data.get('acceptance_criteria', '')
                )
                db.session.add(criteria)
            
            db.session.commit()
            print(f"✅ Data saved to database (PVP Template ID: {pvp_template.id})")
            
            # Step 5: Create PVR Report with sample batch data
            print("\n📌 Step 5: Creating PVR Report with sample batches...")
            
            pvr_report = PVR_Report(
                pvp_template_id=pvp_template.id,
                user_id=test_user.id,
                status='Generated'
            )
            db.session.add(pvr_report)
            db.session.flush()
            
            # Create sample batch data (3 batches)
            batches = ['BATCH001', 'BATCH002', 'BATCH003']
            criteria_list = PVP_Criteria.query.filter_by(pvp_template_id=pvp_template.id).all()
            
            for batch_num in batches:
                for criterion in criteria_list:
                    # Generate sample test results
                    test_result = f"Pass - Within spec"
                    pvr_data = PVR_Data(
                        pvr_report_id=pvr_report.id,
                        batch_number=batch_num,
                        test_id=criterion.test_id,
                        test_result=test_result
                    )
                    db.session.add(pvr_data)
            
            db.session.commit()
            print(f"✅ PVR Report created (ID: {pvr_report.id}) with 3 batches")
            
            # Step 6: Generate PDF Report
            print("\n📌 Step 6: Generating comprehensive PDF report...")
            os.makedirs('uploads/pvr_reports', exist_ok=True)
            
            pdf_generator = ComprehensivePVRGenerator()
            pdf_path = pdf_generator.generate_comprehensive_pvr_pdf(
                pvr_report.id, 
                'uploads/pvr_reports'
            )
            
            print(f"✅ PDF generated: {pdf_path}")
            
            # Step 7: Generate Word Report
            print("\n📌 Step 7: Generating comprehensive Word report...")
            
            word_generator = ComprehensivePVRWordGenerator()
            word_path = word_generator.generate_comprehensive_pvr_word(
                pvr_report.id,
                'uploads/pvr_reports'
            )
            
            print(f"✅ Word document generated: {word_path}")
            
            # Update report paths
            pvr_report.pdf_filepath = pdf_path
            pvr_report.word_filepath = word_path
            pvr_report.conclusion = 'Pass'
            db.session.commit()
            
            # Final Summary
            print("\n" + "="*80)
            print("✅ COMPLETE PV SYSTEM TEST SUCCESSFUL!")
            print("="*80)
            print(f"\n📊 Summary:")
            print(f"   • PVP Template ID: {pvp_template.id}")
            print(f"   • Product: {product_name}")
            print(f"   • PVR Report ID: {pvr_report.id}")
            print(f"   • PDF Report: {pdf_path}")
            print(f"   • Word Report: {word_path}")
            print(f"\n🎉 Both reports should be 40-60 pages with comprehensive data!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_complete_workflow()