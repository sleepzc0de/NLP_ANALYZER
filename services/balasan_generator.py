import re
from datetime import datetime
from services.nota_dinas_extractor import NotaDinas


# Konversi angka ke romawi untuk nomor ND
ROMAWI = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",
          7:"VII",8:"VIII",9:"IX",10:"X",11:"XI",12:"XII"}

BULAN_ID = {
    1:"Januari",2:"Februari",3:"Maret",4:"April",
    5:"Mei",6:"Juni",7:"Juli",8:"Agustus",
    9:"September",10:"Oktober",11:"November",12:"Desember"
}


class BalasanGenerator:
    """
    Generate konsep balasan Nota Dinas Kemenkeu
    berdasarkan data terstruktur hasil ekstraksi.
    """

    @staticmethod
    def _today_str() -> str:
        now = datetime.now()
        return f"{now.day} {BULAN_ID[now.month]} {now.year}"

    @staticmethod
    def _detect_action_type(nd: NotaDinas) -> str:
        """Deteksi jenis tindak lanjut yang diminta."""
        hal_lower = nd.hal.lower()
        isi_text  = " ".join(nd.isi_pokok + nd.poin_penting).lower()

        if any(k in hal_lower for k in ["profil risiko", "risiko"]):
            return "profil_risiko"
        if any(k in hal_lower for k in ["rka", "rencana kerja", "anggaran", "pagu"]):
            return "rka_anggaran"
        if any(k in hal_lower for k in ["infrastruktur", "tik", "server", "jaringan"]):
            return "infrastruktur_tik"
        if any(k in hal_lower for k in ["matriks", "tindak lanjut"]):
            return "tindak_lanjut"
        if any(k in isi_text for k in ["mohon", "diminta", "usulan", "sampaikan"]):
            return "permintaan_data"
        return "umum"

    @classmethod
    def generate(cls, nd: NotaDinas, unit_pembalas: str = "",
                 nama_ttd: str = "", jabatan_ttd: str = "") -> dict:
        """
        Generate konsep balasan lengkap.
        Returns dict dengan berbagai versi/opsi balasan.
        """
        action_type = cls._detect_action_type(nd)
        today       = cls._today_str()

        # Nomor balasan otomatis (template)
        nomor_balasan = f"ND-[NOMOR]/{cls._extract_kode_unit(unit_pembalas)}/{datetime.now().year}"

        # Tentukan penerima balasan (balik dari→kepada)
        penerima = nd.dari if nd.dari else "Yang Terhormat"

        konsep_formal    = cls._buat_konsep_formal(
            nd, nomor_balasan, penerima, today,
            unit_pembalas, nama_ttd, jabatan_ttd, action_type
        )
        konsep_singkat   = cls._buat_konsep_singkat(
            nd, nomor_balasan, penerima, today,
            unit_pembalas, nama_ttd, jabatan_ttd, action_type
        )
        poin_balasan     = cls._buat_poin_balasan(nd, action_type)
        checklist_aksi   = cls._buat_checklist(nd, action_type)

        return {
            "action_type":    action_type,
            "nomor_balasan":  nomor_balasan,
            "penerima":       penerima,
            "tanggal":        today,
            "konsep_formal":  konsep_formal,
            "konsep_singkat": konsep_singkat,
            "poin_balasan":   poin_balasan,
            "checklist_aksi": checklist_aksi,
        }

    @staticmethod
    def _extract_kode_unit(unit: str) -> str:
        if not unit:
            return "XX.X"
        words = unit.upper().split()
        if len(words) >= 2:
            return f"{words[0][:2]}.{words[1][:1]}"
        return unit[:4].upper()

    @classmethod
    def _buat_konsep_formal(cls, nd: NotaDinas, nomor: str,
                             penerima: str, today: str,
                             unit_pembalas: str, nama_ttd: str,
                             jabatan_ttd: str, action_type: str) -> str:

        kepada_str = penerima
        dari_str   = jabatan_ttd or "[Jabatan Anda]"
        hal_balasan = cls._generate_hal_balasan(nd.hal)
        isi         = cls._generate_isi_formal(nd, action_type)
        ttd_nama    = nama_ttd or "[Nama Penandatangan]"
        ttd_jabatan = jabatan_ttd or "[Jabatan]"
        tembusan_str = ""
        if nd.kepada:
            tembusan_list = "\n".join(
                f"{'':4}{i+1}. {k}" for i, k in enumerate(nd.kepada[:3])
            )
            tembusan_str = f"\nTembusan:\n{tembusan_list}"

        return f"""NOTA DINAS
NOMOR {nomor}

Yth.  : {kepada_str}
Dari  : {dari_str}
Sifat : {nd.sifat or 'Biasa'}
Lampiran : -
Hal   : {hal_balasan}
Tanggal  : {today}

{isi}

Demikian kami sampaikan, atas perhatian dan kerja sama yang baik, kami ucapkan terima kasih.

{ttd_jabatan}

[Tanda Tangan Elektronik]
{ttd_nama}
{tembusan_str}"""

    @classmethod
    def _buat_konsep_singkat(cls, nd: NotaDinas, nomor: str,
                              penerima: str, today: str,
                              unit_pembalas: str, nama_ttd: str,
                              jabatan_ttd: str, action_type: str) -> str:

        hal_balasan = cls._generate_hal_balasan(nd.hal)
        isi         = cls._generate_isi_singkat(nd, action_type)
        ttd_nama    = nama_ttd or "[Nama Penandatangan]"
        ttd_jabatan = jabatan_ttd or "[Jabatan]"

        return f"""NOTA DINAS
NOMOR {nomor}

Yth.  : {penerima}
Dari  : {ttd_jabatan}
Sifat : {nd.sifat or 'Biasa'}
Hal   : {hal_balasan}
Tanggal  : {today}

{isi}

Demikian kami sampaikan.

{ttd_jabatan}
{ttd_nama}"""

    @staticmethod
    def _generate_hal_balasan(hal_asli: str) -> str:
        if not hal_asli:
            return "Tanggapan atas Nota Dinas"
        # Deteksi prefix permintaan
        prefixes = ["Permintaan ", "Penyampaian ", "Permohonan ", "Undangan "]
        for prefix in prefixes:
            if hal_asli.startswith(prefix):
                sisa = hal_asli[len(prefix):]
                return f"Penyampaian {sisa}"
        return f"Tanggapan atas {hal_asli}"

    @classmethod
    def _generate_isi_formal(cls, nd: NotaDinas, action_type: str) -> str:
        nd_ref = f"Nota Dinas Nomor {nd.nomor}" if nd.nomor else "nota dinas"
        tanggal_ref = f" tanggal {nd.tanggal}" if nd.tanggal else ""
        hal_ref = f" perihal {nd.hal}" if nd.hal else ""

        pembuka = (
            f"    Sehubungan dengan {nd_ref}{tanggal_ref}{hal_ref}, "
            f"dengan hormat kami sampaikan hal-hal sebagai berikut:"
        )

        if action_type == "profil_risiko":
            isi_poin = cls._isi_profil_risiko(nd)
        elif action_type == "rka_anggaran":
            isi_poin = cls._isi_rka_anggaran(nd)
        elif action_type == "infrastruktur_tik":
            isi_poin = cls._isi_infrastruktur(nd)
        elif action_type == "tindak_lanjut":
            isi_poin = cls._isi_tindak_lanjut(nd)
        elif action_type == "permintaan_data":
            isi_poin = cls._isi_permintaan_data(nd)
        else:
            isi_poin = cls._isi_umum(nd)

        return f"{pembuka}\n{isi_poin}"

    @classmethod
    def _generate_isi_singkat(cls, nd: NotaDinas, action_type: str) -> str:
        nd_ref = f"Nota Dinas Nomor {nd.nomor}" if nd.nomor else "nota dinas dimaksud"
        return (
            f"    Menindaklanjuti {nd_ref}, bersama ini kami sampaikan "
            f"bahwa kami telah menerima dan memahami substansi {nd.hal or 'surat dimaksud'}. "
            f"Kami akan segera menindaklanjuti sesuai ketentuan yang berlaku "
            f"dan berkoordinasi dengan pihak-pihak terkait.\n\n"
            f"    Apabila diperlukan informasi lebih lanjut, kami siap untuk berdiskusi "
            f"lebih lanjut sesuai kebutuhan."
        )

    # ── Template isi per jenis ────────────────────────────────────

    @staticmethod
    def _isi_profil_risiko(nd: NotaDinas) -> str:
        deadline = nd.deadline[0] if nd.deadline else "[tanggal batas waktu]"
        return f"""1. Kami telah menerima dan mencermati arahan mengenai penyusunan Profil Risiko \
sebagaimana disampaikan dalam nota dinas dimaksud.

2. Sehubungan dengan hal tersebut, bersama ini kami sampaikan hal-hal sebagai berikut:
   a. Kami akan menyusun Profil Risiko sesuai dengan Sasaran Strategis Organisasi \
pada unit kami, dengan memperhatikan ketentuan minimal 1 (satu) risiko per Sasaran Strategis;
   b. Penyusunan Profil Risiko akan mempertimbangkan risiko-risiko yang relevan, \
termasuk risiko fraud sebagaimana dipersyaratkan;
   c. Proses penyusunan akan dilakukan dengan melibatkan komunikasi dengan pimpinan unit, \
pemilik proses bisnis, dan pengelola kinerja;
   d. Upside risk akan disertai dengan rencana eksploitasi yang terukur.

3. Konsep Profil Risiko dimaksud akan kami sampaikan kepada Saudara paling lambat \
tanggal {deadline}, sesuai format yang telah ditentukan.

4. Demikian kami sampaikan sebagai bahan pertimbangan lebih lanjut."""

    @staticmethod
    def _isi_rka_anggaran(nd: NotaDinas) -> str:
        deadline = nd.deadline[0] if nd.deadline else "[batas waktu yang ditentukan]"
        return f"""1. Kami telah menerima dan mempelajari nota dinas dimaksud berkenaan dengan \
penyusunan Rencana Kerja dan Anggaran (RKA) Tahun Anggaran 2027.

2. Terkait hal tersebut, kami sampaikan hal-hal sebagai berikut:
   a. Kami akan segera menyusun RKA Satker/Unit sesuai ketentuan yang berlaku, \
dengan mempertimbangkan realisasi anggaran TA 2025 dan asas kepatutan, kewajaran, \
efektivitas, serta efisiensi anggaran;
   b. Penyusunan RKA akan berpedoman pada PMK tentang Standar Biaya Masukan TA 2026 \
sambil menunggu ditetapkannya PMK tentang Standar Biaya Masukan TA 2027;
   c. Kami akan memperhatikan dan memprioritaskan penyelesaian Konstruksi Dalam \
Pengerjaan (KDP) yang masih berjalan;
   d. Data-data tematik (lisensi aplikasi, kebutuhan pelatihan, dll.) akan kami siapkan \
sesuai format terlampir.

3. RKA Satker/Unit berikut dokumen pendukung akan kami sampaikan paling lambat \
{deadline}.

4. Apabila terdapat hal-hal yang memerlukan klarifikasi, kami akan segera berkoordinasi \
dengan Saudara."""

    @staticmethod
    def _isi_infrastruktur(nd: NotaDinas) -> str:
        return """1. Kami telah menerima dan mencermati matriks tindak lanjut One on One Meeting \
kebutuhan infrastruktur TIK sebagaimana disampaikan dalam lampiran nota dinas dimaksud.

2. Berkenaan dengan hal tersebut, kami sampaikan sebagai berikut:
   a. Kami menyetujui dan akan menindaklanjuti kesepakatan yang tertuang dalam \
matriks tindak lanjut dimaksud;
   b. Untuk kebutuhan infrastruktur TIK berupa server dan storage, kami akan \
mengupayakan penggunaan infrastruktur berbagi pakai melalui Kemenkeu Cloud Platform \
sesuai arahan;
   c. Dalam hal terdapat kebutuhan yang bersifat spesifik dan tidak dapat dipenuhi \
melalui shared service, kami akan melaksanakan penganggaran secara mandiri setelah \
berkoordinasi dengan Pusilki BaTii;
   d. Kami akan memastikan seluruh proses pengadaan infrastruktur TIK berpedoman \
pada regulasi yang berlaku, termasuk Perpres Nomor 46 Tahun 2025 dan ketentuan \
penggunaan produk dalam negeri.

3. Kami akan berkoordinasi lebih lanjut dengan unit terkait di BaTii untuk hal-hal \
teknis dalam pemenuhan kebutuhan infrastruktur TIK dimaksud."""

    @staticmethod
    def _isi_tindak_lanjut(nd: NotaDinas) -> str:
        return """1. Kami telah menerima dan mempelajari matriks tindak lanjut sebagaimana \
disampaikan dalam nota dinas dimaksud.

2. Kami menyampaikan bahwa:
   a. Seluruh poin yang tercantum dalam matriks tindak lanjut telah kami pahami \
dan akan kami tindaklanjuti sesuai dengan tugas dan fungsi unit kami;
   b. Kami akan segera melakukan koordinasi internal guna memastikan kesiapan \
unit dalam menindaklanjuti setiap poin yang menjadi tanggung jawab kami;
   c. Progres tindak lanjut akan kami sampaikan secara berkala sesuai mekanisme \
pelaporan yang berlaku.

3. Apabila terdapat hal-hal yang memerlukan klarifikasi atau pembahasan lebih lanjut, \
kami siap untuk berkoordinasi dengan Saudara."""

    @staticmethod
    def _isi_permintaan_data(nd: NotaDinas) -> str:
        deadline = nd.deadline[0] if nd.deadline else "[batas waktu yang ditentukan]"
        return f"""1. Kami telah menerima permintaan data/informasi sebagaimana dimaksud \
dalam nota dinas tersebut.

2. Sehubungan dengan hal dimaksud, kami sampaikan bahwa:
   a. Kami akan segera menyiapkan data/informasi yang diminta sesuai format \
yang telah ditentukan;
   b. Proses pengumpulan dan verifikasi data akan kami lakukan dengan cermat \
untuk memastikan akurasi dan kelengkapan data yang disampaikan;
   c. Data/informasi dimaksud akan kami sampaikan paling lambat {deadline}.

3. Apabila terdapat hal-hal yang perlu dikonfirmasi terkait format atau substansi \
data yang diminta, kami akan segera menghubungi Saudara untuk koordinasi lebih lanjut."""

    @staticmethod
    def _isi_umum(nd: NotaDinas) -> str:
        return """1. Kami telah menerima dan mempelajari nota dinas dimaksud dengan saksama.

2. Berkenaan dengan hal tersebut, kami sampaikan bahwa kami akan segera \
menindaklanjuti substansi nota dinas dimaksud sesuai dengan tugas, fungsi, \
dan kewenangan unit kami.

3. Kami akan memastikan bahwa seluruh tindak lanjut dilaksanakan dengan \
berpedoman pada ketentuan peraturan perundang-undangan yang berlaku.

4. Progres pelaksanaan tindak lanjut akan kami laporkan kepada Saudara \
sesuai mekanisme pelaporan yang telah ditentukan."""

    # ── Poin & Checklist ─────────────────────────────────────────

    @classmethod
    def _buat_poin_balasan(cls, nd: NotaDinas, action_type: str) -> list[str]:
        poin = [
            f"Merespons {nd.hal or 'nota dinas dimaksud'}",
            f"Dokumen referensi: {nd.nomor}" if nd.nomor else "Cantumkan nomor ND referensi",
        ]
        if nd.deadline:
            poin.append(f"Perhatikan batas waktu: {', '.join(nd.deadline)}")
        if nd.referensi_regulasi:
            poin.append(
                f"Berpedoman pada: {nd.referensi_regulasi[0]}"
                + (" (dan regulasi lainnya)" if len(nd.referensi_regulasi) > 1 else "")
            )
        poin.append("Lampirkan dokumen pendukung jika diperlukan")
        return poin

    @classmethod
    def _buat_checklist(cls, nd: NotaDinas, action_type: str) -> list[dict]:
        items = [
            {"item": f"Baca dan pahami isi ND {nd.nomor}", "prioritas": "Tinggi"},
            {"item": "Identifikasi poin-poin yang memerlukan tindak lanjut", "prioritas": "Tinggi"},
            {"item": "Koordinasi internal dengan unit terkait", "prioritas": "Sedang"},
        ]

        if action_type == "profil_risiko":
            items += [
                {"item": "Susun daftar Sasaran Strategis unit", "prioritas": "Tinggi"},
                {"item": "Identifikasi minimal 1 risiko per SS", "prioritas": "Tinggi"},
                {"item": "Susun rencana mitigasi (bukan rutinitas)", "prioritas": "Sedang"},
                {"item": "Identifikasi risiko fraud", "prioritas": "Tinggi"},
                {"item": "Komunikasi dengan pimpinan dan pemilik probis", "prioritas": "Sedang"},
            ]
        elif action_type == "rka_anggaran":
            items += [
                {"item": "Kumpulkan data realisasi anggaran TA 2025", "prioritas": "Tinggi"},
                {"item": "Susun proyeksi kebutuhan TA 2027", "prioritas": "Tinggi"},
                {"item": "Siapkan data tematik (lisensi, pelatihan, dll.)", "prioritas": "Sedang"},
                {"item": "Review KDP yang belum selesai", "prioritas": "Sedang"},
                {"item": "Submit RKA ke Biro Umum", "prioritas": "Tinggi"},
            ]
        elif action_type == "infrastruktur_tik":
            items += [
                {"item": "Review matriks tindak lanjut infrastruktur TIK", "prioritas": "Tinggi"},
                {"item": "Identifikasi kebutuhan shared service vs mandiri", "prioritas": "Tinggi"},
                {"item": "Koordinasi dengan Pusilki BaTii", "prioritas": "Sedang"},
                {"item": "Pastikan kesesuaian dengan regulasi pengadaan", "prioritas": "Sedang"},
            ]

        if nd.deadline:
            items.append({
                "item": f"Selesaikan sebelum {nd.deadline[0]}",
                "prioritas": "Tinggi"
            })

        items += [
            {"item": "Susun draft balasan nota dinas", "prioritas": "Sedang"},
            {"item": "Review dan finalisasi draft balasan", "prioritas": "Sedang"},
            {"item": "Kirim balasan dengan tanda tangan elektronik", "prioritas": "Tinggi"},
        ]

        return items