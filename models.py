 # Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import json
from datetime import datetime
from database import db
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
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

    # Relationships
    companies: Mapped[List["Company"]] = relationship("Company", back_populates="user")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="user")
    activity_logs: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="user")
    pvp_templates: Mapped[List["PVP_Template"]] = relationship("PVP_Template", back_populates="user")
    pvr_reports: Mapped[List["PVR_Report"]] = relationship("PVR_Report", back_populates="user")
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Company(db.Model):
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="companies")
    sub_brands: Mapped[List["SubBrand"]] = relationship("SubBrand", back_populates="company")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="company")
    equipment = relationship('Equipment', backref='company', lazy=True)

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
    company_provided_id = db.Column(db.String(50))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., HPLC, GC, etc.
    make: Mapped[str] = mapped_column(String(100), nullable=True)
    calibration_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    next_calibration_due: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships can be added later if needed
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('companies.id', name="fk_equipment_company"),
        nullable=False
    )

    @property
    def is_calibrated(self):
        return self.next_calibration_due and self.next_calibration_due >= datetime.now()

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
    document: Mapped["Document"] = relationship("Document", backref="amv_details")

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