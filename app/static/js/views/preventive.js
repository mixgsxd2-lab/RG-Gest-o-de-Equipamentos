import { api } from "../api.js";
import { can, esc, fmt, formFields, icon, kpi, loading, modal, options, sitBadge, state, table, toast } from "../ui.js";

const MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const view = { month: null, situation: "" };
const SIT_COLOR = { Atrasada: "var(--critical)", Próxima: "var(--warning)", Programada: "var(--info)", Executada: "var(--good)" };
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export async function render(el, _params, ctx) {
  if (!view.month) { const n = new Date(); view.month = new Date(n.getFullYear(), n.getMonth(), 1); }
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Manutenção preventiva</h1><div class="sub">Calendário, planos periódicos, calibrações, inspeções e geração de ordens de serviço</div></div>
      <div class="actions">${can("preventive.edit") ? `<button class="btn primary" id="new">${icon("plus")} Novo plano</button>` : ""}</div>
    </div>
    <div id="body">${loading()}</div>`;
  el.querySelector("#new")?.addEventListener("click", () => editPlan(null, () => render(el, _params, ctx)));
  const first = new Date(view.month);
  const start = new Date(first); start.setDate(1 - ((first.getDay() + 6) % 7));
  const end = new Date(start); end.setDate(start.getDate() + 41);
  const [plans, events] = await Promise.all([
    api.get("/api/preventive"),
    api.get("/api/preventive/calendar", { start: iso(start), end: iso(end) }),
  ]);
  if (!ctx.isCurrent()) return;
  const count = (s) => plans.filter((p) => p.active && p.situation === s).length;
  const body = el.querySelector("#body");
  const todayIso = iso(new Date());
  const byDay = {};
  events.forEach((e) => { (byDay[e.date] = byDay[e.date] || []).push(e); });
  let cells = "";
  for (let i = 0; i < 42; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i);
    const key = iso(d);
    const evs = byDay[key] || [];
    cells += `<div class="day ${d.getMonth() !== first.getMonth() ? "out" : ""} ${key === todayIso ? "today" : ""}">
      <span class="d">${d.getDate()}</span>
      ${evs.slice(0, 3).map((e) => `<div class="ev" style="color:${SIT_COLOR[e.situation]};background:color-mix(in srgb, ${SIT_COLOR[e.situation]} 12%, transparent)" title="${esc(e.title)} · ${esc(e.team || "")} · ${esc(e.situation)}" data-ticket="${e.ticket_id || ""}"><span style="color:var(--text)">${esc(e.asset || "")} ${esc(e.title)}</span></div>`).join("")}
      ${evs.length > 3 ? `<span class="more">+${evs.length - 3} mais</span>` : ""}</div>`;
  }
  const shown = plans.filter((p) => p.active && (!view.situation || p.situation === view.situation));
  body.innerHTML = `
    <div class="kpis">
      ${kpi({ label: "Planos ativos", value: plans.filter((p) => p.active).length })}
      ${kpi({ label: "Atrasadas", value: count("Atrasada"), dot: "var(--critical)" })}
      ${kpi({ label: "Próximos 7 dias", value: count("Próxima"), dot: "var(--warning)" })}
      ${kpi({ label: "Programadas", value: count("Programada"), dot: "var(--info)" })}
    </div>
    <div class="card" style="margin-bottom:16px"><div class="card-body">
      <div class="cal-head">
        <div class="actions"><button class="btn sm" id="pm" aria-label="Mês anterior">‹</button><h2>${MONTHS[first.getMonth()]} ${first.getFullYear()}</h2><button class="btn sm" id="nm" aria-label="Próximo mês">›</button><button class="btn sm ghost" id="tm">Hoje</button></div>
        <div class="legend">${Object.entries(SIT_COLOR).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join("")}</div>
      </div>
      <div class="calendar">${["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"].map((d) => `<div class="dow">${d}</div>`).join("")}${cells}</div>
    </div></div>
    <div class="card"><div class="card-head"><h3>Planos de manutenção</h3>
      <select id="sit" style="width:auto">${options(["Atrasada", "Próxima", "Programada"], view.situation, { empty: "Todas as situações" })}</select></div>
      <div class="card-body flush" id="plans"></div></div>`;
  // KPIs de situação filtram a lista de planos
  [...body.querySelectorAll(".kpi")].slice(1).forEach((k, i) => {
    k.classList.add("link");
    k.addEventListener("click", () => { view.situation = ["Atrasada", "Próxima", "Programada"][i]; render(el, _params, ctx); });
  });
  body.querySelector("#pm").addEventListener("click", () => { view.month = new Date(first.getFullYear(), first.getMonth() - 1, 1); render(el, _params, ctx); });
  body.querySelector("#nm").addEventListener("click", () => { view.month = new Date(first.getFullYear(), first.getMonth() + 1, 1); render(el, _params, ctx); });
  body.querySelector("#tm").addEventListener("click", () => { view.month = null; render(el, _params, ctx); });
  body.querySelector("#sit").addEventListener("change", (e) => { view.situation = e.target.value; render(el, _params, ctx); });
  body.querySelectorAll(".ev[data-ticket]").forEach((e) => e.addEventListener("click", () => { if (e.dataset.ticket) location.hash = `#/chamados/${e.dataset.ticket}`; }));

  const box = body.querySelector("#plans");
  box.innerHTML = table([
    { label: "Plano", cls: "title-cell", render: (p) => `<b>${esc(p.name)}</b><div class="sub-cell">${esc(p.asset || "Sem ativo")} · ${esc(p.sector || "")}</div>` },
    { label: "Tipo", key: "maintenance_type" },
    { label: "Equipe / executor", render: (p) => `${esc(p.team)}<div class="sub-cell">${esc(p.technician || p.supplier || "—")}</div>` },
    { label: "Frequência", render: (p) => `${p.frequency_days} dias`, num: true },
    { label: "Última", render: (p) => fmt.date(p.last_done), cls: "nowrap" },
    { label: "Próxima", render: (p) => `${fmt.date(p.next_due)}<div class="sub-cell">${p.days_to_due < 0 ? `${-p.days_to_due} dia(s) em atraso` : p.days_to_due === 0 ? "hoje" : p.days_to_due === 1 ? "amanhã" : `em ${p.days_to_due} dias`}</div>`, cls: "nowrap" },
    { label: "Situação", render: (p) => sitBadge(p.situation) },
    { label: "OS", render: (p) => p.open_ticket_id ? `<a href="#/chamados/${p.open_ticket_id}">${esc(p.open_ticket_code)}</a>`
      : can("preventive.edit") ? `<button class="btn sm" data-gen="${p.id}">Gerar OS</button>` : "—" },
    ...(can("preventive.edit") ? [{ label: "", render: (p) => `<button class="btn sm ghost" data-edit="${p.id}" aria-label="Editar">${icon("edit")}</button>` }] : []),
  ], shown, { empty: "Nenhum plano nesta situação" });
  box.querySelectorAll("[data-gen]").forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      const t = await api.post(`/api/preventive/${b.dataset.gen}/generate`);
      toast(`OS ${t.code} gerada`, "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      render(el, _params, ctx);
    } catch (err) { toast(err.message, "err"); b.disabled = false; }
  }));
  box.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editPlan(plans.find((p) => p.id === Number(b.dataset.edit)), () => render(el, _params, ctx))));
}

