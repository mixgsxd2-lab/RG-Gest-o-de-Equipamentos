import { api } from "../api.js";
import { barChart, seriesColor } from "../charts.js";
import { barList, can, confirmDialog, esc, fmt, formFields, icon, kpi, loading, modal, options, state, table, toast } from "../ui.js";

const view = { days: 180, category: "", sector_id: "" };

export async function render(el, _params, ctx) {
  const lk = state.lookups;
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Custos da manutenção</h1><div class="sub">Materiais, mão de obra, terceiros, contratos e investimentos — lançamentos de chamados são automáticos</div></div>
      <div class="actions">${can("indicators.view") ? `<a class="btn" href="/api/intelligence/export/custos.csv">${icon("download")} Exportar CSV</a>` : ""}
        ${can("costs.edit") ? `<button class="btn primary" id="new">${icon("plus")} Novo lançamento</button>` : ""}</div>
    </div>
    <div class="filters">
      <div class="seg">${[[30, "30 dias"], [90, "90 dias"], [180, "6 meses"], [365, "12 meses"]].map(([d, l]) => `<button type="button" data-days="${d}" class="${view.days === d ? "on" : ""}">${l}</button>`).join("")}</div>
      <select id="sector_id">${options(lk.sectors, view.sector_id, { empty: "Todos os setores" })}</select>
      <select id="category">${options(lk.cost_categories, view.category, { empty: "Todas as categorias" })}</select>
    </div>
    <div id="body">${loading()}</div>`;
  const reload = () => render(el, _params, ctx);
  el.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { view.days = Number(b.dataset.days); reload(); }));
  el.querySelector("#sector_id").addEventListener("change", (e) => { view.sector_id = e.target.value; reload(); });
  el.querySelector("#category").addEventListener("change", (e) => { view.category = e.target.value; reload(); });
  el.querySelector("#new")?.addEventListener("click", () => newCost(reload));

  const data = await api.get("/api/costs", view);
  if (!ctx.isCurrent()) return;
  const a = data.analysis;
  const cat = Object.fromEntries(a.by_category.map((c) => [c.label, c.value]));
  const body = el.querySelector("#body");
  const pvc = a.preventive_vs_corrective;
  body.innerHTML = `
    <div class="kpis">
      ${kpi({ label: "Total no período", value: fmt.moneyShort(a.total) })}
      ${lk.cost_categories.map((c, i) => kpi({ label: c, value: fmt.moneyShort(cat[c] || 0), dot: seriesColor(i) })).join("")}
      ${kpi({ label: "Contratos (mensal vigente)", value: fmt.moneyShort(a.contracts_monthly_total) })}
    </div>
    <div class="grid grid-3">
      <div class="card"><div class="card-head"><h3>Custo por tipo de manutenção</h3></div><div class="card-body"><div class="chart-box"><canvas id="c1"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Ativos com maior custo</h3></div><div class="card-body">${barList(a.top_assets, { format: fmt.moneyShort })}</div></div>
      <div class="card"><div class="card-head"><h3>Preventiva × corretiva</h3><span class="hint">Custo de chamados</span></div><div class="card-body">
        ${barList([{ label: "Preventiva/preditiva/inspeção/calibração", value: pvc.preventive, color: seriesColor(2) }, { label: "Corretiva/emergencial", value: pvc.corrective, color: seriesColor(1) }], { format: fmt.moneyShort })}
        <p class="small muted" style="margin-top:12px">${pvc.preventive + pvc.corrective ? `${fmt.pct(Math.round((1000 * pvc.preventive) / (pvc.preventive + pvc.corrective)) / 10)} do custo de chamados é planejado.` : ""}</p>
        <h3 style="margin:16px 0 8px">Por fornecedor</h3>${barList(a.by_supplier.map((s) => ({ ...s, label: s.label.replace(" (fictício)", "") })), { format: fmt.moneyShort, color: seriesColor(3) })}</div></div>
      <div class="card span-3"><div class="card-head"><h3>Lançamentos</h3><span class="hint">${data.items.length} lançamento(s) · ${fmt.money(data.total_amount)}</span></div>
        <div class="card-body flush" id="t"></div></div>
    </div>`;
  barChart(body.querySelector("#c1"), { labels: a.by_maintenance_type.map((x) => x.label), horizontal: true, money: true, datasets: [{ label: "Custo", data: a.by_maintenance_type.map((x) => x.value) }] });
  const rows = data.items.slice(0, 300);
  const box = body.querySelector("#t");
  box.innerHTML = table([
    { label: "Data", render: (c) => fmt.date(c.date), cls: "nowrap" },
    { label: "Categoria", render: (c) => `<span class="tag">${esc(c.category)}</span>` },
    { label: "Descrição", cls: "title-cell", render: (c) => `${esc(c.description)}<div class="sub-cell">${[c.sector, c.asset, c.supplier, c.contract].filter(Boolean).map(esc).join(" · ")}</div>` },
    { label: "Chamado", render: (c) => (c.ticket_id ? `<a href="#/chamados/${c.ticket_id}">${esc(c.ticket_code)}</a>` : "—") },
    { label: "Valor", render: (c) => fmt.money(c.amount), num: true },
    ...(can("costs.edit") ? [{ label: "", render: (c) => (c.ticket_id ? "" : `<button class="btn sm ghost" data-del="${c.id}" aria-label="Excluir">${icon("x")}</button>`) }] : []),
  ], rows, { empty: "Nenhum lançamento no período" }) + (data.items.length > rows.length ? `<div class="pager">Exibindo ${rows.length} de ${data.items.length}. Exporte o CSV para a lista completa.</div>` : "");
  box.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmDialog("Excluir este lançamento de custo?", { danger: true, label: "Excluir" }))) return;
    try { await api.del(`/api/costs/${b.dataset.del}`); toast("Lançamento excluído", "ok"); reload(); } catch (err) { toast(err.message, "err"); }
  }));
}

function newCost(done) {
  const lk = state.lookups;
  modal({
    title: "Novo lançamento de custo", wide: true,
    body: `<div class="form-grid">${formFields([
      { name: "category", label: "Categoria", type: "select", required: true, options: options(lk.cost_categories, "Investimento") },
      { name: "date", label: "Data", type: "date", required: true, value: new Date().toISOString().slice(0, 10) },
      { name: "description", label: "Descrição", required: true, full: true },
      { name: "amount", label: "Valor (R$)", type: "number", step: "0.01", min: 0, required: true },
      { name: "sector_id", label: "Setor / centro de custo", type: "select", options: options(lk.sectors, "", { empty: "—" }) },
      { name: "team_id", label: "Equipe", type: "select", options: options(lk.teams, "", { empty: "—" }) },
      { name: "asset_id", label: "Ativo", type: "select", options: options(lk.assets, "", { empty: "—", label: (a) => `${a.tag} — ${a.name}` }) },
      { name: "supplier_id", label: "Fornecedor", type: "select", options: options(lk.suppliers, "", { empty: "—" }) },
    ])}</div>`,
    onSubmit: async (_f, data) => { await api.post("/api/costs", data); toast("Custo lançado", "ok"); done(); },
  });
}
