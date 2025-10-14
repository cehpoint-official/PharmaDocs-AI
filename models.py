# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from datetime import datetime
from app import db
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
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
