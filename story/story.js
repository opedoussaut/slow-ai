import { predict, featureVector, parameterCount, wilson, escalationDecision, microsPerCall } from "./models.js";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const fmt = new Intl.NumberFormat("en-GB");
const pct = (x, d = 0) => `${(100 * x).toFixed(d)}%`;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const ROUTE_NAMES = { 1: "Route 1 · No AI", 2: "Route 2 · Decision model", 3: "Route 3 · Specialized model", 4: "Route 4 · Frontier model" };

const state = { bundle: null, variant: "main", threshold: 0.8, timings: null, steel: null };

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "style") node.setAttribute("style", v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return node;
}
const badge = (kind) => el("span", { class: "ev", "data-kind": kind, text: {
  measured: "Measured", simulation: "Reproducible simulation", illustrative: "Illustrative", "not-measured": "Not measured" }[kind] });
const metric = (text, kind, tag = "b") => el(tag, { "data-metric": true, "data-ev": kind, text });
const kb = (bytes) => bytes >= 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${(bytes / 1e3).toFixed(1)} KB`;

const V = () => state.bundle.variants[state.variant];

// ---------------------------------------------------------------------------
// Decisions: computed live from the bundle's curated features and trained models
// ---------------------------------------------------------------------------
function decisions() {
  const b = state.bundle, v = V(), m = b.models, f = v.features;
  const supply = v.supply_c_now;
  const q1 = { supply, limit: b.supply_limit_c, above: supply > b.supply_limit_c };
  const pAct = predict(m.actionable, featureVector(m.actionable, f));
  const q2 = { p: pAct[1], confident: Math.max(...pAct) >= 0.8, actionable: pAct[1] >= 0.5 };
  const compact = predict(m.compact_fault, featureVector(m.compact_fault, f));
  const special = predict(m.specialized_fault, featureVector(m.specialized_fault, f));
  const esc = escalationDecision(compact, state.threshold);
  const finalProbs = esc.escalate ? special : compact;
  const finalIdx = finalProbs.indexOf(Math.max(...finalProbs));
  const q3 = { compact, special, esc, finalIdx, finalP: finalProbs[finalIdx], route: esc.escalate ? 3 : 2,
               correct: m.compact_fault.classes[finalIdx] === "branch_restriction" };
  return { q1, q2, q3 };
}

function measureTimings() {
  const b = state.bundle, v = V(), m = b.models, f = v.features;
  const xa = featureVector(m.actionable, f), xc = featureVector(m.compact_fault, f), xs = featureVector(m.specialized_fault, f);
  return {
    r1: microsPerCall(() => v.supply_c_now > b.supply_limit_c),
    r2: microsPerCall(() => predict(m.actionable, xa)),
    r2c: microsPerCall(() => predict(m.compact_fault, xc)),
    r3: microsPerCall(() => predict(m.specialized_fault, xs)),
  };
}
const us = (x) => x < 0.1 ? "< 0.1 µs" : `${x.toFixed(x < 10 ? 2 : 1)} µs`;

// ---------------------------------------------------------------------------
// Hero: one row per data source, one column per minute
// ---------------------------------------------------------------------------
function drawStream() {
  const canvas = $("#stream");
  const v = state.bundle.variants.main;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  const rows = 24 + 2 + 3; // racks, CDUs, event streams
  const rh = (h - 18) / rows; // bottom strip reserved for time labels
  let seed = state.bundle.seed;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
  const flow = v.series.racks.R07.flow_lpm;
  for (let r = 0; r < rows; r++) {
    const y = r * rh;
    const isEvent = r >= 26;
    for (let x = 0; x < w; x += 2) {
      const minute = Math.floor((x / w) * 1440);
      if (isEvent && rnd() > 0.35) continue;
      let alpha = 0.18 + rnd() * 0.22;
      let color = "122,168,222";
      if (r === 6) { // R07: real deviation from the simulated flow series
        const dev = Math.max(0, 1 - flow[Math.min(flow.length - 1, Math.floor(minute / 10))] / 60);
        if (dev > 0.04) { color = "230,162,74"; alpha = 0.35 + dev * 1.6; }
      }
      ctx.fillStyle = `rgba(${color},${Math.min(alpha, 1)})`;
      ctx.fillRect(x, y + rh * 0.2, 1.2, Math.max(1, rh * 0.6));
    }
  }
  ctx.fillStyle = "rgba(219,230,238,.75)";
  ctx.font = "12px Archivo, system-ui, sans-serif";
  ["00:00", "06:00", "12:00", "18:00"].forEach((t, i) => ctx.fillText(t, (i / 4) * w + 2, h - 2));
}

// ---------------------------------------------------------------------------
// Chapter 1: curation
// ---------------------------------------------------------------------------
function renderCuration(animate) {
  const v = V();
  $("#variantNote").textContent = state.variant === "main"
    ? `A restriction in the R07 cooling branch removes up to ${v.injected.restriction_max_pct}% of its flow from ${v.injected.onset}.`
    : `The same fault, but only ${v.injected.restriction_max_pct}% of flow is lost. This is the stress test for the curation rules.`;
  const total = v.raw.total;
  const funnel = $("#funnel");
  funnel.replaceChildren();
  const ledgerItems = v.curation.ledger;
  const stages = v.curation.stages.map((s, i) => i === v.curation.stages.length - 1
    ? { ...s, stage: "Evidence ledger", unit: "items" } : { ...s, unit: i >= 4 ? "episodes" : "records" });
  const bars = [];
  stages.forEach((s) => {
    const bar = el("i");
    const isRecords = s.unit === "records";
    if (isRecords) bars.push([bar, Math.max(0.6, (100 * Math.log10(Math.max(s.kept, 1) + 1)) / Math.log10(total + 1))]);
    funnel.append(el("div", { class: "stage" },
      el("span", { class: "stage-name", text: s.stage }),
      el("span", { class: isRecords ? "stage-bar" : "stage-bar empty", "aria-hidden": "true" }, isRecords ? bar : null),
      el("span", { class: "stage-count" }, metric(`${fmt.format(s.kept)}`, "simulation", "span"), el("span", { class: "small quiet", text: ` ${s.unit}` })),
      el("span", { class: "stage-rule small quiet", text: s.rule })));
  });
  const apply = () => bars.forEach(([bar, w], i) => setTimeout(() => (bar.style.width = `${w}%`), animate && !reduceMotion ? i * 260 : 0));
  if (animate && !reduceMotion) requestAnimationFrame(() => requestAnimationFrame(apply)); else apply();

  const rc = v.recall;
  $("#recallValue").textContent = `${rc.retained} of ${rc.fault_effects}`;
  $("#factRecall").classList.toggle("alert", rc.retained < rc.fault_effects);
  $("#recallNote").textContent = rc.missed.length
    ? `Missed: ${rc.missed.join(", ")}. The rules need a lower threshold or a longer window for slow faults.`
    : "Every effect the injected fault produced is in the ledger.";
  $("#sizeValue").textContent = `${kb(v.raw.bytes_json)} → ${kb(v.curation.ledger_bytes_json)}`;
  const conflicts = ledgerItems.filter((x) => x.type === "conflict");
  $("#conflictValue").textContent = `${conflicts.length} sensor`;
  $("#conflictNote").textContent = conflicts.length ? conflicts[0].detail + "." : "None.";

  funnel.append(el("p", { class: "small quiet", text: `Bars use a logarithmic scale. The ${ledgerItems.length} ledger items point back to ${fmt.format(v.curation.represented_records)} source records.` }));
  const episodes = ledgerItems.filter((x) => x.type === "episode").length;
  $("#ledgerTitle").textContent = `Evidence ledger · ${ledgerItems.length} items (${episodes} fault episodes) out of ${fmt.format(total)} records`;
  const kindName = { episode: "Episode", conflict: "Conflict", context: "Context", document: "Procedure" };
  $("#ledger").replaceChildren(...ledgerItems.map((it) => el("li", {},
    el("span", { class: `kind ${it.type}`, text: kindName[it.type] }),
    el("span", {}, el("b", { text: it.label }), ` — ${it.detail}`),
    el("span", { class: "src", text: `Source: ${it.records.join(" … ")}${it.samples > 1 ? ` (${fmt.format(it.samples)} records)` : ""}` }))));
}

// ---------------------------------------------------------------------------
// Chapter 2: routes
// ---------------------------------------------------------------------------
function renderRoutes() {
  const { q1, q2, q3 } = decisions();
  const m = state.bundle.models, labels = state.bundle.class_labels, t = state.timings, v = V();
  const cls = m.compact_fault.classes;
  const cards = [
    { route: 1, q: "Is coolant supply on loop A above its limit?",
      answer: [q1.above ? "Yes" : "No", `. Supply is `, metric(`${q1.supply.toFixed(1)} °C`, "simulation"), `, limit ${q1.limit} °C.`],
      why: "A trusted sensor and an approved threshold. Arithmetic answers this exactly; a model would only add doubt.",
      meta: [["Method", "comparison with limit"], ["Parameters", "0"], ["Time per call", us(t.r1), "measured"]] },
    { route: 2, q: "Is the R07 flow drop transient or does it need action?",
      answer: q2.confident
        ? [el("b", { text: q2.actionable ? "Needs action" : "Transient" }), " with probability ", metric(q2.actionable ? q2.p.toFixed(2) : (1 - q2.p).toFixed(2), "simulation"), "."]
        : [el("b", { text: "Undecided" }), ": probability of needing action is ", metric(q2.p.toFixed(2), "simulation"), ", below the 0.80 contract. Escalated to a person with the evidence."],
      why: `A bounded yes-or-no question with uncertainty. A calibrated logistic model on ${m.actionable.features.length} curated features states how sure it is.`,
      meta: [["Model", "logistic regression"], ["Parameters", String(parameterCount(m.actionable))], ["Time per call", us(t.r2), "measured"]] },
    { route: q3.route, q: "Which fault pattern is this?",
      answer: [el("b", { text: labels[cls[q3.finalIdx]] }), " with probability ", metric(q3.finalP.toFixed(2), "simulation"), "."],
      why: q3.esc.escalate
        ? `The compact decision model tried first but could only reach ${q3.esc.top.toFixed(2)} (the contract needs ${state.threshold.toFixed(2)}): restriction and pump wear look alike on two features. The question escalated to a model that reads valve, pressure and pump behaviour.`
        : "The compact decision model met the contract on its own, so no escalation was needed.",
      meta: [["Model", q3.esc.escalate ? "multiclass logistic, 8 time-series features" : "multiclass logistic, 2 features"],
             ["Parameters", String(parameterCount(q3.esc.escalate ? m.specialized_fault : m.compact_fault))],
             ["Time per call", us(q3.esc.escalate ? t.r2c + t.r3 : t.r2c), "measured"]] },
    { route: 4, q: "Drain R07 now, or keep the training job running until the 02:00 maintenance window?",
      answer: [el("b", { text: "Not run in this demonstration." }), " It would receive the ", metric(`${v.curation.ledger.length}-item`, "simulation", "span"), " evidence ledger (", metric(kb(v.curation.ledger_bytes_json), "simulation", "span"), "), never the raw day."],
      why: "Service commitments, the thermal trend, staffing and a contradicting flow meter have to be weighed together. No rule or trained model covers that trade-off; for now the approver decides.",
      meta: [["Tokens", "not measured", "not-measured"], ["Cost", "not measured", "not-measured"]] },
  ];
  $("#routes").replaceChildren(...cards.map((c) => el("article", { class: "route", "data-route": String(c.route) },
    el("div", { class: "route-head" }, el("div", { class: "route-name", text: ROUTE_NAMES[c.route] }),
      c.route === 3 && q3.esc.escalate ? el("p", { class: "small quiet", text: "Escalated from route 2" }) : null),
    el("div", {},
      el("p", { class: "route-q", text: c.q }),
      el("p", { class: "route-answer" }, ...c.answer),
      el("p", { class: "route-why", text: c.why }),
      el("div", { class: "route-meta" }, ...c.meta.map(([k, val, kind]) => el("span", {}, `${k}: `,
        kind ? metric(val, kind) : el("b", { text: val }), kind ? " " : null, kind ? badge(kind) : null)))))));
}

// ---------------------------------------------------------------------------
// Chapter 3: escalation
// ---------------------------------------------------------------------------
function probRows(probs, color, threshold) {
  const labels = state.bundle.class_labels, cls = state.bundle.models.compact_fault.classes;
  return probs.map((p, i) => el("div", { class: "prob" },
    el("span", { text: labels[cls[i]] }),
    el("span", { class: "prob-bar", "aria-hidden": "true", style: `--c:${color}` },
      el("i", { style: `width:${(100 * p).toFixed(1)}%` }),
      threshold != null ? el("span", { class: "mark", style: `left:${(100 * threshold).toFixed(1)}%` }) : null),
    metric(p.toFixed(2), "simulation", "span")));
}

function renderEscalation() {
  const { q3 } = decisions();
  const labels = state.bundle.class_labels, cls = state.bundle.models.compact_fault.classes;
  $("#thresholdValue").textContent = state.threshold.toFixed(2);
  $("#compactProbs").replaceChildren(...probRows(q3.compact, "var(--route-2)", state.threshold));
  const verdict = $("#verdict");
  const top = labels[cls[q3.esc.index]];
  verdict.classList.remove("wrong");
  if (q3.esc.escalate) {
    verdict.style.setProperty("--c", "var(--route-3)");
    verdict.replaceChildren(el("b", { text: "Escalated." }), ` Best guess “${top}” at ${q3.esc.top.toFixed(2)} is below the required ${state.threshold.toFixed(2)}.`);
    $("#specialized").hidden = false;
    $("#specialProbs").replaceChildren(...probRows(q3.special, "var(--route-3)", null));
  } else {
    $("#specialized").hidden = true;
    const right = cls[q3.esc.index] === "branch_restriction";
    verdict.style.setProperty("--c", "var(--route-2)");
    if (!right) verdict.classList.add("wrong");
    verdict.replaceChildren(el("b", { text: right ? "Accepted." : "Accepted, and wrong." }),
      ` “${top}” at ${q3.esc.top.toFixed(2)} clears the ${state.threshold.toFixed(2)} threshold, so nothing escalates.`,
      right ? "" : " The injected fault is a branch restriction. A contract that is too lax lets a cheap model answer what it cannot.");
  }
  const ev = state.bundle.models;
  $("#modelQuality").textContent = `On ${ev.compact_fault.evaluation.n} held-out simulated episodes, the compact model is right ${pct(ev.compact_fault.evaluation.accuracy, 1)} of the time and the specialized model ${pct(ev.specialized_fault.evaluation.accuracy, 1)}. The simulation is clean, so the second figure says nothing about real-world accuracy.`;
}

// ---------------------------------------------------------------------------
// Chapter 4: decision record
// ---------------------------------------------------------------------------
function recordData() {
  const { q1, q2, q3 } = decisions();
  const v = V(), labels = state.bundle.class_labels, cls = state.bundle.models.compact_fault.classes;
  const f = v.features;
  const ledger = v.curation.ledger;
  const conflicts = ledger.filter((x) => x.type === "conflict").map((x) => `${x.label}: ${x.detail}`);
  const actionable = q2.confident && q2.actionable;
  return {
    schema: "slowai-decision-record/1",
    evidence_kind: "reproducible_simulation",
    scenario: v.title, seed: state.bundle.seed, decision_time: state.bundle.decision_time,
    situation: `R07 coolant flow ${f.flow_drop_pct.toFixed(0)}% below its baseline; return temperature +${f.return_rise_c.toFixed(1)} °C; ${f.throttle_30min} GPU throttle events in the last 30 min.`,
    most_likely_cause: `${labels[cls[q3.finalIdx]]} (probability ${q3.finalP.toFixed(2)}, route ${q3.route})`,
    proposed_action: actionable
      ? "Reduce load on R07 and inspect its branch strainer and valve. Do not rely on the secondary flow meter."
      : "No intervention yet. Schedule an inspection of the R07 branch and keep monitoring; review again within the hour.",
    open_question: "Drain R07 now or wait for the 02:00 maintenance window. Routed to frontier reasoning, which was not run; the approver decides.",
    routes: [
      { question: "Supply above limit?", route: 1, answer: q1.above ? "yes" : "no" },
      { question: "Transient or actionable?", route: 2, answer: q2.confident ? (q2.actionable ? "actionable" : "transient") : "undecided, escalated to a person", probability_actionable: Number(q2.p.toFixed(3)) },
      { question: "Which fault?", route: q3.route, escalated_from_route_2: q3.esc.escalate, answer: cls[q3.finalIdx], probability: Number(q3.finalP.toFixed(3)), threshold: state.threshold },
      { question: "Drain now or wait?", route: 4, answer: null, note: "not run" },
    ],
    evidence: ledger.map((x) => ({ type: x.type, label: x.label, records: x.records })),
    conflicts,
    approval: { required: true, approver: "Infrastructure Operations", status: "awaiting approval" },
  };
}

function renderRecord() {
  const r = recordData();
  const rows = [
    ["Situation", r.situation],
    ["Most likely cause", r.most_likely_cause],
    ["Proposed action", r.proposed_action],
    ["Open question", r.open_question],
    ["Routes used", r.routes.map((x) => `${x.question} → route ${x.route}${x.escalated_from_route_2 ? " (escalated)" : ""}${x.note ? ` (${x.note})` : ""}`).join(" · ")],
    ["Evidence", `${r.evidence.length} ledger items, each linked to source records`],
    ["Conflicts", r.conflicts.join(" ") || "None"],
    ["Approval", null],
  ];
  $("#recordFields").replaceChildren(...rows.flatMap(([k, val]) => [el("dt", { text: k }),
    val == null ? el("dd", {}, "Required from ", el("b", { text: r.approval.approver }), " · ", el("span", { class: "status", text: "Awaiting approval" })) : el("dd", { text: val })]));
}

function downloadRecord() {
  const blob = new Blob([JSON.stringify(recordData(), null, 2)], { type: "application/json" });
  const a = el("a", { href: URL.createObjectURL(blob), download: `slowai-decision-record-${state.variant}.json` });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------------------------------------------------------------------------
// Chapter 5: measurement
// ---------------------------------------------------------------------------
function renderCosts() {
  const t = state.timings, m = state.bundle.models, { q3 } = decisions();
  const nm = () => el("td", {}, badge("not-measured"));
  const row = (route, where, size, time, tokens) => el("tr", {},
    el("th", { scope: "row", text: ROUTE_NAMES[route] }), el("td", { text: where }), el("td", { text: size }),
    time == null ? nm() : el("td", {}, metric(time, "measured", "span"), " ", badge("measured")),
    tokens == null ? nm() : el("td", { text: tokens }), nm(), nm());
  $("#costTable").replaceChildren(
    row(1, "This browser", "no model", us(t.r1), "0"),
    row(2, "This browser", `${parameterCount(m.actionable)} parameters (transient or actionable) · ${parameterCount(m.compact_fault)} (compact fault model)`, `${us(t.r2)} · ${us(t.r2c)}`, "0"),
    row(3, "This browser", `${parameterCount(m.specialized_fault)} parameters${q3.esc.escalate ? "" : " (not needed)"}`, us(t.r3), "0"),
    el("tr", {}, el("th", { scope: "row", text: ROUTE_NAMES[4] }), el("td", { text: "Not run" }), el("td", { text: "—" }), nm(), nm(), nm(), nm()));
}

async function loadSteel() {
  const box = $("#steelAcc");
  try {
    const res = await fetch("../challenge/evidence/steel-v1.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d = await res.json();
    const rows = [["Always the most frequent fault (no model)", d.results.majority_class_non_ai], ["3-nearest-neighbour classifier", d.results.knn_3]];
    box.replaceChildren(...rows.map(([name, r]) => {
      const [lo, hi] = wilson(r.correct, r.total);
      return el("div", { class: "acc-row" },
        el("span", {}, name, el("br"), el("span", { class: "small quiet", text: `95% interval ${pct(lo, 1)}–${pct(hi, 1)} · macro-F1 ${r.macro_f1.toFixed(2)}` })),
        metric(pct(r.accuracy, 1), "measured", "strong"),
        el("span", { class: "bar", role: "img", "aria-label": `${name}: accuracy ${pct(r.accuracy, 1)}, 95% interval ${pct(lo, 1)} to ${pct(hi, 1)}` },
          el("i", { style: `width:${(100 * r.accuracy).toFixed(1)}%` }),
          el("span", { class: "ci", style: `left:${(100 * lo).toFixed(1)}%;width:${(100 * (hi - lo)).toFixed(1)}%` })));
    }), el("p", { class: "small quiet", text: `${fmt.format(d.dataset_size)} records · ${d.train_count} train / ${d.test_count} test · ${d.license} · source SHA-256 ${d.source_sha256.slice(0, 12)}…` }));
    box.dataset.loaded = "true";
  } catch (err) {
    box.replaceChildren(el("p", { class: "small", text: `The published evidence file could not be loaded (${err.message}). Open the Steel Evidence Explorer instead.` }));
    box.dataset.loaded = "false";
  }
}

// ---------------------------------------------------------------------------
// Wiring
// ---------------------------------------------------------------------------
function setVariant(key) {
  state.variant = key;
  $$("[data-variant]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.variant === key)));
  state.timings = measureTimings();
  renderCuration(true); renderRoutes(); renderEscalation(); renderRecord(); renderCosts();
}

function observeChapters() {
  const links = new Map($$(".rail a").map((a) => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) {
      links.forEach((a, id) => a.setAttribute("aria-current", String(id === e.target.id)));
    }
  }, { rootMargin: "-40% 0px -55% 0px" });
  $$(".chapter").forEach((c) => io.observe(c));
  let played = false;
  const funnelIo = new IntersectionObserver((entries) => {
    if (!played && entries.some((e) => e.isIntersecting)) { played = true; renderCuration(true); funnelIo.disconnect(); }
  }, { threshold: 0.35 });
  funnelIo.observe($("#funnel"));
}


// ---------------------------------------------------------------------------
// Overview: one simulated hour in a 100 MW-class AI factory (story/data/campus-v1.json)
// ---------------------------------------------------------------------------
async function loadCampus() {
  const box = $("#hourRoutes");
  try {
    const res = await fetch("data/campus-v1.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const c = await res.json(), q = c.questions, e = c.escalation_summary;
    $("#campusScale").textContent = `${fmt.format(c.campus.racks)} liquid-cooled racks at ${c.campus.rack_kw} kW, ${c.campus.cdus} cooling loops, ${c.campus.window}.`;
    const rows = [
      [1, `Is ${q.supply_limit.cdu} supply above its limit?`, `No: ${q.supply_limit.supply_c} °C against a ${q.supply_limit.limit_c} °C limit. Every sensor limit and camera frame is checked this way, every second.`],
      [2, "Will rack R14 throttle in the next 15 minutes?", `Yes, probability ${q.throttle_risk.p_compact.toFixed(2)}. In the simulation it throttled at ${q.throttle_risk.actually_throttled_at}. Called only for rack-minutes whose temperature was rising.`],
      [3, "Is that a coolant leak under R14?", `Leak, probability ${q.leak.leak_probability} (simulated output). Also answers the uncertain cases the small model escalates.`],
      [4, `Shed ${q.grid.request_mw} MW from ${q.grid.at}: which jobs to checkpoint first?`, "Grid, customer commitments and cooling weighed together, on curated evidence only. Not run in this demonstration; the approver decides."],
    ];
    const maxLog = Math.log10(c.route_counts["1"] + 1);
    const bars = [];
    box.replaceChildren(...rows.map(([k, question, answer]) => {
      const n = c.route_counts[String(k)], bar = el("i");
      bars.push([bar, (100 * Math.log10(n + 1)) / maxLog]);
      return el("article", { class: "hour-row", "data-route": String(k) },
        el("div", {}, el("span", { class: "hour-name", text: ROUTE_NAMES[k] }),
          metric(fmt.format(n), "simulation", "strong"), el("span", { class: "small quiet", text: n === 1 ? "call this hour" : "calls this hour" })),
        el("div", {}, el("div", { class: "hour-bar", "aria-hidden": "true" }, bar),
          el("p", { class: "hour-q", text: question }), el("p", { class: "hour-a small", text: answer })));
    }));
    $$(".hour-row strong[data-metric]").forEach((n) => n.classList.add("hour-count"));
    const apply = () => bars.forEach(([b, w], i) => setTimeout(() => (b.style.width = `${w.toFixed(1)}%`), reduceMotion ? 0 : i * 200));
    if (reduceMotion) apply(); else requestAnimationFrame(() => requestAnimationFrame(apply));
    $("#hourEscalation").replaceChildren(
      el("p", {}, el("strong", { text: "Was escalating worth it? " }),
        `Of ${fmt.format(e.count)} uncertain cases the small model sent up a level, the specialized model was right `,
        metric(fmt.format(e.specialized_correct), "simulation"), " times and the small model ", metric(fmt.format(e.compact_correct), "simulation"),
        `. Escalation fixed ${e.specialized_correct - e.compact_correct} answers.`),
      el("p", { class: "small quiet", style: "margin-top:8px" },
        "Method: each answer is compared with what the simulated rack actually did in the next 15 minutes. Bars use a logarithmic scale. ",
        el("a", { href: "https://github.com/opedoussaut/slow-ai/blob/main/story/generator/campus.py", text: "Generator source" })));
    box.dataset.loaded = "true";
  } catch (err) {
    box.replaceChildren(el("p", { class: "small", text: `The simulated hour could not be loaded (${err.message}).` }));
    box.dataset.loaded = "false";
  }
}

async function init() {
  try {
    const res = await fetch("data/scenario-v1.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.bundle = await res.json();
  } catch (err) {
    $("#main").prepend(el("p", { class: "lead", role: "alert", text: `The scenario data could not be loaded (${err.message}). Reload the page.` }));
    return;
  }
  $("#rawTotal").textContent = fmt.format(state.bundle.variants.main.raw.total);
  $("#seed").textContent = state.bundle.seed;
  drawStream();
  window.addEventListener("resize", () => drawStream());
  state.timings = measureTimings();
  renderCuration(false); renderRoutes(); renderEscalation(); renderRecord(); renderCosts();
  $$("[data-variant]").forEach((b) => b.addEventListener("click", () => setVariant(b.dataset.variant)));
  $("#threshold").addEventListener("input", (e) => {
    state.threshold = Number(e.target.value);
    renderEscalation(); renderRoutes(); renderRecord(); renderCosts();
  });
  $("#downloadRecord").addEventListener("click", downloadRecord);
  observeChapters();
  await Promise.all([loadCampus(), loadSteel()]);
  document.documentElement.dataset.ready = "true";
}

init();
