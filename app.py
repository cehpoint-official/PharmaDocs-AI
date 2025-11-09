# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.
import models
from database import create_app, db

# Create the app
app = create_app()

# Import routes - renamed to app_routes to avoid conflict with installed routes package
from app_routes import auth, dashboard, documents, equipments, admin, company, user, amv_routes, pv_routes

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

# Root route
@app.route('/')
def index():
    return auth.index()
