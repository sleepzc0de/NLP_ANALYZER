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