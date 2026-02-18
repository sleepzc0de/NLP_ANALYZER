import json
import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from models import db
from models.document import Document
from services.file_processor import FileProcessor
from services.nlp_analyzer import NLPAnalyzer

doc_bp = Blueprint("documents", __name__, url_prefix="/api")


def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf", "docx"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


@doc_bp.route("/upload", methods=["POST"])
def upload_and_analyze():
    """Upload a file, extract text, run NLP, return result WITHOUT saving."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PDF or DOCX."}), 400

    filename = secure_filename(file.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    try:
        file_ext = filename.rsplit(".", 1)[1]
        text = FileProcessor.extract_text(filepath, file_ext)

        if not text.strip():
            return jsonify({"error": "No text could be extracted from file"}), 422

        analysis = NLPAnalyzer.full_analysis(text)

        return jsonify({
            "status": "analyzed",
            "filename": filename,
            "file_type": file_ext,
            "original_text": text[:1000] + "..." if len(text) > 1000 else text,
            "full_text": text,
            **analysis,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@doc_bp.route("/save", methods=["POST"])
def save_document():
    """Save analyzed document to database."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["filename", "full_text", "summary", "keywords", "entities", "sentiment"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    doc = Document(
        filename=data["filename"],
        original_text=data["full_text"],
        summary=data["summary"],
        keywords=json.dumps(data["keywords"]),
        entities=json.dumps(data["entities"]),
        sentiment=data["sentiment"],
        enriched_info=data.get("enriched_info", ""),
        file_type=data.get("file_type", ""),
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify({"status": "saved", "document": doc.to_dict()}), 201


@doc_bp.route("/regenerate", methods=["POST"])
def regenerate():
    """Re-run NLP analysis on provided text (optionally update DB record)."""
    data = request.get_json()
    if not data or "full_text" not in data:
        return jsonify({"error": "full_text is required"}), 400

    text = data["full_text"]
    analysis = NLPAnalyzer.full_analysis(text)

    doc_id = data.get("doc_id")
    if doc_id:
        doc = db.session.get(Document, doc_id)
        if doc:
            doc.summary = analysis["summary"]
            doc.keywords = json.dumps(analysis["keywords"])
            doc.entities = json.dumps(analysis["entities"])
            doc.sentiment = analysis["sentiment"]
            doc.enriched_info = analysis["enriched_info"]
            db.session.commit()
            return jsonify({
                "status": "regenerated_and_updated",
                "document": doc.to_dict(),
                **analysis,
            }), 200

    return jsonify({
        "status": "regenerated",
        "filename": data.get("filename", "unknown"),
        "full_text": text,
        **analysis,
    }), 200


@doc_bp.route("/documents", methods=["GET"])
def list_documents():
    """List all saved documents."""
    docs = Document.query.order_by(Document.created_at.desc()).all()
    return jsonify({"documents": [d.to_dict() for d in docs]}), 200


@doc_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(doc.to_dict()), 200


@doc_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id: int):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"status": "deleted", "id": doc_id}), 200