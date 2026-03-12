const state = {
  payload: null,
  activeTab: "synopsis",
  totalsFilters: { paketo: [], tameio: [], from: "", to: "" },
  apdFilters: {
    tameia: [],
    klados: [],
    typosApodochon: [],
    from: "01/01/2002",
    to: "",
    mode: "Όλα",
    filterPct: 18,
    highlightPct: 21
  }
};

const tabDefs = [
  { id: "synopsis", label: "Σύνοψη", group: "Βασικά", icon: "☰" },
  { id: "timeline", label: "Ιστορικό", group: "Βασικά", icon: "◷" },
  { id: "totals", label: "Σύνολα", group: "Ανάλυση", icon: "Σ" },
  { id: "count", label: "Καταμέτρηση", group: "Ανάλυση", icon: "#" },
  { id: "gaps", label: "Κενά", group: "Ανάλυση", icon: "!" },
  { id: "apd", label: "ΑΠΔ", group: "Ανάλυση", icon: "%" },
  { id: "parallel", label: "Παράλληλη", group: "Περιπτώσεις", icon: "||" },
  { id: "parallel_2017", label: "Παράλληλη 2017+", group: "Περιπτώσεις", icon: "17+" },
  { id: "multi", label: "Πολλαπλή", group: "Περιπτώσεις", icon: "x2" }
];

const tabMeta = {
  synopsis: { title: "Σύνοψη", subtitle: "Κεντρικοί έλεγχοι και κύρια ευρήματα φακέλου." },
  timeline: { title: "Ιστορικό", subtitle: "Οπτική απεικόνιση περιόδων ασφάλισης ανά ταμείο/τύπο." },
  totals: { title: "Σύνολα", subtitle: "Ομαδοποιημένη ανάλυση με φίλτρα και συνολικούς δείκτες." },
  count: { title: "Καταμέτρηση", subtitle: "Αναλυτική καταμέτρηση ημερών ασφάλισης." },
  gaps: { title: "Κενά", subtitle: "Κενά διαστήματα και εγγραφές χωρίς ημέρες." },
  apd: { title: "ΑΠΔ", subtitle: "Ανάλυση ποσοστών, φίλτρων και επισήμανση αποκλίσεων." },
  parallel: { title: "Παράλληλη", subtitle: "Εγγραφές παράλληλης ασφάλισης." },
  parallel_2017: { title: "Παράλληλη 2017+", subtitle: "Παράλληλη ασφάλιση από το 2017 και μετά." },
  multi: { title: "Πολλαπλή", subtitle: "Εγγραφές πολλαπλής απασχόλησης." }
};

const ui = {
  loaderMessage: document.getElementById("loaderMessage"),
  jsonUrl: document.getElementById("jsonUrl"),
  loadFromUrlBtn: document.getElementById("loadFromUrlBtn"),
  jsonFileInput: document.getElementById("jsonFileInput"),
  kpiStrip: document.getElementById("kpiStrip"),
  globalMessages: document.getElementById("globalMessages"),
  tabsContainer: document.getElementById("tabsContainer"),
  tabsNav: document.getElementById("tabsNav"),
  tabContent: document.getElementById("tabContent"),
  appRoot: document.getElementById("appRoot"),
  noDataRoot: document.getElementById("noDataRoot")
};

function isAnalysisPage() {
  return Boolean(ui.tabContent && ui.appRoot);
}

function initFromStorage() {
  if (!isAnalysisPage()) return;
  const raw = sessionStorage.getItem("atlas_report");
  if (!raw) {
    if (ui.noDataRoot) {
      ui.noDataRoot.classList.remove("hidden");
      ui.appRoot.classList.add("hidden");
    }
    return;
  }
  try {
    const payload = JSON.parse(raw);
    state.payload = payload;
    state.activeTab = getAvailableTabs(payload)[0]?.id || "synopsis";
    hydrateDefaultsFromPayload(payload);
    const yearEl = document.getElementById("currentYearBadge");
    if (yearEl) yearEl.textContent = "● " + new Date().getFullYear();
    renderAll();
  } catch (e) {
    if (ui.noDataRoot) {
      ui.noDataRoot.classList.remove("hidden");
      ui.appRoot.classList.add("hidden");
      ui.noDataRoot.querySelector("p").textContent = "Μη έγκυρα δεδομένα.";
    }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initFromStorage);
} else {
  initFromStorage();
}

