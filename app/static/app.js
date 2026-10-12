"use strict";

const $ = (sel) => document.querySelector(sel);

const state = { patient: null, package: null, view: "without", record: null, regions: [], selectedFolder: null, middleZone: null };

// --------------------------------------------------------------------------- //
// Auth (mock)                                                                 //
// --------------------------------------------------------------------------- //
$("#signin").addEventListener("click", async () => {
  $("#auth").classList.add("hidden");
  $("#app").classList.remove("hidden");
  renderConversations(); // empty until a patient's context is downloaded
  renderPortal();
  renderAnatomy(); // glass brain
  await loadRecords();
});

// --------------------------------------------------------------------------- //
// Patients — left pop-out chooser rendered as a care-journey timeline          //
// --------------------------------------------------------------------------- //
const CAT_COLOR = {
  routine: "#6ea8fe", acute: "#ff5c7a",
  hospitalization: "#fbbf24", procedure: "#a78bfa",
};

async function loadRecords() {
  let records = [];
  try {
    records = await (await fetch("/api/records")).json();
  } catch (_) { /* no records */ }
  const host = $("#patient-timeline");
  if (!records.length) {
    host.innerHTML = `<p class="empty">No patients found.</p>`;
    return;
  }
  host.innerHTML = records.map(renderPatientRow).join("");
  host.querySelectorAll(".pt-row").forEach((row) =>
    row.addEventListener("click", () => selectPatient(row.dataset.folder))
  );
  // Auto-select the first patient so HORIZON has a target.
  selectPatient(records[0].folder);
}

function renderPatientRow(r) {
  const who = r.age != null ? `${r.age}${(r.gender || "")[0]?.toUpperCase() || ""}` : "";
  const tl = (r.timeline || []).filter((e) => e.date);
  const times = tl.map((e) => new Date(e.date).getTime()).filter((t) => !isNaN(t));
  const min = Math.min(...times), max = Math.max(...times), span = max - min || 1;
  const markers = tl
    .map((e) => {
      const t = new Date(e.date).getTime();
      const left = isNaN(t) ? 0 : ((t - min) / span) * 100;
      const color = CAT_COLOR[e.type] || CAT_COLOR.routine;
      return `<span class="pt-marker" style="left:${left}%;background:${color}" title="${escapeHtml(e.date)} · ${escapeHtml(e.title)}"></span>`;
    })
    .join("");
  const fmt = (t) => (isNaN(t) ? "" : new Date(t).toISOString().slice(0, 7));
  return `
    <button class="pt-row" data-folder="${escapeHtml(r.folder)}">
      <div class="pt-head">
        <span class="pt-name">${escapeHtml(r.name)}</span>
        <span class="pt-meta">${escapeHtml(who)}</span>
      </div>
      <div class="pt-headline">${escapeHtml(r.headline || "")}</div>
      <div class="pt-track"><div class="pt-line"></div>${markers}</div>
      ${times.length ? `<div class="pt-axis"><span>${fmt(min)}</span><span>${fmt(max)}</span></div>` : ""}
      <div class="pt-count">${r.encounters || tl.length} encounters · download to restore the middle zone</div>
    </button>`;
}

function selectPatient(folder) {
  if (!folder) return;
  state.selectedFolder = folder;
  document.querySelectorAll(".pt-row").forEach((row) =>
    row.classList.toggle("active", row.dataset.folder === folder)
  );
  const row = document.querySelector(`.pt-row[data-folder="${folder}"] .pt-name`);
  $("#active-patient").textContent = row ? row.textContent : folder;
  // Switching patient hides any revealed record until HORIZON is re-downloaded.
  state.record = null;
  state.regions = [];
  state.middleZone = null;
  $("#pane-record").classList.add("hidden");
  renderConversations();
  renderPortal();
  renderAnatomy();
}

// --------------------------------------------------------------------------- //
// Download HORIZON context (from the patient's phone) for the selected patient //
// --------------------------------------------------------------------------- //
$("#download-btn").addEventListener("click", downloadHorizon);

async function downloadHorizon() {
  const folder = state.selectedFolder;
  if (!folder) return;
  const [rec, regions, middleZone] = await Promise.all([
    fetch(`/api/records/${folder}`).then((r) => r.json()),
    fetch(`/api/records/${folder}/regions`).then((r) => r.json()),
    fetch(`/api/records/${folder}/middle-zone`).then((r) => r.json()),
  ]);
  // Gate the render behind the simulated "HORIZON context" download.
  openHorizon(rec, () => {
    state.record = rec;
    state.regions = regions || [];
    state.middleZone = middleZone || { conversations: [], portal: [] };
    renderRecord();
    renderConversations(); // middle zone restored
    renderPortal();
    $("#pane-record").classList.remove("hidden");
    $("#organ-select").value = "brain"; // regions live on the brain
    renderAnatomy();
    if ($("#stage").classList.contains("collapsed")) sideToggle.click();
  });
}

