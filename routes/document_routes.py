import json
import os
import traceback
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from models import db
from models.document import Document
from services.file_processor import FileProcessor
from services.nlp_analyzer import NLPAnalyzer
from services.nota_dinas_extractor import NotaDinasExtractor
from services.balasan_generator import BalasanGenerator

doc_bp = Blueprint("documents", __name__, url_prefix="/api")


def allowed_file(filename: str) -> bool:
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf", "docx"})
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed
    )


@doc_bp.route("/upload", methods=["POST"])
def upload_and_analyze():
    try:
        # Cek apakah ada file di request
        if "file" not in request.files:
            return jsonify({"error": "Tidak ada file dalam request"}), 400

        file = request.files["file"]

        # Cek filename kosong
        if not file or file.filename == "" or file.filename is None:
            return jsonify({"error": "Tidak ada file yang dipilih"}), 400

        # Cek ekstensi
        if not allowed_file(file.filename):
            return jsonify({
                "error": "Format file tidak didukung. Gunakan PDF atau DOCX."
            }), 400

        # Simpan file sementara
        filename = secure_filename(file.filename)
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)

        file.save(filepath)
        current_app.logger.info(f"File saved: {filepath}")

        # Cek file benar-benar tersimpan
        if not os.path.exists(filepath):
            return jsonify({"error": "Gagal menyimpan file sementara"}), 500

        file_size = os.path.getsize(filepath)
        current_app.logger.info(f"File size: {file_size} bytes")

        if file_size == 0:
            os.remove(filepath)
            return jsonify({"error": "File kosong (0 bytes)"}), 422

        # Ekstrak teks
        file_ext = filename.rsplit(".", 1)[1].lower()
        current_app.logger.info(f"Processing {file_ext} file...")

        text = FileProcessor.extract_text(filepath, file_ext)

        if not text or not text.strip():
            return jsonify({
                "error": "Tidak ada teks yang bisa diekstrak dari file ini. "
                         "Pastikan file tidak terproteksi atau kosong."
            }), 422

        current_app.logger.info(f"Text extracted: {len(text)} chars")

        # Analisis NLP
        analysis = NLPAnalyzer.full_analysis(text)

        # Preview teks (500 char)
        preview = text[:500] + "..." if len(text) > 500 else text

        return jsonify({
            "status": "analyzed",
            "filename": filename,
            "file_type": file_ext,
            "original_text": preview,
            "full_text": text,
            "summary": analysis["summary"],
            "keywords": analysis["keywords"],
            "entities": analysis["entities"],
            "sentiment": analysis["sentiment"],
            "enriched_info": analysis["enriched_info"],
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error: {str(e)}"}), 500

    finally:
        # Hapus file sementara
        try:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
                current_app.logger.info(f"Temp file deleted: {filepath}")
        except Exception:
            pass


@doc_bp.route("/save", methods=["POST"])
def save_document():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Tidak ada data JSON"}), 400

        required = ["filename", "full_text", "summary", "keywords", "entities", "sentiment"]
        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            return jsonify({"error": f"Field tidak lengkap: {missing}"}), 400

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

        return jsonify({
            "status": "saved",
            "document": doc.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Gagal menyimpan: {str(e)}"}), 500


@doc_bp.route("/regenerate", methods=["POST"])
def regenerate():
    try:
        data = request.get_json(force=True)
        if not data or "full_text" not in data:
            return jsonify({"error": "full_text wajib diisi"}), 400

        text = data["full_text"].strip()
        if not text:
            return jsonify({"error": "Teks tidak boleh kosong"}), 400

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

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Gagal regenerate: {str(e)}"}), 500


@doc_bp.route("/documents", methods=["GET"])
def list_documents():
    try:
        docs = Document.query.order_by(Document.created_at.desc()).all()
        return jsonify({"documents": [d.to_dict() for d in docs]}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@doc_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id: int):
    try:
        doc = db.session.get(Document, doc_id)
        if not doc:
            return jsonify({"error": "Dokumen tidak ditemukan"}), 404
        return jsonify(doc.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@doc_bp.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id: int):
    try:
        doc = db.session.get(Document, doc_id)
        if not doc:
            return jsonify({"error": "Dokumen tidak ditemukan"}), 404
        db.session.delete(doc)
        db.session.commit()
        return jsonify({"status": "deleted", "id": doc_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@doc_bp.route("/health", methods=["GET"])
def health_check():
    """Endpoint untuk cek apakah API berjalan."""
    return jsonify({
        "status": "ok",
        "upload_folder": current_app.config["UPLOAD_FOLDER"],
        "allowed_extensions": list(current_app.config["ALLOWED_EXTENSIONS"]),
    }), 200

@doc_bp.route("/extract-nota-dinas", methods=["POST"])
def extract_nota_dinas():
    """Ekstrak data terstruktur dari teks Nota Dinas."""
    try:
        data = request.get_json(force=True)
        if not data or "text" not in data:
            return jsonify({"error": "text wajib diisi"}), 400

        text = data["text"]
        nd   = NotaDinasExtractor.extract(text)
        nd_dict = NotaDinasExtractor.to_dict(nd)

        return jsonify({
            "status":    "success",
            "nota_dinas": nd_dict,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@doc_bp.route("/generate-balasan", methods=["POST"])
def generate_balasan():
    """Generate konsep balasan Nota Dinas."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Data tidak boleh kosong"}), 400

        text           = data.get("text", "")
        unit_pembalas  = data.get("unit_pembalas", "")
        nama_ttd       = data.get("nama_ttd", "")
        jabatan_ttd    = data.get("jabatan_ttd", "")
        nd_data        = data.get("nota_dinas_data", None)

        # Gunakan data yang sudah diekstrak jika ada,
        # atau ekstrak ulang dari teks
        if nd_data:
            from services.nota_dinas_extractor import NotaDinas
            nd = NotaDinas(**{
                k: v for k, v in nd_data.items()
                if k in NotaDinas.__dataclass_fields__
            })
        elif text:
            nd = NotaDinasExtractor.extract(text)
        else:
            return jsonify({"error": "Sediakan text atau nota_dinas_data"}), 400

        result = BalasanGenerator.generate(
            nd,
            unit_pembalas=unit_pembalas,
            nama_ttd=nama_ttd,
            jabatan_ttd=jabatan_ttd,
        )

        return jsonify({
            "status":  "success",
            "balasan": result,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500