function setLoaderMessage(text, isError = false) {
  if (!ui.loaderMessage) return;
  ui.loaderMessage.textContent = text;
  ui.loaderMessage.className = isError
    ? "mt-3 text-sm text-red-600"
    : "mt-3 text-sm text-slate-600";
}

async function loadFromUrl() {
  const url = (ui.jsonUrl.value || "").trim();
  if (!url) {
    setLoaderMessage("Δώστε URL JSON.", true);
    return;
  }
  try {
    setLoaderMessage("Φόρτωση JSON από URL...");
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const json = await resp.json();
    setPayload(json);
  } catch (err) {
    setLoaderMessage(`Αποτυχία φόρτωσης URL: ${err.message}`, true);
  }
}

async function loadFromFile(evt) {
  const file = evt.target.files && evt.target.files[0];
  if (!file) {
    return;
  }
  try {
    setLoaderMessage("Ανάγνωση JSON αρχείου...");
    const text = await file.text();
    const json = JSON.parse(text);
    setPayload(json);
  } catch (err) {
    setLoaderMessage(`Μη έγκυρο JSON: ${err.message}`, true);
  }
}

function setPayload(payload) {
  state.payload = payload;
  state.activeTab = getAvailableTabs(payload)[0]?.id || "synopsis";
  hydrateDefaultsFromPayload(payload);
  if (isAnalysisPage()) {
    const yearEl = document.getElementById("currentYearBadge");
    if (yearEl) yearEl.textContent = `● ${new Date().getFullYear()}`;
    renderAll();
  } else {
    try {
      sessionStorage.setItem("atlas_report", JSON.stringify(payload));
      window.location.href = "analysis.html";
    } catch (e) {
      setLoaderMessage("Αποτυχία αποθήκευσης: " + e.message, true);
    }
  }
  setLoaderMessage("Το JSON φορτώθηκε επιτυχώς.");
}

function hydrateDefaultsFromPayload(payload) {
  const apdDefaults = payload?.apd?.filter_defaults || {};
  state.apdFilters.from = apdDefaults.from_date || "01/01/2002";
  state.apdFilters.to = apdDefaults.to_date || "";
  state.apdFilters.mode = apdDefaults.retention_mode || "Όλα";
  state.apdFilters.filterPct = toNumber(apdDefaults.filter_pct, 18);
  state.apdFilters.highlightPct = toNumber(apdDefaults.highlight_pct, 21);
}

function renderAll() {
  renderKpiStrip();
  renderGlobalMessages();
  renderTabs();
  renderActiveTab();
}

function getAvailableTabs(payload) {
  if (!payload) return [];
  return tabDefs.filter((tab) => {
    if (tab.id === "synopsis") return true;
    const section = payload[tab.id];
    if (section == null) return false;
    if (Array.isArray(section)) return section.length > 0;
    if (typeof section === "object") return Object.keys(section).length > 0;
    return Boolean(section);
  });
}

function renderGlobalMessages() {
  if (!state.payload || !ui.globalMessages) return;
  ui.globalMessages.innerHTML = "";
  const blocks = [];
  if (state.payload?.meta?.complex_file_warning) {
    blocks.push(
      `<div class="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
        Προσοχή: Περίπλοκο αρχείο — Ελέγξτε απαραίτητα το πρωτότυπο ΑΤΛΑΣ.
      </div>`
    );
  }
  ui.globalMessages.innerHTML = blocks.join("");
  if (blocks.length) {
    ui.globalMessages.classList.remove("hidden");
    ui.globalMessages.className = "shrink-0 px-4 py-2 space-y-2";
  }
}

