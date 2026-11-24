import { api } from "../api.js";
import { barChart, lineChart, seriesColor } from "../charts.js";
import {
  barList, bindKpiLinks, bindRows, esc, fmt, kpi, loading, options, prioBadge, sitBadge, slaBadge, state,
  statusBadge, table,
} from "../ui.js";

const filters = { days: 180, sector_id: "", team_id: "", maintenance_type: "" };

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite";
}

export async function render(el, _params, ctx) {
  const lk = state.lookups;
  el.innerHTML = `
    <section class="hero">
      <div class="hero-top">
        <span class="eyebrow">Central de manutenção</span>
        <span class="eyebrow">${new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" })}</span>
      </div>
      <h1>${greeting()}, <b>${esc(state.user.name.split(" ")[0])}</b></h1>
      <div class="hero-meta" id="hero-meta"></div>
    </section>
    <div class="filters" role="group" aria-label="Filtros do dashboard">
      <div class="seg" id="f-days">${[[30, "30 dias"], [90, "90 dias"], [180, "6 meses"], [365, "12 meses"]]
        .map(([d, l]) => `<button type="button" data-days="${d}" class="${filters.days == d ? "on" : ""}">${l}</button>`).join("")}</div>
      <select id="f-sector" aria-label="Setor">${options(lk.sectors, filters.sector_id, { empty: "Todos os setores" })}</select>
      <select id="f-team" aria-label="Equipe">${options(lk.teams, filters.team_id, { empty: "Todas as equipes" })}</select>
      <select id="f-type" aria-label="Tipo de manutenção">${options(lk.maintenance_types, filters.maintenance_type, { empty: "Todos os tipos" })}</select>
    </div>
    <div id="dash">${loading()}</div>`;

  el.querySelectorAll("#f-days button").forEach((b) => b.addEventListener("click", () => { filters.days = b.dataset.days; render(el, _params, ctx); }));
  const bind = (id, key) => el.querySelector(id).addEventListener("change", (e) => { filters[key] = e.target.value; render(el, _params, ctx); });
  bind("#f-sector", "sector_id"); bind("#f-team", "team_id"); bind("#f-type", "maintenance_type");

  const d = await api.get("/api/dashboard", filters);
  if (!ctx.isCurrent()) return;
  const k = d.kpis;
  const c = d.charts;
  const box = el.querySelector("#dash");
  el.querySelector("#hero-meta").insertAdjacentHTML("beforeend", `
    <div>Chamados ativos<b>${fmt.num(k.open + k.in_progress)}</b></div>
    <div>Alertas de sensores<b>${fmt.num(k.sensors_alert)}</b></div>`);
  box.innerHTML = `
    <div class="kpis k4">
      ${kpi({ label: "Chamados abertos", value: fmt.num(k.open), href: "#/chamados?status=aberto,recebido", dot: "var(--info)" })}
      ${kpi({ label: "Em andamento", value: fmt.num(k.in_progress), foot: `${k.waiting} aguardando`, href: "#/chamados?status=aceito,em_execucao,aguardando", dot: "var(--warning)" })}
      ${kpi({ label: "Finalizados", value: fmt.num(k.finished), foot: `de ${fmt.num(k.total)} no período`, href: "#/chamados?status=finalizado,encerrado", dot: "var(--good)" })}
      ${kpi({ label: "SLA cumprido", value: fmt.pct(k.sla_compliance), foot: `${k.sla_violated_open} violados · ${k.sla_at_risk} em risco`, href: "#/chamados?sla=violado" })}
      ${kpi({ label: "Tempo médio", value: fmt.hours(k.avg_resolution_hours), foot: `Resposta: ${fmt.hours(k.avg_response_hours)}` })}
      ${kpi({ label: "Custo total", value: fmt.moneyShort(k.total_cost), foot: `${fmt.money(k.avg_cost_per_ticket)} por chamado`, href: "#/custos" })}
      ${kpi({ label: "Disponibilidade", value: fmt.pct(k.availability), foot: `${k.assets_down} de ${k.assets_total} parados`, href: "#/ativos" })}
      ${kpi({ label: "Preventivas", value: fmt.pct(d.preventive.compliance), foot: `${d.preventive.overdue} atrasadas · ${d.preventive.next_7_days} em 7 dias`, href: "#/preventivas" })}
    </div>

    <div class="grid grid-3">
      <div class="card span-2"><div class="card-head"><h3>Abertos × finalizados</h3></div>
        <div class="card-body"><div class="chart-box"><canvas id="ch-monthly" aria-label="Chamados abertos e finalizados por mês"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>SLA cumprido</h3></div>
        <div class="card-body"><div class="chart-box"><canvas id="ch-sla"></canvas></div></div></div>

      <div class="card"><div class="card-head"><h3>Por tipo</h3></div>
        <div class="card-body"><div class="chart-box"><canvas id="ch-type"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Por setor</h3><span class="hint">Top ${c.by_sector.length}</span></div>
        <div class="card-body"><div class="chart-box"><canvas id="ch-sector"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Status dos ativos</h3><a class="hint" href="#/ativos">Inventário</a></div>
        <div class="card-body">${barList(c.assets_by_status.filter((s) => s.value), { format: (v) => fmt.num(v) })}
          <p class="muted small" style="margin-top:12px">${k.sensors_alert ? `<span class="badge b-critical">${k.sensors_alert} sensor(es) em alerta</span>` : '<span class="badge b-good">Sensores dentro da faixa</span>'}</p></div></div>

      <div class="card span-2"><div class="card-head"><h3>Custos por mês</h3><a class="hint" href="#/custos">Ver custos</a></div>
        <div class="card-body"><div class="chart-box"><canvas id="ch-costs"></canvas></div></div></div>
      <div class="card"><div class="card-head"><h3>Custos por categoria</h3></div>
        <div class="card-body">${barList(c.costs_by_category.map((x, i) => ({ ...x, color: seriesColor(i) })), { format: fmt.moneyShort })}</div></div>

      <div class="card span-2"><div class="card-head"><h3>Preventivas atrasadas e próximas</h3><a class="hint" href="#/preventivas">Calendário</a></div>
        <div class="card-body flush" id="prev"></div></div>
      <div class="card"><div class="card-head"><h3>Estoque abaixo do mínimo</h3><a class="hint" href="#/estoque">Estoque</a></div>
        <div class="card-body flush" id="stock"></div></div>

      <div class="card span-3"><div class="card-head"><h3>Chamados ativos recentes</h3><a class="hint" href="#/chamados">Todos</a></div>
        <div class="card-body flush" id="recent"></div></div>
    </div>`;
  bindKpiLinks(box);

  lineChart(box.querySelector("#ch-monthly"), {
    labels: c.monthly.labels,
    datasets: [{ label: "Abertos", data: c.monthly.opened }, { label: "Finalizados", data: c.monthly.finished, colorIndex: 2 }],
  });
  barChart(box.querySelector("#ch-type"), { labels: c.by_type.map((x) => x.label), datasets: [{ label: "Chamados", data: c.by_type.map((x) => x.value) }], horizontal: true });
  barChart(box.querySelector("#ch-sector"), { labels: c.by_sector.map((x) => x.label), datasets: [{ label: "Chamados", data: c.by_sector.map((x) => x.value) }], horizontal: true });
  lineChart(box.querySelector("#ch-sla"), { labels: c.monthly.labels, datasets: [{ label: "SLA cumprido", data: c.monthly.sla }], pct: true, max: 100 });
  barChart(box.querySelector("#ch-costs"), {
    labels: c.costs_monthly.labels, stacked: true, money: true,
    datasets: c.costs_monthly.series.map((s, i) => ({ label: s.label, data: s.data, colorIndex: i })),
  });

  const prevRows = d.preventive.upcoming;
  box.querySelector("#prev").innerHTML = table([
    { label: "Plano", render: (r) => `<b>${esc(r.name)}</b><div class="sub-cell">${esc(r.asset || "")}</div>`, cls: "title-cell" },
    { label: "Equipe", key: "team" },
    { label: "Vencimento", render: (r) => fmt.date(r.next_due), cls: "nowrap" },
    { label: "Situação", render: (r) => sitBadge(r.situation) },
  ], prevRows, { empty: "Nenhuma preventiva atrasada ou próxima", onRow: true });
  bindRows(box.querySelector("#prev"), prevRows, () => { location.hash = "#/preventivas"; });

  box.querySelector("#stock").innerHTML = table([
    { label: "Produto", render: (r) => `<b>${esc(r.name)}</b><div class="sub-cell">${esc(r.code)}</div>`, cls: "title-cell" },
    { label: "Saldo", render: (r) => `${fmt.num(r.quantity)} ${esc(r.unit)}`, num: true },
    { label: "Mínimo", render: (r) => fmt.num(r.min_stock), num: true },
  ], d.stock.below_list, { empty: "Todos os itens acima do mínimo" });

  const recent = d.recent;
  box.querySelector("#recent").innerHTML = table([
    { label: "Chamado", render: (r) => `<b>${esc(r.code)}</b> · ${esc(r.title)}<div class="sub-cell">${esc(r.sector || "")} · ${esc(r.team)}</div>`, cls: "title-cell" },
    { label: "Tipo", key: "maintenance_type" },
    { label: "Prioridade", render: (r) => prioBadge(r.priority) },
    { label: "Status", render: (r) => statusBadge(r.status, r.status_label) },
    { label: "SLA", render: (r) => slaBadge(r.sla_status) },
    { label: "Aberto", render: (r) => fmt.rel(r.created_at), cls: "nowrap" },
  ], recent, { onRow: true, empty: "Nenhum chamado ativo" });
  bindRows(box.querySelector("#recent"), recent, (r) => { location.hash = `#/chamados/${r.id}`; });
}