// --------------------------------------------------------------------------- //
// HORIZON context download (popup + ~5s status bar)                           //
// --------------------------------------------------------------------------- //
function openHorizon(rec, onReady) {
  // Triggered by the top-bar "Download HORIZON" button, so start pulling
  // immediately — the modal is the progress UI for the phone download.
  const modal = $("#horizon-modal");
  $("#hz-title").textContent = rec.name;
  $("#hz-download")?.classList.add("hidden");
  $("#hz-progress").classList.remove("hidden");
  $("#hz-bar-fill").style.width = "0%";
  modal.classList.remove("hidden");
  runHorizonProgress(() => {
    modal.classList.add("hidden");
    onReady();
  });
}

function runHorizonProgress(done) {
  const fill = $("#hz-bar-fill");
  const status = $("#hz-status");
  const steps = [
    [8, "Connecting to HORIZON…"],
    [26, "Pulling encounters & clinical notes…"],
    [46, "Reconciling medications…"],
    [66, "Restoring middle-zone context…"],
    [86, "Mapping brain regions of concern…"],
    [100, "Context packaged."],
  ];
  let i = 0;
  const perStep = 5000 / steps.length; // ~5s total
  (function next() {
    if (i >= steps.length) return setTimeout(done, 250);
    const [pct, msg] = steps[i++];
    fill.style.width = pct + "%";
    status.textContent = msg;
    setTimeout(next, perStep);
  })();
}