function renderKpiStrip() {
  if (!state.payload) {
    ui.kpiStrip.classList.add("hidden");
    ui.kpiStrip.innerHTML = "";
    return;
  }
  const auditCount = (state.payload.audit || []).length;
  const totalsRows = (state.payload?.totals?.rows || []).length;
  const apdRows = (state.payload?.apd?.rows || []).length;
  const gapsCount = (state.payload?.gaps?.gaps || []).length;
  const cards = [
    { label: "Έλεγχοι Σύνοψης", value: formatInt(auditCount), tone: "from-indigo-500 to-indigo-700" },
    { label: "Γραμμές Συνόλων", value: formatInt(totalsRows), tone: "from-sky-500 to-sky-700" },
    { label: "Εγγραφές ΑΠΔ", value: formatInt(apdRows), tone: "from-emerald-500 to-emerald-700" },
    { label: "Κενά Διαστήματα", value: formatInt(gapsCount), tone: "from-amber-500 to-amber-700" }
  ];
  ui.kpiStrip.classList.remove("hidden");
  ui.kpiStrip.className = "shrink-0 grid gap-3 grid-cols-2 md:grid-cols-4 px-4 py-3 border-b border-slate-200 bg-white/80";
  ui.kpiStrip.innerHTML = cards.map((c) => `
    <article class="rounded-2xl bg-gradient-to-br ${c.tone} p-[1px] shadow-sm">
      <div class="rounded-2xl bg-white/90 px-4 py-3">
        <p class="text-xs font-medium text-slate-500">${c.label}</p>
        <p class="mt-1 text-xl font-semibold text-slate-900">${c.value}</p>
      </div>
    </article>
  `).join("");
}

function renderTabs() {
  const tabs = getAvailableTabs(state.payload);
  if (ui.tabsContainer) ui.tabsContainer.classList.remove("hidden");
  const grouped = tabs.reduce((acc, t) => {
    const key = t.group || "Λοιπά";
    if (!acc[key]) acc[key] = [];
    acc[key].push(t);
    return acc;
  }, {});
  const groupOrder = ["Βασικά", "Ανάλυση", "Περιπτώσεις", "Λοιπά"];
  const blocks = groupOrder
    .filter((g) => grouped[g]?.length)
    .map((g) => `
      <div class="mb-3">
        <p class="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">${g}</p>
        <div class="space-y-1">
          ${grouped[g]
            .map((t) => {
              const active = t.id === state.activeTab;
              const cls = active ? "nav-btn active" : "nav-btn idle";
              return `<button data-tab="${t.id}" class="${cls}">
                <span class="inline-flex w-8 shrink-0 items-center justify-center text-[11px] font-semibold opacity-90">${renderTabIcon(t.id)}</span>
                <span>${t.label}</span>
              </button>`;
            })
            .join("")}
        </div>
      </div>`)
    .join("");
  ui.tabsNav.innerHTML = `
    <div class="mb-2 px-2 pb-2">
      <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Καρτέλες Αναφοράς</p>
    </div>
    ${blocks}`;

  ui.tabsNav.querySelectorAll("button[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.activeTab = btn.getAttribute("data-tab");
      renderTabs();
      renderActiveTab();
    });
  });
}

function renderActiveTab() {
  if (!state.payload) return;
  switch (state.activeTab) {
    case "synopsis":
      renderSynopsis();
      break;
    case "timeline":
      renderTimeline();
      break;
    case "totals":
      renderTotals();
      break;
    case "count":
      renderCount();
      break;
    case "gaps":
      renderGaps();
      break;
    case "apd":
      renderApd();
      break;
    case "parallel":
    case "parallel_2017":
    case "multi":
      renderSimpleArrayTab(state.activeTab);
      break;
    default:
      ui.tabContent.innerHTML = renderTabFrame(state.activeTab, `<p class="text-sm text-slate-600">Δεν υπάρχει renderer για ${state.activeTab}.</p>`);
  }
}

function renderTabFrame(tabId, bodyHtml) {
  const m = tabMeta[tabId] || { title: tabId, subtitle: "" };
  return `
    <section class="fade-in">
      <header class="mb-4 rounded-2xl border border-slate-200 bg-gradient-to-r from-white to-slate-50 px-4 py-3">
        <h2 class="text-lg font-semibold text-slate-900">${escapeHtml(m.title)}</h2>
        <p class="mt-1 text-sm text-slate-600">${escapeHtml(m.subtitle)}</p>
      </header>
      ${bodyHtml}
    </section>`;
}

