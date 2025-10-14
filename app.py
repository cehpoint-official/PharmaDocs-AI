# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
migrate = Migrate(app, db)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pharmadocs.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import routes - renamed to app_routes to avoid conflict with installed routes package
from app_routes import auth, dashboard, documents, equipments, admin, company, user

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(company.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(documents.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(equipments.bp)
app.register_blueprint(user.bp)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Root route
@app.route('/')
def index():
    return auth.index()
