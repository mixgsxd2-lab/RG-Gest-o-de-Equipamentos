import { api } from "../api.js";
import { barChart } from "../charts.js";
import { bindRows, can, esc, fmt, formFields, icon, loading, modal, options, prioBadge, state, statusBadge, table, toast } from "../ui.js";

const view = { tab: "distribuicao", days: 90 };

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Equipes e técnicos</h1><div class="sub">Especialidades, distribuição de demandas e produtividade — próprios e terceirizados</div></div>
      <div class="actions">${can("teams.edit") ? `<button class="btn primary" id="new">${icon("plus")} Novo técnico</button>` : ""}</div>
    </div>
    <div class="tabs">${[["distribuicao", "Distribuição de demandas"], ["produtividade", "Produtividade"], ["tecnicos", "Técnicos e especialidades"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; render(el, _params, ctx); }));
  el.querySelector("#new")?.addEventListener("click", () => editTech(null, () => render(el, _params, ctx)));
  const body = el.querySelector("#body");
  if (view.tab === "distribuicao") return workload(body, ctx, () => render(el, _params, ctx));
  if (view.tab === "produtividade") return productivity(body, ctx, () => render(el, _params, ctx));
  return technicians(body, ctx, () => render(el, _params, ctx));
}

async function workload(body, ctx, reload) {
  const data = await api.get("/api/technicians/workload");
  if (!ctx.isCurrent()) return;
  const lk = state.lookups;
  body.innerHTML = `
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Carga atual por técnico</h3><span class="hint">Chamados recebidos, aceitos, em execução ou aguardando</span></div>
        <div class="card-body"><div class="chart-box tall"><canvas id="wl"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Fila sem técnico designado</h3><span class="hint">${data.unassigned.length} chamado(s)</span></div>
        <div class="card-body flush" id="queue"></div></div>
      <div class="card span-2"><div class="card-head"><h3>Demandas por técnico</h3></div><div class="card-body flush" id="bytech"></div></div>
    </div>`;
  const techs = data.technicians;
  barChart(body.querySelector("#wl"), {
    labels: techs.map((t) => t.name), horizontal: true, stacked: true,
    datasets: [
      { label: "Urgente/Alta", data: techs.map((t) => t.urgent), colorIndex: 1 },
      { label: "Demais prioridades", data: techs.map((t) => t.active_tickets - t.urgent), colorIndex: 0 },
    ],
  });
  const q = body.querySelector("#queue");
  q.innerHTML = table([
    { label: "Chamado", cls: "title-cell", render: (t) => `<a href="#/chamados/${t.id}"><b>${esc(t.code)}</b></a> · ${esc(t.title)}<div class="sub-cell">${esc(t.team)} · ${fmt.rel(t.created_at)}</div>` },
    { label: "Prioridade", render: (t) => prioBadge(t.priority) },
    ...(can("tickets.manage") ? [{ label: "Designar", render: (t) => `<select data-assign="${t.id}" aria-label="Designar técnico" style="min-width:150px">${options(lk.technicians.filter((x) => x.team_id === t.team_id), "", { empty: "Técnico…" })}</select>` }] : []),
  ], data.unassigned, { empty: "Nenhum chamado aguardando designação" });
  q.querySelectorAll("[data-assign]").forEach((s) => s.addEventListener("change", async () => {
    if (!s.value) return;
    try {
      await api.post(`/api/tickets/${s.dataset.assign}/actions/assign`, { technician_id: s.value });
      toast("Técnico designado", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      reload();
    } catch (err) { toast(err.message, "err"); }
  }));
  body.querySelector("#bytech").innerHTML = table([
    { label: "Técnico", cls: "title-cell", render: (t) => `<b>${esc(t.name)}</b>${t.external ? ' <span class="tag">Terceiro</span>' : ""}<div class="sub-cell">${esc(t.team || "")} · ${esc(t.specialty || "")}</div>` },
    { label: "Ativos", key: "active_tickets", num: true },
    { label: "Chamados", render: (t) => t.tickets.map((x) => `<a href="#/chamados/${x.id}" class="nowrap">${esc(x.code)}</a> ${statusBadge(x.status, state.lookups.statuses[x.status])}`).join("<br>") || '<span class="muted">Livre</span>' },
  ], techs);
}

async function productivity(body, ctx, reload) {
  const rows = await api.get("/api/technicians/productivity", { days: view.days });
  if (!ctx.isCurrent()) return;
  const active = rows.filter((r) => r.assigned);
  body.innerHTML = `
    <div class="filters"><div class="seg">${[[30, "30 dias"], [90, "90 dias"], [180, "6 meses"], [365, "12 meses"]]
      .map(([d, l]) => `<button type="button" data-days="${d}" class="${view.days === d ? "on" : ""}">${l}</button>`).join("")}</div></div>
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Chamados finalizados por técnico</h3></div><div class="card-body"><div class="chart-box tall"><canvas id="p1"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Horas trabalhadas por técnico</h3></div><div class="card-body"><div class="chart-box tall"><canvas id="p2"></canvas></div></div></div>
      <div class="card span-2"><div class="card-body flush" id="ptable"></div></div>
    </div>`;
  body.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { view.days = Number(b.dataset.days); reload(); }));
  barChart(body.querySelector("#p1"), { labels: active.map((r) => r.name), horizontal: true, datasets: [{ label: "Finalizados", data: active.map((r) => r.finished) }] });
  barChart(body.querySelector("#p2"), { labels: active.map((r) => r.name), horizontal: true, datasets: [{ label: "Horas", data: active.map((r) => r.hours), colorIndex: 2 }] });
  body.querySelector("#ptable").innerHTML = table([
    { label: "Técnico", cls: "title-cell", render: (r) => `<b>${esc(r.name)}</b>${r.external ? ' <span class="tag">Terceiro</span>' : ""}<div class="sub-cell">${esc(r.team || "")}</div>` },
    { label: "Atribuídos", key: "assigned", num: true },
    { label: "Finalizados", key: "finished", num: true },
    { label: "Em andamento", key: "in_progress", num: true },
    { label: "Horas", render: (r) => fmt.num(r.hours, 1), num: true },
    { label: "Tempo médio", render: (r) => fmt.hours(r.avg_resolution_hours), num: true },
    { label: "SLA cumprido", render: (r) => fmt.pct(r.sla_compliance), num: true },
  ], rows);
}

