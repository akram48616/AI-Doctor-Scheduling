"""
Resource management routes.
"""
import logging
from flask import Blueprint, request, jsonify
from backend.models import Resource, Hospital
from backend.utils.db import get_session
from backend.models import ResourceType

logger = logging.getLogger(__name__)
resource_bp = Blueprint("resource", __name__, url_prefix="/api/resource")


def json_response(success: bool, data=None, message: str = "", status: int = 200):
    return jsonify({"success": success, "data": data or {}, "message": message}), status


@resource_bp.route("/", methods=["POST"])
def add_resource():
    try:
        data = request.get_json() or {}
        required = ["hospital_id", "name", "resource_type"]
        missing = [f for f in required if f not in data]
        if missing:
            return json_response(False, message=f"Missing: {', '.join(missing)}", status=400)
        with get_session() as session:
            hospital = session.query(Hospital).filter(Hospital.id == data["hospital_id"]).first()
            if not hospital:
                return json_response(False, message="Hospital not found", status=404)
            rtype = data["resource_type"]
            if rtype not in [e.value for e in ResourceType]:
                return json_response(False, message="Invalid resource_type", status=400)
            resource = Resource(hospital_id=data["hospital_id"], name=data["name"], resource_type=rtype, description=data.get("description"), is_available=1 if data.get("is_available", True) else 0)
            session.add(resource)
            session.commit()
            return json_response(True, data={"id": resource.id}, message="Resource added", status=201)
    except Exception as e:
        logger.exception("Error adding resource")
        return json_response(False, message=str(e), status=500)


@resource_bp.route("/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    try:
        with get_session() as session:
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                return json_response(False, message="Resource not found", status=404)
            data = {"id": resource.id, "hospital_id": resource.hospital_id, "name": resource.name, "resource_type": getattr(resource.resource_type, "value", resource.resource_type), "description": resource.description, "is_available": bool(resource.is_available)}
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting resource")
        return json_response(False, message=str(e), status=500)


@resource_bp.route("/hospital/<int:hospital_id>", methods=["GET"])
def list_hospital_resources(hospital_id):
    try:
        with get_session() as session:
            resources = session.query(Resource).filter(Resource.hospital_id == hospital_id).all()
            data = [{"id": r.id, "name": r.name, "resource_type": getattr(r.resource_type, "value", r.resource_type), "is_available": bool(r.is_available)} for r in resources]
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error listing resources")
        return json_response(False, message=str(e), status=500)


@resource_bp.route("/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    try:
        data = request.get_json() or {}
        with get_session() as session:
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                return json_response(False, message="Resource not found", status=404)
            for field in ["name", "description"]:
                if field in data:
                    setattr(resource, field, data[field])
            if "is_available" in data:
                resource.is_available = 1 if data["is_available"] else 0
            session.commit()
            return json_response(True, message="Resource updated")
    except Exception as e:
        logger.exception("Error updating resource")
        return json_response(False, message=str(e), status=500)


@resource_bp.route("/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    try:
        with get_session() as session:
            resource = session.query(Resource).filter(Resource.id == resource_id).first()
            if not resource:
                return json_response(False, message="Resource not found", status=404)
            session.delete(resource)
            session.commit()
            return json_response(True, message="Resource deleted")
    except Exception as e:
        logger.exception("Error deleting resource")
        return json_response(False, message=str(e), status=500)