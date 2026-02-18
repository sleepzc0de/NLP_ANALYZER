import os
from flask import Flask, render_template, jsonify
from config import Config
from models import db
from routes.document_routes import doc_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Buat folder uploads jika belum ada
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(doc_bp)

    # Handle error global
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File terlalu besar. Maksimal 16MB."}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    @app.route("/")
    def index():
        return render_template("index.html")

    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified")
        print(f"✅ Upload folder: {app.config['UPLOAD_FOLDER']}")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)