from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import pdfplumber
import re
import os

# Update these imports to match your project
from database import db
from models import PVP_Template, PVP_Criteria
# from flask_login import current_user, login_required # Add auth later

pv_bp = Blueprint('pv_bp', __name__)

# --- DEFINE YOUR UPLOAD FOLDER ---
# Make sure this 'uploads' folder exists in your project root
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def simple_ai_parser(pdf_path):
    """
    This is our 'AI' parser. It reads the PDF text and uses
    regular expressions (regex) to find specific rules.
    """
    extracted_rules = []
    full_text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Use x_tolerance=2 to keep text in paragraphs
                full_text += page.extract_text(x_tolerance=2) or "" 
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return []

    # --- AI Rule 1: Find Bulk pH ---
    # Looks for "Bulk Manufacturing" then "pH" then "8.5 to 9.1"
    ph_match = re.search(
        r'Bulk Manufacturing.*?pH.*?(\d\.\d\s*to\s*\d\.\d)', 
        full_text, 
        re.DOTALL | re.IGNORECASE
    )
    if ph_match:
        extracted_rules.append({
            'test_id': 'bulk_ph',
            'test_name': 'Bulk Manufacturing pH',
            'acceptance_criteria': ph_match.group(1).replace('\n', ' ')
        })

    # --- AI Rule 2: Find Bulk Assay ---
    assay_match = re.search(
        r'Bulk Manufacturing.*?Assay.*?(\d{2,3}\.\d\s*%\s*to\s*\d{2,3}\.\d\s*%)', 
        full_text, 
        re.DOTALL | re.IGNORECASE
    )
    if assay_match:
         extracted_rules.append({
            'test_id': 'bulk_assay',
            'test_name': 'Bulk Manufacturing Assay',
            'acceptance_criteria': assay_match.group(1).replace('\n', ' ')
        })

    # --- AI Rule 3: Find Final pH ---
    final_ph_match = re.search(
        r'Quality Control Attributes.*?pH.*?(\d\.\d\s*to\s*\d\.\d)', 
        full_text, 
        re.DOTALL | re.IGNORECASE
    )
    if final_ph_match:
         extracted_rules.append({
            'test_id': 'final_ph',
            'test_name': 'Final Product pH',
            'acceptance_criteria': final_ph_match.group(1).replace('\n', ' ')
        })

    return extracted_rules


@pv_bp.route('/pv/upload-template', methods=['GET', 'POST'])
# @login_required # Add this later
def upload_pvp_template():
    if request.method == 'POST':
        pvp_file = request.files.get('pvp_file')
        template_name = request.form.get('template_name')

        if not pvp_file or not template_name:
            flash('Template Name and File are required.', 'danger')
            return redirect(request.url)

        # Check for duplicate template name
        existing = PVP_Template.query.filter_by(template_name=template_name).first()
        if existing:
            flash('A template with this name already exists.', 'danger')
            return redirect(request.url)

        # Save the file
        filename = secure_filename(pvp_file.filename)
        upload_path = os.path.join(UPLOAD_FOLDER, filename)
        pvp_file.save(upload_path)

        # Save to DB
        new_template = PVP_Template(
            template_name=template_name,
            original_filepath=upload_path
            # user_id=current_user.id # Add this
        )
        db.session.add(new_template)
        db.session.commit() # Commit to get the new_template.id

        # --- Run the AI Parser ---
        extracted_rules = simple_ai_parser(upload_path)

        # --- Save extracted rules to the DB ---
        for rule in extracted_rules:
            new_criterion = PVP_Criteria(
                template=new_template, # Link to the template
                test_id=rule['test_id'],
                test_name=rule['test_name'],
                acceptance_criteria=rule['acceptance_criteria']
            )
            db.session.add(new_criterion)

        db.session.commit()

        flash(f'Template "{template_name}" created. AI found {len(extracted_rules)} rules.', 'success')
        return redirect(url_for('dashboard.bp.dashboard')) # Change 'dashboard.bp.dashboard' to your main dashboard route

    return render_template('upload_pvp.html')