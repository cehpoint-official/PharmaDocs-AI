# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import json
from datetime import datetime
from database import db
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List, Optional

class User(db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    subscription_plan: Mapped[str] = mapped_column(String(50), default='free', nullable=False)
    subscription_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), default='active', nullable=False)  # active, canceled, past_due, incomplete
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    documents_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # Per month limit

    # Relationships
    companies: Mapped[List["Company"]] = relationship("Company", back_populates="user")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="user")
    activity_logs: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="user")
    pvp_templates: Mapped[List["PVP_Template"]] = relationship("PVP_Template", back_populates="user")
    pvr_reports: Mapped[List["PVR_Report"]] = relationship("PVR_Report", back_populates="user")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_plan_limits(self):
        """Get limits for current subscription plan"""
        limits = {
            'free': {
                'documents_per_month': 5,
                'storage_mb': 100,
                'api_requests_per_day': 10,
                'features': ['basic_reports', 'email_support']
            },
            'basic': {
                'documents_per_month': 50,
                'storage_mb': 1000,
                'api_requests_per_day': 100,
                'features': ['basic_reports', 'advanced_reports', 'email_support', 'priority_support']
            },
            'premium': {
                'documents_per_month': -1,  # Unlimited
                'storage_mb': 10000,
                'api_requests_per_day': 1000,
                'features': ['all_reports', 'custom_templates', 'priority_support', 'phone_support', 'api_access']
            }
        }
        return limits.get(self.subscription_plan, limits['free'])

    def can_create_document(self):
        """Check if user can create more documents this month"""
        if self.subscription_plan == 'premium':
            return True
        
        from datetime import datetime
        from sqlalchemy import extract
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        monthly_docs = Document.query.filter(
            Document.user_id == self.id,
            extract('month', Document.created_at) == current_month,
            extract('year', Document.created_at) == current_year
        ).count()
        
        limits = self.get_plan_limits()
        return monthly_docs < limits['documents_per_month']

    def is_subscription_active(self):
        """Check if subscription is active and not expired"""
        if self.subscription_plan == 'free':
            return True
        
        if self.subscription_status != 'active':
            return False
            
        if self.subscription_expiry and self.subscription_expiry < datetime.now():
            return False
            
        return True

class Company(db.Model):
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    glass_materials: Mapped[str] = mapped_column(Text, nullable=True) # JSON string for glass materials

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="companies")
    sub_brands: Mapped[List["SubBrand"]] = relationship("SubBrand", back_populates="company")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="company")
    equipment_list: Mapped[List["Equipment"]] = relationship("Equipment", back_populates="company")
    glass_materials_list: Mapped[List["GlassMaterial"]] = relationship("GlassMaterial", back_populates="company")
    other_materials_list: Mapped[List["OtherMaterial"]] = relationship("OtherMaterial", back_populates="company")
    reagents_list: Mapped[List["Reagent"]] = relationship("Reagent", back_populates="company")
    reference_products_list: Mapped[List["ReferenceProduct"]] = relationship("ReferenceProduct", back_populates="company")

class SubBrand(db.Model):
    __tablename__ = 'sub_brands'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    reviewer_name: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewer_designation: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewer_signature_url: Mapped[str] = mapped_column(String(500), nullable=True)
    checker_name: Mapped[str] = mapped_column(String(100), nullable=True)
    checker_designation: Mapped[str] = mapped_column(String(100), nullable=True)
    checker_signature_url: Mapped[str] = mapped_column(String(500), nullable=True)
    analyst_name: Mapped[str] = mapped_column(String(100), nullable=True)
    analyst_designation: Mapped[str] = mapped_column(String(100), nullable=True)
    analyst_signature_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="sub_brands")

class Document(db.Model):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AMV, PV, Stability, etc.
    document_number: Mapped[str] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='draft')  # draft, generated, completed
    stp_file_url: Mapped[str] = mapped_column(String(500), nullable=True)
    raw_data_url: Mapped[str] = mapped_column(String(500), nullable=True)
    method_analysis_file_url: Mapped[str] = mapped_column(String(500), nullable=True)  # Added for AMV
    generated_doc_url: Mapped[str] = mapped_column(String(500), nullable=True)
    generated_excel_url: Mapped[str] = mapped_column(String(500), nullable=True)
    document_metadata: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string for additional data
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="documents")
    company: Mapped["Company"] = relationship("Company", back_populates="documents")
    amv_details: Mapped["AMVDocument"] = relationship("AMVDocument", back_populates="document", uselist=False)
    amv_verification_details: Mapped["AMVVerificationDocument"] = relationship("AMVVerificationDocument", back_populates="document", uselist=False)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="activity_logs")

