# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import json
from datetime import datetime
from database import db
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List

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
    # type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., HPLC, GC, etc.
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