async function technicians(body, ctx, reload) {
  const rows = await api.get("/api/technicians", { all: 1 });
  if (!ctx.isCurrent()) return;
  body.innerHTML = `<div class="card"><div class="card-body flush" id="tlist"></div></div>`;
  const box = body.querySelector("#tlist");
  box.innerHTML = table([
    { label: "Técnico", cls: "title-cell", render: (t) => `<b>${esc(t.name)}</b>${t.external ? ` <span class="tag">Terceiro · ${esc(t.supplier)}</span>` : ""}<div class="sub-cell">${esc(t.specialty || "")}</div>` },
    { label: "Equipe", key: "team" },
    { label: "Turno", key: "shift" },
    { label: "Matrícula", key: "registration" },
    { label: "Usuário", render: (t) => esc(t.username || "—") },
    { label: "Custo/hora", render: (t) => fmt.money(t.hourly_rate), num: true },
    { label: "Situação", render: (t) => (t.active ? '<span class="badge b-good">Ativo</span>' : '<span class="badge b-neutral">Inativo</span>') },
  ], rows, { onRow: can("teams.edit") });
  if (can("teams.edit")) bindRows(box, rows, (t) => editTech(t, reload));
}

function editTech(t, done) {
  const lk = state.lookups;
  t = t || { active: true, hourly_rate: 50 };
  modal({
    title: t.id ? `Editar ${t.name}` : "Novo técnico",
    body: `<div class="form-grid">${formFields([
      { name: "name", label: "Nome", required: true, full: true },
      { name: "specialty", label: "Especialidade", full: true },
      { name: "team_id", label: "Equipe", type: "select", options: options(lk.teams, t.team_id, { empty: "—" }) },
      { name: "supplier_id", label: "Empresa (se terceiro)", type: "select", options: options(lk.suppliers, t.supplier_id, { empty: "Próprio" }) },
      { name: "shift", label: "Turno" },
      { name: "registration", label: "Matrícula" },
      { name: "phone", label: "Telefone" },
      { name: "hourly_rate", label: "Custo/hora (R$)", type: "number", step: "0.01", min: 0 },
      ...(t.id ? [{ name: "active", label: "Situação", type: "checkbox", checkLabel: "Ativo", value: t.active }] : []),
    ], t)}</div>`,
    onSubmit: async (_f, data) => {
      if (t.id) await api.put(`/api/technicians/${t.id}`, data); else await api.post("/api/technicians", data);
      toast("Técnico salvo", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}
