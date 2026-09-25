import { api } from "../api.js";
import { destroyCharts, sensorChart } from "../charts.js";
import { can, esc, fmt, formFields, icon, levelBadge, loading, modal, options, state, table, toast } from "../ui.js";

const KIND_ICON = { energia: "zap", agua: "droplet", gases: "wind", temperatura: "thermo", umidade: "droplet", vibracao: "activity", pressao: "wind" };
const view = { tab: "sensores", sensor: null, hours: 24, kind: "" };

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Monitoramento e manutenção preditiva</h1><div class="sub">Sensores de energia, água, gases medicinais e condição de equipamentos · base para IoT e Machine Learning</div></div>
      <div class="actions">${can("iot.edit") ? `<button class="btn" id="new">${icon("plus")} Novo sensor</button>` : ""}</div>
    </div>
    <div class="tabs">${[["sensores", "Sensores / IoT"], ["preditiva", "Risco preditivo"], ["integracao", "Integração"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; render(el, _params, ctx); }));
  el.querySelector("#new")?.addEventListener("click", () => editSensor(() => render(el, _params, ctx)));
  const body = el.querySelector("#body");
  if (view.tab === "sensores") return sensors(body, ctx);
  if (view.tab === "preditiva") return predictive(body, ctx);
  return integration(body);
}

async function sensors(body, ctx) {
  const list = await api.get("/api/iot/sensors");
  if (!ctx.isCurrent()) return;
  const kinds = state.lookups.sensor_kinds;
  const shown = list.filter((s) => !view.kind || s.kind === view.kind);
  if (!view.sensor || !list.some((s) => s.id === view.sensor)) view.sensor = (list.find((s) => s.state === "alerta") || list[0] || {}).id;
  const alerts = list.filter((s) => s.state === "alerta");
  body.innerHTML = `
    ${alerts.length ? `<div class="notice warn" style="margin-bottom:14px">${icon("alert")} <b>${alerts.length} sensor(es) fora da faixa operacional:</b> ${alerts.map((s) => esc(s.name)).join(", ")}. Avalie abrir um chamado preditivo.</div>` : ""}
    <div class="filters"><div class="seg">${[["", "Todos"], ...Object.entries(kinds).filter(([k]) => list.some((s) => s.kind === k))]
      .map(([k, l]) => `<button type="button" data-kind="${k}" class="${view.kind === k ? "on" : ""}">${esc(l)}</button>`).join("")}</div></div>
    <div class="sensor-grid" style="margin-bottom:16px">${shown.map((s) => `
      <div class="card sensor ${s.id === view.sensor ? "sel" : ""}" data-id="${s.id}" tabindex="0" role="button" aria-label="${esc(s.name)}"><div class="card-body" style="padding:12px 14px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="small muted">${icon(KIND_ICON[s.kind] || "cpu")} ${esc(s.kind_label)}</span>
          ${levelBadge(s.state, s.state === "alerta" ? "Alerta" : s.state === "normal" ? "Normal" : "Sem dados")}</div>
        <div style="font-weight:600;margin:6px 0 2px">${esc(s.name)}</div>
        <div class="val">${fmt.num(s.last_value, Math.abs(s.last_value) < 10 ? 2 : 1)} <small>${esc(s.unit || "")}</small></div>
        <div class="small muted">Faixa ${fmt.num(s.min_value, 1)} a ${fmt.num(s.max_value, 1)} · ${esc(s.code)} · ${esc(s.protocol)}</div>
      </div></div>`).join("")}</div>
    <div class="card"><div class="card-head"><h3 id="s-title">Leituras</h3>
      <div class="seg">${[[24, "24 h"], [72, "3 dias"], [168, "7 dias"]].map(([h, l]) => `<button type="button" data-h="${h}" class="${view.hours === h ? "on" : ""}">${l}</button>`).join("")}</div></div>
      <div class="card-body"><div class="chart-box tall"><canvas id="s-chart"></canvas></div><div id="s-meta" class="small muted" style="margin-top:8px"></div></div></div>`;
  body.querySelectorAll("[data-kind]").forEach((b) => b.addEventListener("click", () => { view.kind = b.dataset.kind; sensors(body, ctx); }));
  body.querySelectorAll(".sensor").forEach((c) => {
    const pick = () => { view.sensor = Number(c.dataset.id); sensors(body, ctx); };
    c.addEventListener("click", pick);
    c.addEventListener("keydown", (e) => { if (e.key === "Enter") pick(); });
  });
  body.querySelectorAll("[data-h]").forEach((b) => b.addEventListener("click", () => { view.hours = Number(b.dataset.h); sensors(body, ctx); }));
  if (!view.sensor) return;
  const data = await api.get(`/api/iot/sensors/${view.sensor}/readings`, { hours: view.hours });
  if (!ctx.isCurrent()) return;
  const s = data.sensor;
  body.querySelector("#s-title").textContent = `${s.name} (${s.unit || ""})`;
  destroyCharts();
  sensorChart(body.querySelector("#s-chart"), { points: data.readings, min: s.min_value, max: s.max_value, unit: s.unit });
  const vals = data.readings.map((r) => r.value);
  body.querySelector("#s-meta").innerHTML = vals.length
    ? `Mín. ${fmt.num(Math.min(...vals), 2)} · Média ${fmt.num(vals.reduce((a, b) => a + b, 0) / vals.length, 2)} · Máx. ${fmt.num(Math.max(...vals), 2)} · ${vals.length} leituras · Ativo: ${esc(s.asset || s.sector || "—")}`
    : "Sem leituras no período.";
}

