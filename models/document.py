from datetime import datetime, timezone
from models import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    keywords = db.Column(db.Text, nullable=True)       # JSON string
    entities = db.Column(db.Text, nullable=True)       # JSON string
    sentiment = db.Column(db.String(50), nullable=True)
    enriched_info = db.Column(db.Text, nullable=True)  # generated/enriched
    file_type = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "filename": self.filename,
            "original_text": self.original_text[:500] + "..." if len(self.original_text) > 500 else self.original_text,
            "full_text": self.original_text,
            "summary": self.summary,
            "keywords": json.loads(self.keywords) if self.keywords else [],
            "entities": json.loads(self.entities) if self.entities else [],
            "sentiment": self.sentiment,
            "enriched_info": self.enriched_info,
            "file_type": self.file_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }