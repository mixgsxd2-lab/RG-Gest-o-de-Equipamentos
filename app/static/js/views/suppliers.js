import { api } from "../api.js";
import { barChart } from "../charts.js";
import { bindRows, can, esc, fmt, formFields, icon, kpi, loading, modal, options, sitBadge, state, table, toast } from "../ui.js";

const view = { tab: "desempenho", days: 180 };

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Fornecedores e contratos</h1><div class="sub">Terceiros, contratos de manutenção, SLA contratual e desempenho</div></div>
      <div class="actions">${can("teams.edit") ? `<button class="btn" id="new-sup">${icon("plus")} Fornecedor</button><button class="btn primary" id="new-ct">${icon("plus")} Contrato</button>` : ""}</div>
    </div>
    <div class="tabs">${[["desempenho", "Desempenho"], ["contratos", "Contratos"], ["fornecedores", "Fornecedores"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  const reload = () => render(el, _params, ctx);
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; reload(); }));
  el.querySelector("#new-sup")?.addEventListener("click", () => editSupplier(null, reload));
  el.querySelector("#new-ct")?.addEventListener("click", () => editContract(null, reload));
  const body = el.querySelector("#body");
  if (view.tab === "desempenho") return performance(body, ctx, reload);
  if (view.tab === "contratos") return contracts(body, ctx, reload);
  return suppliers(body, ctx, reload);
}

async function performance(body, ctx, reload) {
  const rows = await api.get("/api/suppliers/performance", { days: view.days });
  if (!ctx.isCurrent()) return;
  body.innerHTML = `
    <div class="filters"><div class="seg">${[[90, "90 dias"], [180, "6 meses"], [365, "12 meses"]]
      .map(([d, l]) => `<button type="button" data-days="${d}" class="${view.days === d ? "on" : ""}">${l}</button>`).join("")}</div></div>
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Índice de desempenho (0–100)</h3><span class="hint">SLA 50% · avaliação 30% · conclusão 20%</span></div>
        <div class="card-body"><div class="chart-box tall"><canvas id="c1"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Custo com terceiros e contratos</h3></div>
        <div class="card-body"><div class="chart-box tall"><canvas id="c2"></canvas></div></div></div>
      <div class="card span-2"><div class="card-body flush" id="t"></div></div>
    </div>`;
  body.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { view.days = Number(b.dataset.days); reload(); }));
  barChart(body.querySelector("#c1"), { labels: rows.map((r) => r.name.replace(" (fictício)", "")), horizontal: true, datasets: [{ label: "Índice", data: rows.map((r) => r.score) }] });
  const byCost = [...rows].sort((a, b) => b.cost - a.cost);
  barChart(body.querySelector("#c2"), { labels: byCost.map((r) => r.name.replace(" (fictício)", "")), horizontal: true, money: true, datasets: [{ label: "Custo", data: byCost.map((r) => r.cost), colorIndex: 1 }] });
  body.querySelector("#t").innerHTML = table([
    { label: "Fornecedor", cls: "title-cell", render: (r) => `<b>${esc(r.name)}</b><div class="sub-cell">${esc(r.category || "")}</div>` },
    { label: "Chamados", key: "tickets", num: true },
    { label: "Finalizados", key: "finished", num: true },
    { label: "Tempo médio", render: (r) => fmt.hours(r.avg_resolution_hours), num: true },
    { label: "SLA", render: (r) => fmt.pct(r.sla_compliance), num: true },
    { label: "Avaliação", render: (r) => `${fmt.num(r.rating, 1)} / 5`, num: true },
    { label: "Contratos ativos", render: (r) => `${r.active_contracts} · ${fmt.money(r.contract_monthly)}/mês`, num: true },
    { label: "Custo no período", render: (r) => fmt.money(r.cost), num: true },
    { label: "Índice", render: (r) => `<b>${fmt.num(r.score, 0)}</b>`, num: true },
  ], rows);
}

