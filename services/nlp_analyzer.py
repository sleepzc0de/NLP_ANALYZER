import json
import re
import nltk
from collections import Counter
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag


# Label mapping untuk Named Entity
NE_LABEL_MAP = {
    "ORGANIZATION": "Organisasi",
    "PERSON":       "Orang",
    "GPE":          "Lokasi/Negara",
    "LOCATION":     "Lokasi",
    "FACILITY":     "Fasilitas",
    "GSP":          "Geo-Sosial-Politik",
    "MONEY":        "Nilai Uang",
    "DATE":         "Tanggal",
    "TIME":         "Waktu",
}

POSITIVE_WORDS = {
    "good", "great", "excellent", "positive", "success", "successful",
    "benefit", "improve", "improvement", "effective", "efficient",
    "increase", "gain", "profit", "growth", "achieve", "advantage",
    "outstanding", "remarkable", "wonderful", "perfect", "best",
    "innovative", "superior", "robust", "reliable", "strong",
    "bagus", "baik", "sukses", "berhasil", "meningkat", "untung",
    "positif", "efektif", "efisien", "inovatif", "unggul",
}

NEGATIVE_WORDS = {
    "bad", "poor", "negative", "failure", "fail", "loss", "decrease",
    "problem", "issue", "risk", "danger", "harm", "damage", "deficit",
    "decline", "wrong", "error", "defect", "weak", "critical", "severe",
    "crisis", "collapse", "threat", "obstacle", "insufficient",
    "buruk", "gagal", "rugi", "masalah", "risiko", "bahaya",
    "menurun", "negatif", "lemah", "krisis", "ancaman",
}