class Equipment(db.Model):
    __tablename__ = 'equipment'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    company_provided_id: Mapped[str] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., HPLC, GC, etc.
    code: Mapped[str] = mapped_column(String(100), nullable=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=True)
    make: Mapped[str] = mapped_column(String(100), nullable=True)
    verification_frequency: Mapped[str] = mapped_column(String(200), nullable=True)
    
    # CHANGED: DateTime to String for all calibration fields
    last_calibration: Mapped[str] = mapped_column(String(50), nullable=True)  # Changed from DateTime
    next_calibration: Mapped[str] = mapped_column(String(50), nullable=True)  # Changed from DateTime
    calibration_date: Mapped[str] = mapped_column(String(50), nullable=True)  # Changed from DateTime
    next_calibration_due: Mapped[str] = mapped_column(String(50), nullable=True)  # Changed from DateTime
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="equipment_list")

    @property
    def is_calibrated(self):
        """Check if equipment is calibrated - updated for string dates"""
        if self.next_calibration_due:
            try:
                # Parse string date to datetime for comparison
                due_date = datetime.strptime(self.next_calibration_due, '%Y-%m-%d')
                return due_date >= datetime.now()
            except (ValueError, TypeError):
                # If date format is invalid, return False
                return False
        return False

    # Helper methods to work with dates
    def get_last_calibration_date(self):
        """Get last_calibration as datetime object"""
        if self.last_calibration:
            try:
                return datetime.strptime(self.last_calibration, '%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        return None

    def get_next_calibration_date(self):
        """Get next_calibration as datetime object"""
        if self.next_calibration:
            try:
                return datetime.strptime(self.next_calibration, '%Y-%m-%d')
            except (ValueError, TypeError):
                return None
        return None

    def set_last_calibration_date(self, date_obj):
        """Set last_calibration from datetime object or string"""
        if isinstance(date_obj, datetime):
            self.last_calibration = date_obj.strftime('%Y-%m-%d')
        else:
            self.last_calibration = date_obj

    def set_next_calibration_date(self, date_obj):
        """Set next_calibration from datetime object or string"""
        if isinstance(date_obj, datetime):
            self.next_calibration = date_obj.strftime('%Y-%m-%d')
        else:
            self.next_calibration = date_obj

class GlassMaterial(db.Model):
    __tablename__ = 'glass_materials'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    characteristics: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="glass_materials_list")

class OtherMaterial(db.Model):
    __tablename__ = 'other_materials'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    characteristics: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="other_materials_list")

class Reagent(db.Model):
    __tablename__ = 'reagents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    batch: Mapped[str] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="reagents_list")

class ReferenceProduct(db.Model):
    __tablename__ = 'reference_products'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey('companies.id'), nullable=False)
    standard_type: Mapped[str] = mapped_column(String(100), nullable=True)
    standard_name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=True)
    potency: Mapped[str] = mapped_column(String(50), nullable=True)
    due_date: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="reference_products_list")

class AMVDocument(db.Model):
    """Specific model for AMV documents with detailed parameters"""
    __tablename__ = 'amv_documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey('documents.id'), nullable=False)
    
    # Basic Information
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    label_claim: Mapped[str] = mapped_column(String(100), nullable=False)
    active_ingredient: Mapped[str] = mapped_column(String(200), nullable=False)
    strength: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Instrument Information
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)  # uv, hplc, gc, titration, ir, aas
    
    # Instrument-specific Parameters (stored as JSON)
    instrument_params: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Validation Parameters
    validation_params: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of selected parameters
    parameters_to_validate: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of parameters to validate
    
    # File References
    stp_filename: Mapped[str] = mapped_column(String(500), nullable=True)
    method_filename: Mapped[str] = mapped_column(String(500), nullable=True)
    raw_data_filename: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Status and Metadata
    validation_status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, in_progress, completed, failed
    protocol_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    report_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="amv_details")

    def get_instrument_params(self):
        """Get instrument parameters as dictionary"""
        if self.instrument_params:
            try:
                return json.loads(self.instrument_params)
            except:
                return {}
        return {}

    def set_instrument_params(self, params):
        """Set instrument parameters from dictionary"""
        self.instrument_params = json.dumps(params)

    def get_validation_params(self):
        """Get validation parameters as list"""
        if self.validation_params:
            try:
                return json.loads(self.validation_params)
            except:
                return []
        return []

    def set_validation_params(self, params):
        """Set validation parameters from list"""
        self.validation_params = json.dumps(params)

    def get_parameters_to_validate(self):
        """Get parameters to validate as list"""
        if self.parameters_to_validate:
            try:
                return json.loads(self.parameters_to_validate)
            except:
                return []
        return []

    def set_parameters_to_validate(self, params):
        """Set parameters to validate from list"""
        self.parameters_to_validate = json.dumps(params)