async function contracts(body, ctx, reload) {
  const rows = await api.get("/api/contracts");
  if (!ctx.isCurrent()) return;
  const active = rows.filter((c) => c.status === "Vigente" || c.status === "A vencer");
  body.innerHTML = `
    <div class="kpis">
      ${kpi({ label: "Contratos vigentes", value: active.length })}
      ${kpi({ label: "A vencer (60 dias)", value: rows.filter((c) => c.status === "A vencer").length, dot: "var(--warning)" })}
      ${kpi({ label: "Vencidos", value: rows.filter((c) => c.status === "Vencido").length, dot: "var(--critical)" })}
      ${kpi({ label: "Valor mensal vigente", value: fmt.moneyShort(active.reduce((a, c) => a + c.monthly_value, 0)), foot: `${fmt.money(active.reduce((a, c) => a + c.annual_value, 0))} / ano` })}
    </div>
    <div class="card"><div class="card-body flush" id="t"></div></div>`;
  const box = body.querySelector("#t");
  box.innerHTML = table([
    { label: "Contrato", cls: "title-cell", render: (c) => `<b>${esc(c.number)}</b> · ${esc(c.scope)}<div class="sub-cell">${esc(c.supplier)} · ${esc(c.team || "")}</div>` },
    { label: "Vigência", render: (c) => `${fmt.date(c.start_date)} a ${fmt.date(c.end_date)}<div class="sub-cell">${c.days_to_end >= 0 ? `${c.days_to_end} dias restantes` : `vencido há ${-c.days_to_end} dias`}</div>`, cls: "nowrap" },
    { label: "SLA (resp./solução)", render: (c) => `${c.sla_response_hours} h / ${c.sla_resolution_hours} h`, num: true },
    { label: "Mensal", render: (c) => fmt.money(c.monthly_value), num: true },
    { label: "Situação", render: (c) => sitBadge(c.status) },
  ], rows, { onRow: can("teams.edit") });
  if (can("teams.edit")) bindRows(box, rows, (c) => editContract(c, reload));
}

async function suppliers(body, ctx, reload) {
  const rows = await api.get("/api/suppliers", { all: 1 });
  if (!ctx.isCurrent()) return;
  body.innerHTML = `<div class="card"><div class="card-body flush" id="t"></div></div>`;
  const box = body.querySelector("#t");
  box.innerHTML = table([
    { label: "Fornecedor", cls: "title-cell", render: (s) => `<b>${esc(s.name)}</b><div class="sub-cell">CNPJ ${esc(s.cnpj || "—")}</div>` },
    { label: "Categoria", key: "category" },
    { label: "Contato", render: (s) => `${esc(s.contact_name || "—")}<div class="sub-cell">${esc(s.phone || "")} · ${esc(s.email || "")}</div>` },
    { label: "Avaliação", render: (s) => `${fmt.num(s.rating, 1)} / 5`, num: true },
    { label: "Situação", render: (s) => (s.active ? '<span class="badge b-good">Ativo</span>' : '<span class="badge b-neutral">Inativo</span>') },
  ], rows, { onRow: can("teams.edit") });
  if (can("teams.edit")) bindRows(box, rows, (s) => editSupplier(s, reload));
}

function editSupplier(s, done) {
  s = s || { rating: 4, active: true };
  modal({
    title: s.id ? `Editar ${s.name}` : "Novo fornecedor",
    body: `<div class="form-grid">${formFields([
      { name: "name", label: "Razão social / nome", required: true, full: true },
      { name: "cnpj", label: "CNPJ" }, { name: "category", label: "Categoria" },
      { name: "contact_name", label: "Contato" }, { name: "phone", label: "Telefone" },
      { name: "email", label: "E-mail", type: "email" },
      { name: "rating", label: "Avaliação (0 a 5)", type: "number", step: "0.1", min: 0, attrs: 'max="5"' },
      ...(s.id ? [{ name: "active", label: "Situação", type: "checkbox", checkLabel: "Ativo", value: s.active }] : []),
    ], s)}</div>`,
    onSubmit: async (_f, data) => {
      if (s.id) await api.put(`/api/suppliers/${s.id}`, data); else await api.post("/api/suppliers", data);
      toast("Fornecedor salvo", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}

function editContract(c, done) {
  const lk = state.lookups;
  c = c || { sla_response_hours: 4, sla_resolution_hours: 24 };
  modal({
    title: c.id ? `Contrato ${c.number}` : "Novo contrato", wide: true,
    body: `<div class="form-grid">${formFields([
      { name: "number", label: "Número", required: true },
      { name: "supplier_id", label: "Fornecedor", type: "select", required: true, options: options(lk.suppliers, c.supplier_id, { empty: "Selecione…" }) },
      { name: "scope", label: "Objeto / escopo", required: true, full: true },
      { name: "team_id", label: "Equipe gestora", type: "select", options: options(lk.teams, c.team_id, { empty: "—" }) },
      { name: "monthly_value", label: "Valor mensal (R$)", type: "number", step: "0.01", min: 0 },
      { name: "start_date", label: "Início", type: "date", required: true },
      { name: "end_date", label: "Término", type: "date", required: true },
      { name: "sla_response_hours", label: "SLA de resposta (h)", type: "number", min: 0 },
      { name: "sla_resolution_hours", label: "SLA de solução (h)", type: "number", min: 0 },
      { name: "notes", label: "Observações", type: "textarea", full: true },
    ], c)}</div>`,
    onSubmit: async (_f, data) => {
      if (c.id) await api.put(`/api/contracts/${c.id}`, data); else await api.post("/api/contracts", data);
      toast("Contrato salvo", "ok");
      done();
    },
  });
}
