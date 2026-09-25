import { api } from "../api.js";
import { bindRows, can, esc, fmt, formFields, icon, kpi, loading, modal, options, state, table, toast } from "../ui.js";

const view = { tab: "produtos", q: "", below: false, kind: "", page: 1 };
const KIND = { entrada: ["b-good", "Entrada"], saida: ["b-serious", "Saída"], ajuste: ["b-info", "Ajuste"] };

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Estoque de peças e materiais</h1><div class="sub">Entradas, saídas, estoque mínimo, custo médio e consumo por chamado</div></div>
      <div class="actions">${can("stock.edit") ? `<button class="btn" data-mov="entrada">${icon("download")} Entrada</button><button class="btn" data-mov="saida">Saída avulsa</button><button class="btn primary" id="new">${icon("plus")} Novo produto</button>` : ""}</div>
    </div>
    <div class="tabs">${[["produtos", "Produtos"], ["movimentos", "Movimentações"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  const reload = () => render(el, _params, ctx);
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; view.page = 1; reload(); }));
  el.querySelectorAll("[data-mov]").forEach((b) => b.addEventListener("click", () => movement(null, b.dataset.mov, reload)));
  el.querySelector("#new")?.addEventListener("click", () => editProduct(null, reload));
  const body = el.querySelector("#body");
  if (view.tab === "movimentos") return movements(body, ctx);
  return products(body, ctx, reload);
}

