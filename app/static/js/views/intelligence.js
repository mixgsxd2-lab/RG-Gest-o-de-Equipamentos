import { api } from "../api.js";
import { barChart } from "../charts.js";
import { esc, fmt, icon, kpi, levelBadge, loading, table } from "../ui.js";

const view = { tab: "falhas", days: 365 };
const DATASETS = {
  chamados: "Chamados completos (tempos, custos, SLA, responsáveis)",
  ativos: "Inventário com depreciação calculada",
  custos: "Livro de custos (materiais, mão de obra, terceiros, contratos, investimentos)",
  movimentos_estoque: "Entradas, saídas e ajustes de estoque",
  apontamentos: "Apontamentos de horas por técnico",
  ml_features: "Variáveis por ativo para modelos de Machine Learning",
};

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Indicadores e inteligência</h1><div class="sub">Análise de falhas, depreciação, apoio à decisão e dados para BI / Big Data / ML</div></div>
    </div>
    <div class="tabs">${[["falhas", "Análise de falhas"], ["depreciacao", "Depreciação de ativos"], ["decisao", "Apoio à decisão"], ["bi", "BI e exportação de dados"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  const reload = () => render(el, _params, ctx);
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; reload(); }));
  const body = el.querySelector("#body");
  if (view.tab === "falhas") return failures(body, ctx, reload);
  if (view.tab === "depreciacao") return depreciation(body, ctx);
  if (view.tab === "decisao") return decision(body, ctx);
  return bi(body);
}

async function failures(body, ctx, reload) {
  const d = await api.get("/api/intelligence/failures", { days: view.days });
  if (!ctx.isCurrent()) return;
  const worst = d.assets[0];
  body.innerHTML = `
    <div class="filters"><div class="seg">${[[90, "90 dias"], [180, "6 meses"], [365, "12 meses"]].map(([x, l]) => `<button type="button" data-days="${x}" class="${view.days === x ? "on" : ""}">${l}</button>`).join("")}</div></div>
    <div class="kpis">
      ${kpi({ label: "Falhas (corretivas + emergenciais)", value: fmt.num(d.total_failures) })}
      ${kpi({ label: "Ativos com falha", value: fmt.num(d.assets.length) })}
      ${kpi({ label: "Principal causa", value: `<span style="font-size:1.05rem">${esc(d.pareto_causes[0]?.label || "—")}</span>`, foot: d.pareto_causes[0] ? `${d.pareto_causes[0].value} ocorrências` : "" })}
      ${kpi({ label: "Ativo com mais falhas", value: `<span style="font-size:1.05rem">${esc(worst ? worst.tag : "—")}</span>`, foot: worst ? `${esc(worst.name)} · ${worst.failures} falhas` : "" })}
    </div>
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Pareto de causas de falha</h3><span class="hint">Barras = ocorrências · tabela com % acumulado</span></div>
        <div class="card-body"><div class="chart-box"><canvas id="c1"></canvas></div>
        <div style="margin-top:10px">${table([{ label: "Causa", key: "label" }, { label: "Ocorrências", key: "value", num: true }, { label: "% acumulado", render: (r) => fmt.pct(r.cumulative), num: true }], d.pareto_causes, { responsive: false })}</div></div></div>
      <div class="card"><div class="card-head"><h3>Falhas por categoria de ativo</h3></div>
        <div class="card-body"><div class="chart-box"><canvas id="c2"></canvas></div></div></div>
      <div class="card span-2"><div class="card-head"><h3>Confiabilidade por ativo</h3><span class="hint">MTBF = tempo médio entre falhas · MTTR = tempo médio de reparo</span></div>
        <div class="card-body flush" id="t"></div></div>
    </div>`;
  body.querySelectorAll("[data-days]").forEach((b) => b.addEventListener("click", () => { view.days = Number(b.dataset.days); reload(); }));
  barChart(body.querySelector("#c1"), { labels: d.pareto_causes.map((x) => x.label), horizontal: true, datasets: [{ label: "Ocorrências", data: d.pareto_causes.map((x) => x.value), colorIndex: 1 }] });
  barChart(body.querySelector("#c2"), { labels: d.by_category.map((x) => x.label), horizontal: true, datasets: [{ label: "Falhas", data: d.by_category.map((x) => x.value) }] });
  body.querySelector("#t").innerHTML = table([
    { label: "Ativo", cls: "title-cell", render: (a) => `<a href="#/ativos/${a.asset_id}"><b>${esc(a.tag)}</b></a> · ${esc(a.name)}<div class="sub-cell">${esc(a.category)} · ${esc(a.sector || "")}</div>` },
    { label: "Falhas", key: "failures", num: true },
    { label: "MTBF", render: (a) => fmt.hours(a.mtbf_hours), num: true },
    { label: "MTTR", render: (a) => fmt.hours(a.mttr_hours), num: true },
    { label: "Disponibilidade", render: (a) => fmt.pct(a.availability), num: true },
    { label: "Custo", render: (a) => fmt.money(a.cost), num: true },
  ], d.assets, { empty: "Nenhuma falha registrada no período" });
}

