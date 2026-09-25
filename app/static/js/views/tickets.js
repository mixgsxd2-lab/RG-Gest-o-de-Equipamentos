import { api } from "../api.js";
import {
  bindRows, can, esc, fmt, formFields, icon, loading, modal, options, prioBadge, slaBadge, state, statusBadge,
  table, toast, toLocalInput,
} from "../ui.js";

const FAILURE_CAUSES = ["Desgaste de componente", "Desgaste natural", "Fim de vida útil", "Falha eletrônica",
  "Mau uso / dano físico", "Falta de limpeza", "Sobrecarga elétrica", "Conexão frouxa", "Vazamento",
  "Qualidade da água", "Intempéries", "Outra"];

const FLOW = [["aberto", "Aberto"], ["recebido", "Recebido"], ["aceito", "Aceito"], ["em_execucao", "Em execução"],
  ["aguardando", "Aguardando material/terceiro"], ["finalizado", "Finalizado"], ["encerrado", "Encerrado"]];

const QUICK = [
  ["", "Todos"], ["aberto,recebido", "Abertos"], ["aceito,em_execucao", "Em andamento"],
  ["aguardando", "Aguardando"], ["finalizado,encerrado", "Finalizados"], ["cancelado", "Cancelados"],
];

const listState = { status: "", q: "", team_id: "", sector_id: "", maintenance_type: "", priority: "", mine: "", sla: "", page: 1 };

export async function render(el, params, ctx) {
  if (params[0] === "novo") return renderNew(el);
  if (params[0]) return renderDetail(el, Number(params[0]), ctx);
  if (ctx.query && Object.keys(ctx.query).length) {
    Object.assign(listState, { status: "", sla: "", mine: "", page: 1 }, ctx.query);
    history.replaceState(null, "", "#/chamados");
  }
  return renderList(el, ctx);
}

