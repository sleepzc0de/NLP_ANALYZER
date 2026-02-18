from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Text, JSON

db = SQLAlchemy()

class DocumentRecord(db.Model):
    __tablename__ = "document_records"

    id              = db.Column(db.Integer, primary_key=True)
    filename        = db.Column(db.String(255), nullable=False)
    file_type       = db.Column(db.String(10), nullable=False)
    original_text   = db.Column(Text, nullable=False)
    cleaned_text    = db.Column(Text)
    language        = db.Column(db.String(50))
    word_count      = db.Column(db.Integer)
    char_count      = db.Column(db.Integer)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    # Relasi ke hasil analisis
    analyses = db.relationship("AnalysisResult", backref="document", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id":            self.id,
            "filename":      self.filename,
            "file_type":     self.file_type,
            "language":      self.language,
            "word_count":    self.word_count,
            "char_count":    self.char_count,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
        }


class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"

    id              = db.Column(db.Integer, primary_key=True)
    document_id     = db.Column(db.Integer, db.ForeignKey("document_records.id"), nullable=False)
    analysis_type   = db.Column(db.String(50), nullable=False)   # 'full' | 'regenerated'
    summary         = db.Column(Text)
    keywords        = db.Column(JSON)   # list of strings
    entities        = db.Column(JSON)   # list of {text, label}
    sentiment       = db.Column(JSON)   # {label, score}
    topics          = db.Column(JSON)   # list of strings
    additional_info = db.Column(JSON)   # info tambahan dari regenerasi
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":              self.id,
            "document_id":     self.document_id,
            "analysis_type":   self.analysis_type,
            "summary":         self.summary,
            "keywords":        self.keywords,
            "entities":        self.entities,
            "sentiment":       self.sentiment,
            "topics":          self.topics,
            "additional_info": self.additional_info,
            "created_at":      self.created_at.isoformat(),
        }