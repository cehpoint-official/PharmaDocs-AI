# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.
import models
from database import create_app, db
import json
from flask import send_from_directory

# Create the app
app = create_app()

# Import routes - renamed to app_routes to avoid conflict with installed routes package
from app_routes import auth, dashboard, documents, equipments, admin, company, user, amv_routes, pv_routes, subscription_routes, razorpay_routes

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
app.register_blueprint(pv_routes.pv_routes)
app.register_blueprint(subscription_routes.bp)
app.register_blueprint(razorpay_routes.bp)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()


# Register context processor on the main app (not blueprint)
@app.context_processor
def utility_processor():
    from utils.subscription_middleware import inject_subscription_context
    context = {
        'get_amv_documents_count': get_amv_documents_count,
        'get_amv_verification_count': get_amv_verification_count
    }
    # Add subscription context
    subscription_context = inject_subscription_context()()
    context.update(subscription_context)
    return context


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

@app.template_filter('currency')
def currency_filter(value):
    """Format currency values"""
    try:
        return f"${value:.2f}"
    except (TypeError, ValueError):
        return f"${0:.2f}"

@app.template_filter('percentage')
def percentage_filter(value):
    """Format percentage values"""
    try:
        return f"{value:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"
@app.route('/google215dea7272f51f3b.html')
def google_verification():
    return send_from_directory('static', 'google215dea7272f51f3b.html')
# Root route
@app.route('/')
def index():
    return auth.index()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