# --- PROCESS VALIDATION (PV) MODULE MODELS ---
# PROCESS VALIDATION STAGE TEMPLATES (Reference Data)

class PV_Stage_Template(db.Model):
    """Reference template for validation stages by product type"""
    __tablename__ = 'pv_stage_templates'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_description: Mapped[str] = mapped_column(Text, nullable=True)
    key_parameters: Mapped[str] = mapped_column(Text, nullable=True)
    validation_objective: Mapped[str] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f'<PV_Stage_Template {self.product_type} - Stage {self.stage_number}: {self.stage_name}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'product_type': self.product_type,
            'stage_number': self.stage_number,
            'stage_name': self.stage_name,
            'activity_description': self.activity_description,
            'key_parameters': self.key_parameters,
            'validation_objective': self.validation_objective,
            'is_optional': self.is_optional
        }


# PROCESS VALIDATION MODELS (User Data)

class PVP_Template(db.Model):
    """
    Stores the master PVP file (the 'template' uploaded by the user).
    """
    __tablename__ = 'pvp_template'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filepath: Mapped[str] = mapped_column(String(300), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Extracted product information
    product_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    product_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    batch_size: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Schema Mismatch Fix: Commenting out fields not present in SQLite DB
    # company_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # company_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # company_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # company_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # company_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # company_pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pvp_templates")
    criteria: Mapped[List["PVP_Criteria"]] = relationship("PVP_Criteria", back_populates="template", cascade="all, delete-orphan")
    reports: Mapped[List["PVR_Report"]] = relationship("PVR_Report", back_populates="template", cascade="all, delete-orphan")
    equipment_list: Mapped[List["PVP_Equipment"]] = relationship("PVP_Equipment", back_populates="pvp_template", cascade="all, delete-orphan")
    materials_list: Mapped[List["PVP_Material"]] = relationship("PVP_Material", back_populates="pvp_template", cascade="all, delete-orphan")
    extracted_stages: Mapped[List["PVP_Extracted_Stage"]] = relationship("PVP_Extracted_Stage", back_populates="pvp_template", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<PVP_Template {self.template_name}>'

class PVP_Criteria(db.Model):
    """
    Stores the 'rules' (acceptance criteria) extracted from the PVP 
    by our AI parser. This is the AI's 'memory'.
    """
    __tablename__ = 'pvp_criteria'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvp_template_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_template.id'), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'bulk_ph'
    test_name: Mapped[str] = mapped_column(String(200), nullable=True)  # e.g., 'Bulk Manufacturing pH'
    acceptance_criteria: Mapped[str] = mapped_column(String(300), nullable=True)  # e.g., '8.5 to 9.1'

    # Relationship
    template: Mapped["PVP_Template"] = relationship("PVP_Template", back_populates="criteria")

    def __repr__(self):
        return f'<PVP_Criteria {self.test_name}>'
    
# ENHANCED PVP DATA MODELS (Equipment, Materials, Stages)


class PVP_Equipment(db.Model):
    """Equipment used in validation process"""
    __tablename__ = 'pvp_equipment'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvp_template_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_template.id'), nullable=False)
    equipment_name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    calibration_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    calibration_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationship
    pvp_template = relationship('PVP_Template', back_populates='equipment_list')
    
    def __repr__(self):
        return f'<PVP_Equipment {self.equipment_name}>'


class PVP_Material(db.Model):
    """Materials (API, Excipients, Packaging) used in validation"""
    __tablename__ = 'pvp_materials'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvp_template_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_template.id'), nullable=False)
    material_type: Mapped[str] = mapped_column(String(50), nullable=False)  # API, Excipient, Packaging
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specification: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Relationship
    pvp_template = relationship('PVP_Template', back_populates='materials_list')
    
    def __repr__(self):
        return f'<PVP_Material {self.material_name}>'


class PVP_Extracted_Stage(db.Model):
    """Stages extracted from PVP, linked to stage templates"""
    __tablename__ = 'pvp_extracted_stages'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvp_template_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_template.id'), nullable=False)
    stage_template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('pv_stage_templates.id'), nullable=True)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    specific_parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    acceptance_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_methods: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    pvp_template = relationship('PVP_Template', back_populates='extracted_stages')
    stage_template = relationship('PV_Stage_Template')
    batch_results = relationship('PVR_Stage_Result', back_populates='extracted_stage', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PVP_Extracted_Stage {self.stage_name}>'


class PVR_Stage_Result(db.Model):
    """Batch results for each validated stage"""
    __tablename__ = 'pvr_stage_results'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvr_report_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvr_report.id'), nullable=False)
    extracted_stage_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_extracted_stages.id'), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    actual_value: Mapped[str] = mapped_column(String(200), nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(String(200), nullable=False)
    result_status: Mapped[str] = mapped_column(String(20), nullable=False)  # Pass/Fail
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    pvr_report = relationship('PVR_Report', back_populates='stage_results')
    extracted_stage = relationship('PVP_Extracted_Stage', back_populates='batch_results')
    
    def __repr__(self):
        return f'<PVR_Stage_Result Batch:{self.batch_number} - {self.parameter_name}>'

class PVR_Report(db.Model):
    """
    Tracks the final PVR documents we generate.
    """
    __tablename__ = 'pvr_report'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvp_template_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvp_template.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    pdf_filepath: Mapped[str] = mapped_column(String(300), nullable=True)
    word_filepath: Mapped[str] = mapped_column(String(300), nullable=True)  
    status: Mapped[str] = mapped_column(String(50), default='Draft')
    
    # Additional PVR metadata
    protocol_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    validation_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Prospective/Concurrent/Retrospective
    manufacturing_site: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    prepared_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    checked_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    template: Mapped["PVP_Template"] = relationship("PVP_Template", back_populates="reports")
    user: Mapped["User"] = relationship("User", back_populates="pvr_reports")
    data: Mapped[List["PVR_Data"]] = relationship("PVR_Data", back_populates="report", cascade="all, delete-orphan")
    stage_results: Mapped[List["PVR_Stage_Result"]] = relationship("PVR_Stage_Result", back_populates="pvr_report", cascade="all, delete-orphan")

class PVR_Data(db.Model):
    """
    Stores the actual batch data (the 'answers') for a report.
    """
    __tablename__ = 'pvr_data'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pvr_report_id: Mapped[int] = mapped_column(Integer, ForeignKey('pvr_report.id'), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturing_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Manufacturing date for batch
    batch_size: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Batch-specific size
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'bulk_ph'
    test_result: Mapped[str] = mapped_column(String(200), nullable=True)  # e.g., '9.024'

    # Relationship
    report: Mapped["PVR_Report"] = relationship("PVR_Report", back_populates="data")

class AMVVerificationDocument(db.Model):
    """Specific model for AMV Verification documents with detailed parameters"""
    __tablename__ = 'amv_verification_documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey('documents.id'), nullable=False)
    
    # Basic Information
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active_ingredient: Mapped[str] = mapped_column(String(200), nullable=False)
    label_claim: Mapped[str] = mapped_column(String(100), nullable=False)
    test_method: Mapped[str] = mapped_column(String(50), nullable=False)  # HPLC, UV, Titration, etc.
    
    # Company Information
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_location: Mapped[str] = mapped_column(String(500), nullable=True)
    protocol_number: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Method Parameters (stored as JSON)
    method_parameters: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Equipment and Materials (stored as JSON)
    selected_equipment: Mapped[str] = mapped_column(Text, nullable=True)
    selected_glass_materials: Mapped[str] = mapped_column(Text, nullable=True)
    selected_reagents: Mapped[str] = mapped_column(Text, nullable=True)
    selected_reference: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Validation Parameters
    validation_parameters: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    
    # Team Information
    prepared_by_name: Mapped[str] = mapped_column(String(100), nullable=True)
    prepared_by_dept: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewed_by_name: Mapped[str] = mapped_column(String(100), nullable=True)
    reviewed_by_dept: Mapped[str] = mapped_column(String(100), nullable=True)
    approved_by_name: Mapped[str] = mapped_column(String(100), nullable=True)
    approved_by_dept: Mapped[str] = mapped_column(String(100), nullable=True)
    authorized_by_name: Mapped[str] = mapped_column(String(100), nullable=True)
    authorized_by_dept: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Technical Parameters
    specification_range: Mapped[str] = mapped_column(String(100), nullable=True)
    wavelength: Mapped[str] = mapped_column(String(50), nullable=True)
    molecular_weight: Mapped[str] = mapped_column(String(50), nullable=True)
    molecular_formula: Mapped[str] = mapped_column(String(100), nullable=True)
    smiles: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Status and Metadata
    verification_status: Mapped[str] = mapped_column(String(20), default='draft')  # draft, in_progress, completed
    protocol_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    report_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())

    # Relationships - FIXED: Use back_populates instead of backref
    document: Mapped["Document"] = relationship("Document", back_populates="amv_verification_details")

    def get_method_parameters(self):
        """Get method parameters as dictionary"""
        if self.method_parameters:
            try:
                return json.loads(self.method_parameters)
            except:
                return {}
        return {}

    def set_method_parameters(self, params):
        """Set method parameters from dictionary"""
        self.method_parameters = json.dumps(params)

    def get_selected_equipment(self):
        """Get selected equipment as list"""
        if self.selected_equipment:
            try:
                return json.loads(self.selected_equipment)
            except:
                return []
        return []

    def set_selected_equipment(self, equipment):
        """Set selected equipment from list"""
        self.selected_equipment = json.dumps(equipment)

    def get_selected_glass_materials(self):
        """Get selected glass materials as list"""
        if self.selected_glass_materials:
            try:
                return json.loads(self.selected_glass_materials)
            except:
                return []
        return []

    def set_selected_glass_materials(self, materials):
        """Set selected glass materials from list"""
        self.selected_glass_materials = json.dumps(materials)

    def get_selected_reagents(self):
        """Get selected reagents as list"""
        if self.selected_reagents:
            try:
                return json.loads(self.selected_reagents)
            except:
                return []
        return []

    def set_selected_reagents(self, reagents):
        """Set selected reagents from list"""
        self.selected_reagents = json.dumps(reagents)

    def get_selected_reference(self):
        """Get selected reference as dictionary"""
        if self.selected_reference:
            try:
                return json.loads(self.selected_reference)
            except:
                return {}
        return {}

    def set_selected_reference(self, reference):
        """Set selected reference from dictionary"""
        self.selected_reference = json.dumps(reference)

    def get_validation_parameters(self):
        """Get validation parameters as list"""
        if self.validation_parameters:
            try:
                return json.loads(self.validation_parameters)
            except:
                return []
        return []

    def set_validation_parameters(self, params):
        """Set validation parameters from list"""
        self.validation_parameters = json.dumps(params)

class Subscription(db.Model):
    """Model for tracking subscription history and details"""
    __tablename__ = 'subscriptions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_plan_id: Mapped[str] = mapped_column(String(255), nullable=True)
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False)  # free, basic, premium
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # active, canceled, past_due, incomplete, trialing
    current_period_start: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    trial_start: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    trial_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), onupdate=datetime.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="subscription")

    def is_trial(self):
        """Check if subscription is in trial period"""
        if not self.trial_start or not self.trial_end:
            return False
        now = datetime.now()
        return self.trial_start <= now <= self.trial_end

    def days_until_expiry(self):
        """Get days until subscription expires"""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - datetime.now()
        return max(0, delta.days)