// ============================================================== Lista
async function renderList(el, ctx) {
  const lk = state.lookups;
  const isOp = state.user.role === "operador";
  const mineTabs = [["requested", "Abertos por mim"]].concat(isOp ? [["assigned", "Atribuídos a mim"]] : []);
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Chamados</h1><div class="sub">${can("tickets.view_all") ? "Todos os chamados de manutenção do hospital" : "Chamados abertos por você"}</div></div>
      <div class="actions"><a class="btn primary" href="#/chamados/novo">${icon("plus")} Abrir chamado</a></div>
    </div>
    <div class="filters">
      <div class="seg" id="quick">
        ${QUICK.map(([v, l]) => `<button type="button" data-status="${v}" class="${!listState.mine && !listState.sla && listState.status === v ? "on" : ""}">${l}</button>`).join("")}
        ${can("tickets.view_all") ? mineTabs.map(([v, l]) => `<button type="button" data-mine="${v}" class="${listState.mine === v ? "on" : ""}">${l}</button>`).join("") : ""}
        ${can("tickets.view_all") ? `<button type="button" data-sla="violado" class="${listState.sla === "violado" ? "on" : ""}">SLA violado</button>` : ""}
      </div>
    </div>
    <div class="filters">
      <input type="search" id="q" placeholder="Buscar por código, título, descrição ou local…" value="${esc(listState.q)}">
      <select id="team_id" aria-label="Equipe">${options(lk.teams, listState.team_id, { empty: "Setor de manutenção" })}</select>
      <select id="sector_id" aria-label="Setor">${options(lk.sectors, listState.sector_id, { empty: "Setor do hospital" })}</select>
      <select id="maintenance_type" aria-label="Tipo">${options(lk.maintenance_types, listState.maintenance_type, { empty: "Tipo" })}</select>
      <select id="priority" aria-label="Prioridade">${options(lk.priorities, listState.priority, { empty: "Prioridade" })}</select>
    </div>
    <div class="card" id="list">${loading()}</div>`;

  const reload = () => renderList(el, ctx);
  el.querySelectorAll("#quick [data-status]").forEach((b) => b.addEventListener("click", () => { Object.assign(listState, { status: b.dataset.status, mine: "", sla: "", page: 1 }); reload(); }));
  el.querySelectorAll("#quick [data-mine]").forEach((b) => b.addEventListener("click", () => { Object.assign(listState, { mine: b.dataset.mine, status: "", sla: "", page: 1 }); reload(); }));
  el.querySelectorAll("#quick [data-sla]").forEach((b) => b.addEventListener("click", () => { Object.assign(listState, { sla: "violado", status: "", mine: "", page: 1 }); reload(); }));
  ["team_id", "sector_id", "maintenance_type", "priority"].forEach((id) => el.querySelector(`#${id}`).addEventListener("change", (e) => { listState[id] = e.target.value; listState.page = 1; reload(); }));
  let t;
  el.querySelector("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { listState.q = e.target.value; listState.page = 1; loadList(el, ctx); }, 300); });
  await loadList(el, ctx);
}

async function loadList(el, ctx) {
  const params = { ...listState, per_page: 25 };
  if (listState.sla) delete params.status;
  const data = await api.get("/api/tickets", params);
  if (!ctx.isCurrent()) return;
  const box = el.querySelector("#list");
  box.innerHTML = table([
    { label: "Chamado", cls: "title-cell", render: (r) => `<b>${esc(r.code)}</b> · ${esc(r.title)}<div class="sub-cell">${esc(r.team)} · ${esc(r.sector || "—")}${r.location ? " · " + esc(r.location) : ""}</div>` },
    { label: "Tipo", key: "maintenance_type" },
    { label: "Prioridade", render: (r) => prioBadge(r.priority) },
    { label: "Status", render: (r) => statusBadge(r.status, r.status_label) },
    { label: "SLA", render: (r) => slaBadge(r.sla_status) },
    { label: "Solicitante", render: (r) => esc(r.requester) },
    { label: "Operador", render: (r) => (r.operator ? esc(r.operator) : '<span class="muted">—</span>') },
    { label: "Aberto em", render: (r) => `<span title="${fmt.datetime(r.created_at)}">${fmt.datetime(r.created_at)}</span>`, cls: "nowrap" },
  ], data.items, { onRow: true, empty: "Nenhum chamado encontrado com os filtros atuais" }) +
    (data.pages > 1 || data.total ? `<div class="pager"><span>${data.total} chamado(s)</span>
      <span class="actions"><button class="btn sm" id="prev" ${data.page <= 1 ? "disabled" : ""}>Anterior</button>
      <span>Página ${data.page} de ${Math.max(1, data.pages)}</span>
      <button class="btn sm" id="next" ${data.page >= data.pages ? "disabled" : ""}>Próxima</button></span></div>` : "");
  bindRows(box, data.items, (r) => { location.hash = `#/chamados/${r.id}`; });
  box.querySelector("#prev")?.addEventListener("click", () => { listState.page--; loadList(el, ctx); });
  box.querySelector("#next")?.addEventListener("click", () => { listState.page++; loadList(el, ctx); });
}

// ============================================================== Novo chamado
function renderNew(el) {
  const lk = state.lookups;
  const u = state.user;
  el.innerHTML = `
    <div class="page-head">
      <div><a href="#/chamados" class="muted small">${icon("back")} Chamados</a><h1 style="margin-top:4px">Abrir chamado</h1>
      <div class="sub">Descreva o problema e escolha o setor de manutenção que deve atender</div></div>
    </div>
    <form class="card" id="new-form" novalidate>
      <div class="card-body">
        <div class="form-grid">
          ${formFields([
            { name: "title", label: "Título / resumo do problema", required: true, full: true, placeholder: "Ex.: Monitor sem leitura de SpO2 no leito 3" },
            { name: "team_id", label: "Setor de manutenção (destino)", type: "select", required: true, options: options(lk.teams, "", { empty: "Selecione…" }) },
            { name: "maintenance_type", label: "Tipo de manutenção", type: "select", required: true, options: options(lk.maintenance_types, "Corretiva") },
            { name: "priority", label: "Prioridade", type: "select", required: true, options: options(lk.priorities, "Média") },
            { name: "criticality", label: "Criticidade (impacto assistencial)", type: "select", required: true, options: options(lk.criticalities, "Média") },
            { name: "sector_id", label: "Setor do hospital (local do problema)", type: "select", options: options(lk.sectors, u.sector_id, { empty: "Selecione…" }) },
            { name: "location", label: "Local específico", placeholder: "Ex.: Leito 3, Sala 2, Banheiro do corredor" },
            { name: "asset_id", label: "Ativo / equipamento (opcional)", type: "select", full: true, options: "" },
            { name: "description", label: "Descrição detalhada", type: "textarea", required: true, full: true, placeholder: "O que está acontecendo? Desde quando? Há risco ao paciente ou à operação?" },
            { name: "files", label: "Fotos e anexos", type: "file", multiple: true, full: true, accept: "image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt", attrs: 'capture="environment"' },
          ])}
          <div class="full notice info" id="sla-info"></div>
        </div>
      </div>
      <div class="modal-foot"><a class="btn" href="#/chamados">Cancelar</a><button class="btn primary" type="submit">${icon("check")} Registrar chamado</button></div>
    </form>`;
  const form = el.querySelector("#new-form");
  const fillAssets = () => {
    const sid = form.sector_id.value;
    const list = lk.assets.filter((a) => !sid || String(a.sector_id) === sid);
    form.asset_id.innerHTML = options(list, "", { empty: list.length ? "Nenhum ativo específico" : "Nenhum ativo cadastrado neste setor", label: (a) => `${a.tag} — ${a.name}${a.location ? " (" + a.location + ")" : ""}` });
  };
  const slaInfo = () => {
    const h = form.maintenance_type.value === "Emergencial" ? lk.sla_hours.Emergencial : lk.sla_hours[form.priority.value];
    el.querySelector("#sla-info").innerHTML = `${icon("clock")} Prazo de atendimento (SLA) para este chamado: <b>${fmt.hours(h)}</b> a partir da abertura.`;
  };
  form.sector_id.addEventListener("change", fillAssets);
  form.asset_id.addEventListener("change", () => {
    const a = lk.assets.find((x) => String(x.id) === form.asset_id.value);
    if (a && !form.location.value) form.location.value = a.location || "";
  });
  form.priority.addEventListener("change", slaInfo);
  form.maintenance_type.addEventListener("change", () => {
    if (form.maintenance_type.value === "Emergencial") form.priority.value = "Urgente";
    slaInfo();
  });
  fillAssets(); slaInfo();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.checkValidity()) return form.reportValidity();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const t = await api.post("/api/tickets", new FormData(form));
      toast(`Chamado ${t.code} registrado`, "ok");
      window.dispatchEvent(new Event("rg:data-changed"));
      location.hash = `#/chamados/${t.id}`;
    } catch (err) {
      toast(err.message, "err");
      btn.disabled = false;
    }
  });
}

