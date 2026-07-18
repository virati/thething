"use strict";

const $ = (sel) => document.querySelector(sel);

const state = { patient: null, package: null, view: "without" };

// --------------------------------------------------------------------------- //
// Auth (mock)                                                                 //
// --------------------------------------------------------------------------- //
$("#signin").addEventListener("click", async () => {
  $("#auth").classList.add("hidden");
  $("#app").classList.remove("hidden");
  await loadPatients();
});

// --------------------------------------------------------------------------- //
// Data loading                                                                //
// --------------------------------------------------------------------------- //
async function loadPatients() {
  const res = await fetch("/api/patients");
  if (!res.ok) {
    $("#conversations-list").innerHTML =
      `<p class="empty">No data. Run: uv run python scripts/generate_stories.py</p>`;
    return;
  }
  const patients = await res.json();
  const sel = $("#patient-select");
  sel.innerHTML = patients
    .map(
      (p) =>
        `<option value="${p.id}">${p.name} · ${p.age}${p.sex} · ${p.primary_condition}</option>`
    )
    .join("");
  sel.addEventListener("change", () => selectPatient(sel.value));
  await selectPatient(patients[0].id);
}

async function selectPatient(id) {
  const res = await fetch(`/api/patients/${id}`);
  state.patient = await res.json();
  state.package = null;
  $("#organ-select").value = state.patient.focus || "heart";
  renderConversations();
  renderAnatomy();
}

$("#organ-select").addEventListener("change", renderAnatomy);

// --------------------------------------------------------------------------- //
// Conversations pane                                                          //
// --------------------------------------------------------------------------- //
const SRC_ICON = { Claude: "✦", ChatGPT: "◍", "Care team call": "📞" };

function sentimentClass(s) {
  return s === "negative" ? "neg" : s === "positive" ? "pos" : "";
}

function renderConversations() {
  const list = $("#conversations-list");
  const convs = state.patient.conversations || [];
  list.innerHTML = convs
    .map((c) => {
      const sig = c.signals || {};
      const icon = SRC_ICON[c.source] || (c.type === "phone" ? "📞" : "💬");
      const eng = Math.round((sig.engagement || 0) * 100);
      const needs = (sig.needs || []).map((n) => `<span class="chip">${n}</span>`).join("");
      const affectSub =
        c.type === "phone"
          ? `<div class="sub"><h4>Affect</h4>
               <span class="chip affect">${c.affect || "—"}</span>
               <span class="chip ${sentimentClass(sig.sentiment)}">${sig.sentiment || ""}</span>
               <div class="meter"><i style="width:${eng}%"></i></div>
               <div class="chips" style="margin-top:8px">${needs}</div>
             </div>`
          : `<div class="sub"><h4>Signals</h4>
               <span class="chip affect">${c.affect || "—"}</span>
               <span class="chip ${sentimentClass(sig.sentiment)}">${sig.sentiment || ""}</span>
               <div class="chips" style="margin-top:8px">${needs}</div>
             </div>`;
      return `
        <details class="conv">
          <summary>
            <span class="chev">▶</span>
            <span class="src-icon">${icon}</span>
            <span class="src-name">${c.source}</span>
            <span class="src-meta">${c.date}</span>
          </summary>
          <div class="conv-body">
            <div class="sub"><h4>Transcript</h4>
              <div class="transcript">${escapeHtml(c.transcript || "")}</div>
            </div>
            ${affectSub}
          </div>
        </details>`;
    })
    .join("");
  if (!convs.length) list.innerHTML = `<p class="empty">No conversations.</p>`;
}

// --------------------------------------------------------------------------- //
// Anatomy / Imaging pane (3D)                                                 //
// --------------------------------------------------------------------------- //
function renderAnatomy() {
  const organ = $("#organ-select").value || state.patient.focus || "heart";
  const imaging = state.patient.imaging || [];
  // markers come from imaging for the selected organ
  const annotations = imaging
    .filter((img) => (img.region || state.patient.focus) === organ)
    .flatMap((img) => img.annotations || []);

  window.Anatomy3D.render($("#anatomy"), { focus: organ, annotations });

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
$("#package-btn").addEventListener("click", openPackage);
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
