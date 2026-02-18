import spacy
import nltk
import re
from collections import Counter
from langdetect import detect, LangDetectException
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer

# Download resource NLTK yang diperlukan
nltk.download("punkt",      quiet=True)
nltk.download("stopwords",  quiet=True)
nltk.download("punkt_tab",  quiet=True)

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Load model spaCy (unduh dulu: python -m spacy download en_core_web_sm)
try:
    nlp_en = spacy.load("en_core_web_sm")
except OSError:
    nlp_en = None
    print("⚠️  Model spaCy 'en_core_web_sm' belum tersedia. Jalankan: python -m spacy download en_core_web_sm")


# ─────────────────────────── Deteksi Bahasa ─────────────────────────────────

def detect_language(text: str) -> str:
    try:
        return detect(text[:1000])
    except LangDetectException:
        return "unknown"


# ─────────────────────────── Ekstraksi Keyword ──────────────────────────────

def extract_keywords(text: str, lang: str = "en", top_n: int = 20) -> list[str]:
    try:
        stop_words = set(stopwords.words("english" if lang == "en" else "english"))
    except Exception:
        stop_words = set()

    tokens = word_tokenize(text.lower())
    filtered = [
        w for w in tokens
        if w.isalpha() and w not in stop_words and len(w) > 3
    ]
    freq = Counter(filtered)
    return [word for word, _ in freq.most_common(top_n)]


# ─────────────────────────── Named Entity Recognition ───────────────────────

def extract_entities(text: str) -> list[dict]:
    if nlp_en is None:
        return []
    
    # Potong teks jika terlalu panjang (batas spaCy default 1.000.000 char)
    doc = nlp_en(text[:100_000])
    seen  = set()
    entities = []
    for ent in doc.ents:
        key = (ent.text.strip(), ent.label_)
        if key not in seen:
            seen.add(key)
            entities.append({"text": ent.text.strip(), "label": ent.label_})
    return entities


# ─────────────────────────── Sentimen Sederhana ─────────────────────────────

POSITIVE_WORDS = {
    "good", "great", "excellent", "positive", "best", "amazing", "wonderful",
    "fantastic", "success", "successful", "benefit", "improve", "effective",
    "efficient", "innovative", "strong", "growth", "profit", "advantage", "baik",
    "bagus", "hebat", "sukses", "berhasil", "meningkat", "maju", "unggul"
}

NEGATIVE_WORDS = {
    "bad", "poor", "negative", "worst", "terrible", "failure", "fail", "loss",
    "problem", "issue", "risk", "danger", "weak", "decline", "difficult",
    "buruk", "gagal", "rugi", "masalah", "risiko", "bahaya", "lemah", "turun"
}


def analyze_sentiment(text: str) -> dict:
    tokens    = word_tokenize(text.lower())
    pos_count = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg_count = sum(1 for t in tokens if t in NEGATIVE_WORDS)

    total = pos_count + neg_count or 1
    if pos_count > neg_count:
        label, score = "POSITIVE", round(pos_count / total, 2)
    elif neg_count > pos_count:
        label, score = "NEGATIVE", round(neg_count / total, 2)
    else:
        label, score = "NEUTRAL", 0.5

    return {
        "label":          label,
        "score":          score,
        "positive_count": pos_count,
        "negative_count": neg_count,
    }


# ─────────────────────────── Ringkasan (Sumy) ───────────────────────────────

def generate_summary(text: str, sentence_count: int = 5, method: str = "lsa") -> str:
    try:
        parser     = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer() if method == "lsa" else LexRankSummarizer()
        sentences  = summarizer(parser.document, sentence_count)
        return " ".join(str(s) for s in sentences)
    except Exception as e:
        # Fallback: ambil kalimat pertama
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[:sentence_count])


# ─────────────────────────── Ekstraksi Topik Sederhana ──────────────────────

def extract_topics(text: str, keywords: list[str]) -> list[str]:
    """
    Pengelompokan topik sederhana berbasis domain keyword.
    Bisa diganti dengan LDA (gensim) untuk produksi.
    """
    text_lower = text.lower()
    topic_map = {
        "Technology":  ["technology", "software", "hardware", "ai", "machine learning", "data", "cloud"],
        "Business":    ["business", "company", "market", "revenue", "profit", "sales", "investment"],
        "Health":      ["health", "medical", "disease", "treatment", "patient", "hospital", "medicine"],
        "Education":   ["education", "school", "university", "learning", "student", "teaching"],
        "Environment": ["environment", "climate", "carbon", "energy", "sustainable", "green"],
        "Law & Policy":["law", "regulation", "policy", "government", "legal", "court", "compliance"],
    }

    detected_topics = []
    for topic, terms in topic_map.items():
        if any(term in text_lower for term in terms):
            detected_topics.append(topic)

    return detected_topics or ["General"]


# ─────────────────────────── Pipeline Utama ─────────────────────────────────

def full_analysis(text: str) -> dict:
    lang     = detect_language(text)
    keywords = extract_keywords(text, lang)
    entities = extract_entities(text)
    sentiment= analyze_sentiment(text)
    summary  = generate_summary(text)
    topics   = extract_topics(text, keywords)

    return {
        "language":  lang,
        "summary":   summary,
        "keywords":  keywords,
        "entities":  entities,
        "sentiment": sentiment,
        "topics":    topics,
        "word_count": len(text.split()),
        "char_count": len(text),
    }


def regenerate_analysis(original_text: str, additional_context: str = "") -> dict:
    """
    Regenerasi analisis dengan konteks tambahan.
    Menggabungkan teks asli dengan informasi tambahan dari user.
    """
    combined_text = original_text
    if additional_context:
        combined_text = f"{original_text}\n\n[ADDITIONAL CONTEXT]\n{additional_context}"

    result = full_analysis(combined_text)
    result["additional_info"] = {
        "has_additional_context": bool(additional_context),
        "extra_summary":          generate_summary(combined_text, sentence_count=8, method="lexrank"),
        "extra_keywords":         extract_keywords(combined_text, top_n=30),
    }
    return result