function renderSynopsis() {
  const rows = state.payload.audit || [];
  if (!rows.length) {
    ui.tabContent.innerHTML = `<p class="text-sm text-slate-600">Δεν βρέθηκαν στοιχεία.</p>`;
    return;
  }
  const cards = rows
    .map((r) => {
      return `<article class="rounded-xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4 shadow-sm">
        <p class="text-[11px] font-semibold uppercase tracking-wide text-slate-500">${escapeHtml(r["Έλεγχος"] || "-")}</p>
        <p class="mt-2 text-base font-semibold text-slate-900">${escapeHtml(r["Εύρημα"] || "-")}</p>
        <p class="mt-2 text-xs leading-relaxed text-slate-600">${safeHtml(r["Λεπτομέρειες"] || "-")}</p>
      </article>`;
    })
    .join("");
  ui.tabContent.innerHTML = renderTabFrame("synopsis", `
    <div class="mb-4 rounded-2xl bg-gradient-to-r from-indigo-950 via-indigo-900 to-slate-900 px-5 py-4 text-white shadow-lg">
      <p class="text-xs uppercase tracking-wide text-indigo-200">Σύνοψη Ασφαλιστικού Φακέλου</p>
      <p class="mt-1 text-2xl font-semibold">${formatInt(rows.length)} έλεγχοι</p>
    </div>
    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">${cards}</div>
  `);
}

function renderTimeline() {
  const timeline = state.payload.timeline || {};
  const periodFrom = timeline?.period?.from || "-";
  const periodTo = timeline?.period?.to || "-";
  const groups = timeline.groups || [];

  if (!groups.length) {
    ui.tabContent.innerHTML = `<p class="text-sm text-slate-600">Δεν υπάρχουν δεδομένα χρονοδιαγράμματος.</p>`;
    return;
  }

  const minDate = parseDate(timeline?.period?.from) || minOfGroupDates(groups);
  const maxDate = parseDate(timeline?.period?.to) || maxOfGroupDates(groups);
  const total = Math.max(1, daysBetween(minDate, maxDate));

  const rowsHtml = groups
    .map((g) => {
      const bars = (g.bars || [])
        .map((b) => {
          const start = parseDate(b.apo) || minDate;
          const end = parseDate(b.eos) || maxDate;
          const left = Math.max(0, ((start - minDate) / (maxDate - minDate || 1)) * 100);
          const width = Math.max(0.6, (daysBetween(start, end) / total) * 100);
          return `<div class="absolute top-1 h-3 rounded bg-blue-500" style="left:${left}%;width:${width}%" title="${escapeHtml(`${b.apo} - ${b.eos}`)}"></div>`;
        })
        .join("");
      return `<div class="grid grid-cols-12 items-center gap-2">
        <div class="col-span-12 text-xs font-medium text-slate-700 md:col-span-3">${escapeHtml(g.label || "-")}</div>
        <div class="col-span-12 md:col-span-9">
          <div class="relative h-5 rounded bg-slate-100">${bars}</div>
        </div>
      </div>`;
    })
    .join("");

  ui.tabContent.innerHTML = renderTabFrame("timeline", `
    <div class="space-y-4">
      <div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <p class="text-xs uppercase tracking-wide text-slate-500">Χρονικό εύρος</p>
        <p class="mt-1 text-sm font-semibold text-slate-800">${escapeHtml(periodFrom)} - ${escapeHtml(periodTo)}</p>
      </div>
      <div class="space-y-3">${rowsHtml}</div>
    </div>`);
}