// ============================================================== Detalhe
async function renderDetail(el, id, ctx) {
  el.innerHTML = loading();
  const t = await api.get(`/api/tickets/${id}`);
  if (!ctx.isCurrent()) return;
  draw(el, t);
}

function flowHtml(t) {
  if (t.status === "cancelado") return `<div class="notice warn">${icon("x")} Chamado cancelado.</div>`;
  const idx = FLOW.findIndex(([s]) => s === t.status);
  const waited = t.events.some((e) => e.to_status === "aguardando");
  return `<div class="flow" aria-label="Etapas do chamado">${FLOW.map(([s, l], i) => {
    let cls = i < idx ? "done" : i === idx ? "current" : "";
    if (s === "aguardando" && i < idx && !waited) cls = "";
    return `<div class="step ${cls}"><div class="c">${cls === "done" ? "✓" : i + 1}</div>${l}</div>`;
  }).join("")}</div>`;
}

const ACTION_BTNS = {
  receive: ["Receber", "primary", "check"], assign: ["Designar técnico", "", "users"], accept: ["Aceitar chamado", "primary", "check"],
  start: ["Iniciar execução", "primary", "play"], wait: ["Aguardar material/terceiro", "", "pause"], resume: ["Retomar execução", "primary", "play"],
  finish: ["Finalizar serviço", "good", "check"], close: ["Encerrar chamado", "primary", "check"], reopen: ["Reabrir", "", "refresh"],
  update: ["Editar dados", "", "edit"], cancel: ["Cancelar", "danger", "x"],
};

