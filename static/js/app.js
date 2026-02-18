/* ═══════════════════════════════════════════════════
   DocAnalyzer — Main Application Script
   jQuery 3.7.1 + Flask API
═══════════════════════════════════════════════════ */

$(function () {

  /* ── State ── */
  let currentAnalysis = null;
  let savedDocId = null;

  /* ════════════════════════
     UTILS
  ════════════════════════ */
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
    setTimeout(() => $t.addClass("hidden"), 3500);
  }

  function setLoading(loading) {
    $("#btnAnalyze").prop("disabled", loading);
    $("#analyzeText").toggleClass("hidden", loading);
    $("#analyzeLoading").toggleClass("hidden", !loading);
  }

  function sentimentStyle(sentiment) {
    const map = {
      "Positive": "bg-emerald-100 text-emerald-700",
      "Negative": "bg-rose-100 text-rose-700",
      "Neutral":  "bg-slate-100 text-slate-600",
    };
    return map[sentiment] || "bg-slate-100 text-slate-600";
  }

  /* ════════════════════════
     TABS (main)
  ════════════════════════ */
  $(".tab-btn[data-target]").on("click", function () {
    const target = $(this).data("target");
    $(".tab-btn[data-target]").removeClass("active");
    $(this).addClass("active");
    $("#sectionUpload, #sectionHistory").addClass("hidden");
    $(`#${target}`).removeClass("hidden");

    if (target === "sectionHistory") loadHistory();
  });

  /* ════════════════════════
     RESULT INNER TABS
  ════════════════════════ */
  $(document).on("click", ".result-tab-btn", function () {
    $(".result-tab-btn").removeClass("active");
    $(this).addClass("active");
    $(".result-tab-content").addClass("hidden");
    $(`#${$(this).data("rtarget")}`).removeClass("hidden");
  });

  /* ════════════════════════
     FILE DROP / SELECT
  ════════════════════════ */
  const $dropzone = $("#dropzone");
  const $fileInput = $("#fileInput");

  $dropzone.on("click", () => $fileInput.trigger("click"));

  $dropzone.on("dragover dragenter", function (e) {
    e.preventDefault();
    $(this).addClass("border-sky-400 bg-sky-50");
  }).on("dragleave drop", function (e) {
    e.preventDefault();
    $(this).removeClass("border-sky-400 bg-sky-50");
    if (e.type === "drop") {
      const file = e.originalEvent.dataTransfer.files[0];
      if (file) setFile(file);
    }
  });

  $fileInput.on("change", function () {
    if (this.files[0]) setFile(this.files[0]);
  });

  function setFile(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "doc"].includes(ext)) {
      showToast("Format tidak didukung. Gunakan PDF atau DOCX.", "error");
      return;
    }
    $("#fileName").text(file.name);
    $("#filePreview").removeClass("hidden");
    $("#btnAnalyze").prop("disabled", false);
  }

  $("#clearFile").on("click", function (e) {
    e.stopPropagation();
    $fileInput.val("");
    $("#filePreview").addClass("hidden");
    $("#btnAnalyze").prop("disabled", true);
    $("#resultCard").addClass("hidden");
    currentAnalysis = null;
    savedDocId = null;
  });

  /* ════════════════════════
     ANALYZE
  ════════════════════════ */
  $("#btnAnalyze").on("click", function () {
    const file = $fileInput[0].files[0];
    if (!file) return showToast("Pilih file terlebih dahulu.", "warning");

    const fd = new FormData();
    fd.append("file", file);

    setLoading(true);
    savedDocId = null;
    $("#savedDocInfo").addClass("hidden");

    $.ajax({
      url: "/api/upload",
      method: "POST",
      data: fd,
      processData: false,
      contentType: false,
      success(res) {
        currentAnalysis = res;
        renderResult(res);
        showToast("Analisis selesai!", "success");
      },
      error(xhr) {
        const msg = xhr.responseJSON?.error || "Gagal menganalisis dokumen.";
        showToast(msg, "error");
      },
      complete() {
        setLoading(false);
      }
    });
  });

  /* ════════════════════════
     RENDER RESULT
  ════════════════════════ */
  function renderResult(data) {
    /* header */
    $("#resultFilename").text(data.filename);
    $("#sentimentBadge")
      .attr("class", `badge text-sm px-3 py-1 ${sentimentStyle(data.sentiment)}`)
      .text(`Sentimen: ${data.sentiment}`);

    /* summary */
    $("#summaryText").text(data.summary || "Tidak ada ringkasan.");

    /* keywords */
    const kw = data.keywords || [];
    const colors = [
      "bg-sky-100 text-sky-700", "bg-violet-100 text-violet-700",
      "bg-emerald-100 text-emerald-700", "bg-amber-100 text-amber-700",
      "bg-rose-100 text-rose-700", "bg-indigo-100 text-indigo-700",
    ];
    const kwHtml = kw.map((k, i) =>
      `<span class="badge ${colors[i % colors.length]} text-sm py-1 px-3">${k}</span>`
    ).join("");
    $("#keywordsContainer").html(kwHtml || "<span class='text-slate-400 text-sm'>Tidak ada kata kunci.</span>");

    /* entities */
    const ents = data.entities || [];
    const entHtml = ents.map(e =>
      `<div class="flex items-center gap-3 px-4 py-3 bg-slate-50 rounded-xl">
         <span class="badge bg-indigo-100 text-indigo-700 shrink-0">${e.label}</span>
         <span class="text-sm text-slate-700 font-medium">${e.text}</span>
         <span class="text-xs text-slate-400 ml-auto">${e.description}</span>
       </div>`
    ).join("");
    $("#entitiesContainer").html(entHtml || "<span class='text-slate-400 text-sm'>Tidak ada entitas terdeteksi.</span>");

    /* enriched */
    $("#enrichedText").text(data.enriched_info || "");

    /* raw text */
    $("#rawTextArea").val(data.full_text || "");

    /* show card, reset to first tab */
    $(".result-tab-btn").first().trigger("click");
    $("#resultCard").removeClass("hidden");
    $("html, body").animate({ scrollTop: $("#resultCard").offset().top - 80 }, 400);
  }

  /* ════════════════════════
     SAVE
  ════════════════════════ */
  function saveDocument(analysis, callback) {
    if (!analysis) return showToast("Tidak ada data untuk disimpan.", "warning");

    $.ajax({
      url: "/api/save",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(analysis),
      success(res) {
        savedDocId = res.document.id;
        currentAnalysis.doc_id = savedDocId;
        $("#savedDocId").text(savedDocId);
        $("#savedDocInfo").removeClass("hidden");
        showToast(`Dokumen disimpan (ID: ${savedDocId})`, "success");
        if (callback) callback(res);
      },
      error(xhr) {
        showToast(xhr.responseJSON?.error || "Gagal menyimpan.", "error");
      }
    });
  }

  $("#btnSaveOnly").on("click", function () {
    saveDocument(currentAnalysis);
  });

  /* ════════════════════════
     REGENERATE
  ════════════════════════ */
  function regenerateAnalysis(docId) {
    const textToAnalyze = $("#rawTextArea").val().trim();
    if (!textToAnalyze) return showToast("Teks kosong untuk dianalisis ulang.", "warning");

    const payload = {
      full_text: textToAnalyze,
      filename: currentAnalysis?.filename || "unknown",
      doc_id: docId || null,
    };

    showToast("Menganalisis ulang...", "info");

    $.ajax({
      url: "/api/regenerate",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(payload),
      success(res) {
        currentAnalysis = { ...currentAnalysis, ...res };
        renderResult(currentAnalysis);
        showToast("Generate ulang selesai!", "success");
      },
      error(xhr) {
        showToast(xhr.responseJSON?.error || "Gagal generate ulang.", "error");
      }
    });
  }

  $("#btnRegenerate").on("click", function () {
    regenerateAnalysis(savedDocId || null);
  });

  /* ════════════════════════
     SAVE + REGENERATE
  ════════════════════════ */
  $("#btnSaveThenRegen").on("click", function () {
    saveDocument(currentAnalysis, function () {
      setTimeout(() => regenerateAnalysis(savedDocId), 500);
    });
  });

  /* ════════════════════════
     HISTORY
  ════════════════════════ */
  function loadHistory() {
    $("#historyLoading").removeClass("hidden");
    $("#historyEmpty").addClass("hidden");
    $("#historyList").empty();

    $.get("/api/documents", function (res) {
      const docs = res.documents || [];
      $("#historyLoading").addClass("hidden");

      if (!docs.length) {
        $("#historyEmpty").removeClass("hidden");
        return;
      }

      const html = docs.map(doc => `
        <div class="flex items-center gap-4 px-5 py-4 rounded-xl border border-slate-100
                    bg-white hover:border-sky-200 hover:shadow-sm transition-all">
          <div class="w-10 h-10 rounded-xl bg-sky-50 flex items-center justify-center shrink-0">
            <span class="text-sky-500 text-lg">${doc.file_type === "pdf" ? "📄" : "📝"}</span>
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
            <button class="btn-secondary text-xs py-1.5 px-3 btn-view-doc" data-id="${doc.id}">
              👁 Detail
            </button>
            <button class="btn-danger text-xs py-1.5 px-3 btn-delete-doc" data-id="${doc.id}">
              🗑
            </button>
          </div>
        </div>
      `).join("");

      $("#historyList").html(html);
    }).fail(() => {
      $("#historyLoading").addClass("hidden");
      showToast("Gagal memuat riwayat.", "error");
    });
  }

  $("#btnRefreshHistory").on("click", loadHistory);

  /* View detail */
  $(document).on("click", ".btn-view-doc", function () {
    const id = $(this).data("id");
    $.get(`/api/documents/${id}`, function (doc) {
      const kw = (doc.keywords || []).join(", ") || "—";
      const ents = (doc.entities || []).map(e =>
        `<span class='badge bg-indigo-100 text-indigo-700 mr-1 mb-1'>${e.text} (${e.label})</span>`
      ).join("") || "—";

      $("#modalTitle").text(doc.filename);
      $("#modalBody").html(`
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><span class="text-slate-400">File Type</span>
               <p class="font-semibold text-slate-700 mt-1">${doc.file_type || "—"}</p></div>
          <div><span class="text-slate-400">Sentimen</span>
               <p class="mt-1">
                 <span class="badge ${sentimentStyle(doc.sentiment)}">${doc.sentiment || "—"}</span>
               </p></div>
          <div class="col-span-2"><span class="text-slate-400">Dibuat</span>
               <p class="font-medium text-slate-700 mt-1">
                 ${new Date(doc.created_at).toLocaleString("id-ID")}</p></div>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Ringkasan</p>
          <div class="bg-slate-50 rounded-xl p-4 text-sm text-slate-700 leading-relaxed">
            ${doc.summary || "—"}
          </div>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Kata Kunci</p>
          <p class="text-sm text-slate-700">${kw}</p>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Entitas</p>
          <div class="flex flex-wrap">${ents}</div>
        </div>
        <div>
          <p class="text-slate-400 text-sm mb-2">Cuplikan Teks</p>
          <div class="bg-slate-50 rounded-xl p-4 text-xs text-slate-600 leading-relaxed max-h-48 overflow-y-auto">
            ${doc.original_text || "—"}
          </div>
        </div>
      `);

      $("#detailModal").removeClass("hidden").addClass("flex");
    }).fail(() => showToast("Gagal memuat detail dokumen.", "error"));
  });

  /* Delete */
  $(document).on("click", ".btn-delete-doc", function () {
    const id = $(this).data("id");
    if (!confirm(`Hapus dokumen ID ${id}?`)) return;

    $.ajax({
      url: `/api/documents/${id}`,
      method: "DELETE",
      success() {
        showToast(`Dokumen ID ${id} dihapus.`, "info");
        loadHistory();
      },
      error() { showToast("Gagal menghapus.", "error"); }
    });
  });

  /* Close modal */
  $("#closeModal, #detailModal").on("click", function (e) {
    if (e.target === this) {
      $("#detailModal").addClass("hidden").removeClass("flex");
    }
  });

});