function editPlan(p, done) {
  const lk = state.lookups;
  p = p || { maintenance_type: "Preventiva", frequency_days: 30, estimated_hours: 2 };
  modal({
    title: p.id ? "Editar plano" : "Novo plano de manutenção", wide: true,
    body: `<div class="form-grid">${formFields([
      { name: "name", label: "Nome do plano", required: true, full: true },
      { name: "asset_id", label: "Ativo", type: "select", full: true, options: options(lk.assets, p.asset_id, { empty: "—", label: (a) => `${a.tag} — ${a.name}` }) },
      { name: "team_id", label: "Equipe", type: "select", required: true, options: options(lk.teams, p.team_id, { empty: "Selecione…" }) },
      { name: "maintenance_type", label: "Tipo", type: "select", options: options(["Preventiva", "Preditiva", "Inspeção", "Calibração"], p.maintenance_type) },
      { name: "technician_id", label: "Técnico responsável", type: "select", options: options(lk.technicians, p.technician_id, { empty: "—" }) },
      { name: "supplier_id", label: "Fornecedor (se terceirizado)", type: "select", options: options(lk.suppliers, p.supplier_id, { empty: "—" }) },
      { name: "frequency_days", label: "Frequência (dias)", type: "number", min: 1, required: true },
      { name: "estimated_hours", label: "Horas estimadas", type: "number", step: "0.5", min: 0 },
      { name: "last_done", label: "Última execução", type: "date" },
      { name: "next_due", label: "Próximo vencimento", type: "date", help: "Se vazio, calculado pela última execução + frequência" },
      { name: "checklist", label: "Checklist (um item por linha)", type: "textarea", full: true },
      ...(p.id ? [{ name: "active", label: "Situação", type: "checkbox", checkLabel: "Plano ativo", value: p.active }] : []),
    ], p)}</div>`,
    onSubmit: async (_f, data) => {
      if (p.id) await api.put(`/api/preventive/${p.id}`, data); else await api.post("/api/preventive", data);
      toast("Plano salvo", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}

