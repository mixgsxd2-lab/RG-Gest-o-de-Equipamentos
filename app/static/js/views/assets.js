import { api } from "../api.js";
import {
  assetBadge, bindRows, can, confirmDialog, esc, fmt, formFields, icon, kpi, levelBadge, loading, modal, options,
  prioBadge, sitBadge, state, statusBadge, table, toast,
} from "../ui.js";

const f = { q: "", sector_id: "", category: "", status: "", kind: "", page: 1 };

export async function render(el, params, ctx) {
  if (params[0]) return renderDetail(el, Number(params[0]), ctx);
  const lk = state.lookups;
  const cats = await api.get("/api/assets/categories");
  if (!ctx.isCurrent()) return;
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Inventário de ativos</h1><div class="sub">Equipamentos médicos, instalações e estruturas com vida útil, depreciação e histórico</div></div>
      <div class="actions">${can("indicators.view") ? `<a class="btn" href="/api/intelligence/export/ativos.csv">${icon("download")} Exportar CSV</a>` : ""}
      ${can("assets.edit") ? `<button class="btn primary" id="new">${icon("plus")} Novo ativo</button>` : ""}</div>
    </div>
    <div class="filters">
      <input type="search" id="q" placeholder="Buscar patrimônio, nome, fabricante, modelo, local…" value="${esc(f.q)}">
      <select id="sector_id">${options(lk.sectors, f.sector_id, { empty: "Todos os setores" })}</select>
      <select id="category">${options(cats, f.category, { empty: "Todas as categorias" })}</select>
      <select id="kind">${options(lk.asset_kinds, f.kind, { empty: "Equipamentos e estruturas" })}</select>
      <select id="status">${options(lk.asset_statuses, f.status, { empty: "Todos os status" })}</select>
    </div>
    <div class="card" id="list">${loading()}</div>`;
  ["sector_id", "category", "kind", "status"].forEach((id) => el.querySelector(`#${id}`).addEventListener("change", (e) => { f[id] = e.target.value; f.page = 1; load(el, ctx); }));
  let t;
  el.querySelector("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { f.q = e.target.value; f.page = 1; load(el, ctx); }, 300); });
  el.querySelector("#new")?.addEventListener("click", () => editAsset(null, cats, () => load(el, ctx)));
  await load(el, ctx);
}

async function load(el, ctx) {
  const data = await api.get("/api/assets", { ...f, per_page: 30 });
  if (!ctx.isCurrent()) return;
  const box = el.querySelector("#list");
  box.innerHTML = table([
    { label: "Patrimônio / ativo", cls: "title-cell", render: (a) => `<b>${esc(a.tag)}</b> · ${esc(a.name)}<div class="sub-cell">${esc(a.manufacturer || "")} ${esc(a.model || "")}</div>` },
    { label: "Categoria", render: (a) => `${esc(a.category)}<div class="sub-cell">${esc(a.kind)}</div>` },
    { label: "Setor / local", render: (a) => `${esc(a.sector || "—")}<div class="sub-cell">${esc(a.location || "")}</div>` },
    { label: "Criticidade", render: (a) => prioBadge(a.criticality) },
    { label: "Status", render: (a) => assetBadge(a.status) },
    { label: "Valor contábil", render: (a) => fmt.money(a.depreciation.book_value), num: true },
    { label: "Vida útil restante", render: (a) => `${fmt.num(a.depreciation.remaining_years, 1)} anos`, num: true },
  ], data.items, { onRow: true, empty: "Nenhum ativo encontrado" }) +
    `<div class="pager"><span>${data.total} ativo(s)</span><span class="actions">
      <button class="btn sm" id="prev" ${data.page <= 1 ? "disabled" : ""}>Anterior</button><span>Página ${data.page} de ${Math.max(1, data.pages)}</span>
      <button class="btn sm" id="next" ${data.page >= data.pages ? "disabled" : ""}>Próxima</button></span></div>`;
  bindRows(box, data.items, (a) => { location.hash = `#/ativos/${a.id}`; });
  box.querySelector("#prev")?.addEventListener("click", () => { f.page--; load(el, ctx); });
  box.querySelector("#next")?.addEventListener("click", () => { f.page++; load(el, ctx); });
}

function editAsset(a, cats, done) {
  const lk = state.lookups;
  a = a || { kind: "Equipamento", status: "Operacional", criticality: "Média", useful_life_years: 10 };
  modal({
    title: a.id ? `Editar ${a.tag}` : "Novo ativo", wide: true, submitLabel: "Salvar",
    body: `<div class="form-grid">${formFields([
      { name: "tag", label: "Patrimônio", required: true },
      { name: "name", label: "Nome", required: true },
      { name: "category", label: "Categoria", required: true, attrs: 'list="cats"' },
      { name: "kind", label: "Tipo", type: "select", options: options(lk.asset_kinds, a.kind) },
      { name: "sector_id", label: "Setor", type: "select", options: options(lk.sectors, a.sector_id, { empty: "—" }) },
      { name: "location", label: "Localização" },
      { name: "manufacturer", label: "Fabricante" },
      { name: "model", label: "Modelo" },
      { name: "serial_number", label: "Nº de série" },
      { name: "supplier_id", label: "Fornecedor / assistência", type: "select", options: options(lk.suppliers, a.supplier_id, { empty: "—" }) },
      { name: "acquisition_date", label: "Data de aquisição", type: "date" },
      { name: "acquisition_cost", label: "Custo de aquisição (R$)", type: "number", step: "0.01", min: 0 },
      { name: "useful_life_years", label: "Vida útil (anos)", type: "number", step: "0.5", min: 0 },
      { name: "residual_value", label: "Valor residual (R$)", type: "number", step: "0.01", min: 0 },
      { name: "warranty_until", label: "Garantia até", type: "date" },
      { name: "criticality", label: "Criticidade", type: "select", options: options(lk.criticalities, a.criticality) },
      { name: "status", label: "Status", type: "select", options: options(lk.asset_statuses, a.status) },
      { name: "notes", label: "Observações", type: "textarea", full: true },
    ], a)}</div><datalist id="cats">${cats.map((c) => `<option value="${esc(c)}">`).join("")}</datalist>`,
    onSubmit: async (_f, data) => {
      if (a.id) await api.put(`/api/assets/${a.id}`, data); else await api.post("/api/assets", data);
      toast("Ativo salvo", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}

async function renderDetail(el, id, ctx) {
  el.innerHTML = loading();
  const a = await api.get(`/api/assets/${id}`);
  if (!ctx.isCurrent()) return;
  const d = a.depreciation;
  const s = a.summary;
  el.innerHTML = `
    <div class="page-head">
      <div><a href="#/ativos" class="muted small">${icon("back")} Inventário</a>
        <h1 style="margin-top:4px">${esc(a.tag)} · ${esc(a.name)}</h1>
        <div class="actions" style="margin-top:8px">${assetBadge(a.status)} ${prioBadge(a.criticality)} <span class="badge b-neutral plain">${esc(a.category)}</span></div></div>
      <div class="actions">
        ${can("tickets.create") ? `<a class="btn primary" href="#/chamados/novo">${icon("plus")} Abrir chamado</a>` : ""}
        ${can("assets.edit") ? `<button class="btn" id="edit">${icon("edit")} Editar</button><button class="btn danger" id="del">Baixar / excluir</button>` : ""}
      </div>
    </div>
    <div class="kpis">
      ${kpi({ label: "Chamados (histórico)", value: fmt.num(s.tickets), foot: `${s.failures} falhas corretivas/emergenciais` })}
      ${kpi({ label: "Custo de manutenção", value: fmt.moneyShort(s.maintenance_cost), foot: `${fmt.num(s.labor_hours, 1)} h de mão de obra` })}
      ${kpi({ label: "Valor contábil", value: fmt.moneyShort(d.book_value), foot: `Aquisição ${fmt.money(a.acquisition_cost)}` })}
      ${kpi({ label: "Depreciação acumulada", value: fmt.pct(d.percent), foot: `${fmt.money(d.annual)} / ano` })}
      ${kpi({ label: "Vida útil restante", value: `${fmt.num(d.remaining_years, 1)} anos`, foot: `Idade ${fmt.num(d.age_years, 1)} de ${fmt.num(a.useful_life_years, 1)} anos` })}
    </div>
    <div class="grid grid-3">
      <div class="card"><div class="card-head"><h3>Cadastro</h3></div><div class="card-body"><dl class="kv">
        <dt>Tipo</dt><dd>${esc(a.kind)}</dd>
        <dt>Setor</dt><dd>${esc(a.sector || "—")}</dd><dt>Localização</dt><dd>${esc(a.location || "—")}</dd>
        <dt>Fabricante</dt><dd>${esc(a.manufacturer || "—")}</dd><dt>Modelo</dt><dd>${esc(a.model || "—")}</dd>
        <dt>Nº de série</dt><dd>${esc(a.serial_number || "—")}</dd><dt>Fornecedor</dt><dd>${esc(a.supplier || "—")}</dd>
        <dt>Aquisição</dt><dd>${fmt.date(a.acquisition_date)}</dd><dt>Garantia até</dt><dd>${fmt.date(a.warranty_until)}</dd>
        <dt>Última manutenção</dt><dd>${fmt.datetime(s.last_maintenance)}</dd>
      </dl>${a.notes ? `<p class="muted small" style="margin-top:10px">${esc(a.notes)}</p>` : ""}</div></div>
      <div class="card"><div class="card-head"><h3>Depreciação (linear)</h3></div><div class="card-body stack" style="gap:10px">
        <div class="meter" title="${fmt.pct(d.percent)} depreciado"><div style="width:${Math.min(100, d.percent)}%"></div></div>
        <dl class="kv">
          <dt>Custo de aquisição</dt><dd>${fmt.money(a.acquisition_cost)}</dd><dt>Valor residual</dt><dd>${fmt.money(a.residual_value)}</dd>
          <dt>Depreciação anual</dt><dd>${fmt.money(d.annual)}</dd><dt>Acumulada</dt><dd>${fmt.money(d.accumulated)}</dd>
          <dt>Valor contábil</dt><dd><b>${fmt.money(d.book_value)}</b></dd>
        </dl>
        ${d.remaining_years <= 1.5 ? `<div class="notice warn">${icon("alert")} Ativo próximo ou além do fim da vida útil — avaliar substituição.</div>` : ""}
      </div></div>
      <div class="card"><div class="card-head"><h3>Planos e sensores</h3></div><div class="card-body stack" style="gap:10px">
        ${a.plans.length ? a.plans.map((p) => `<div><b>${esc(p.name)}</b><div class="small muted">A cada ${p.frequency_days} dias · próximo ${fmt.date(p.next_due)} ${sitBadge(p.situation)}</div></div>`).join("") : '<span class="muted small">Nenhum plano preventivo</span>'}
        ${a.sensors.length ? a.sensors.map((x) => `<div><b>${esc(x.name)}</b><div class="small muted">${fmt.num(x.last_value, 2)} ${esc(x.unit || "")} ${levelBadge(x.state, x.state === "alerta" ? "Alerta" : "Normal")}</div></div>`).join("") : ""}
      </div></div>
      <div class="card span-3"><div class="card-head"><h3>Histórico de manutenção</h3><span class="hint">${a.history.length} chamado(s)</span></div>
        <div class="card-body flush" id="hist"></div></div>
    </div>`;
  const hist = el.querySelector("#hist");
  hist.innerHTML = table([
    { label: "Chamado", cls: "title-cell", render: (t) => `<b>${esc(t.code)}</b> · ${esc(t.title)}` },
    { label: "Tipo", key: "maintenance_type" },
    { label: "Status", render: (t) => statusBadge(t.status, t.status_label) },
    { label: "Operador", render: (t) => esc(t.operator || "—") },
    { label: "Abertura", render: (t) => fmt.date(t.created_at), cls: "nowrap" },
    { label: "Tempo", render: (t) => fmt.hours(t.resolution_hours), num: true },
    { label: "Custo", render: (t) => fmt.money(t.total_cost), num: true },
  ], a.history, { onRow: true, empty: "Sem histórico de manutenção" });
  bindRows(hist, a.history, (t) => { location.hash = `#/chamados/${t.id}`; });
  el.querySelector("#edit")?.addEventListener("click", async () => {
    const cats = await api.get("/api/assets/categories");
    editAsset(a, cats, () => renderDetail(el, id, ctx));
  });
  el.querySelector("#del")?.addEventListener("click", async () => {
    if (!(await confirmDialog("Ativos com histórico são desativados (baixa patrimonial); ativos sem histórico são excluídos. Continuar?", { danger: true, label: "Confirmar baixa" }))) return;
    const r = await api.del(`/api/assets/${a.id}`);
    toast(r.deactivated ? "Ativo desativado" : "Ativo excluído", "ok");
    window.dispatchEvent(new Event("rg:data-changed"));
    location.hash = r.deactivated ? `#/ativos/${a.id}` : "#/ativos";
    if (r.deactivated) renderDetail(el, id, ctx);
  });
}
