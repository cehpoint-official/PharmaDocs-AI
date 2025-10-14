# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

from flask import Blueprint, request, jsonify
from models import db, Equipment
from utils.helpers import parse_date

bp = Blueprint("equipment", __name__)


# Create Equipment
@bp.route("/equipment/create", methods=["POST"])
def create_equipment():
    try:
        name = request.form.get("name")
        type_ = request.form.get("type")
        make = request.form.get("make")
        instrument_id = request.form.get("company_provided_id")
        calibration_date = parse_date(request.form.get("calibration_date"))
        next_due = parse_date(request.form.get("next_calibration_due"))
        company_id = request.form.get("company_id")

        if not name or not type_ or not company_id:
            return jsonify({"success": False, "error": "Missing required fields"})

        equipment = Equipment(
            name=name,
            type=type_,
            make=make,
            company_provided_id=instrument_id,
            calibration_date=calibration_date or None,
            next_calibration_due=next_due or None,
            company_id=company_id
        )
        db.session.add(equipment)
        db.session.commit()
        return jsonify({"success": True, "equipment_id": equipment.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})



# Get Equipment by ID

@bp.route("/equipment/<int:eq_id>", methods=["GET"])
def get_equipment(eq_id):
    eq = Equipment.query.get(eq_id)
    if not eq:
        return jsonify({"success": False, "error": "Not found"})

    return jsonify({
        "success": True,
        "equipment": {
            "id": eq.id,
            "name": eq.name,
            "type": eq.type,
            "make": eq.make,
            "calibration_date": eq.calibration_date.strftime("%Y-%m-%d") if eq.calibration_date else "",
            "next_calibration_due": eq.next_calibration_due.strftime("%Y-%m-%d") if eq.next_calibration_due else ""
        }
    })



# Update Equipment

@bp.route("/equipment/update/<int:eq_id>", methods=["POST"])
def update_equipment(eq_id):
    eq = Equipment.query.get(eq_id)
    if not eq:
        return jsonify({"success": False, "error": "Not found"})

    try:
        eq.name = request.form.get("name") or eq.name
        eq.type = request.form.get("type") or eq.type
        eq.make = request.form.get("make") or eq.make
        eq.calibration_date = request.form.get("calibration_date") or None
        eq.next_calibration_due = request.form.get("next_calibration_due") or None
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})



# Delete Equipment

@bp.route("/equipment/delete/<int:eq_id>", methods=["POST"])
def delete_equipment(eq_id):
    eq = Equipment.query.get(eq_id)
    if not eq:
        return jsonify({"success": False, "error": "Not found"})
    try:
        db.session.delete(eq)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})
