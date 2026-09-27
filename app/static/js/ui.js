// Utilitários de interface: formatação, ícones, badges, modais, formulários e tabelas

export const state = { user: null, lookups: null };
export const can = (perm) => !!state.user && state.user.permissions.includes(perm);

export function esc(v) {
  if (v === null || v === undefined) return "";
  return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const brlShort = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1 });
export const fmt = {
  money: (v) => brl.format(v || 0),
  moneyShort: (v) => (Math.abs(v || 0) >= 10000 ? brlShort.format(v || 0) : brl.format(v || 0)),
  num: (v, d = 0) => (v === null || v === undefined ? "—" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d })),
  pct: (v) => (v === null || v === undefined ? "—" : `${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`),
  hours: (v) => {
    if (v === null || v === undefined) return "—";
    if (v < 1) return `${Math.round(v * 60)} min`;
    if (v >= 48) return `${(v / 24).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} dias`;
    return `${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} h`;
  },
  date: (iso) => (iso ? new Date(iso.length === 10 ? iso + "T00:00:00" : iso).toLocaleDateString("pt-BR") : "—"),
  datetime: (iso) => (iso ? new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"),
  rel: (iso) => {
    if (!iso) return "—";
    const diff = (Date.now() - new Date(iso).getTime()) / 60000;
    const fut = diff < 0; const m = Math.abs(diff);
    let s;
    if (m < 60) s = `${Math.round(m)} min`;
    else if (m < 60 * 48) s = `${Math.round(m / 60)} h`;
    else s = `${Math.round(m / 1440)} dias`;
    return fut ? `em ${s}` : `há ${s}`;
  },
};