function renderRecord() {
  const r = state.record;
  const ls = r.longitudinal_summary || {};
  const demo = [
    ["DOB", r.birthDate], ["Age", r.age], ["Sex", r.gender],
    ["Marital", r.marital], ["Location", r.address], ["Language", r.language],
  ].filter(([, v]) => v != null && v !== "");

  const counts = Object.entries(ls.resource_counts || {})
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<span class="chip">${escapeHtml(k)} ${v}</span>`)
    .join("");

  const regionCards = (state.regions || [])
    .map((rg) => `
      <div class="region-row sev-${escapeHtml(rg.severity || "low")}">
        <div class="region-dot"></div>
        <div><b>${escapeHtml(rg.label)}</b><p>${escapeHtml(rg.reason || "")}</p></div>
      </div>`)
    .join("");

  const encounters = (r.encounters || [])
    .map((e, i) => `
      <details class="conv" ${i === r.encounters.length - 1 ? "open" : ""}>
        <summary>
          <span class="chev">▶</span>
          <span class="src-name">${escapeHtml(e.visit_title || e.visit_type || "Encounter")}</span>
          <span class="src-meta">${escapeHtml((e.date || "").slice(0, 10))}</span>
        </summary>
        <div class="conv-body">
          ${e.note ? section("Clinical note", e.note) : ""}
          ${e.transcript ? section("Visit transcript", e.transcript) : ""}
          ${e.after_visit_summary ? section("After-visit summary", e.after_visit_summary) : ""}
        </div>
      </details>`)
    .join("");

  $("#record-body").innerHTML = `
    <div class="rec-head">
      <div class="rec-name">${escapeHtml(r.name)}</div>
      <div class="chips">${demo.map(([k, v]) => `<span class="chip"><b>${escapeHtml(k)}</b> ${escapeHtml(String(v))}</span>`).join("")}</div>
    </div>

    <div class="rec-block">
      <h4>Problem list <span class="muted">(${(ls.condition_labels || []).length})</span></h4>
      <ul class="rec-list">${(ls.condition_labels || []).map((c) => `<li>${escapeHtml(c)}</li>`).join("")}</ul>
    </div>

    <div class="rec-block">
      <h4>Medications <span class="muted">(${(ls.medication_labels || []).length})</span></h4>
      <ul class="rec-list">${(ls.medication_labels || []).map((m) => `<li>${escapeHtml(m)}</li>`).join("")}</ul>
    </div>

    ${regionCards ? `<div class="rec-block"><h4>Brain — regions of concern</h4>${regionCards}</div>` : ""}

    <div class="rec-block">
      <h4>Longitudinal record</h4>
      <div class="chips">${counts}</div>
    </div>

    <div class="rec-block">
      <h4>Encounters <span class="muted">(${(r.encounters || []).length})</span></h4>
      <div class="conv-list">${encounters}</div>
    </div>`;
}

function section(title, text) {
  return `<div class="sub"><h4>${escapeHtml(title)}</h4>
    <div class="transcript">${escapeHtml(text)}</div></div>`;
}

$("#organ-select").addEventListener("change", renderAnatomy);
$("#dz-toggle").addEventListener("change", renderAnatomy);

// Collapsible side panel
const sideToggle = $("#side-toggle");
sideToggle.addEventListener("click", () => {
  const collapsed = $("#stage").classList.toggle("collapsed");
  sideToggle.textContent = collapsed ? "‹" : "›";
  sideToggle.setAttribute("aria-expanded", String(!collapsed));
  sideToggle.setAttribute("aria-label", collapsed ? "Expand panel" : "Collapse panel");
  // the stage width animates (.28s) — resize the 3D canvas as it settles
  window.dispatchEvent(new Event("resize"));
  setTimeout(() => window.dispatchEvent(new Event("resize")), 320);
});

// Collapsible left pop-out (patient chooser)
const leftToggle = $("#left-toggle");
leftToggle.addEventListener("click", () => {
  const collapsed = $("#stage").classList.toggle("left-collapsed");
  leftToggle.textContent = collapsed ? "›" : "‹";
  leftToggle.setAttribute("aria-expanded", String(!collapsed));
  window.dispatchEvent(new Event("resize"));
  setTimeout(() => window.dispatchEvent(new Event("resize")), 320);
});

// --------------------------------------------------------------------------- //
// Middle-zone panes (Conversations + Portal) — from data/middle-zone           //
// --------------------------------------------------------------------------- //
// signal_value -> chip class (how much the signal matters to the clinical goal)
const SIGNAL_CLASS = { high: "neg", moderate: "warn", low: "muted" };
const SIGNAL_LABEL = { high: "high signal", moderate: "moderate", low: "low" };
const PROMPT = `<p class="empty">Download HORIZON to restore the middle zone.</p>`;

function renderConversations() {
  const list = $("#conversations-list");
  if (!state.record) { list.innerHTML = PROMPT; return; }
  const convs = (state.middleZone && state.middleZone.conversations) || [];
  if (!convs.length) { list.innerHTML = `<p class="empty">No between-visit conversations.</p>`; return; }
  list.innerHTML = convs
    .map((c) => {
      const sigCls = SIGNAL_CLASS[c.signal_value] || "muted";
      return `
        <details class="conv">
          <summary>
            <span class="chev">▶</span>
            <span class="src-icon">${c.icon || (c.type === "chat" ? "💬" : "📞")}</span>
            <span class="src-name">${escapeHtml(c.source)}</span>
            <span class="src-meta">${escapeHtml(c.date)}</span>
          </summary>
          <div class="conv-body">
            <div class="mz-title">${escapeHtml(c.title)}
              <span class="chip ${sigCls}">${SIGNAL_LABEL[c.signal_value] || "low"}</span>
            </div>
            <div class="sub"><h4>${c.type === "chat" ? "Session" : "Transcript"}</h4>
              <div class="transcript">${escapeHtml(c.transcript || "")}</div>
            </div>
            <div class="sub"><h4>Middle-zone signal</h4>
              ${c.intent ? `<div class="mz-line"><b>Intent</b> ${escapeHtml(c.intent)}</div>` : ""}
              ${c.needs ? `<div class="mz-line"><b>Needs</b> ${escapeHtml(c.needs)}</div>` : ""}
              ${c.sentiment ? `<div class="mz-line"><b>Sentiment</b> ${escapeHtml(c.sentiment)}</div>` : ""}
              ${c.journey_position ? `<div class="mz-line"><b>Position</b> ${escapeHtml(c.journey_position)}</div>` : ""}
            </div>
          </div>
        </details>`;
    })
    .join("");
}

function renderPortal() {
  const list = $("#portal-list");
  if (!state.record) { list.innerHTML = PROMPT; return; }
  const items = (state.middleZone && state.middleZone.portal) || [];
  if (!items.length) { list.innerHTML = `<p class="empty">No portal interactions.</p>`; return; }
  list.innerHTML = items
    .slice()
    .sort((a, b) => (a.date < b.date ? 1 : -1)) // newest first
    .map((it) => {
      const sigCls = SIGNAL_CLASS[it.signal_value] || "muted";
      const dir =
        it.direction === "inbound" ? "Patient → system"
        : it.direction === "passive" ? "Passive / device"
        : "System → patient";
      const kind = (it.channel || "").split(".")[1] || "portal";
      return `
        <div class="portal-item">
          <span class="portal-icon">${it.icon || "🔔"}</span>
          <div class="portal-main">
            <div class="portal-top">
              <span class="portal-title">${escapeHtml(it.title)}</span>
              <span class="chip ${sigCls}">${SIGNAL_LABEL[it.signal_value] || "low"}</span>
            </div>
            <p class="portal-detail">${escapeHtml(it.transcript || it.detail || "")}</p>
            ${it.needs ? `<div class="mz-line"><b>Needs</b> ${escapeHtml(it.needs)}</div>` : ""}
            <div class="portal-meta">
              <span class="portal-type">${escapeHtml(kind)}</span>
              <span>${escapeHtml(dir)}</span>
              <span>${escapeHtml(it.date)}</span>
            </div>
          </div>
        </div>`;
    })
    .join("");
}

// --------------------------------------------------------------------------- //
// Anatomy / Imaging pane (3D)                                                 //
// --------------------------------------------------------------------------- //
function renderAnatomy() {
  const organ = $("#organ-select").value || (state.patient && state.patient.focus) || "brain";
  const imaging = (state.patient && state.patient.imaging) || [];
  // markers come from imaging for the selected organ (suppressed when a real
  // record is active — its brain shows the regions of concern instead)
  const annotations = state.record
    ? []
    : imaging
        .filter((img) => (img.region || (state.patient && state.patient.focus)) === organ)
        .flatMap((img) => img.annotations || []);

  // regions of concern (explicit 3D coords) apply to the brain of the active record
  const regions = organ === "brain" ? (state.regions || []) : [];

  // depression-circuit correlome overlay (ported from rseeg do_map_overlay)
  const dzOn = $("#dz-toggle").checked && organ === "brain";
  const overlay = dzOn ? { url: "/static/assets/depression_map.glb", color: 0xff3fae } : null;

  window.Anatomy3D.render($("#anatomy"), { focus: organ, annotations, regions, overlay });

  $("#imaging-notes").innerHTML = imaging
    .map(
      (img) => `
      <div class="img-note">
        <b>${img.modality}</b> · <span style="color:var(--muted)">${img.date}</span>
        <p>${escapeHtml(img.findings)}</p>
      </div>`
    )
    .join("");
}

// --------------------------------------------------------------------------- //
// Context package drawer                                                      //
// --------------------------------------------------------------------------- //
$("#package-btn")?.addEventListener("click", openPackage);
$("#drawer-close").addEventListener("click", closePackage);
$("#scrim").addEventListener("click", closePackage);
document.querySelectorAll(".toggle").forEach((t) =>
  t.addEventListener("click", () => {
    document.querySelectorAll(".toggle").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    state.view = t.dataset.view;
    renderPackage();
  })
);

async function openPackage() {
  if (!state.patient) return;
  const res = await fetch(`/api/patients/${state.patient.id}/package`);
  state.package = await res.json();
  state.view = "without";
  document.querySelectorAll(".toggle").forEach((x) =>
    x.classList.toggle("active", x.dataset.view === "without")
  );
  $("#drawer").classList.remove("hidden");
  $("#scrim").classList.remove("hidden");
  renderPackage();
}

function closePackage() {
  $("#drawer").classList.add("hidden");
  $("#scrim").classList.add("hidden");
}

function renderPackage() {
  const body = $("#package-body");
  if (!state.package) return;

  if (state.view === "without") {
    const w = state.package.without_middle_zones;
    body.innerHTML = `
      <div class="pk-card">
        <div class="pk-headline">${escapeHtml(w.headline)}</div>
      </div>
      <div class="pk-card">
        <h3>Known to the EHR</h3>
        <ul>${w.known_to_ehr.map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
      </div>
      <p class="empty">${escapeHtml(w.note)}</p>`;
    return;
  }

  const m = state.package.with_middle_zones;
  const scoreColor =
    m.engagement_score < 0.45 ? "var(--bad)" : m.engagement_score < 0.7 ? "var(--warn)" : "var(--good)";
  body.innerHTML = `
    <div class="pk-card">
      <div class="pk-headline">${escapeHtml(m.headline)}</div>
      <div class="score" style="margin-top:10px">
        <span class="big" style="color:${scoreColor}">${Math.round(m.engagement_score * 100)}%</span>
        <span>engagement · <b>${escapeHtml(m.engagement_label)}</b></span>
      </div>
    </div>
    <div class="pk-card">
      <h3>Unmet needs</h3>
      ${m.unmet_needs.length
        ? `<div class="chips">${m.unmet_needs.map((n) => `<span class="chip affect">${escapeHtml(n)}</span>`).join("")}</div>`
        : `<p class="empty">None flagged.</p>`}
    </div>
    <div class="pk-card">
      <h3>From the middle zones</h3>
      ${m.middle_zone_highlights
        .map(
          (h) => `<div class="hl">
            <div>${escapeHtml(h.insight)}</div>
            <div class="meta">${escapeHtml(h.source)} · ${escapeHtml(h.date)} · affect: ${escapeHtml(h.affect)}</div>
          </div>`
        )
        .join("")}
    </div>
    <div class="pk-card">
      <h3>Ask the right questions sooner</h3>
      ${m.suggested_questions.map((q) => `<div class="q">${escapeHtml(q)}</div>`).join("")}
    </div>
    <p class="empty">${escapeHtml(m.note)}</p>`;
}

// --------------------------------------------------------------------------- //
function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