class NLPAnalyzer:

    @staticmethod
    def _get_stopwords() -> set:
        try:
            en_stop = set(stopwords.words("english"))
        except Exception:
            en_stop = set()
        try:
            id_stop = set(stopwords.words("indonesian"))
        except Exception:
            id_stop = set()
        return en_stop | id_stop

    @staticmethod
    def summarize(text: str, max_sentences: int = 5) -> str:
        """Extractive summarization menggunakan frekuensi kata."""
        try:
            sentences = sent_tokenize(text)
        except Exception:
            sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        if not sentences:
            return text[:500]

        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        stop_words = NLPAnalyzer._get_stopwords()

        # Hitung frekuensi kata
        try:
            words = word_tokenize(text.lower())
        except Exception:
            words = text.lower().split()

        word_freq: dict[str, int] = {}
        for w in words:
            if w.isalpha() and w not in stop_words and len(w) > 2:
                word_freq[w] = word_freq.get(w, 0) + 1

        if not word_freq:
            return " ".join(sentences[:max_sentences])

        max_freq = max(word_freq.values())
        word_freq = {w: f / max_freq for w, f in word_freq.items()}

        # Skor tiap kalimat
        sentence_scores: dict[int, float] = {}
        for i, sentence in enumerate(sentences):
            try:
                sent_words = word_tokenize(sentence.lower())
            except Exception:
                sent_words = sentence.lower().split()

            score = sum(word_freq.get(w, 0) for w in sent_words if w.isalpha())
            sentence_scores[i] = score

        # Ambil top N indeks, urutkan sesuai posisi asli
        top_indices = sorted(
            sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:max_sentences]
        )
        return " ".join(sentences[i] for i in top_indices)

    @staticmethod
    def extract_keywords(text: str, top_n: int = 15) -> list[str]:
        """Ekstrak keyword menggunakan POS tagging + frekuensi."""
        stop_words = NLPAnalyzer._get_stopwords()
        lemmatizer = WordNetLemmatizer()

        try:
            tokens = word_tokenize(text)
            tagged = pos_tag(tokens)
        except Exception:
            tokens = text.split()
            tagged = [(t, "NN") for t in tokens]

        keywords: list[str] = []
        for word, tag in tagged:
            if (
                word.isalpha()
                and len(word) > 2
                and word.lower() not in stop_words
                and tag in ("NN", "NNS", "NNP", "NNPS", "JJ", "VBG")
            ):
                try:
                    lemma = lemmatizer.lemmatize(word.lower())
                except Exception:
                    lemma = word.lower()
                keywords.append(lemma)

        freq = Counter(keywords)
        return [word for word, _ in freq.most_common(top_n)]

    @staticmethod
    def extract_entities(text: str) -> list[dict]:
        """Named Entity Recognition menggunakan NLTK ne_chunk."""
        entities: list[dict] = []
        seen: set[str] = set()

        # Batasi teks agar tidak terlalu lambat
        truncated = text[:8000]

        try:
            sentences = sent_tokenize(truncated)
            for sentence in sentences:
                tokens = word_tokenize(sentence)
                tagged = pos_tag(tokens)
                chunks = ne_chunk(tagged, binary=False)

                for chunk in chunks:
                    if hasattr(chunk, "label"):
                        entity_text = " ".join(c[0] for c in chunk)
                        entity_label = chunk.label()
                        key = f"{entity_text}|{entity_label}"

                        if key not in seen and entity_text.strip():
                            seen.add(key)
                            entities.append({
                                "text": entity_text,
                                "label": entity_label,
                                "description": NE_LABEL_MAP.get(
                                    entity_label, entity_label
                                ),
                            })
        except Exception as e:
            entities.append({
                "text": "NER tidak tersedia",
                "label": "INFO",
                "description": str(e),
            })

        return entities[:30]  # max 30 entitas

    @staticmethod
    def analyze_sentiment(text: str) -> str:
        """Analisis sentimen berbasis kamus kata positif/negatif."""
        try:
            tokens = word_tokenize(text[:5000].lower())
        except Exception:
            tokens = text[:5000].lower().split()

        token_set = {t for t in tokens if t.isalpha()}
        pos_score = len(token_set & POSITIVE_WORDS)
        neg_score = len(token_set & NEGATIVE_WORDS)

        if pos_score > neg_score:
            return "Positive"
        elif neg_score > pos_score:
            return "Negative"
        return "Neutral"

    @staticmethod
    def generate_enriched_info(
        text: str,
        keywords: list[str],
        entities: list[dict],
        summary: str,
    ) -> str:
        """Buat laporan analisis lengkap."""
        word_count = len(text.split())
        char_count = len(text)

        try:
            sentence_count = len(sent_tokenize(text))
        except Exception:
            sentence_count = text.count(".") + text.count("!") + text.count("?")

        entity_lines = "\n".join(
            f"  - {e['text']} [{e['label']}] → {e['description']}"
            for e in entities[:15]
        ) or "  - Tidak ada entitas terdeteksi"

        keyword_str = ", ".join(keywords[:12]) if keywords else "Tidak ada"

        # Deteksi topik sederhana dari keywords
        topic_hint = keywords[0].title() if keywords else "Umum"

        enriched = (
            "╔══════════════════════════════════════════╗\n"
            "║       LAPORAN ANALISIS DOKUMEN NLP       ║\n"
            "╚══════════════════════════════════════════╝\n\n"
            f"► RINGKASAN EKSEKUTIF\n"
            f"{summary}\n\n"
            f"► STATISTIK DOKUMEN\n"
            f"  • Total karakter   : {char_count:,}\n"
            f"  • Total kata       : {word_count:,}\n"
            f"  • Total kalimat    : {sentence_count:,}\n"
            f"  • Topik utama      : {topic_hint}\n\n"
            f"► KATA KUNCI UTAMA\n"
            f"  {keyword_str}\n\n"
            f"► ENTITAS TERDETEKSI ({len(entities)} entitas)\n"
            f"{entity_lines}\n\n"
            f"► REKOMENDASI INFORMASI TAMBAHAN\n"
            f"  Berdasarkan analisis, dokumen ini membahas topik seputar '{topic_hint}'.\n"
            f"  Pertimbangkan untuk menambahkan:\n"
            f"  • Referensi atau sitasi terkait topik\n"
            f"  • Data statistik pendukung\n"
            f"  • Konteks historis atau latar belakang\n"
            f"  • Kesimpulan dan rekomendasi tindak lanjut\n"
        )
        return enriched

    @classmethod
    def full_analysis(cls, text: str) -> dict:
        summary   = cls.summarize(text)
        keywords  = cls.extract_keywords(text)
        entities  = cls.extract_entities(text)
        sentiment = cls.analyze_sentiment(text)
        enriched  = cls.generate_enriched_info(text, keywords, entities, summary)

        return {
            "summary":      summary,
            "keywords":     keywords,
            "entities":     entities,
            "sentiment":    sentiment,
            "enriched_info": enriched,
        }