function renderTotals() {
  const totals = state.payload.totals || {};
  const rows = totals.rows || [];
  const paketoOptions = totals?.filter_options?.paketo_options || [];
  const tameioOptions = totals?.filter_options?.tameio_options || [];
  const filteredRows = filterTotalsRows(rows);
  const summary = computeTotalsSummaryFromRaw();
  const warnTypes = [];
  if ((state.payload.parallel || []).length) warnTypes.push("παράλληλη ασφάλιση");
  if ((state.payload.parallel_2017 || []).length) warnTypes.push("παράλληλη απασχόληση 2017+");
  if ((state.payload.multi || []).length) warnTypes.push("πολλαπλή απασχόληση");
  const message = warnTypes.length
    ? `Προσοχή: υπάρχει πιθανή ${warnTypes.join(", ")}. Το άθροισμα ημερών μπορεί να δώσει λάθος αποτελέσματα.`
    : "Επιλέξτε πακέτα κάλυψης για αθροιστική προϋπηρεσία.";

  ui.tabContent.innerHTML = renderTabFrame("totals", `
    <div class="space-y-4">
      <div class="rounded-2xl border ${warnTypes.length ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-slate-50"} p-4 text-sm">
        <p class="font-medium">${escapeHtml(message)}</p>
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          <div class="rounded-xl bg-white px-3 py-2 shadow-sm"><span class="text-xs text-slate-500">Εκτίμηση Ημερών</span><p class="text-lg font-semibold">${formatInt(summary.days)}</p></div>
          <div class="rounded-xl bg-white px-3 py-2 shadow-sm"><span class="text-xs text-slate-500">Συνολικά Έτη</span><p class="text-lg font-semibold">${summary.years.toFixed(2)}</p></div>
        </div>
      </div>

      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        ${renderMultiSelect("totalsPaketo", "Πακέτο", paketoOptions, state.totalsFilters.paketo)}
        ${renderMultiSelect("totalsTameio", "Ταμείο", tameioOptions, state.totalsFilters.tameio)}
        <label class="text-sm">Από (dd/mm/yyyy)
          <input id="totalsFrom" class="input-base mt-1 w-full" value="${escapeHtml(state.totalsFilters.from)}" placeholder="01/01/2000">
        </label>
        <label class="text-sm">Έως (dd/mm/yyyy)
          <input id="totalsTo" class="input-base mt-1 w-full" value="${escapeHtml(state.totalsFilters.to)}" placeholder="31/12/2025">
        </label>
      </div>

      ${renderDataTable(filteredRows)}
      <p class="text-xs text-slate-500">Εμφανίζονται ${filteredRows.length} γραμμές.</p>
    </div>`);

  bindTotalsControls();
}

function bindTotalsControls() {
  bindMultiSelect("totalsPaketo", (vals) => {
    state.totalsFilters.paketo = vals;
    renderTotals();
  });
  bindMultiSelect("totalsTameio", (vals) => {
    state.totalsFilters.tameio = vals;
    renderTotals();
  });
  const fromEl = document.getElementById("totalsFrom");
  const toEl = document.getElementById("totalsTo");
  if (fromEl) {
    fromEl.addEventListener("input", () => {
      state.totalsFilters.from = fromEl.value.trim();
      renderTotals();
    });
  }
  if (toEl) {
    toEl.addEventListener("input", () => {
      state.totalsFilters.to = toEl.value.trim();
      renderTotals();
    });
  }
}

function filterTotalsRows(rows) {
  const from = parseDate(state.totalsFilters.from);
  const to = parseDate(state.totalsFilters.to);
  return rows.filter((r) => {
    const paketoOk =
      !state.totalsFilters.paketo.length ||
      state.totalsFilters.paketo.includes(String(r["Κλάδος/Πακέτο Κάλυψης"] || "").trim());
    const tameioOk =
      !state.totalsFilters.tameio.length ||
      state.totalsFilters.tameio.includes(String(r["Ταμείο"] || "").trim());
    const fromDt = parseDate(r["Από"]);
    const toDt = parseDate(r["Έως"]);
    const afterFrom = !from || !fromDt || fromDt >= from;
    const beforeTo = !to || !toDt || toDt <= to;
    return paketoOk && tameioOk && afterFrom && beforeTo;
  });
}

function computeTotalsSummaryFromRaw() {
  const rawRecords = state.payload?.totals?.raw_records || [];
  const from = parseDate(state.totalsFilters.from);
  const to = parseDate(state.totalsFilters.to);
  let days = 0;
  rawRecords.forEach((r) => {
    const paketoOk = !state.totalsFilters.paketo.length || state.totalsFilters.paketo.includes(String(r.p || "").trim());
    const tameioOk = !state.totalsFilters.tameio.length || state.totalsFilters.tameio.includes(String(r.t || "").trim());
    const apoDt = parseDate(r.apo);
    const eosDt = parseDate(r.eos);
    const afterFrom = !from || !apoDt || apoDt >= from;
    const beforeTo = !to || !eosDt || eosDt <= to;
    if (paketoOk && tameioOk && afterFrom && beforeTo) {
      days += toNumber(r.h, 0);
    }
  });
  return { days, years: days / 300 };
}