async function products(body, ctx, reload) {
  const rows = await api.get("/api/products", { q: view.q });
  if (!ctx.isCurrent()) return;
  const below = rows.filter((p) => p.below_minimum);
  const shown = view.below ? below : rows;
  body.innerHTML = `
    <div class="kpis">
      ${kpi({ label: "Itens cadastrados", value: rows.length })}
      ${kpi({ label: "Valor em estoque", value: fmt.moneyShort(rows.reduce((a, p) => a + p.total_value, 0)) })}
      ${kpi({ label: "Abaixo do mínimo", value: below.length, dot: "var(--critical)", foot: below.filter((p) => p.quantity <= 0).length + " sem saldo" })}
    </div>
    <div class="filters">
      <input type="search" id="q" placeholder="Buscar código, nome ou categoria…" value="${esc(view.q)}">
      <label class="small" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="below" ${view.below ? "checked" : ""}> Somente abaixo do mínimo</label>
    </div>
    <div class="card"><div class="card-body flush" id="t"></div></div>`;
  let t;
  body.querySelector("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { view.q = e.target.value; products(body, ctx, reload).then(() => { const q = body.querySelector("#q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }); }, 300); });
  body.querySelector("#below").addEventListener("change", (e) => { view.below = e.target.checked; products(body, ctx, reload); });
  const box = body.querySelector("#t");
  box.innerHTML = table([
    { label: "Produto", cls: "title-cell", render: (p) => `<b>${esc(p.name)}</b><div class="sub-cell">${esc(p.code)} · ${esc(p.category || "")} · ${esc(p.storage_location || "")}</div>` },
    { label: "Saldo", render: (p) => `<b>${fmt.num(p.quantity, p.quantity % 1 ? 2 : 0)}</b> ${esc(p.unit)}`, num: true },
    { label: "Mínimo", render: (p) => fmt.num(p.min_stock), num: true },
    { label: "Situação", render: (p) => (p.quantity <= 0 ? '<span class="badge b-critical">Sem saldo</span>' : p.below_minimum ? '<span class="badge b-warning">Repor</span>' : '<span class="badge b-good">OK</span>') },
    { label: "Custo médio", render: (p) => fmt.money(p.unit_cost), num: true },
    { label: "Valor total", render: (p) => fmt.money(p.total_value), num: true },
    { label: "Fornecedor", render: (p) => esc(p.supplier || "—") },
    ...(can("stock.edit") ? [{ label: "", render: (p) => `<span class="actions" style="flex-wrap:nowrap"><button class="btn sm" data-in="${p.id}">Entrada</button><button class="btn sm ghost" data-adj="${p.id}">Ajuste</button></span>` }] : []),
  ], shown, { onRow: can("stock.edit"), empty: "Nenhum produto encontrado" });
  if (can("stock.edit")) {
    bindRows(box, shown, (p) => editProduct(p, reload));
    box.querySelectorAll("[data-in]").forEach((b) => b.addEventListener("click", () => movement(rows.find((p) => p.id === Number(b.dataset.in)), "entrada", reload)));
    box.querySelectorAll("[data-adj]").forEach((b) => b.addEventListener("click", () => movement(rows.find((p) => p.id === Number(b.dataset.adj)), "ajuste", reload)));
  }
}

async function movements(body, ctx) {
  const data = await api.get("/api/stock/movements", { kind: view.kind, page: view.page, per_page: 30 });
  if (!ctx.isCurrent()) return;
  body.innerHTML = `
    <div class="filters"><div class="seg">${[["", "Todas"], ["entrada", "Entradas"], ["saida", "Saídas"], ["ajuste", "Ajustes"]]
      .map(([k, l]) => `<button type="button" data-k="${k}" class="${view.kind === k ? "on" : ""}">${l}</button>`).join("")}</div></div>
    <div class="card"><div class="card-body flush">${table([
      { label: "Data", render: (m) => fmt.datetime(m.created_at), cls: "nowrap" },
      { label: "Tipo", render: (m) => `<span class="badge ${KIND[m.kind][0]}">${KIND[m.kind][1]}</span>` },
      { label: "Produto", cls: "title-cell", render: (m) => `<b>${esc(m.product)}</b><div class="sub-cell">${esc(m.product_code)}</div>` },
      { label: "Qtd.", render: (m) => `${fmt.num(m.quantity, m.quantity % 1 ? 2 : 0)} ${esc(m.unit || "")}`, num: true },
      { label: "Valor", render: (m) => fmt.money(Math.abs(m.total)), num: true },
      { label: "Origem / destino", render: (m) => (m.ticket_id ? `<a href="#/chamados/${m.ticket_id}">${esc(m.ticket_code)}</a>` : esc(m.supplier || m.document || "—")) },
      { label: "Usuário", render: (m) => esc(m.user || "—") },
      { label: "Obs.", render: (m) => `<span class="small">${esc(m.note || "")}</span>` },
    ], data.items)}
    <div class="pager"><span>${data.total} movimentação(ões)</span><span class="actions">
      <button class="btn sm" id="prev" ${data.page <= 1 ? "disabled" : ""}>Anterior</button><span>Página ${data.page} de ${Math.max(1, data.pages)}</span>
      <button class="btn sm" id="next" ${data.page >= data.pages ? "disabled" : ""}>Próxima</button></span></div></div></div>`;
  body.querySelectorAll("[data-k]").forEach((b) => b.addEventListener("click", () => { view.kind = b.dataset.k; view.page = 1; movements(body, ctx); }));
  body.querySelector("#prev")?.addEventListener("click", () => { view.page--; movements(body, ctx); });
  body.querySelector("#next")?.addEventListener("click", () => { view.page++; movements(body, ctx); });
}

function movement(product, kind, done) {
  const lk = state.lookups;
  const titles = { entrada: "Entrada de material (compra/recebimento)", saida: "Saída avulsa (requisição de setor)", ajuste: "Ajuste de inventário" };
  modal({
    title: titles[kind],
    body: `<div class="form-grid">${formFields([
      { name: "product_id", label: "Produto", type: "select", required: true, full: true, options: options(lk.products, product?.id, { empty: "Selecione…", label: (p) => `${p.code} — ${p.name} (saldo ${fmt.num(p.quantity)} ${p.unit})` }) },
      { name: "quantity", label: kind === "ajuste" ? "Novo saldo contado" : "Quantidade", type: "number", step: "0.01", min: 0, required: true },
      ...(kind === "entrada" ? [
        { name: "unit_cost", label: "Custo unitário (R$)", type: "number", step: "0.01", min: 0, value: product?.unit_cost },
        { name: "supplier_id", label: "Fornecedor", type: "select", options: options(lk.suppliers, product?.supplier_id, { empty: "—" }) },
        { name: "document", label: "Nota fiscal / documento" },
      ] : []),
      ...(kind === "saida" ? [{ name: "sector_id", label: "Setor requisitante (lança custo)", type: "select", options: options(lk.sectors, "", { empty: "—" }) }] : []),
      { name: "note", label: "Observação", full: true },
    ])}</div>`,
    onSubmit: async (_f, data) => {
      await api.post("/api/stock/movements", { ...data, kind });
      toast("Movimentação registrada", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}

function editProduct(p, done) {
  const lk = state.lookups;
  p = p || { unit: "un", min_stock: 0 };
  modal({
    title: p.id ? `Editar ${p.code}` : "Novo produto", wide: true,
    body: `<div class="form-grid">${formFields([
      { name: "code", label: "Código", required: true }, { name: "name", label: "Nome", required: true },
      { name: "category", label: "Categoria" }, { name: "unit", label: "Unidade" },
      { name: "min_stock", label: "Estoque mínimo", type: "number", step: "0.01", min: 0 },
      { name: "unit_cost", label: "Custo unitário (R$)", type: "number", step: "0.01", min: 0 },
      ...(p.id ? [] : [{ name: "quantity", label: "Saldo inicial", type: "number", step: "0.01", min: 0 }]),
      { name: "storage_location", label: "Localização no almoxarifado" },
      { name: "supplier_id", label: "Fornecedor", type: "select", options: options(lk.suppliers, p.supplier_id, { empty: "—" }) },
    ], p)}</div>`,
    onSubmit: async (_f, data) => {
      if (p.id) await api.put(`/api/products/${p.id}`, data); else await api.post("/api/products", data);
      toast("Produto salvo", "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      done();
    },
  });
}
