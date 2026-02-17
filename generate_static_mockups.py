
import os
import shutil
from flask import Flask, render_template, url_for
from datetime import datetime, timedelta

# Create a mock Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# Output directory
OUTPUT_DIR = 'static_mockups'

# Dummy Data Classes
class MockUser:
    def __init__(self, name="John Doe", email="john@example.com", role="admin", plan="premium"):
        self.name = name
        self.email = email
        self.is_admin = (role == 'admin')
        self.subscription_plan = plan
        self.subscription_expiry = datetime.now() + timedelta(days=30)
        self.id = 1

class MockDoc:
    def __init__(self, title, doc_type, status):
        self.title = title
        self.document_number = f"DOC-{datetime.now().strftime('%Y%m%d')}"
        self.document_type = doc_type
        self.status = status
        self.updated_at = datetime.now()
        self.id = 1

class MockCompany:
    def __init__(self, name):
        self.name = name
        self.address = "123 Pharma Way, Science City"
        self.logo_url = None

# Context Data
mock_user = MockUser()
mock_docs = [
    MockDoc("Paracetamol Process Validation", "Process Validation", "completed"),
    MockDoc("Metformin Assay Method", "AMV", "draft"),
    MockDoc("Stability Study - Batch 001", "Stability", "generated")
]
mock_companies = [MockCompany("Atlas Labs"), MockCompany("Zenith Pharma")]
mock_stats = {
    'total': 42,
    'amv': 15,
    'pv': 10,
    'stability': 12,
    'degradation': 3,
    'compatibility': 2
}
mock_usage = {'documents': {'used': 5}}
mock_limits = {'documents_per_month': 100}


def generate_mockups():
    # 1. Setup Output Directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    
    # Copy Static Assets
    if os.path.exists('static'):
        shutil.copytree('static', os.path.join(OUTPUT_DIR, 'static'))
        print(f"Copied static assets to {OUTPUT_DIR}/static")

    # 2. Context Injection
    with app.test_request_context():
        # Override url_for to point to local HTML files
        # We cheat a bit by injecting a custom context processor or just handling urls in templates
        # Since we can't easily override url_for globally without registering routes, 
        # we will rely on relative paths or replace them post-render if needed.
        # However, Flask's url_for usually returns absolute paths or root-relative. 
        # For a truly static local file view, we might need relative links. 
        # For now, we will assume root-relative is okay if serving via a simple http server, 
        # OR we try to make them relative.
        
        # Actually, let's just render the templates. Links might be broken (pointing to /login instead of login.html),
        # but the request was "templates gulake arekta folder er moddhe rakh" (keep templates in another folder).
        # To make them strictly "clickable" file-to-file, we'd need to replace /route with route.html.
        
        # Let's define the pages we want to render
        pages = [
            ('index.html', 'index.html', {}),
            ('dashboard.html', 'dashboard.html', {
                'user': mock_user, 
                'session': {'user_id': 1}, 
                'doc_stats': mock_stats,
                'recent_documents': mock_docs,
                'companies': mock_companies,
                'user_usage': mock_usage,
                'user_limits': mock_limits,
                'get_amv_documents_count': lambda x: 5,
                'get_amv_verification_count': lambda x: 2
            }),
            ('login.html', 'login.html', {}),
            ('register.html', 'register.html', {}),
            ('create_amv.html', 'create_amv.html', {
                'user': mock_user,
                'companies': mock_companies,
                'equipment_list': [
                    {'id': 1, 'name': 'HPLC System', 'code': 'HPLC-001', 'brand': 'Agilent'},
                    {'id': 2, 'name': 'UV-Vis Spectrometer', 'code': 'UV-002', 'brand': 'Shimadzu'}
                ],
                'glass_materials_list': [
                    {'id': 1, 'name': 'Volumetric Flask 100ml', 'characteristics': 'Class A'},
                    {'id': 2, 'name': 'Beaker 250ml', 'characteristics': 'Borosilicate'}
                ],
                'other_materials_list': [
                    {'id': 1, 'name': 'Filter Paper', 'characteristics': 'Whatman No. 1'},
                    {'id': 2, 'name': 'Syringe Filter', 'characteristics': '0.45 micron'}
                ],
                'reagents_list': [
                    {'id': 1, 'name': 'Methanol HPLC Grade', 'batch': 'MT001', 'expiry_date': '2025-12-31'},
                    {'id': 2, 'name': 'Acetonitrile', 'batch': 'AC002', 'expiry_date': '2025-10-30'}
                ],
                'references_list': [
                    {'id': 1, 'standard_name': 'Paracetamol WS', 'potency': '99.8'},
                    {'id': 2, 'standard_name': 'Ibuprofen RS', 'potency': '100.1'}
                ],
                'config': {'DEBUG': True}
            }),
            ('amv_verification_protocol.html', 'amv_verification_protocol.html', {
                'user': mock_user,
                'companies': mock_companies,
                'equipment_list': [
                    {'id': 1, 'name': 'HPLC System', 'code': 'HPLC-001', 'brand': 'Agilent'},
                    {'id': 2, 'name': 'UV-Vis Spectrometer', 'code': 'UV-002', 'brand': 'Shimadzu'}
                ],
                'glass_materials_list': [
                    {'id': 1, 'name': 'Volumetric Flask 100ml', 'characteristics': 'Class A'},
                    {'id': 2, 'name': 'Beaker 250ml', 'characteristics': 'Borosilicate'}
                ],
                'other_materials_list': [
                    {'id': 1, 'name': 'Filter Paper', 'characteristics': 'Whatman No. 1'},
                    {'id': 2, 'name': 'Syringe Filter', 'characteristics': '0.45 micron'}
                ],
                'reagents_list': [
                    {'id': 1, 'name': 'Methanol HPLC Grade', 'batch': 'MT001', 'expiry_date': '2025-12-31'},
                    {'id': 2, 'name': 'Acetonitrile', 'batch': 'AC002', 'expiry_date': '2025-10-30'}
                ],
                'references_list': [
                    {'id': 1, 'standard_name': 'Paracetamol WS', 'potency': '99.8'},
                    {'id': 2, 'standard_name': 'Ibuprofen RS', 'potency': '100.1'}
                ],
                'config': {'DEBUG': True}
            }),
             # Add more as needed
        ]

        # Global Context Processor replacement
        @app.context_processor
        def inject_globals():
            return {
                'user': mock_user,
                'get_flashed_messages': lambda **kwargs: [],
                'url_for': mock_url_for # Custom url_for
            }

        for template_name, output_name, context in pages:
            try:
                # Render
                html = render_template(template_name, **context)
                
                # Post-processing to fix common links if feasible
                # html = html.replace('href="/"', 'href="index.html"')
                # html = html.replace('href="/login"', 'href="login.html"')
                
                output_path = os.path.join(OUTPUT_DIR, output_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"Generated: {output_name}")
            except Exception as e:
                print(f"Failed to render {template_name}: {e}")

def mock_url_for(endpoint, **values):
    # Map common endpoints to HTML files
    mapping = {
        'auth.index': 'index.html',
        'auth.login': 'login.html',
        'auth.register': 'register.html',
        'dashboard.user_dashboard': 'dashboard.html',
        'amv_bp.create_amv_form': 'create_amv.html',
        'static':  lambda: f"static/{values.get('filename', '')}"
    }
    
    if endpoint == 'static':
        return f"static/{values.get('filename', '')}"
        
    if endpoint in mapping:
        return mapping[endpoint]
        
    # Default fallback
    return f"#{endpoint}"

if __name__ == "__main__":
    generate_mockups()