export function initials(name) {
  return (name || "?").split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

// ---------------------------------------------------------------- Ícones (SVG em linha)
const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  ticket: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  asset: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  truck: '<path d="M1 3h15v13H1zM16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
  box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.27 6.96 12 12.01l8.73-5.05M12 22.08V12"/>',
  money: '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  chart: '<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>',
  menu: '<path d="M3 12h18M3 6h18M3 18h18"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  clip: '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
  back: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/>',
  zap: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
  droplet: '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
  wind: '<path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/>',
  thermo: '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
  refresh: '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
  play: '<path d="m5 3 14 9-14 9z"/>',
  pause: '<path d="M6 4h4v16H6zM14 4h4v16h-4z"/>',
  key: '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
};
// Estrela de quatro pontas do símbolo do Hospital Rio Grande
const SPARK = "M11.2 2h1.6v6.4a2.8 2.8 0 0 0 2.8 2.8H22v1.6h-6.4a2.8 2.8 0 0 0-2.8 2.8V22h-1.6v-6.4a2.8 2.8 0 0 0-2.8-2.8H2v-1.6h6.4a2.8 2.8 0 0 0 2.8-2.8z";
export const sparkIcon = (cls = "") => `<svg class="icon spark ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${SPARK}"/></svg>`;
export const icon = (name, cls = "") => `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;

// ---------------------------------------------------------------- Badges
const STATUS_CLASS = {
  aberto: "b-info", recebido: "b-violet", aceito: "b-info", em_execucao: "b-warning", aguardando: "b-serious",
  finalizado: "b-good", encerrado: "b-neutral", cancelado: "b-neutral",
};
export const statusBadge = (s, label) => `<span class="badge ${STATUS_CLASS[s] || "b-neutral"}">${esc(label || s)}</span>`;
const PRIO_CLASS = { Baixa: "b-neutral", Média: "b-info", Alta: "b-serious", Urgente: "b-critical", Crítica: "b-critical" };
export const prioBadge = (p) => `<span class="badge ${PRIO_CLASS[p] || "b-neutral"}">${esc(p)}</span>`;
const SLA = { no_prazo: ["b-good", "No prazo"], em_risco: ["b-warning", "Em risco"], violado: ["b-critical", "Violado"], cumprido: ["b-good", "Cumprido"] };
export const slaBadge = (s) => (s ? `<span class="badge ${SLA[s][0]}">${SLA[s][1]}</span>` : '<span class="muted">—</span>');
const ASSET = { Operacional: "b-good", "Em manutenção": "b-warning", Inoperante: "b-critical", Reserva: "b-info", Desativado: "b-neutral" };
export const assetBadge = (s) => `<span class="badge ${ASSET[s] || "b-neutral"}">${esc(s)}</span>`;
const SIT = { Atrasada: "b-critical", Próxima: "b-warning", Programada: "b-info", Executada: "b-good", Vigente: "b-good", "A vencer": "b-warning", Vencido: "b-critical", Futuro: "b-info" };
export const sitBadge = (s) => `<span class="badge ${SIT[s] || "b-neutral"}">${esc(s)}</span>`;
const LEVEL = { Alto: "b-critical", Médio: "b-warning", Baixo: "b-good", alerta: "b-critical", normal: "b-good", sem_dados: "b-neutral" };
export const levelBadge = (s, label) => `<span class="badge ${LEVEL[s] || "b-neutral"}">${esc(label || s)}</span>`;

// ---------------------------------------------------------------- Toast
export function toast(msg, type = "") {
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => el.remove(), type === "err" ? 5500 : 3200);
}

// ---------------------------------------------------------------- Formulários
export function options(list, selected, { empty = null, value = "id", label = "name" } = {}) {
  let html = empty !== null ? `<option value="">${esc(empty)}</option>` : "";
  for (const item of list) {
    const v = typeof item === "object" ? item[value] : item;
    const l = typeof item === "object" ? (typeof label === "function" ? label(item) : item[label]) : item;
    html += `<option value="${esc(v)}" ${String(v) === String(selected ?? "") ? "selected" : ""}>${esc(l)}</option>`;
  }
  return html;
}

/** fields: [{name,label,type,options,required,full,help,step,placeholder,attrs}] */
export function formFields(fields, values = {}) {
  return fields.map((f) => {
    const v = values[f.name] ?? f.value ?? "";
    const req = f.required ? "required" : "";
    const id = `f_${f.name}`;
    let input;
    if (f.type === "select") {
      input = `<select id="${id}" name="${f.name}" ${req} ${f.attrs || ""}>${f.options}</select>`;
    } else if (f.type === "textarea") {
      input = `<textarea id="${id}" name="${f.name}" ${req} placeholder="${esc(f.placeholder || "")}" ${f.attrs || ""}>${esc(v)}</textarea>`;
    } else if (f.type === "file") {
      input = `<input id="${id}" type="file" name="${f.name}" ${f.multiple ? "multiple" : ""} accept="${f.accept || ""}" ${f.attrs || ""}>`;
    } else if (f.type === "checkbox") {
      input = `<label style="display:flex;gap:8px;align-items:center;font-weight:500"><input id="${id}" type="checkbox" name="${f.name}" ${v ? "checked" : ""}> ${esc(f.checkLabel || "")}</label>`;
    } else if (f.type === "html") {
      return `<div class="${f.full ? "full" : ""}">${f.html}</div>`;
    } else {
      input = `<input id="${id}" type="${f.type || "text"}" name="${f.name}" value="${esc(v)}" ${req} ${f.step ? `step="${f.step}"` : ""} ${f.min !== undefined ? `min="${f.min}"` : ""} placeholder="${esc(f.placeholder || "")}" ${f.attrs || ""}>`;
    }
    return `<div class="field ${f.full ? "full" : ""}"><label for="${id}">${esc(f.label)}${f.required ? ' <span class="req">*</span>' : ""}</label>${input}${f.help ? `<span class="help">${esc(f.help)}</span>` : ""}</div>`;
  }).join("");
}

export function readForm(form) {
  const data = {};
  for (const el of form.elements) {
    if (!el.name || el.type === "file") continue;
    if (el.type === "checkbox") data[el.name] = el.checked;
    else data[el.name] = el.value;
  }
  return data;
}

// ---------------------------------------------------------------- Modal
export function modal({ title, body, wide = false, submitLabel = "Salvar", cancelLabel = "Cancelar", onSubmit, onOpen, onClose, danger = false, noFooter = false }) {
  const back = document.createElement("div");
  back.className = "modal-back";
  back.innerHTML = `
    <form class="modal ${wide ? "wide" : ""}" novalidate>
      <div class="modal-head"><h2>${esc(title)}</h2><button type="button" class="icon-btn" data-close aria-label="Fechar">${icon("x")}</button></div>
      <div class="modal-body">${body}</div>
      ${noFooter ? "" : `<div class="modal-foot">
        <button type="button" class="btn" data-close>${esc(cancelLabel)}</button>
        ${onSubmit ? `<button type="submit" class="btn ${danger ? "danger" : "primary"}">${esc(submitLabel)}</button>` : ""}
      </div>`}
    </form>`;
  document.body.appendChild(back);
  const form = back.querySelector("form");
  const close = () => {
    back.remove();
    document.removeEventListener("keydown", onKey);
    if (onClose) onClose();
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  document.addEventListener("keydown", onKey);
  back.addEventListener("mousedown", (e) => { if (e.target === back) close(); });
  back.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!onSubmit) return close();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      const keep = await onSubmit(form, readForm(form));
      if (keep !== false) close();
    } catch (err) {
      toast(err.message, "err");
    } finally {
      btn.disabled = false;
    }
  });
  if (onOpen) onOpen(form, close);
  const first = form.querySelector(".modal-body input:not([type=hidden]), .modal-body select, .modal-body textarea");
  if (first && window.innerWidth > 720) first.focus();
  return close;
}

export function confirmDialog(message, { title = "Confirmar", label = "Confirmar", danger = false } = {}) {
  return new Promise((resolve) => {
    let ok = false;
    modal({ title, body: `<p>${esc(message)}</p>`, submitLabel: label, danger,
      onSubmit: () => { ok = true; }, onClose: () => resolve(ok) });
  });
}

// ---------------------------------------------------------------- Tabelas
/** columns: [{label, key, render(row), cls, num}] */
export function table(columns, rows, { onRow = null, empty = "Nenhum registro encontrado", responsive = true } = {}) {
  if (!rows.length) return `<div class="empty">${esc(empty)}</div>`;
  const head = columns.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.label)}</th>`).join("");
  const body = rows.map((r, i) => `<tr ${onRow ? `class="clickable" data-row="${i}"` : ""}>${columns.map((c) => {
    const val = c.render ? c.render(r) : esc(r[c.key] ?? "—");
    return `<td class="${c.cls || ""} ${c.num ? "num" : ""}" data-label="${esc(c.label)}">${val}</td>`;
  }).join("")}</tr>`).join("");
  return `<div class="table-wrap"><table class="table ${responsive ? "responsive" : ""}"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function bindRows(container, rows, fn) {
  container.querySelectorAll("tr[data-row]").forEach((tr) => {
    tr.addEventListener("click", (e) => {
      if (e.target.closest("a,button,input,select")) return;
      fn(rows[Number(tr.dataset.row)]);
    });
  });
}

export function loading() {
  return '<div class="loading"><div class="spinner"></div>Carregando…</div>';
}

export function kpi({ label, value, foot = "", href = "", dot = "" }) {
  return `<div class="kpi ${href ? "link" : ""}" ${href ? `data-href="${href}" role="link" tabindex="0"` : ""}>
    <div class="label">${dot ? `<span class="ind" style="background:${dot}"></span>` : ""}${esc(label)}</div>
    <div class="value">${value}</div>${foot ? `<div class="foot">${foot}</div>` : ""}</div>`;
}

export function bindKpiLinks(root) {
  root.querySelectorAll(".kpi[data-href]").forEach((el) => {
    const go = () => { location.hash = el.dataset.href; };
    el.addEventListener("click", go);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  });
}

export function barList(items, { format = (v) => fmt.num(v), color = "var(--series-1)" } = {}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  if (!items.length) return '<div class="empty">Sem dados no período</div>';
  return `<div class="bar-list">${items.map((i) => `
    <div class="bar-row" title="${esc(i.label)}: ${esc(format(i.value))}">
      <span class="lbl">${esc(i.label)}</span>
      <span class="trk"><span class="fill" style="display:block;width:${(100 * i.value) / max}%;background:${i.color || color}"></span></span>
      <span class="v">${esc(format(i.value))}</span>
    </div>`).join("")}</div>`;
}

export function toLocalInput(d = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function downloadLink(href, label) {
  return `<a class="btn sm" href="${href}" download>${icon("download")} ${esc(label)}</a>`;
}