class Payment(db.Model):
    """Model for tracking all payment transactions"""
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, ForeignKey('subscriptions.id'), nullable=True)
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_charge_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_order_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Amount in paise for INR or cents for USD
    currency: Mapped[str] = mapped_column(String(10), default='usd', nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # succeeded, failed, pending, refunded
    payment_method: Mapped[str] = mapped_column(String(50), nullable=True)  # card, bank_transfer, etc.
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    payment_metadata: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string for additional data
    receipt_url: Mapped[str] = mapped_column(String(500), nullable=True)
    refunded_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Amount refunded in cents
    failure_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="payments")

    def get_amount_dollars(self):
        """Get amount in dollars"""
        return self.amount / 100.0

    def get_refunded_dollars(self):
        """Get refunded amount in dollars"""
        return self.refunded_amount / 100.0

    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'succeeded'

    def is_refunded(self):
        """Check if payment was refunded"""
        return self.refunded_amount > 0

    def get_metadata(self):
        """Get metadata as dictionary"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except:
                return {}
        return {}

    def set_metadata(self, data):
        """Set metadata from dictionary"""
        self.metadata = json.dumps(data)

class SubscriptionPlan(db.Model):
    """Model for defining subscription plan details"""
    __tablename__ = 'subscription_plans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # Price in cents
    currency: Mapped[str] = mapped_column(String(10), default='usd', nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), default='month', nullable=False)  # month, year
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=True)
    documents_per_month: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    api_requests_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string of features
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())

    def get_price_dollars(self):
        """Get price in dollars"""
        return self.price / 100.0

    def get_features_list(self):
        """Get features as list"""
        if self.features:
            try:
                return json.loads(self.features)
            except:
                return []
        return []

    def set_features_list(self, features):
        """Set features from list"""
        self.features = json.dumps(features)