async function depreciation(body, ctx) {
  const d = await api.get("/api/intelligence/depreciation");
  if (!ctx.isCurrent()) return;
  const t = d.totals;
  body.innerHTML = `
    <div class="kpis">
      ${kpi({ label: "Valor de aquisição", value: fmt.moneyShort(t.acquisition) })}
      ${kpi({ label: "Valor contábil atual", value: fmt.moneyShort(t.book_value) })}
      ${kpi({ label: "Depreciação acumulada", value: fmt.moneyShort(t.accumulated), foot: fmt.pct(Math.round((1000 * t.accumulated) / (t.acquisition || 1)) / 10) + " do parque" })}
      ${kpi({ label: "Depreciação anual", value: fmt.moneyShort(t.annual) })}
    </div>
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Valor contábil × depreciado por categoria</h3></div>
        <div class="card-body"><div class="chart-box tall"><canvas id="c1"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Ativos no fim da vida útil</h3><span class="hint">≤ 1,5 ano restante</span></div>
        <div class="card-body flush" id="eol"></div></div>
      <div class="card span-2"><div class="card-body flush" id="t"></div></div>
    </div>`;
  barChart(body.querySelector("#c1"), {
    labels: d.by_category.map((x) => x.category), horizontal: true, stacked: true, money: true,
    datasets: [{ label: "Valor contábil", data: d.by_category.map((x) => x.book_value) }, { label: "Depreciado", data: d.by_category.map((x) => x.accumulated), colorIndex: 1 }],
  });
  body.querySelector("#eol").innerHTML = table([
    { label: "Ativo", cls: "title-cell", render: (a) => `<a href="#/ativos/${a.id}"><b>${esc(a.tag)}</b></a> · ${esc(a.name)}<div class="sub-cell">${esc(a.sector || "")}</div>` },
    { label: "Restante", render: (a) => `${fmt.num(a.depreciation.remaining_years, 1)} anos`, num: true },
    { label: "Valor contábil", render: (a) => fmt.money(a.depreciation.book_value), num: true },
  ], d.end_of_life, { empty: "Nenhum ativo próximo do fim da vida útil" });
  body.querySelector("#t").innerHTML = table([
    { label: "Categoria", key: "category", cls: "title-cell" },
    { label: "Ativos", key: "assets", num: true },
    { label: "Aquisição", render: (r) => fmt.money(r.acquisition), num: true },
    { label: "Depreciação anual", render: (r) => fmt.money(r.annual), num: true },
    { label: "Acumulada", render: (r) => fmt.money(r.accumulated), num: true },
    { label: "Valor contábil", render: (r) => fmt.money(r.book_value), num: true },
  ], d.by_category);
}