async function predictive(body, ctx) {
  const data = await api.get("/api/intelligence/predictive", { limit: 40 });
  if (!ctx.isCurrent()) return;
  body.innerHTML = `
    <div class="notice info" style="margin-bottom:14px">${icon("cpu")} Modelo atual: <b>${esc(data.model)}</b> (regras ponderadas). A estrutura está pronta para um modelo de Machine Learning treinado com o dataset
      <a href="/api/intelligence/export/ml_features.csv">ml_features.csv</a> — variáveis: ${data.features.map((f) => `<code>${f}</code>`).join(" ")}.</div>
    <div class="card"><div class="card-head"><h3>Ranking de risco de falha por ativo</h3><span class="hint">Pontuação 0–100</span></div>
      <div class="card-body flush" id="risk"></div></div>`;
  body.querySelector("#risk").innerHTML = table([
    { label: "Ativo", cls: "title-cell", render: (r) => `<a href="#/ativos/${r.asset_id}"><b>${esc(r.tag)}</b></a> · ${esc(r.name)}<div class="sub-cell">${esc(r.sector || "")} · criticidade ${esc(r.criticality)}</div>` },
    { label: "Risco", render: (r) => `<div style="display:flex;align-items:center;gap:8px;min-width:130px"><div class="meter" style="flex:1"><div style="width:${r.score}%;background:${r.level === "Alto" ? "var(--status-critical)" : r.level === "Médio" ? "var(--status-warning)" : "var(--status-good)"}"></div></div><b>${fmt.num(r.score, 0)}</b></div>` },
    { label: "Nível", render: (r) => levelBadge(r.level) },
    { label: "Falhas 12m", render: (r) => r.features.failures_365d, num: true },
    { label: "MTTR", render: (r) => fmt.hours(r.features.mttr_hours), num: true },
    { label: "Vida útil usada", render: (r) => fmt.pct(Math.round(r.features.age_ratio * 100)), num: true },
    { label: "Alertas 7d", render: (r) => r.features.sensor_alerts_7d, num: true },
    { label: "Recomendação", render: (r) => `<span class="small">${esc(r.recommendation)}</span>` },
  ], data.assets);
}

function integration(body) {
  const origin = location.origin;
  body.innerHTML = `
    <div class="grid grid-2">
      <div class="card"><div class="card-head"><h3>Ingestão de leituras (gateways IoT)</h3></div><div class="card-body stack" style="gap:10px">
        <p class="small">Medidores de energia, hidrômetros, sensores de pressão de gases, temperatura e vibração podem enviar leituras via HTTP. Conectores MQTT, Modbus TCP e BACnet podem ser acoplados reutilizando o mesmo serviço de ingestão.</p>
        <pre class="notice mono" style="white-space:pre-wrap;overflow-x:auto;margin:0">curl -X POST ${esc(origin)}/api/iot/readings \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: &lt;chave do gateway&gt;" \\
  -d '{"readings":[{"sensor":"GS-O2-01","value":4.02}]}'</pre>
        <p class="small muted">A chave é definida pela variável de ambiente <code>IOT_API_KEY</code>. Leituras fora da faixa geram alertas automáticos e alimentam o risco preditivo.</p>
      </div></div>
      <div class="card"><div class="card-head"><h3>Roteiro de evolução</h3></div><div class="card-body">
        <ul class="timeline">
          <li><div class="t-head">1. Telemetria de utilidades</div><div class="t-note">Energia (QGBT, gerador, nobreaks), água (reservatórios, vazão, osmose) e gases medicinais (O2, ar, vácuo).</div></li>
          <li><div class="t-head">2. Condição de equipamentos</div><div class="t-note">Vibração de chillers e bombas, temperatura de câmaras frias e rede de frio.</div></li>
          <li><div class="t-head">3. Abertura automática de chamados</div><div class="t-note">Regras que geram OS preditivas quando o sensor sai da faixa.</div></li>
          <li><div class="t-head">4. Machine Learning</div><div class="t-note">Treino com histórico de falhas + telemetria (dataset exportável) e substituição do modelo baseline.</div></li>
        </ul></div></div>
    </div>`;
}

function editSensor(done) {
  const lk = state.lookups;
  modal({
    title: "Novo sensor", wide: true,
    body: `<div class="form-grid">${formFields([
      { name: "code", label: "Código", required: true, placeholder: "Ex.: EN-QD-02" },
      { name: "name", label: "Nome", required: true },
      { name: "kind", label: "Tipo", type: "select", required: true, options: options(Object.entries(lk.sensor_kinds).map(([id, name]) => ({ id, name })), "energia") },
      { name: "unit", label: "Unidade", placeholder: "kW, bar, °C, m³/h…" },
      { name: "asset_id", label: "Ativo", type: "select", options: options(lk.assets, "", { empty: "—", label: (a) => `${a.tag} — ${a.name}` }) },
      { name: "sector_id", label: "Setor", type: "select", options: options(lk.sectors, "", { empty: "—" }) },
      { name: "min_value", label: "Limite mínimo", type: "number", step: "any" },
      { name: "max_value", label: "Limite máximo", type: "number", step: "any" },
      { name: "protocol", label: "Protocolo", type: "select", options: options(["MQTT", "Modbus TCP", "HTTP", "BACnet"], "MQTT") },
    ])}</div>`,
    onSubmit: async (_f, data) => { await api.post("/api/iot/sensors", data); toast("Sensor cadastrado", "ok"); done(); },
  });
}
