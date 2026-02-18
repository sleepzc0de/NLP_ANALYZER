import os
import json
from flask import Flask, request, jsonify
from config import Config
from models import db, DocumentRecord, AnalysisResult
from file_handler import (
    allowed_file, extract_text, clean_text, save_upload
)
from nlp_processor import full_analysis, regenerate_analysis

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# ── Buat tabel jika belum ada ────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    print("✅  Database tables ready.")


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 1 — Upload & Analisis Dokumen
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/upload", methods=["POST"])
def upload_document():
    """
    Upload file Word/PDF, ekstrak teks, lalu analisis dengan NLP.
    
    Form-data:
        file        : file (required)
    
    Response:
        analyzed_text, analysis_result, doc_id (sementara, sebelum disimpan)
    """
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang diunggah."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nama file kosong."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Format file tidak didukung. Gunakan PDF atau DOCX."}), 400

    try:
        filepath, file_type = save_upload(file, app.config["UPLOAD_FOLDER"])
        raw_text            = extract_text(filepath, file_type)
        cleaned             = clean_text(raw_text)

        if not cleaned:
            return jsonify({"error": "Tidak ada teks yang dapat diekstrak dari file."}), 422

        analysis = full_analysis(cleaned)

        # Simpan sementara di session / kembalikan ke client untuk keputusan selanjutnya
        return jsonify({
            "message":       "Analisis selesai. Pilih aksi selanjutnya.",
            "filename":      file.filename,
            "file_type":     file_type,
            "preview_text":  cleaned[:500] + ("..." if len(cleaned) > 500 else ""),
            "analysis":      analysis,
            # Kirim raw text terenkode (digunakan saat save/regenerate)
            "raw_text_ref":  cleaned,   # ⚠️  Di produksi: simpan di Redis/cache, kirim token
            "actions": {
                "save_only":          "POST /documents/save",
                "regenerate_only":    "POST /documents/regenerate",
                "save_and_regenerate":"POST /documents/save-and-regenerate",
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 2 — Simpan ke Database Saja
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents/save", methods=["POST"])
def save_document():
    """
    Simpan dokumen + hasil analisis ke PostgreSQL.
    
    JSON Body:
        filename     : str
        file_type    : str
        raw_text     : str
        analysis     : dict  (dari /upload)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON diperlukan."}), 400

    required = ["filename", "file_type", "raw_text", "analysis"]
    missing  = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Field berikut wajib ada: {missing}"}), 400

    try:
        analysis = data["analysis"]

        # Simpan dokumen
        doc = DocumentRecord(
            filename     = data["filename"],
            file_type    = data["file_type"],
            original_text= data["raw_text"],
            cleaned_text = data["raw_text"],
            language     = analysis.get("language", "unknown"),
            word_count   = analysis.get("word_count", 0),
            char_count   = analysis.get("char_count", 0),
        )
        db.session.add(doc)
        db.session.flush()  # Dapatkan doc.id sebelum commit

        # Simpan hasil analisis
        result = AnalysisResult(
            document_id  = doc.id,
            analysis_type= "full",
            summary      = analysis.get("summary"),
            keywords     = analysis.get("keywords"),
            entities     = analysis.get("entities"),
            sentiment    = analysis.get("sentiment"),
            topics       = analysis.get("topics"),
        )
        db.session.add(result)
        db.session.commit()

        return jsonify({
            "message":     "Dokumen berhasil disimpan.",
            "document_id": doc.id,
            "analysis_id": result.id,
            "document":    doc.to_dict(),
            "analysis":    result.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 3 — Generate Ulang Analisis (Tanpa Simpan Dokumen Baru)
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents/regenerate", methods=["POST"])
def regenerate_document():
    """
    Generate ulang analisis dari teks yang sudah ada (tidak simpan ke DB).
    
    JSON Body:
        raw_text            : str
        additional_context  : str  (opsional — informasi tambahan)
    """
    data = request.get_json()
    if not data or "raw_text" not in data:
        return jsonify({"error": "Field 'raw_text' wajib ada."}), 400

    try:
        additional = data.get("additional_context", "")
        analysis   = regenerate_analysis(data["raw_text"], additional)

        return jsonify({
            "message":  "Regenerasi analisis selesai.",
            "analysis": analysis,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 4 — Simpan Dulu, Lalu Generate Ulang (Tambah Info)
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents/save-and-regenerate", methods=["POST"])
def save_and_regenerate():
    """
    Simpan dokumen ke DB, kemudian generate ulang analisis dengan info tambahan
    dan simpan juga hasil regenerasi tersebut.
    
    JSON Body:
        filename            : str
        file_type           : str
        raw_text            : str
        analysis            : dict   (hasil analisis pertama)
        additional_context  : str    (informasi tambahan untuk regenerasi)
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON diperlukan."}), 400

    required = ["filename", "file_type", "raw_text", "analysis"]
    missing  = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Field berikut wajib ada: {missing}"}), 400

    try:
        analysis   = data["analysis"]
        additional = data.get("additional_context", "")

        # ── Langkah 1: Simpan dokumen & analisis awal ──────────────────────
        doc = DocumentRecord(
            filename     = data["filename"],
            file_type    = data["file_type"],
            original_text= data["raw_text"],
            cleaned_text = data["raw_text"],
            language     = analysis.get("language", "unknown"),
            word_count   = analysis.get("word_count", 0),
            char_count   = analysis.get("char_count", 0),
        )
        db.session.add(doc)
        db.session.flush()

        initial_result = AnalysisResult(
            document_id  = doc.id,
            analysis_type= "full",
            summary      = analysis.get("summary"),
            keywords     = analysis.get("keywords"),
            entities     = analysis.get("entities"),
            sentiment    = analysis.get("sentiment"),
            topics       = analysis.get("topics"),
        )
        db.session.add(initial_result)

        # ── Langkah 2: Regenerasi dengan konteks tambahan ──────────────────
        regen_analysis = regenerate_analysis(data["raw_text"], additional)

        regen_result = AnalysisResult(
            document_id  = doc.id,
            analysis_type= "regenerated",
            summary      = regen_analysis.get("summary"),
            keywords     = regen_analysis.get("keywords"),
            entities     = regen_analysis.get("entities"),
            sentiment    = regen_analysis.get("sentiment"),
            topics       = regen_analysis.get("topics"),
            additional_info = regen_analysis.get("additional_info"),
        )
        db.session.add(regen_result)
        db.session.commit()

        return jsonify({
            "message":            "Dokumen disimpan & regenerasi selesai.",
            "document_id":        doc.id,
            "initial_analysis_id": initial_result.id,
            "regen_analysis_id":  regen_result.id,
            "document":           doc.to_dict(),
            "initial_analysis":   initial_result.to_dict(),
            "regenerated_analysis": regen_result.to_dict(),
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 5 — Ambil Semua Dokumen
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents", methods=["GET"])
def list_documents():
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    docs     = DocumentRecord.query.order_by(DocumentRecord.created_at.desc())\
                                   .paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "total":     docs.total,
        "page":      docs.page,
        "per_page":  docs.per_page,
        "pages":     docs.pages,
        "documents": [d.to_dict() for d in docs.items],
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 6 — Detail Dokumen + Semua Analisisnya
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id: int):
    doc = DocumentRecord.query.get_or_404(doc_id)
    analyses = [a.to_dict() for a in doc.analyses]
    return jsonify({
        "document": doc.to_dict(),
        "analyses": analyses,
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 7 — Hapus Dokumen
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/documents/<int:doc_id>", methods=["DELETE"])
def delete_document(doc_id: int):
    doc = DocumentRecord.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"message": f"Dokumen ID {doc_id} berhasil dihapus."}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTE 8 — Health Check
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "NLP Analyzer API"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)