function renderCount() {
  const rows = state.payload?.count?.rows || [];
  const excl = state.payload?.meta?.excluded_packages_label || "-";
  ui.tabContent.innerHTML = renderTabFrame("count", `
    <div class="space-y-3">
      <div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">Εξαιρούνται από την καταμέτρηση: <strong>${escapeHtml(excl)}</strong></div>
      ${renderDataTable(rows)}
    </div>`);
}

function renderGaps() {
  const gaps = state.payload?.gaps?.gaps || [];
  const zeroDuration = state.payload?.gaps?.zero_duration || [];
  ui.tabContent.innerHTML = renderTabFrame("gaps", `
    <div class="space-y-5">
      <section>
        <h3 class="mb-2 text-sm font-semibold text-slate-800">Κενά Διαστήματα</h3>
        ${renderDataTable(gaps)}
      </section>
      <section>
        <h3 class="mb-2 text-sm font-semibold text-slate-800">Διαστήματα χωρίς ημέρες ασφάλισης</h3>
        ${renderDataTable(zeroDuration)}
      </section>
      <div class="rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        Τα διαστήματα χωρίς ημέρες ασφάλισης δεν αποτελούν εξ ορισμού κενό, μπορεί να υπάρχει μερική επικάλυψη με άλλες εγγραφές.
      </div>
    </div>`);
}

function renderApd() {
  const apd = state.payload?.apd || {};
  const rows = apd.rows || [];
  const filtered = filterApdRows(rows);
  const infoStatus = apd.insurance_status_message || "-";
  const excluded = apd.excluded_packages_label || "-";

  ui.tabContent.innerHTML = renderTabFrame("apd", `
    <div class="space-y-4">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        ${renderArraySelect("apdTameia", "Ταμείο", apd?.options?.tameia || [], state.apdFilters.tameia)}
        ${renderArraySelect("apdKlados", "Κλάδος/Πακέτο", apd?.options?.klados || [], state.apdFilters.klados)}
        ${renderArraySelect("apdTypos", "Τύπος Αποδοχών", apd?.options?.typos_apodochon || [], state.apdFilters.typosApodochon)}
        <label class="text-sm">Από (dd/mm/yyyy)
          <input id="apdFrom" class="input-base mt-1 w-full" value="${escapeHtml(state.apdFilters.from)}">
        </label>
        <label class="text-sm">Έως (dd/mm/yyyy)
          <input id="apdTo" class="input-base mt-1 w-full" value="${escapeHtml(state.apdFilters.to)}">
        </label>
        <label class="text-sm">Φίλτρο %
          <input id="apdFilterPct" type="number" step="0.1" class="input-base mt-1 w-full" value="${state.apdFilters.filterPct}">
        </label>
        <label class="text-sm">Τύπος φίλτρου
          <select id="apdMode" class="input-base mt-1 w-full">
            ${["Όλα", "Μεγαλύτερο ή ίσο", "Μικρότερο από"].map((m) => `<option ${m === state.apdFilters.mode ? "selected" : ""}>${m}</option>`).join("")}
          </select>
        </label>
        <label class="text-sm">Επισήμανση <
          <input id="apdHighlightPct" type="number" step="0.1" class="input-base mt-1 w-full" value="${state.apdFilters.highlightPct}">
        </label>
      </div>

      <div class="grid gap-2 md:grid-cols-2">
        <div class="rounded border border-sky-200 bg-sky-50 p-2 text-sm">Καθεστώς: <strong>${escapeHtml(infoStatus)}</strong></div>
        <div class="rounded border border-slate-200 bg-slate-50 p-2 text-sm">Εξαιρούνται: <strong>${escapeHtml(excluded)}</strong></div>
      </div>
      ${renderDataTable(filtered, { highlightApd: true, highlightThreshold: state.apdFilters.highlightPct })}
      <p class="text-xs text-slate-500">Εμφανίζονται ${filtered.length} γραμμές.</p>
    </div>`);

  bindApdControls();
}