function draw(el, t) {
  const acts = t.actions;
  const person = (role, name, when, extra = "") => `<div class="person"><div class="role">${role}</div><div class="name">${name ? esc(name) : '<span class="muted">Não definido</span>'}</div><div class="when">${when ? fmt.datetime(when) : "&nbsp;"}${extra}</div></div>`;
  const section = (title, text) => (text ? `<div><h3 style="margin-bottom:4px">${title}</h3><div class="text-block">${esc(text)}</div></div>` : "");
  el.innerHTML = `
    <div class="page-head">
      <div style="min-width:0">
        <a href="#/chamados" class="muted small">${icon("back")} Chamados</a>
        <h1 style="margin-top:4px">${esc(t.code)} · ${esc(t.title)}</h1>
        <div class="actions" style="margin-top:8px">${statusBadge(t.status, t.status_label)} ${prioBadge(t.priority)}
          <span class="badge b-neutral plain">${esc(t.maintenance_type)}</span> <span class="badge b-neutral plain">Criticidade ${esc(t.criticality)}</span>
          ${slaBadge(t.sla_status)} ${t.waiting_reason ? `<span class="badge b-serious">Aguardando ${esc(t.waiting_reason.toLowerCase())}</span>` : ""}</div>
      </div>
      <div class="actions">
        ${Object.entries(ACTION_BTNS).filter(([a]) => acts.includes(a)).map(([a, [l, c, ic]]) => `<button class="btn ${c}" data-action="${a}">${icon(ic)} ${l}</button>`).join("")}
      </div>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="card-body">${flowHtml(t)}</div></div>
    <div class="detail-grid">
      <div class="stack">
        <div class="card"><div class="card-body stack">
          <div class="people">
            ${person("Solicitante — abriu", t.requester, t.created_at)}
            ${person("Responsável — recebeu", t.receiver, t.received_at)}
            ${person("Operador — aceitou/executou", t.operator, t.accepted_at)}
          </div>
          <dl class="kv">
            <dt>Setor de manutenção</dt><dd>${esc(t.team)}</dd>
            <dt>Setor / local</dt><dd>${esc(t.sector || "—")}${t.location ? " · " + esc(t.location) : ""}</dd>
            <dt>Ativo</dt><dd>${t.asset_id ? `<a href="#/ativos/${t.asset_id}">${esc(t.asset)}</a>` : "—"}</dd>
            <dt>Prazo SLA</dt><dd>${fmt.datetime(t.sla_due_at)} <span class="muted">(${fmt.hours(t.sla_hours)})</span></dd>
            <dt>Início / término</dt><dd>${fmt.datetime(t.started_at)} → ${fmt.datetime(t.finished_at)}</dd>
            <dt>Tempo de atendimento</dt><dd>${fmt.hours(t.resolution_hours)} <span class="muted">· resposta ${fmt.hours(t.response_hours)}</span></dd>
            ${t.supplier ? `<dt>Terceiro</dt><dd>${esc(t.supplier)}</dd>` : ""}
            ${t.closed_at ? `<dt>Encerrado em</dt><dd>${fmt.datetime(t.closed_at)}${t.satisfaction ? ` · satisfação ${"★".repeat(t.satisfaction)}${"☆".repeat(5 - t.satisfaction)}` : ""}</dd>` : ""}
          </dl>
          ${section("Descrição", t.description)}
        </div></div>

        ${t.diagnosis || t.solution || t.observations || t.closing_notes ? `<div class="card"><div class="card-head"><h3>Execução e fechamento</h3></div><div class="card-body stack">
          ${section("Diagnóstico", t.diagnosis)}${section("O que foi feito", t.solution)}
          ${t.failure_cause ? `<div><h3 style="margin-bottom:4px">Causa da falha</h3><span class="tag">${esc(t.failure_cause)}</span></div>` : ""}
          ${section("Observações", t.observations)}${section("Informações de fechamento", t.closing_notes)}
        </div></div>` : ""}

        <div class="card"><div class="card-head"><h3>Apontamentos de horas</h3>${acts.includes("worklog") ? `<button class="btn sm" data-action="worklog">${icon("plus")} Apontar horas</button>` : ""}</div>
          <div class="card-body flush">${table([
            { label: "Técnico", render: (w) => esc(w.technician || "—") },
            { label: "Início", render: (w) => fmt.datetime(w.started_at), cls: "nowrap" },
            { label: "Término", render: (w) => fmt.datetime(w.ended_at), cls: "nowrap" },
            { label: "Horas", render: (w) => fmt.num(w.hours, 2), num: true },
            { label: "Custo", render: (w) => fmt.money(w.cost), num: true },
            { label: "Atividade", render: (w) => esc(w.description || "") },
          ], t.worklogs, { empty: "Nenhum apontamento registrado" })}</div></div>

        <div class="card"><div class="card-head"><h3>Peças e materiais utilizados</h3>${acts.includes("material") ? `<button class="btn sm" data-action="material">${icon("plus")} Lançar material</button>` : ""}</div>
          <div class="card-body flush">${table([
            { label: "Material", render: (m) => `${esc(m.name)}${m.code ? `<div class="sub-cell">${esc(m.code)}</div>` : '<div class="sub-cell">Fora do estoque</div>'}`, cls: "title-cell" },
            { label: "Qtd.", render: (m) => `${fmt.num(m.quantity, m.quantity % 1 ? 2 : 0)} ${esc(m.unit)}`, num: true },
            { label: "Custo unit.", render: (m) => fmt.money(m.unit_cost), num: true },
            { label: "Total", render: (m) => fmt.money(m.total), num: true },
          ], t.materials, { empty: "Nenhum material lançado" })}</div></div>

        <div class="card"><div class="card-head"><h3>Fotos e anexos</h3>${acts.includes("attach") ? `<button class="btn sm" data-action="attach">${icon("clip")} Anexar</button>` : ""}</div>
          <div class="card-body">${t.attachments.length ? `<div class="attachments">${t.attachments.map((a) => `
            <a class="att" href="${a.url}" target="_blank" rel="noopener" title="${esc(a.filename)}">
              ${a.is_image ? `<img src="${a.url}" alt="${esc(a.filename)}" loading="lazy">` : `<div class="ph">${icon("file")}</div>`}
              <span>${esc(a.filename)}</span><span class="muted" style="padding-top:0">${esc(a.stage)}</span></a>`).join("")}</div>` : '<div class="empty" style="padding:8px">Nenhum anexo</div>'}</div></div>
      </div>

      <div class="stack">
        <div class="card"><div class="card-head"><h3>Custos</h3></div><div class="card-body">
          <div class="cost-box">
            <div><span>Mão de obra (${fmt.num(t.labor_hours, 1)} h)</span><b>${fmt.money(t.labor_cost)}</b></div>
            <div><span>Materiais</span><b>${fmt.money(t.material_cost)}</b></div>
            <div><span>Terceiros</span><b>${fmt.money(t.third_party_cost)}</b></div>
            <div><span>Horas trabalhadas</span><b>${fmt.num(t.labor_hours, 1)} h</b></div>
            <div class="total"><span>Custo total</span><b>${fmt.money(t.total_cost)}</b></div>
          </div></div></div>
        <div class="card"><div class="card-head"><h3>Histórico completo</h3><span class="hint">${t.events.length} registro(s)</span></div>
          <div class="card-body">
            <ul class="timeline">${t.events.slice().reverse().map((e) => `<li>
              <div class="t-head">${esc(e.action)}${e.to_label && e.from_label ? ` <span class="muted small">(${esc(e.from_label)} → ${esc(e.to_label)})</span>` : ""}</div>
              <div class="t-meta">${fmt.datetime(e.created_at)} · ${esc(e.user)}</div>
              ${e.note ? `<div class="t-note">${esc(e.note)}</div>` : ""}</li>`).join("")}</ul>
            ${t.status !== "cancelado" ? `<form id="comment" class="stack" style="gap:8px;margin-top:6px">
              <textarea name="note" placeholder="Adicionar comentário ao histórico…" style="min-height:60px" required></textarea>
              <button class="btn sm" type="submit" style="align-self:flex-end">Comentar</button></form>` : ""}
          </div></div>
      </div>
    </div>`;

  el.querySelectorAll("[data-action]").forEach((b) => b.addEventListener("click", () => openAction(el, t, b.dataset.action)));
  el.querySelector("#comment")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const note = e.target.note.value.trim();
    if (!note) return;
    try { draw(el, await api.post(`/api/tickets/${t.id}/comments`, { note })); } catch (err) { toast(err.message, "err"); }
  });
}

