# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from database import create_app, db
import json

# Create the app
app = create_app()

# Import routes - renamed to app_routes to avoid conflict with installed routes package
from app_routes import auth, dashboard, documents, equipments, admin, company, user, amv_routes, validation_routes

# Import the functions from amv_routes
from app_routes.amv_routes import get_amv_documents_count, get_amv_verification_count

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(company.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(documents.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(equipments.bp)
app.register_blueprint(user.bp)
app.register_blueprint(amv_routes.amv_bp)
app.register_blueprint(validation_routes.validation_bp)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Register context processor on the main app (not blueprint)
@app.context_processor
def utility_processor():
    return {
        'get_amv_documents_count': get_amv_documents_count,
        'get_amv_verification_count': get_amv_verification_count
    }


@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    if not value:
        return {}
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}

# Root route
@app.route('/')
def index():
    return auth.index()