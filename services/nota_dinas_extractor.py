import re
from dataclasses import dataclass, field


@dataclass
class NotaDinas:
    nomor: str = ""
    kepada: list[str] = field(default_factory=list)
    dari: str = ""
    sifat: str = ""
    lampiran: str = ""
    hal: str = ""
    tanggal: str = ""
    isi_pokok: list[str] = field(default_factory=list)
    poin_penting: list[str] = field(default_factory=list)
    deadline: list[str] = field(default_factory=list)
    referensi_regulasi: list[str] = field(default_factory=list)
    penandatangan: str = ""
    jabatan_penandatangan: str = ""
    tembusan: list[str] = field(default_factory=list)
    unit_asal: str = ""
    jenis_dokumen: str = "Nota Dinas"


class NotaDinasExtractor:
    """
    Ekstraktor data terstruktur dari Nota Dinas Kemenkeu.
    Menggunakan rule-based regex + pattern matching.
    """

    # ── Regex patterns ──────────────────────────────────────────
    PATTERN_NOMOR = re.compile(
        r"NOMOR\s+(ND[-/][\w./]+)",
        re.IGNORECASE
    )
    PATTERN_KEPADA = re.compile(
        r"Yth\s*[.:]\s*(.*?)(?=Dari\s*[.:])",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_DARI = re.compile(
        r"Dari\s*[.:]\s*(.+?)(?=Sifat\s*[.:])",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_SIFAT = re.compile(
        r"Sifat\s*[.:]\s*(.+?)(?=Lampiran\s*[.:]|Hal\s*[.:])",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_LAMPIRAN = re.compile(
        r"Lampiran\s*[.:]\s*(.+?)(?=Hal\s*[.:])",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_HAL = re.compile(
        r"Hal\s*[.:]\s*(.+?)(?=Tanggal\s*[.:])",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_TANGGAL = re.compile(
        r"Tanggal\s*[.:]\s*(.+?)(?=\n)",
        re.IGNORECASE
    )
    PATTERN_DEADLINE = re.compile(
        r"(?:paling lambat|batas waktu|selambat-lambatnya|"
        r"deadline|tanggal)\s+(\d{1,2}\s+\w+\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
        re.IGNORECASE
    )
    PATTERN_REGULASI = re.compile(
        r"(?:Peraturan|Keputusan|Instruksi|Perpres|Inpres|PMK|KMK|SE|"
        r"Undang-Undang|UU)\s+[\w\s./]+(?:Nomor|No\.?)\s+[\w\s./]+(?:Tahun\s+\d{4})?",
        re.IGNORECASE
    )
    PATTERN_TEMBUSAN = re.compile(
        r"Tembusan\s*[:\n](.*?)(?:Dokumen ini|$)",
        re.IGNORECASE | re.DOTALL
    )
    PATTERN_PENANDATANGAN = re.compile(
        r"(?:Ditandatangani secara elektronik\s*\n\s*)([\w\s.]+?)(?:\n|$)",
        re.IGNORECASE
    )
    PATTERN_JABATAN_TTD = re.compile(
        r"((?:Kepala|Direktur|Sekretaris|Inspektur|Plt\.|Pjs\.)[\w\s.,]+)"
        r"\s*\n\s*(?:Ditandatangani|u\.b\.|ub\.)",
        re.IGNORECASE
    )
    PATTERN_UNIT = re.compile(
        r"(BADAN|DIREKTORAT|SEKRETARIAT|INSPEKTORAT|PUSAT|BIRO)[\w\s,]+",
        re.IGNORECASE
    )
    PATTERN_NOMOR_ND_REFERENSI = re.compile(
        r"ND[-/][\w./]+",
        re.IGNORECASE
    )

    # Bulan Indonesia
    BULAN_ID = {
        "januari": "Januari", "februari": "Februari", "maret": "Maret",
        "april": "April", "mei": "Mei", "juni": "Juni",
        "juli": "Juli", "agustus": "Agustus", "september": "September",
        "oktober": "Oktober", "november": "November", "desember": "Desember",
    }

    @classmethod
    def extract(cls, text: str) -> NotaDinas:
        nd = NotaDinas()
        clean = cls._clean_text(text)

        nd.nomor                = cls._extract_nomor(clean)
        nd.kepada               = cls._extract_kepada(clean)
        nd.dari                 = cls._extract_dari(clean)
        nd.sifat                = cls._extract_sifat(clean)
        nd.lampiran             = cls._extract_lampiran(clean)
        nd.hal                  = cls._extract_hal(clean)
        nd.tanggal              = cls._extract_tanggal(clean)
        nd.isi_pokok            = cls._extract_isi_pokok(clean)
        nd.poin_penting         = cls._extract_poin_penting(clean)
        nd.deadline             = cls._extract_deadline(clean)
        nd.referensi_regulasi   = cls._extract_regulasi(clean)
        nd.penandatangan        = cls._extract_penandatangan(clean)
        nd.jabatan_penandatangan = cls._extract_jabatan_ttd(clean)
        nd.tembusan             = cls._extract_tembusan(clean)
        nd.unit_asal            = cls._extract_unit_asal(clean, nd.dari)
        nd.jenis_dokumen        = cls._detect_jenis(clean)

        return nd

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        # Normalisasi whitespace berlebih
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @classmethod
    def _extract_nomor(cls, text: str) -> str:
        m = cls.PATTERN_NOMOR.search(text)
        return m.group(1).strip() if m else ""

    @classmethod
    def _extract_kepada(cls, text: str) -> list[str]:
        m = cls.PATTERN_KEPADA.search(text)
        if not m:
            return []
        raw = m.group(1).strip()
        # Split by numbering pattern: "1.", "2.", dll
        items = re.split(r"\n?\s*\d+\.\s+", raw)
        result = []
        for item in items:
            item = item.strip()
            if item and len(item) > 3:
                result.append(item)
        return result if result else [raw.strip()]

    @classmethod
    def _extract_dari(cls, text: str) -> str:
        m = cls.PATTERN_DARI.search(text)
        if not m:
            return ""
        return re.sub(r"\s+", " ", m.group(1)).strip()

    @classmethod
    def _extract_sifat(cls, text: str) -> str:
        m = cls.PATTERN_SIFAT.search(text)
        if not m:
            return ""
        return m.group(1).strip().split("\n")[0].strip()

    @classmethod
    def _extract_lampiran(cls, text: str) -> str:
        m = cls.PATTERN_LAMPIRAN.search(text)
        if not m:
            return ""
        return m.group(1).strip().split("\n")[0].strip()

    @classmethod
    def _extract_hal(cls, text: str) -> str:
        m = cls.PATTERN_HAL.search(text)
        if not m:
            return ""
        return re.sub(r"\s+", " ", m.group(1)).strip()

    @classmethod
    def _extract_tanggal(cls, text: str) -> str:
        m = cls.PATTERN_TANGGAL.search(text)
        if not m:
            return ""
        return m.group(1).strip()

    @classmethod
    def _extract_isi_pokok(cls, text: str) -> list[str]:
        """Ekstrak paragraf isi setelah blok header."""
        # Cari body setelah 'Tanggal : ...'
        split = re.split(r"Tanggal\s*[.:]\s*.+?\n", text, maxsplit=1)
        if len(split) < 2:
            return []

        body = split[1].strip()
        # Ambil paragraf sebelum tembusan/tanda tangan
        body = re.split(r"\nTembusan\s*:", body, maxsplit=1)[0]
        body = re.split(r"Demikian\s+(?:kami\s+)?disampaikan", body, maxsplit=1)[0]

        # Split per nomor poin
        paragraphs = re.split(r"\n(?=\d+\.)", body)
        result = []
        for p in paragraphs:
            p = re.sub(r"\s+", " ", p).strip()
            if len(p) > 20:
                result.append(p)
        return result[:10]  # max 10 poin

    @classmethod
    def _extract_poin_penting(cls, text: str) -> list[str]:
        """Ekstrak poin tindakan/action item."""
        poin = []

        # Cari kalimat yang mengandung kata kerja tindakan
        action_keywords = [
            "mohon", "diminta", "agar", "diharapkan", "harus",
            "wajib", "perlu", "segera", "melakukan", "menyampaikan",
            "melaksanakan", "memperhatikan", "berkoordinasi",
        ]
        sentences = re.split(r"[.;]\s*", text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 20:
                continue
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in action_keywords):
                clean = re.sub(r"\s+", " ", sent).strip()
                if len(clean) > 20 and clean not in poin:
                    poin.append(clean)

        return poin[:8]

    @classmethod
    def _extract_deadline(cls, text: str) -> list[str]:
        matches = cls.PATTERN_DEADLINE.findall(text)
        # Juga cari pola "tanggal DD Bulan YYYY"
        extra = re.findall(
            r"\b(\d{1,2}\s+(?:" + "|".join(cls.BULAN_ID.keys()) + r")\s+\d{4})\b",
            text, re.IGNORECASE
        )
        all_dates = list(set(matches + extra))
        return all_dates[:5]

    @classmethod
    def _extract_regulasi(cls, text: str) -> list[str]:
        matches = cls.PATTERN_REGULASI.findall(text)
        seen = set()
        result = []
        for m in matches:
            clean = re.sub(r"\s+", " ", m).strip()
            if clean not in seen and len(clean) > 10:
                seen.add(clean)
                result.append(clean)
        return result[:10]

    @classmethod
    def _extract_penandatangan(cls, text: str) -> str:
        m = cls.PATTERN_PENANDATANGAN.search(text)
        if m:
            return m.group(1).strip()
        # Fallback: nama setelah "elektronik"
        fallback = re.search(
            r"elektronik\s*\n\s*([\w\s.]+?)(?:\n|Tembusan)",
            text, re.IGNORECASE
        )
        return fallback.group(1).strip() if fallback else ""

    @classmethod
    def _extract_jabatan_ttd(cls, text: str) -> str:
        # Cari jabatan sebelum TTD
        patterns = [
            r"((?:Plt\.|Pjs\.)?\s*(?:Kepala|Direktur|Sekretaris|Inspektur)"
            r"[\w\s,./]+?)\s*\n\s*(?:u\.b\.|Ditandatangani)",
            r"(Sekretaris Jenderal[\s\S]{0,50}?u\.b\.\s*\n\s*[\w\s]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return re.sub(r"\s+", " ", m.group(1)).strip()
        return ""

    @classmethod
    def _extract_tembusan(cls, text: str) -> list[str]:
        m = cls.PATTERN_TEMBUSAN.search(text)
        if not m:
            return []
        raw = m.group(1).strip()
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        result = []
        for ln in lines:
            ln = re.sub(r"^\d+\.\s*", "", ln).strip()
            if ln and len(ln) > 3:
                result.append(ln)
        return result

    @classmethod
    def _extract_unit_asal(cls, text: str, dari: str) -> str:
        # Ambil dari field "Dari" jika ada
        if dari:
            return dari

        # Fallback: cari nama unit dari header dokumen
        lines = text.split("\n")[:10]
        for line in lines:
            line = line.strip()
            if any(kw in line.upper() for kw in
                   ["BADAN", "DIREKTORAT", "SEKRETARIAT", "INSPEKTORAT",
                    "PUSAT", "BIRO", "KEMENTERIAN"]):
                if len(line) > 10:
                    return line
        return ""

    @classmethod
    def _detect_jenis(cls, text: str) -> str:
        text_upper = text.upper()
        if "NOTA DINAS" in text_upper:
            return "Nota Dinas"
        elif "SURAT EDARAN" in text_upper:
            return "Surat Edaran"
        elif "SURAT KEPUTUSAN" in text_upper:
            return "Surat Keputusan"
        elif "INSTRUKSI" in text_upper:
            return "Instruksi"
        return "Surat Dinas"

    @classmethod
    def to_dict(cls, nd: NotaDinas) -> dict:
        return {
            "nomor":                  nd.nomor,
            "kepada":                 nd.kepada,
            "dari":                   nd.dari,
            "sifat":                  nd.sifat,
            "lampiran":               nd.lampiran,
            "hal":                    nd.hal,
            "tanggal":                nd.tanggal,
            "isi_pokok":              nd.isi_pokok,
            "poin_penting":           nd.poin_penting,
            "deadline":               nd.deadline,
            "referensi_regulasi":     nd.referensi_regulasi,
            "penandatangan":          nd.penandatangan,
            "jabatan_penandatangan":  nd.jabatan_penandatangan,
            "tembusan":               nd.tembusan,
            "unit_asal":              nd.unit_asal,
            "jenis_dokumen":          nd.jenis_dokumen,
        }