function bindApdControls() {
  bindArraySelect("apdTameia", (vals) => { state.apdFilters.tameia = vals; renderApd(); });
  bindArraySelect("apdKlados", (vals) => { state.apdFilters.klados = vals; renderApd(); });
  bindArraySelect("apdTypos", (vals) => { state.apdFilters.typosApodochon = vals; renderApd(); });
  const mapping = [
    ["apdFrom", "from"],
    ["apdTo", "to"],
    ["apdMode", "mode"],
    ["apdFilterPct", "filterPct"],
    ["apdHighlightPct", "highlightPct"]
  ];
  mapping.forEach(([id, key]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", () => {
      state.apdFilters[key] = (key === "filterPct" || key === "highlightPct") ? toNumber(el.value, 0) : el.value;
      renderApd();
    });
    el.addEventListener("change", () => {
      state.apdFilters[key] = (key === "filterPct" || key === "highlightPct") ? toNumber(el.value, 0) : el.value;
      renderApd();
    });
  });
}

function filterApdRows(rows) {
  const from = parseDate(state.apdFilters.from);
  const to = parseDate(state.apdFilters.to);
  return rows.filter((r) => {
    const tameio = String(r["Ταμείο"] || "").trim();
    const klados = String(r["Κλάδος/Πακέτο Κάλυψης"] || "").trim();
    const apodCol = Object.keys(r).find((k) => k.includes("Τύπος Αποδοχών"));
    const apodVal = String(apodCol ? r[apodCol] : "").trim();
    const tameioOk = !state.apdFilters.tameia.length || state.apdFilters.tameia.includes(tameio);
    const kladosOk = !state.apdFilters.klados.length || state.apdFilters.klados.includes(klados);
    const apodOk = !state.apdFilters.typosApodochon.length || state.apdFilters.typosApodochon.includes(apodVal);

    const fromDate = parseDate(r["Από"]);
    const fromOk = !from || !fromDate || fromDate >= from;
    const toOk = !to || !fromDate || fromDate <= to;

    const retention = getRetentionPct(r);
    let retentionOk = true;
    if (state.apdFilters.mode === "Μεγαλύτερο ή ίσο") {
      retentionOk = retention >= toNumber(state.apdFilters.filterPct, 0);
    } else if (state.apdFilters.mode === "Μικρότερο από") {
      retentionOk = retention < toNumber(state.apdFilters.filterPct, 0);
    }

    return tameioOk && kladosOk && apodOk && fromOk && toOk && retentionOk;
  });
}

function getRetentionPct(row) {
  if (row["ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ"] != null && row["ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ"] !== "") {
    return toNumber(row["ΠΟΣΟΣΤΟ ΕΙΣΦΟΡΑΣ"], 0);
  }
  const contrib = toNumber(row["ΣΥΝΟΛΙΚΕΣ ΕΙΣΦΟΡΕΣ"] ?? row["Συνολικές εισφορές"], 0);
  const gross = toNumber(row["ΜΙΚΤΕΣ ΑΠΟΔΟΧΕΣ"] ?? row["Μικτές αποδοχές"], 0);
  if (!gross) return 0;
  return (contrib / gross) * 100;
}

function renderSimpleArrayTab(tabId) {
  const arr = state.payload?.[tabId] || [];
  ui.tabContent.innerHTML = renderTabFrame(tabId, renderDataTable(arr));
}

function renderDataTable(rows, opts = {}) {
  if (!rows || !rows.length) {
    return `<div class="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">Δεν υπάρχουν δεδομένα.</div>`;
  }
  const keys = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  const colCount = keys.length;
  const minTableWidth = Math.max(400, colCount * 82);
  const thead = keys.map((k) => `<th class="table-th">${escapeHtml(k)}</th>`).join("");
  const tbody = rows.map((row) => {
    const retention = opts.highlightApd ? getRetentionPct(row) : null;
    const trClass = opts.highlightApd && retention < toNumber(opts.highlightThreshold, 21)
      ? "bg-amber-50/60"
      : "odd:bg-white even:bg-slate-50/40";
    const tds = keys.map((k) => `<td class="table-td">${safeHtml(row[k])}</td>`).join("");
    return `<tr class="${trClass}">${tds}</tr>`;
  }).join("");
  return `<div class="table-scroll-wrapper">
    <table class="table-wide" style="min-width:${minTableWidth}px">
      <thead><tr>${thead}</tr></thead>
      <tbody>${tbody}</tbody>
    </table>
  </div>`;
}

