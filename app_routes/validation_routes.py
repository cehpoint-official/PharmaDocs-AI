from flask import Blueprint, render_template, request, jsonify, send_file
from datetime import datetime
from .pvr_templates import get_template
from .pdf_generator import generate_pvr_pdf
from flask import send_file
import json
import os

# Create Blueprint
validation_bp = Blueprint('validation', __name__, url_prefix='/validation')

@validation_bp.route('/protocol-generator')
def protocol_generator():
    """Main page for validation protocol generator"""
    return render_template('validation_protocol.html')

@validation_bp.route('/protocol/save', methods=['POST'])
def save_protocol():
    """Save validation protocol data"""
    try:
        data = request.json
        
        # Create folder for saving protocols
        upload_folder = 'uploads/validation_protocols'
        os.makedirs(upload_folder, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        protocol_num = data.get('protocolNo', 'UNKNOWN').replace('/', '_')
        filename = f"protocol_{protocol_num}_{timestamp}.json"
        filepath = os.path.join(upload_folder, filename)
        
        # Save data to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            'status': 'success',
            'message': 'Protocol saved successfully!',
            'filename': filename
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@validation_bp.route('/protocol/list')
def list_protocols():
    """List all saved protocols"""
    try:
        upload_folder = 'uploads/validation_protocols'
        
        if not os.path.exists(upload_folder):
            return jsonify({'status': 'success', 'protocols': []})
        
        protocols = []
        for filename in os.listdir(upload_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(upload_folder, filename)
                
                # Read protocol data
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    stat = os.stat(filepath)
                    
                    protocols.append({
                        'filename': filename,
                        'protocolNo': data.get('protocolNo', 'N/A'),
                        'productName': data.get('productName', 'N/A'),
                        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': f"{stat.st_size / 1024:.2f} KB"
                    })
                except:
                    # If file is corrupted, skip it
                    continue
        
        protocols.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'status': 'success', 'protocols': protocols})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@validation_bp.route('/protocol/load/<filename>')
def load_protocol(filename):
    """Load a specific protocol"""
    try:
        filepath = os.path.join('uploads/validation_protocols', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'status': 'error', 'message': 'Protocol not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify({'status': 'success', 'data': data})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@validation_bp.route('/protocol/delete/<filename>', methods=['DELETE'])
def delete_protocol(filename):
    """Delete a protocol"""
    try:
        filepath = os.path.join('uploads/validation_protocols', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'status': 'error', 'message': 'Protocol not found'}), 404
        
        os.remove(filepath)
        
        return jsonify({'status': 'success', 'message': 'Protocol deleted successfully'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    

@validation_bp.route('/report-generator')
def report_generator():
    """PVR Report Generator page"""
    return render_template('pvr_generator.html')

@validation_bp.route('/template/<template_type>')
def get_template_data(template_type):
    """Get template data by type"""
    template = get_template(template_type)
    if template:
        return jsonify({'status': 'success', 'template': template})
    return jsonify({'status': 'error', 'message': 'Template not found'}), 404

@validation_bp.route('/report/save', methods=['POST'])
def save_pvr_data():
    """Save PVR data with batch results"""
    try:
        data = request.json
        
        # Create folder
        upload_folder = 'uploads/pvr_reports'
        os.makedirs(upload_folder, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_name = data.get('productName', 'UNKNOWN').replace(' ', '_')
        filename = f"pvr_{product_name}_{timestamp}.json"
        filepath = os.path.join(upload_folder, filename)
        
        # Save
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return jsonify({
            'status': 'success',
            'message': 'PVR data saved successfully!',
            'filename': filename
        })
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@validation_bp.route('/report/generate-pdf', methods=['POST'])
def generate_pvr_pdf_route():
    """Generate PDF from PVR data"""
    try:
        print("=" * 50)
        print("PDF GENERATION STARTED")
        print("=" * 50)
        
        data = request.json
        print(f"Received data for product: {data.get('productName', 'UNKNOWN')}")
        
        # Check if pdf_generator module exists
        try:
            from .pdf_generator import generate_pvr_pdf
            print("✅ pdf_generator module imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import pdf_generator: {e}")
            return jsonify({'status': 'error', 'message': f'Import error: {str(e)}'}), 500
        
        print("Generating PDF...")
        pdf_path = generate_pvr_pdf(data)
        print(f"✅ PDF generated at: {pdf_path}")
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found at: {pdf_path}")
            return jsonify({'status': 'error', 'message': 'PDF file not created'}), 500
        
        print(f"PDF file size: {os.path.getsize(pdf_path)} bytes")
        print("Sending PDF to browser...")
        
        # Send file to user
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=os.path.basename(pdf_path)
        )
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500