async function decision(body, ctx) {
  const [fail, dep, pred, dash] = await Promise.all([
    api.get("/api/intelligence/failures", { days: 365 }),
    api.get("/api/intelligence/depreciation"),
    api.get("/api/intelligence/predictive", { limit: 8 }),
    api.get("/api/dashboard", { days: 180 }),
  ]);
  if (!ctx.isCurrent()) return;
  // Candidatos à substituição: custo de manutenção relevante frente ao valor contábil ou fim de vida útil
  const bookByTag = {};
  dep.end_of_life.forEach((a) => { bookByTag[a.tag] = a; });
  const replace = fail.assets.map((a) => ({ ...a, eol: bookByTag[a.tag] })).filter((a) => a.eol || a.failures >= 3).slice(0, 8);
  const k = dash.kpis;
  const insights = [];
  if (k.sla_compliance < 85) insights.push(["alto", `SLA cumprido em ${fmt.pct(k.sla_compliance)} nos últimos 6 meses — abaixo da meta de 85%. Revise a distribuição de demandas e os prazos por prioridade.`]);
  else insights.push(["info", `SLA cumprido em ${fmt.pct(k.sla_compliance)} nos últimos 6 meses — dentro da meta de 85%.`]);
  if (dash.preventive.overdue) insights.push(["alto", `${dash.preventive.overdue} plano(s) preventivo(s) atrasado(s). Atrasos em preventivas elevam falhas corretivas.`]);
  if (dash.stock.below_minimum) insights.push(["medio", `${dash.stock.below_minimum} item(ns) de estoque abaixo do mínimo — risco de chamados aguardando material.`]);
  const worstSup = [...dash.suppliers].filter((s) => s.tickets).sort((a, b) => a.score - b.score)[0];
  if (worstSup) insights.push(["medio", `Menor índice de desempenho entre terceiros: ${worstSup.name} (${fmt.num(worstSup.score, 0)}/100). Avalie no próximo ciclo contratual.`]);
  if (pred.assets[0]) insights.push(["alto", `Maior risco preditivo: ${pred.assets[0].tag} — ${pred.assets[0].name} (${fmt.num(pred.assets[0].score, 0)}/100). ${pred.assets[0].recommendation}.`]);
  const SEV = { alto: "b-serious", medio: "b-warning", info: "b-info" };
  body.innerHTML = `
    <div class="grid grid-2">
      <div class="card span-2"><div class="card-head"><h3>Destaques para a gestão</h3><span class="hint">Gerado automaticamente a partir dos dados</span></div>
        <div class="card-body stack" style="gap:10px">${insights.map(([s, t]) => `<div style="display:flex;gap:10px;align-items:flex-start"><span class="badge ${SEV[s]}">${s === "alto" ? "Atenção" : s === "medio" ? "Acompanhar" : "Info"}</span><span>${esc(t)}</span></div>`).join("")}</div></div>
      <div class="card"><div class="card-head"><h3>Candidatos à substituição</h3><span class="hint">Falhas recorrentes ou fim de vida útil</span></div>
        <div class="card-body flush">${table([
          { label: "Ativo", cls: "title-cell", render: (a) => `<a href="#/ativos/${a.asset_id}"><b>${esc(a.tag)}</b></a> · ${esc(a.name)}` },
          { label: "Falhas 12m", key: "failures", num: true },
          { label: "Custo 12m", render: (a) => fmt.money(a.cost), num: true },
          { label: "Motivo", render: (a) => (a.eol ? '<span class="badge b-warning">Fim de vida útil</span>' : '<span class="badge b-serious">Falhas recorrentes</span>') },
        ], replace, { empty: "Nenhum candidato identificado" })}</div></div>
      <div class="card"><div class="card-head"><h3>Maior risco de falha (preditivo)</h3><a class="hint" href="#/monitoramento">Detalhes</a></div>
        <div class="card-body flush">${table([
          { label: "Ativo", cls: "title-cell", render: (a) => `<a href="#/ativos/${a.asset_id}"><b>${esc(a.tag)}</b></a> · ${esc(a.name)}` },
          { label: "Risco", render: (a) => `<b>${fmt.num(a.score, 0)}</b>`, num: true },
          { label: "Nível", render: (a) => levelBadge(a.level) },
        ], pred.assets)}</div></div>
    </div>`;
}

function bi(body) {
  const origin = location.origin;
  body.innerHTML = `
    <div class="notice info" style="margin-bottom:14px">${icon("chart")} Todos os dados estão disponíveis em <b>CSV</b> (Excel, Power BI, Metabase) e <b>JSON</b> (APIs, data lake / Big Data).
      O banco pode ser trocado de SQLite para PostgreSQL/SQL Server pela variável <code>DATABASE_URL</code>, permitindo conexão direta de ferramentas de BI.</div>
    <div class="card"><div class="card-body flush">${table([
      { label: "Conjunto de dados", cls: "title-cell", render: (r) => `<b>${esc(r.name)}</b><div class="sub-cell">${esc(r.desc)}</div>` },
      { label: "Endpoint", render: (r) => `<code>/api/intelligence/export/${esc(r.name)}.csv</code>` },
      { label: "Baixar", render: (r) => `<span class="actions" style="flex-wrap:nowrap"><a class="btn sm" href="/api/intelligence/export/${r.name}.csv">${icon("download")} CSV</a><a class="btn sm" href="/api/intelligence/export/${r.name}.json" target="_blank" rel="noopener">JSON</a></span>` },
    ], Object.entries(DATASETS).map(([name, desc]) => ({ name, desc })))}</div></div>
    <div class="card" style="margin-top:16px"><div class="card-head"><h3>Exemplo — Power BI / Python</h3></div><div class="card-body">
      <pre class="notice mono" style="white-space:pre-wrap;overflow-x:auto;margin:0">import pandas as pd
# autenticar via sessão ou publicar o endpoint para a rede interna do BI
df = pd.read_csv("${esc(origin)}/api/intelligence/export/chamados.csv", sep=";")
df.groupby(["team", "maintenance_type"])["total_cost"].sum()</pre></div></div>`;
}