function renderMultiSelect(id, label, options, selectedValues) {
  const opts = options
    .map((o) => {
      const selected = selectedValues.includes(o.value) ? "selected" : "";
      return `<option ${selected} value="${escapeHtml(o.value)}">${escapeHtml(o.label)}</option>`;
    })
    .join("");
  return `<label class="text-sm">${escapeHtml(label)}
    <select id="${id}" multiple class="mt-1 h-32 w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-1 text-xs">${opts}</select>
  </label>`;
}

function renderArraySelect(id, label, options, selectedValues) {
  const opts = options
    .map((v) => {
      const selected = selectedValues.includes(v) ? "selected" : "";
      return `<option ${selected} value="${escapeHtml(v)}">${escapeHtml(v)}</option>`;
    })
    .join("");
  return `<label class="text-sm">${escapeHtml(label)}
    <select id="${id}" multiple class="mt-1 h-32 w-full rounded-xl border border-slate-200 bg-slate-50 px-2 py-1 text-xs">${opts}</select>
  </label>`;
}

function bindMultiSelect(id, cb) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("change", () => {
    const vals = Array.from(el.selectedOptions).map((o) => o.value);
    cb(vals);
  });
}
function bindArraySelect(id, cb) {
  return bindMultiSelect(id, cb);
}

function parseDate(v) {
  if (!v || typeof v !== "string") return null;
  const m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!m) return null;
  const d = Number(m[1]);
  const mm = Number(m[2]) - 1;
  const y = Number(m[3]);
  const dt = new Date(y, mm, d);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function minOfGroupDates(groups) {
  let min = new Date(2100, 0, 1);
  groups.forEach((g) => (g.bars || []).forEach((b) => {
    const d = parseDate(b.apo);
    if (d && d < min) min = d;
  }));
  return min;
}

function maxOfGroupDates(groups) {
  let max = new Date(1970, 0, 1);
  groups.forEach((g) => (g.bars || []).forEach((b) => {
    const d = parseDate(b.eos);
    if (d && d > max) max = d;
  }));
  return max;
}

function daysBetween(a, b) {
  if (!a || !b) return 1;
  const ms = b.getTime() - a.getTime();
  return Math.max(1, Math.floor(ms / 86400000) + 1);
}

function toNumber(v, fallback = 0) {
  if (v == null || v === "") return fallback;
  if (typeof v === "number") return Number.isFinite(v) ? v : fallback;
  const normalized = String(v).replace(/\./g, "").replace(",", ".");
  const n = Number(normalized);
  return Number.isFinite(n) ? n : fallback;
}

function formatInt(n) {
  return new Intl.NumberFormat("el-GR", { maximumFractionDigits: 0 }).format(toNumber(n, 0));
}

function safeHtml(v) {
  if (v == null) return "";
  const s = String(v);
  if (s.includes("<div") || s.includes("<br") || s.includes("</")) {
    return s;
  }
  return escapeHtml(s);
}

function escapeHtml(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderTabIcon(tabId) {
  const base = "h-4 w-4";
  switch (tabId) {
    case "synopsis":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16M4 12h16M4 18h10"/></svg>`;
    case "timeline":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12h16"/><path d="M8 8v8M16 10v4"/></svg>`;
    case "totals":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h6"/></svg>`;
    case "count":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M8 4L6 20M14 4l-2 16M4 10h16M3 14h16"/></svg>`;
    case "gaps":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 8v5"/><circle cx="12" cy="17" r="1"/><path d="M10.3 3.9L2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>`;
    case "apd":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 19l14-14"/><path d="M7 7h.01M17 17h.01"/></svg>`;
    case "parallel":
    case "parallel_2017":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 5v14M17 5v14"/><path d="M7 12h10"/></svg>`;
    case "multi":
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6L6 18"/></svg>`;
    default:
      return `<svg class="${base}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/></svg>`;
  }
}
