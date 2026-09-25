// Gráficos (Chart.js) — cores lidas dos tokens CSS (paleta categórica validada, ordem fixa)
import { fmt } from "./ui.js";

const charts = new Set();
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export const seriesColor = (i) => css(`--series-${Math.min(i, 7) + 1}`);

export function destroyCharts() {
  charts.forEach((c) => c.destroy());
  charts.clear();
}

function base({ money = false, pct = false, legend = false, horizontal = false, stacked = false, max } = {}) {
  const muted = css("--chart-muted");
  const grid = css("--chart-grid");
  const axis = css("--chart-axis");
  const f = (v) => (money ? fmt.moneyShort(v) : pct ? `${v}%` : fmt.num(v));
  const valueAxis = {
    beginAtZero: true, stacked, max,
    grid: { color: grid, drawTicks: false }, border: { display: false },
    ticks: { color: muted, padding: 6, callback: f, maxTicksLimit: 6, precision: money ? undefined : 0 },
  };
  const catAxis = {
    stacked, grid: { display: false }, border: { color: axis },
    ticks: { color: muted, padding: 4, autoSkip: true, maxRotation: 0,
      callback(v) { const l = this.getLabelForValue(v); const n = horizontal ? 20 : 14; return l && l.length > n ? l.slice(0, n - 1) + "…" : l; } },
  };
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 250 },
    interaction: { mode: "index", intersect: false, axis: horizontal ? "y" : "x" },
    indexAxis: horizontal ? "y" : "x",
    plugins: {
      legend: { display: legend, position: "top", align: "start",
        labels: { color: css("--text-2"), usePointStyle: true, pointStyle: "rectRounded", boxWidth: 10, boxHeight: 10, padding: 14, font: { size: 12 } } },
      tooltip: {
        backgroundColor: css("--surface"), titleColor: css("--text"), bodyColor: css("--text-2"),
        borderColor: css("--border-strong"), borderWidth: 1, padding: 10, boxPadding: 4, usePointStyle: true,
        callbacks: { label: (ctx) => ` ${ctx.dataset.label ? ctx.dataset.label + ": " : ""}${ctx.parsed[horizontal ? "x" : "y"] === null ? "—" : money ? fmt.money(ctx.parsed[horizontal ? "x" : "y"]) : pct ? fmt.pct(ctx.parsed[horizontal ? "x" : "y"]) : fmt.num(ctx.parsed[horizontal ? "x" : "y"])}` },
      },
    },
    scales: horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
  };
}

function mount(canvas, config) {
  if (!canvas || !window.Chart) return null;
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
  const chart = new Chart(canvas, config);
  charts.add(chart);
  return chart;
}

/** Barras. datasets: [{label, data, colorIndex}] */
export function barChart(canvas, { labels, datasets, horizontal = false, stacked = false, money = false, pct = false, colors }) {
  const surface = css("--chart-surface");
  return mount(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: datasets.map((d, i) => ({
        label: d.label,
        data: d.data,
        backgroundColor: colors || seriesColor(d.colorIndex ?? i),
        borderRadius: stacked ? 0 : 4,
        borderSkipped: "start",
        borderColor: surface,
        borderWidth: stacked ? { top: 2 } : 0,
        maxBarThickness: horizontal ? 18 : 34,
        categoryPercentage: 0.72,
        barPercentage: 0.9,
      })),
    },
    options: base({ money, pct, legend: datasets.length > 1, horizontal, stacked }),
  });
}

/** Linhas (tendência temporal). */
export function lineChart(canvas, { labels, datasets, money = false, pct = false, max }) {
  const surface = css("--chart-surface");
  return mount(canvas, {
    type: "line",
    data: {
      labels,
      datasets: datasets.map((d, i) => {
        const c = seriesColor(d.colorIndex ?? i);
        return {
          label: d.label, data: d.data, borderColor: c, backgroundColor: c, borderWidth: 2, cubicInterpolationMode: "monotone",
          pointRadius: labels.length > 20 ? 0 : 3, pointHoverRadius: 5, pointBorderColor: surface, pointBorderWidth: 2,
          spanGaps: true, fill: false,
        };
      }),
    },
    options: base({ money, pct, legend: datasets.length > 1, max }),
  });
}

/** Série temporal de sensor com faixa operacional (min/max) como linhas de referência. */
export function sensorChart(canvas, { points, min, max, unit }) {
  const labels = points.map((p) => new Date(p.recorded_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }));
  const c = seriesColor(0);
  const crit = css("--status-critical");
  const ref = (v, label) => ({ label, data: labels.map(() => v), borderColor: crit, borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 0, fill: false });
  const datasets = [{ label: `Leitura (${unit || ""})`, data: points.map((p) => p.value), borderColor: c, backgroundColor: c, borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, cubicInterpolationMode: "monotone" }];
  if (max !== null && max !== undefined) datasets.push(ref(max, "Limite máximo"));
  if (min !== null && min !== undefined) datasets.push(ref(min, "Limite mínimo"));
  const opts = base({ legend: true });
  opts.scales.y.beginAtZero = false;
  opts.scales.y.ticks.callback = (v) => fmt.num(v, Math.abs(v) < 10 ? 1 : 0);
  opts.scales.x.ticks.maxTicksLimit = 8;
  opts.plugins.tooltip.callbacks.label = (ctx) => ` ${ctx.dataset.label}: ${fmt.num(ctx.parsed.y, 2)}`;
  return mount(canvas, { type: "line", data: { labels, datasets }, options: opts });
}
