$(function () {

  let currentAnalysis = null;
  let savedDocId      = null;
  let selectedFile    = null; // ← simpan file di variabel terpisah

  /* ── Toast ── */
  function showToast(message, type = "success") {
    const colors = {
      success: "bg-emerald-50 border-emerald-200 text-emerald-800",
      error:   "bg-rose-50 border-rose-200 text-rose-800",
      info:    "bg-sky-50 border-sky-200 text-sky-700",
      warning: "bg-amber-50 border-amber-200 text-amber-800",
    };
    const $t = $("#toast");
    $t.attr("class",
      `fixed top-20 right-6 z-50 min-w-72 px-5 py-4 rounded-2xl shadow-xl
       border text-sm font-medium transition-all ${colors[type] || colors.info}`
    ).text(message).removeClass("hidden");
    setTimeout(() => $t.addClass("hidden"), 4000);
  }

  /* ── Loading ── */
  function setLoading(loading) {
    $("#btnAnalyze").prop("disabled", loading);
    $("#analyzeText").toggleClass("hidden", loading);
    $("#analyzeLoading").toggleClass("hidden", !loading);
  }

  function sentimentStyle(s) {
    return { Positive: "bg-emerald-100 text-emerald-700",
             Negative: "bg-rose-100 text-rose-700",
             Neutral:  "bg-slate-100 text-slate-600" }[s]
           || "bg-slate-100 text-slate-600";
  }

  /* ════ TABS UTAMA ════ */
  $(".tab-btn[data-target]").on("click", function () {
    $(".tab-btn[data-target]").removeClass("active");
    $(this).addClass("active");
    $("#sectionUpload, #sectionHistory").addClass("hidden");
    $(`#${$(this).data("target")}`).removeClass("hidden");
    if ($(this).data("target") === "sectionHistory") loadHistory();
  });

  /* ════ RESULT INNER TABS ════ */
  $(document).on("click", ".result-tab-btn", function () {
    $(".result-tab-btn").removeClass("active");
    $(this).addClass("active");
    $(".result-tab-content").addClass("hidden");
    $(`#${$(this).data("rtarget")}`).removeClass("hidden");
  });

  /* ════════════════════════════════════════
     FILE SELECT & DRAG DROP
     - selectedFile menyimpan File object
     - fileInput murni sebagai trigger klik
  ════════════════════════════════════════ */
  const $dropzone  = $("#dropzone");
  const $fileInput = $("#fileInput");

  /* Klik dropzone → buka file dialog */
  $dropzone.on("click", function (e) {
    if ($(e.target).closest("#clearFile").length) return;
    $fileInput.trigger("click");
  });

  /* File dipilih via dialog */
  $fileInput.on("change", function () {
    if (this.files && this.files.length > 0) {
      handleFile(this.files[0]);
    }
  });

  /* Drag over */
  $dropzone.on("dragover dragenter", function (e) {
    e.preventDefault();
    e.stopPropagation();
    $(this).addClass("border-sky-400 bg-sky-50");
  });

  $dropzone.on("dragleave dragend", function (e) {
    e.preventDefault();
    $(this).removeClass("border-sky-400 bg-sky-50");
  });

  /* Drop */
  $dropzone.on("drop", function (e) {
    e.preventDefault();
    e.stopPropagation();
    $(this).removeClass("border-sky-400 bg-sky-50");
    const files = e.originalEvent.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  });

  /* ── handleFile: validasi & simpan ke selectedFile ── */
  function handleFile(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "doc"].includes(ext)) {
      showToast("Format tidak didukung. Gunakan PDF atau DOCX.", "error");
      return;
    }
    if (file.size === 0) {
      showToast("File kosong (0 bytes).", "error");
      return;
    }
    if (file.size > 16 * 1024 * 1024) {
      showToast("File terlalu besar. Maksimal 16MB.", "error");
      return;
    }

    // ← Simpan di variabel JS, bukan di input
    selectedFile = file;

    const sizeKB = (file.size / 1024).toFixed(1);
    $("#fileName").text(`${file.name} (${sizeKB} KB)`);
    $("#filePreview").removeClass("hidden");
    $("#btnAnalyze").prop("disabled", false);
    $("#resultCard").addClass("hidden");
    currentAnalysis = null;
    savedDocId      = null;
  }

  /* Clear file */
  $("#clearFile").on("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    selectedFile = null;
    $fileInput.val("");
    $("#filePreview").addClass("hidden");
    $("#btnAnalyze").prop("disabled", true);
    $("#resultCard").addClass("hidden");
    currentAnalysis = null;
    savedDocId      = null;
  });

  /* ════════════════════════════════════════
     NOTA DINAS — File Handling
  ════════════════════════════════════════ */
  let selectedFileND  = null;
  let currentNDData   = null;

  const $dropzoneND  = $("#dropzoneND");
  const $fileInputND = $("#fileInputND");

  $dropzoneND.on("click", function (e) {
    if ($(e.target).closest("#clearFileND").length) return;
    $fileInputND.trigger("click");
  });

  $fileInputND.on("change", function () {
    if (this.files && this.files.length > 0) handleFileND(this.files[0]);
  });

  $dropzoneND.on("dragover dragenter", function (e) {
    e.preventDefault(); e.stopPropagation();
    $(this).addClass("border-violet-400 bg-violet-50");
  });
  $dropzoneND.on("dragleave dragend", function (e) {
    e.preventDefault();
    $(this).removeClass("border-violet-400 bg-violet-50");
  });
  $dropzoneND.on("drop", function (e) {
    e.preventDefault(); e.stopPropagation();
    $(this).removeClass("border-violet-400 bg-violet-50");
    const files = e.originalEvent.dataTransfer.files;
    if (files && files.length > 0) handleFileND(files[0]);
  });

  function handleFileND(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "doc"].includes(ext)) {
      showToast("Format tidak didukung. Gunakan PDF atau DOCX.", "error");
      return;
    }
    selectedFileND = file;
    const sizeKB = (file.size / 1024).toFixed(1);
    $("#fileNameND").text(`${file.name} (${sizeKB} KB)`);
    $("#filePreviewND").removeClass("hidden");
    $("#btnExtractND").prop("disabled", false);
    $("#ndResultCard").addClass("hidden");
    currentNDData = null;
  }

  $("#clearFileND").on("click", function (e) {
    e.preventDefault(); e.stopPropagation();
    selectedFileND = null;
    $fileInputND.val("");
    $("#filePreviewND").addClass("hidden");
    $("#btnExtractND").prop("disabled", true);
    $("#ndResultCard").addClass("hidden");
  });

  /* ════ EXTRACT NOTA DINAS ════ */
  $("#btnExtractND").on("click", function () {
    if (!selectedFileND) {
      showToast("Pilih file Nota Dinas terlebih dahulu.", "warning");
      return;
    }

    const fd = new FormData();
    fd.append("file", selectedFileND, selectedFileND.name);

    $("#btnExtractND").prop("disabled", true);
    $("#extractNDText").addClass("hidden");
    $("#extractNDLoading").removeClass("hidden");

    // Step 1: Upload & ekstrak teks
    $.ajax({
      url: "/api/upload",
      method: "POST",
      data: fd,
      processData: false,
      contentType: false,
      timeout: 120000,
      success: function (res) {
        // Step 2: Ekstrak struktur Nota Dinas
        $.ajax({
          url: "/api/extract-nota-dinas",
          method: "POST",
          contentType: "application/json",
          data: JSON.stringify({ text: res.full_text }),
          success: function (ndRes) {
            currentNDData = {
              nota_dinas: ndRes.nota_dinas,
              full_text:  res.full_text,
            };
            renderNotaDinas(ndRes.nota_dinas);
            showToast("✅ Nota Dinas berhasil dianalisis!", "success");
          },
          error: function (xhr) {
            showToast(xhr.responseJSON?.error || "Gagal mengekstrak struktur.", "error");
          }
        });
      },
      error: function (xhr) {
        const msg = xhr.responseJSON?.error || "Gagal memproses file.";
        showToast(msg, "error");
      },
      complete: function () {
        $("#btnExtractND").prop("disabled", false);
        $("#extractNDText").removeClass("hidden");
        $("#extractNDLoading").addClass("hidden");
      }
    });
  });

  /* ════ RENDER NOTA DINAS ════ */
  function renderNotaDinas(nd) {
    // Header info
    $("#ndJenis").text(nd.jenis_dokumen || "Nota Dinas");
    $("#ndNomor").text(nd.nomor || "Nomor tidak terdeteksi");
    $("#ndHal").text(nd.hal || "—");
    $("#ndSifat").text(nd.sifat || "Biasa");
    $("#ndDari").text(nd.dari || "—");
    $("#ndTanggal").text(nd.tanggal || "—");
    $("#ndTTD").text(nd.penandatangan || "—");
    $("#ndDeadline").text(
      nd.deadline?.length ? nd.deadline.join(", ") : "Tidak ada batas waktu"
    );

    // Kepada
    const kepadaHtml = (nd.kepada || []).length
      ? nd.kepada.map((k, i) =>
          `<div class="flex gap-3 items-start px-4 py-2.5 bg-slate-50 rounded-xl">
             <span class="badge bg-violet-100 text-violet-700 shrink-0 mt-0.5">${i+1}</span>
             <span class="text-sm text-slate-700">${k}</span>
           </div>`
        ).join("")
      : "<p class='text-slate-400 text-sm'>Tidak terdeteksi</p>";
    $("#ndKepadaList").html(kepadaHtml);

    // Isi Pokok
    const isiHtml = (nd.isi_pokok || []).length
      ? nd.isi_pokok.map((p, i) =>
          `<div class="px-4 py-3 bg-slate-50 rounded-xl border-l-3 border-violet-300">
             <p class="text-sm text-slate-700 leading-relaxed">${p}</p>
           </div>`
        ).join("")
      : "<p class='text-slate-400 text-sm'>Tidak terdeteksi</p>";
    $("#ndIsiList").html(isiHtml);

    // Poin Aksi
    const poinHtml = (nd.poin_penting || []).length
      ? nd.poin_penting.map(p =>
          `<div class="flex gap-3 items-start px-4 py-2.5 bg-amber-50 rounded-xl border border-amber-100">
             <span class="text-amber-500 shrink-0">⚡</span>
             <span class="text-sm text-slate-700">${p}</span>
           </div>`
        ).join("")
      : "<p class='text-slate-400 text-sm'>Tidak ada poin aksi terdeteksi</p>";
    $("#ndPoinList").html(poinHtml);

    // Regulasi
    const regHtml = (nd.referensi_regulasi || []).length
      ? nd.referensi_regulasi.map(r =>
          `<div class="flex gap-3 items-start px-4 py-2.5 bg-blue-50 rounded-xl">
             <span class="text-blue-500 shrink-0">📜</span>
             <span class="text-xs text-slate-600">${r}</span>
           </div>`
        ).join("")
      : "<p class='text-slate-400 text-sm'>Tidak ada referensi regulasi</p>";
    $("#ndRegulasiList").html(regHtml);

    // Tembusan
    const tembusanHtml = (nd.tembusan || []).length
      ? nd.tembusan.map(t =>
          `<div class="flex gap-3 items-center px-4 py-2 bg-slate-50 rounded-xl">
             <span class="text-slate-400">→</span>
             <span class="text-sm text-slate-600">${t}</span>
           </div>`
        ).join("")
      : "<p class='text-slate-400 text-sm'>Tidak ada tembusan</p>";
    $("#ndTembusanList").html(tembusanHtml);

    // Tampilkan section hasil
    $(".nd-tab-btn").first().trigger("click");
    $("#ndResultCard").removeClass("hidden");
    $("html, body").animate({ scrollTop: $("#ndResultCard").offset().top - 80 }, 400);
  }

  /* ════ ND INNER TABS ════ */
  $(document).on("click", ".nd-tab-btn", function () {
    $(".nd-tab-btn").removeClass("active");
    $(this).addClass("active");
    $(".nd-tab-content").addClass("hidden");
    $(`#${$(this).data("ndtarget")}`).removeClass("hidden");
  });

  /* ════ BALASAN TABS ════ */
  $(document).on("click", ".balasan-tab-btn", function () {
    $(".balasan-tab-btn").removeClass("active");
    $(this).addClass("active");
    $(".balasan-tab-content").addClass("hidden");
    $(`#${$(this).data("btarget")}`).removeClass("hidden");
  });

  /* ════ GENERATE BALASAN ════ */
  $("#btnGenerateBalasan").on("click", function () {
    if (!currentNDData) {
      showToast("Upload Nota Dinas terlebih dahulu.", "warning");
      return;
    }

    const unit     = $("#inputUnitPembalas").val().trim();
    const nama     = $("#inputNamaTTD").val().trim();
    const jabatan  = $("#inputJabatanTTD").val().trim();

    $("#btnGenerateBalasan").prop("disabled", true);
    $("#balasanText").addClass("hidden");
    $("#balasanLoading").removeClass("hidden");

    $.ajax({
      url: "/api/generate-balasan",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({
        nota_dinas_data: currentNDData.nota_dinas,
        text:            currentNDData.full_text,
        unit_pembalas:   unit,
        nama_ttd:        nama,
        jabatan_ttd:     jabatan,
      }),
      success: function (res) {
        renderBalasan(res.balasan);
        showToast("✅ Konsep balasan berhasil dibuat!", "success");
      },
      error: function (xhr) {
        showToast(xhr.responseJSON?.error || "Gagal generate balasan.", "error");
      },
      complete: function () {
        $("#btnGenerateBalasan").prop("disabled", false);
        $("#balasanText").removeClass("hidden");
        $("#balasanLoading").addClass("hidden");
      }
    });
  });

  /* ════ RENDER BALASAN ════ */
  function renderBalasan(balasan) {
    $("#balasanFormal").val(balasan.konsep_formal || "");
    $("#balasanSingkat").val(balasan.konsep_singkat || "");

    // Checklist
    const cl = balasan.checklist_aksi || [];
    const clHtml = cl.map(item => {
      const color = item.prioritas === "Tinggi"
        ? "bg-rose-50 border-rose-200 text-rose-600"
        : "bg-slate-50 border-slate-200 text-slate-500";
      return `
        <div class="flex items-center gap-3 px-4 py-3 rounded-xl border ${color}">
          <input type="checkbox" class="w-4 h-4 rounded accent-emerald-500" />
          <span class="text-sm flex-1">${item.item}</span>
          <span class="badge text-xs ${
            item.prioritas === "Tinggi"
              ? "bg-rose-100 text-rose-600"
              : "bg-slate-100 text-slate-500"
          }">${item.prioritas}</span>
        </div>`;
    }).join("");
    $("#checklistContainer").html(clHtml);

    $(".balasan-tab-btn").first().trigger("click");
    $("#balasanResultCard").removeClass("hidden");
    $("html, body").animate(
      { scrollTop: $("#balasanResultCard").offset().top - 80 }, 400
    );
  }

  /* ════ COPY BALASAN ════ */
  $("#btnCopyBalasan").on("click", function () {
    const activeTab = $(".balasan-tab-content:not(.hidden)");
    const textarea  = activeTab.find("textarea");
    if (textarea.length) {
      navigator.clipboard.writeText(textarea.val())
        .then(() => showToast("✅ Teks berhasil disalin!", "success"))
        .catch(() => showToast("Gagal menyalin.", "error"));
    }
  });

  /* ════════════════════════════════════════
     ANALYZE — pakai selectedFile langsung
  ════════════════════════════════════════ */
  $("#btnAnalyze").on("click", function () {
    // Cek selectedFile (dari drag drop ATAU file dialog)
    if (!selectedFile) {
      showToast("Pilih file terlebih dahulu.", "warning");
      return;
    }

    console.log("📤 Uploading:", selectedFile.name, selectedFile.size, "bytes");

    const fd = new FormData();
    fd.append("file", selectedFile, selectedFile.name);

    setLoading(true);
    savedDocId = null;
    $("#savedDocInfo").addClass("hidden");

    $.ajax({
      url: "/api/upload",
      method: "POST",
      data: fd,
      processData: false,
      contentType: false,
      timeout: 120000,
      xhr: function () {
        const xhr = new window.XMLHttpRequest();
        xhr.upload.addEventListener("progress", function (e) {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            $("#analyzeLoading").text(`⏳ Upload ${pct}%...`);
          }
        });
        return xhr;
      },
      success: function (res) {
        console.log("✅ Success:", res);
        currentAnalysis = res;
        renderResult(res);
        showToast("✅ Analisis selesai!", "success");
      },
      error: function (xhr, status, error) {
        console.error("❌ Error:", status, error, xhr.responseText);
        let msg = "Gagal menganalisis dokumen.";
        try {
          msg = JSON.parse(xhr.responseText).error || msg;
        } catch (_) {
          if (status === "timeout") msg = "Timeout. Coba file yang lebih kecil.";
          else msg = `Error: ${status}`;
        }
        showToast(msg, "error");
      },
      complete: function () {
        setLoading(false);
        $("#analyzeLoading").text("⏳ Menganalisis...");
      }
    });
  });

  /* ════ RENDER RESULT ════ */
  function renderResult(data) {
    $("#resultFilename").text(data.filename || "Unknown");
    $("#sentimentBadge")
      .attr("class", `badge text-sm px-3 py-1 ${sentimentStyle(data.sentiment)}`)
      .text(`Sentimen: ${data.sentiment || "—"}`);

    $("#summaryText").text(data.summary || "Tidak ada ringkasan.");

    const kw = data.keywords || [];
    const colors = [
      "bg-sky-100 text-sky-700","bg-violet-100 text-violet-700",
      "bg-emerald-100 text-emerald-700","bg-amber-100 text-amber-700",
      "bg-rose-100 text-rose-700","bg-indigo-100 text-indigo-700",
    ];
    $("#keywordsContainer").html(
      kw.length
        ? kw.map((k, i) => `<span class="badge ${colors[i%colors.length]} text-sm py-1 px-3">${k}</span>`).join("")
        : "<span class='text-slate-400 text-sm'>Tidak ada kata kunci.</span>"
    );

    const ents = data.entities || [];
    $("#entitiesContainer").html(
      ents.length
        ? ents.map(e =>
            `<div class="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
               <span class="badge bg-indigo-100 text-indigo-700 shrink-0">${e.label}</span>
               <span class="text-sm text-slate-700 font-medium">${e.text}</span>
               <span class="text-xs text-slate-400 ml-auto">${e.description}</span>
             </div>`
          ).join("")
        : "<span class='text-slate-400 text-sm'>Tidak ada entitas.</span>"
    );

    $("#enrichedText").text(data.enriched_info || "");
    $("#rawTextArea").val(data.full_text || "");

    $(".result-tab-btn").first().trigger("click");
    $("#resultCard").removeClass("hidden");
    $("html, body").animate({ scrollTop: $("#resultCard").offset().top - 80 }, 400);
  }

  /* ════ SAVE ════ */
  function saveDocument(analysis, callback) {
    if (!analysis) return showToast("Tidak ada data.", "warning");
    $.ajax({
      url: "/api/save",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({
        filename:      analysis.filename,
        full_text:     analysis.full_text,
        summary:       analysis.summary,
        keywords:      analysis.keywords,
        entities:      analysis.entities,
        sentiment:     analysis.sentiment,
        enriched_info: analysis.enriched_info,
        file_type:     analysis.file_type,
      }),
      success: function (res) {
        savedDocId = res.document.id;
        currentAnalysis.doc_id = savedDocId;
        $("#savedDocId").text(savedDocId);
        $("#savedDocInfo").removeClass("hidden");
        showToast(`✅ Dokumen disimpan (ID: ${savedDocId})`, "success");
        if (callback) callback(res);
      },
      error: function (xhr) {
        showToast(xhr.responseJSON?.error || "Gagal menyimpan.", "error");
      }
    });
  }

  $("#btnSaveOnly").on("click",     () => saveDocument(currentAnalysis));
  $("#btnRegenerate").on("click",   () => regenerateAnalysis(savedDocId));
  $("#btnSaveThenRegen").on("click", function () {
    saveDocument(currentAnalysis, () => setTimeout(() => regenerateAnalysis(savedDocId), 600));
  });

  /* ════ REGENERATE ════ */
  function regenerateAnalysis(docId) {
    const text = $("#rawTextArea").val().trim();
    if (!text) return showToast("Teks kosong.", "warning");
    showToast("🔄 Menganalisis ulang...", "info");
    $.ajax({
      url: "/api/regenerate",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({
        full_text: text,
        filename:  currentAnalysis?.filename || "unknown",
        doc_id:    docId || null,
      }),
      timeout: 120000,
      success: function (res) {
        currentAnalysis = { ...currentAnalysis, ...res };
        renderResult(currentAnalysis);
        showToast("✅ Generate ulang selesai!", "success");
      },
      error: function (xhr) {
        showToast(xhr.responseJSON?.error || "Gagal regenerate.", "error");
      }
    });
  }

  /* ════ HISTORY ════ */
  function loadHistory() {
    $("#historyLoading").removeClass("hidden");
    $("#historyEmpty").addClass("hidden");
    $("#historyList").empty().addClass("hidden");

    $.get("/api/documents", function (res) {
      const docs = res.documents || [];
      $("#historyLoading").addClass("hidden");
      if (!docs.length) { $("#historyEmpty").removeClass("hidden"); return; }

      $("#historyList").html(docs.map(doc => `
        <div class="flex items-center gap-4 px-5 py-4 rounded-xl border border-slate-100
                    bg-white hover:border-sky-200 hover:shadow-sm transition-all">
          <div class="w-10 h-10 rounded-xl bg-sky-50 flex items-center justify-center shrink-0">
            <span class="text-xl">${doc.file_type === "pdf" ? "📄" : "📝"}</span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-slate-800 truncate">${doc.filename}</p>
            <p class="text-xs text-slate-400 mt-0.5">
              ID: ${doc.id} · ${new Date(doc.created_at).toLocaleString("id-ID")}
            </p>
          </div>
          <span class="badge ${sentimentStyle(doc.sentiment)} hidden sm:inline-flex">
            ${doc.sentiment || "—"}
          </span>
          <div class="flex gap-2 shrink-0">
            <button class="btn-secondary text-xs py-1.5 px-3 btn-view-doc" data-id="${doc.id}">👁 Detail</button>
            <button class="btn-danger text-xs py-1.5 px-3 btn-delete-doc" data-id="${doc.id}">🗑</button>
          </div>
        </div>`
      ).join("")).removeClass("hidden");
    }).fail(() => {
      $("#historyLoading").addClass("hidden");
      showToast("Gagal memuat riwayat.", "error");
    });
  }

  $("#btnRefreshHistory").on("click", loadHistory);

  $(document).on("click", ".btn-view-doc", function () {
    $.get(`/api/documents/${$(this).data("id")}`, function (doc) {
      const kw   = (doc.keywords || []).join(", ") || "—";
      const ents = (doc.entities || [])
        .map(e => `<span class='badge bg-indigo-100 text-indigo-700 mr-1 mb-1'>${e.text} (${e.label})</span>`)
        .join("") || "—";
      $("#modalTitle").text(doc.filename);
      $("#modalBody").html(`
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><p class="text-slate-400">File Type</p>
               <p class="font-semibold text-slate-700 mt-1 uppercase">${doc.file_type||"—"}</p></div>
          <div><p class="text-slate-400">Sentimen</p>
               <p class="mt-1"><span class="badge ${sentimentStyle(doc.sentiment)}">${doc.sentiment||"—"}</span></p></div>
          <div class="col-span-2"><p class="text-slate-400">Dibuat</p>
               <p class="font-medium text-slate-700 mt-1">${new Date(doc.created_at).toLocaleString("id-ID")}</p></div>
        </div>
        <div><p class="text-slate-400 text-sm mb-2">Ringkasan</p>
             <div class="bg-slate-50 rounded-xl p-4 text-sm text-slate-700 leading-relaxed">${doc.summary||"—"}</div></div>
        <div><p class="text-slate-400 text-sm mb-2">Kata Kunci</p>
             <p class="text-sm text-slate-700">${kw}</p></div>
        <div><p class="text-slate-400 text-sm mb-2">Entitas</p>
             <div class="flex flex-wrap gap-1">${ents}</div></div>
        <div><p class="text-slate-400 text-sm mb-2">Cuplikan Teks</p>
             <div class="bg-slate-50 rounded-xl p-4 text-xs text-slate-600 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">${doc.original_text||"—"}</div></div>
      `);
      $("#detailModal").removeClass("hidden").addClass("flex");
    }).fail(() => showToast("Gagal memuat detail.", "error"));
  });

  $(document).on("click", ".btn-delete-doc", function () {
    const id = $(this).data("id");
    if (!confirm(`Hapus dokumen ID ${id}?`)) return;
    $.ajax({
      url: `/api/documents/${id}`, method: "DELETE",
      success: () => { showToast(`Dokumen ID ${id} dihapus.`, "info"); loadHistory(); },
      error:   () => showToast("Gagal menghapus.", "error")
    });
  });

  $("#closeModal").on("click", () => $("#detailModal").addClass("hidden").removeClass("flex"));
  $("#detailModal").on("click", function (e) {
    if ($(e.target).is(this)) $(this).addClass("hidden").removeClass("flex");
  });

  $.get("/api/health", res => console.log("✅ API OK:", res));
});