function techOptions(t, selected) {
  const lk = state.lookups;
  const same = lk.technicians.filter((x) => x.team_id === t.team_id);
  const other = lk.technicians.filter((x) => x.team_id !== t.team_id);
  const lbl = (x) => `${x.name}${x.external ? " (terceiro)" : ""} — ${x.specialty || ""}`;
  return `<option value="">Selecione…</option><optgroup label="${esc(t.team)}">${options(same, selected, { label: lbl })}</optgroup><optgroup label="Outras equipes">${options(other, selected, { label: lbl })}</optgroup>`;
}

async function uploadFiles(t, input, stage) {
  if (!input || !input.files.length) return null;
  const fd = new FormData();
  [...input.files].forEach((f) => fd.append("files", f));
  if (stage) fd.append("stage", stage);
  return api.post(`/api/tickets/${t.id}/attachments`, fd);
}

function openAction(el, t, action) {
  const lk = state.lookups;
  const note = { name: "note", label: "Observação", type: "textarea", full: true };
  const post = async (data) => {
    const upd = await api.post(`/api/tickets/${t.id}/actions/${action}`, data);
    toast("Chamado atualizado", "ok");
    window.dispatchEvent(new Event("rg:data-changed"));
    return upd;
  };
  const simple = (title, fields, submitLabel, transform = (d) => d) => modal({
    title, submitLabel, body: `<div class="form-grid">${formFields(fields)}</div>`,
    onSubmit: async (_f, data) => draw(el, await post(transform(data))),
  });

  switch (action) {
    case "receive":
      return simple("Receber chamado", [note], "Receber");
    case "assign":
      return simple("Designar técnico / operador", [{ name: "technician_id", label: "Técnico", type: "select", required: true, full: true, options: techOptions(t, t.operator_id) }, note], "Designar");
    case "accept":
      return simple("Aceitar chamado", can("tickets.manage") && !t.operator_id
        ? [{ name: "technician_id", label: "Operador que executará", type: "select", required: true, full: true, options: techOptions(t) }, note]
        : [note], "Aceitar");
    case "start":
      return simple("Iniciar execução", [{ name: "started_at", label: "Início", type: "datetime-local", value: toLocalInput(), required: true }, note], "Iniciar");
    case "wait":
      return simple("Aguardar material ou terceiro", [
        { name: "waiting_reason", label: "Motivo", type: "select", required: true, options: options(["Material", "Terceiro"], "Material") },
        { name: "supplier_id", label: "Fornecedor / terceiro", type: "select", options: options(lk.suppliers, t.supplier_id, { empty: "—" }) },
        note], "Confirmar");
    case "resume":
      return simple("Retomar execução", [note], "Retomar");
    case "reopen":
      return simple("Reabrir chamado", [{ ...note, label: "Motivo da reabertura", required: true }], "Reabrir");
    case "cancel":
      return simple("Cancelar chamado", [{ ...note, label: "Motivo do cancelamento", required: true }], "Cancelar chamado");
    case "close":
      return simple("Encerrar chamado", [
        { name: "closing_notes", label: "Informações de fechamento", type: "textarea", full: true, placeholder: "Conferência do serviço, pendências, orientações…" },
        { name: "satisfaction", label: "Satisfação do solicitante", type: "select", options: options([["5", "★★★★★ Excelente"], ["4", "★★★★ Bom"], ["3", "★★★ Regular"], ["2", "★★ Ruim"], ["1", "★ Péssimo"]].map(([v, l]) => ({ id: v, name: l })), "5") },
      ], "Encerrar");
    case "update":
      return simple("Editar dados do chamado", [
        { name: "title", label: "Título", value: t.title, full: true },
        { name: "team_id", label: "Setor de manutenção", type: "select", options: options(lk.teams, t.team_id) },
        { name: "maintenance_type", label: "Tipo", type: "select", options: options(lk.maintenance_types, t.maintenance_type) },
        { name: "priority", label: "Prioridade", type: "select", options: options(lk.priorities, t.priority) },
        { name: "criticality", label: "Criticidade", type: "select", options: options(lk.criticalities, t.criticality) },
        { name: "sector_id", label: "Setor do hospital", type: "select", options: options(lk.sectors, t.sector_id, { empty: "—" }) },
        { name: "location", label: "Local", value: t.location },
        { name: "asset_id", label: "Ativo", type: "select", full: true, options: options(lk.assets, t.asset_id, { empty: "—", label: (a) => `${a.tag} — ${a.name}` }) },
      ], "Salvar");
    case "finish":
      return modal({
        title: "Finalizar serviço", wide: true, submitLabel: "Finalizar",
        body: `<div class="form-grid">${formFields([
          { name: "diagnosis", label: "Diagnóstico", type: "textarea", value: t.diagnosis, full: true },
          { name: "solution", label: "O que foi feito", type: "textarea", required: true, value: t.solution, full: true },
          { name: "failure_cause", label: "Causa da falha", value: t.failure_cause, attrs: 'list="causes"' },
          { name: "finished_at", label: "Término", type: "datetime-local", value: toLocalInput(), required: true },
          ...(t.worklogs.length ? [] : [{ name: "labor_hours", label: "Horas trabalhadas", type: "number", step: "0.25", min: 0, help: "Gera o apontamento automaticamente" }]),
          { name: "third_party_cost", label: "Custo de terceiros (R$)", type: "number", step: "0.01", min: 0, value: t.third_party_cost || "" },
          { name: "supplier_id", label: "Terceiro", type: "select", options: options(lk.suppliers, t.supplier_id, { empty: "—" }) },
          { name: "observations", label: "Observações", type: "textarea", value: t.observations, full: true },
          { name: "files", label: "Fotos do serviço", type: "file", multiple: true, full: true, accept: "image/*,.pdf" },
        ])}</div><datalist id="causes">${FAILURE_CAUSES.map((c) => `<option value="${esc(c)}">`).join("")}</datalist>`,
        onSubmit: async (form, data) => {
          const upd = await post(data);
          const withFiles = await uploadFiles(upd, form.querySelector('[name="files"]'), "fechamento");
          draw(el, withFiles || upd);
        },
      });
    case "worklog": {
      const start = new Date(Date.now() - 3600 * 1000);
      return modal({
        title: "Apontar horas trabalhadas", submitLabel: "Registrar",
        body: `<div class="form-grid">${formFields([
          { name: "technician_id", label: "Técnico", type: "select", full: true, options: techOptions(t, t.operator_id) },
          { name: "started_at", label: "Início", type: "datetime-local", value: toLocalInput(start), required: true },
          { name: "ended_at", label: "Término", type: "datetime-local", value: toLocalInput(), required: true },
          { name: "description", label: "Atividade realizada", type: "textarea", full: true },
        ])}</div>`,
        onSubmit: async (_f, data) => { draw(el, await api.post(`/api/tickets/${t.id}/worklogs`, data)); toast("Horas registradas", "ok"); },
      });
    }
    case "material":
      return modal({
        title: "Lançar peça / material", submitLabel: "Lançar",
        body: `<div class="form-grid">${formFields([
          { name: "product_id", label: "Produto do estoque", type: "select", full: true, options: options(lk.products, "", { empty: "Material fora do estoque (descrever abaixo)", label: (p) => `${p.code} — ${p.name} (saldo ${fmt.num(p.quantity)} ${p.unit})` }) },
          { name: "quantity", label: "Quantidade", type: "number", step: "0.01", min: 0, required: true, value: 1 },
          { name: "description", label: "Descrição (se fora do estoque)" },
          { name: "unit_cost", label: "Custo unitário (se fora do estoque)", type: "number", step: "0.01", min: 0 },
        ])}</div><p class="muted small" style="margin-top:10px">Itens do estoque geram baixa automática e custo pelo preço médio.</p>`,
        onSubmit: async (_f, data) => {
          draw(el, await api.post(`/api/tickets/${t.id}/materials`, data));
          toast("Material lançado", "ok");
          window.dispatchEvent(new Event("rg:data-changed"));
        },
      });
    case "attach":
      return modal({
        title: "Anexar fotos / arquivos", submitLabel: "Enviar",
        body: `<div class="form-grid">${formFields([{ name: "files", label: "Arquivos", type: "file", multiple: true, full: true, required: true, accept: "image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt" }])}</div>`,
        onSubmit: async (form) => {
          const upd = await uploadFiles(t, form.querySelector('[name="files"]'));
          if (!upd) throw new Error("Selecione ao menos um arquivo");
          draw(el, upd);
        },
      });
    default:
      return null;
  }
}
