import { api } from "../api.js";
import { bindRows, esc, fmt, formFields, icon, loading, modal, options, state, table, toast } from "../ui.js";

const view = { tab: "usuarios" };
const PERM_LABELS = {
  "dashboard.view": "Ver dashboard", "tickets.create": "Abrir chamados", "tickets.view_all": "Ver todos os chamados",
  "tickets.manage": "Receber, designar, cancelar e encerrar", "tickets.execute": "Aceitar e executar chamados",
  "assets.view": "Consultar ativos", "assets.edit": "Cadastrar ativos", "preventive.view": "Ver preventivas",
  "preventive.edit": "Gerenciar preventivas", "teams.view": "Ver equipes e fornecedores", "teams.edit": "Gerenciar equipes, fornecedores e contratos",
  "stock.view": "Consultar estoque", "stock.edit": "Movimentar estoque", "costs.view": "Ver custos", "costs.edit": "Lançar custos",
  "iot.view": "Monitoramento", "iot.edit": "Gerenciar sensores", "indicators.view": "Indicadores e BI", "users.manage": "Usuários e acessos",
};

export async function render(el, _params, ctx) {
  el.innerHTML = `
    <div class="page-head">
      <div><h1>Usuários e acessos</h1><div class="sub">Perfis, permissões e integrações de identidade corporativa</div></div>
      <div class="actions"><button class="btn primary" id="new">${icon("plus")} Novo usuário</button></div>
    </div>
    <div class="tabs">${[["usuarios", "Usuários"], ["perfis", "Perfis e permissões"], ["integracoes", "Integrações"]]
      .map(([k, l]) => `<button type="button" data-tab="${k}" class="${view.tab === k ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="body">${loading()}</div>`;
  const reload = () => render(el, _params, ctx);
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { view.tab = b.dataset.tab; reload(); }));
  el.querySelector("#new").addEventListener("click", () => editUser(null, reload));
  const body = el.querySelector("#body");
  if (view.tab === "perfis") return matrix(body, ctx);
  if (view.tab === "integracoes") return integrations(body, ctx);
  const rows = await api.get("/api/users");
  if (!ctx.isCurrent()) return;
  body.innerHTML = `<div class="card"><div class="card-body flush" id="t"></div></div>`;
  const box = body.querySelector("#t");
  box.innerHTML = table([
    { label: "Usuário", cls: "title-cell", render: (u) => `<b>${esc(u.name)}</b><div class="sub-cell">${esc(u.username)} · ${esc(u.email || "")}</div>` },
    { label: "Perfil", render: (u) => `<span class="tag">${esc(u.role_label)}</span>` },
    { label: "Setor / equipe", render: (u) => `${esc(u.sector || "—")}<div class="sub-cell">${esc(u.team || "")}</div>` },
    { label: "Autenticação", render: (u) => esc(u.auth_provider === "local" ? "Local" : u.auth_provider) },
    { label: "Último acesso", render: (u) => fmt.datetime(u.last_login_at), cls: "nowrap" },
    { label: "Situação", render: (u) => (u.active ? '<span class="badge b-good">Ativo</span>' : '<span class="badge b-neutral">Inativo</span>') },
  ], rows, { onRow: true });
  bindRows(box, rows, (u) => editUser(u, reload));
}

function editUser(u, done) {
  const lk = state.lookups;
  const roles = Object.entries(lk.roles).map(([id, name]) => ({ id, name }));
  u = u || { role: "solicitante", active: true };
  modal({
    title: u.id ? `Editar ${u.username}` : "Novo usuário",
    body: `<div class="form-grid">${formFields([
      ...(u.id ? [] : [{ name: "username", label: "Usuário (login)", required: true }]),
      { name: "name", label: "Nome completo", required: true, full: !!u.id },
      { name: "email", label: "E-mail", type: "email" },
      { name: "role", label: "Perfil", type: "select", required: true, options: options(roles, u.role) },
      { name: "sector_id", label: "Setor", type: "select", options: options(lk.sectors, u.sector_id, { empty: "—" }) },
      { name: "team_id", label: "Equipe de manutenção", type: "select", options: options(lk.teams, u.team_id, { empty: "—" }) },
      { name: "password", label: u.id ? "Nova senha (opcional)" : "Senha", type: "password", required: !u.id, help: "Mínimo de 6 caracteres" },
      ...(u.id ? [{ name: "active", label: "Situação", type: "checkbox", checkLabel: "Usuário ativo", value: u.active }] : []),
    ], u)}</div>`,
    onSubmit: async (_f, data) => {
      if (u.id) await api.put(`/api/users/${u.id}`, data); else await api.post("/api/users", data);
      toast("Usuário salvo", "ok");
      done();
    },
  });
}

async function matrix(body, ctx) {
  const m = await api.get("/api/access/matrix");
  if (!ctx.isCurrent()) return;
  const roles = Object.keys(m.roles);
  body.innerHTML = `<div class="card"><div class="card-body flush"><div class="table-wrap"><table class="table">
    <thead><tr><th>Permissão</th>${roles.map((r) => `<th style="text-align:center">${esc(m.roles[r])}</th>`).join("")}</tr></thead>
    <tbody>${Object.entries(m.permissions).map(([p, allowed]) => `<tr><td>${esc(PERM_LABELS[p] || p)}<div class="sub-cell"><code>${esc(p)}</code></div></td>
      ${roles.map((r) => `<td style="text-align:center">${allowed.includes(r) ? `<span style="color:var(--good)" aria-label="Permitido">${icon("check")}</span>` : '<span class="muted" aria-label="Negado">—</span>'}</td>`).join("")}</tr>`).join("")}</tbody>
  </table></div></div></div>`;
}

async function integrations(body, ctx) {
  const d = await api.get("/api/integrations");
  if (!ctx.isCurrent()) return;
  const desc = {
    local: "Usuário e senha armazenados com hash no banco do sistema.",
    active_directory: "Autenticação LDAP no AD do hospital, com mapeamento de grupos para perfis.",
    microsoft365: "Login único (SSO) via Microsoft Entra ID / OpenID Connect.",
    google_workspace: "Login único (SSO) via Google Workspace / OpenID Connect.",
  };
  body.innerHTML = `
    <div class="grid grid-2">
      ${d.identity.map((p) => `<div class="card"><div class="card-body">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><h3>${esc(p.label)}</h3>
          ${p.enabled ? '<span class="badge b-good">Ativo</span>' : '<span class="badge b-neutral">Preparado</span>'}</div>
        <p class="small muted" style="margin-top:6px">${esc(desc[p.key] || "")}</p>
        ${p.enabled ? "" : `<p class="small">Para ativar, configure as variáveis de ambiente do provedor (ver README) e implemente o conector em <code>app/auth_providers.py</code>.</p>`}
      </div></div>`).join("")}
      <div class="card"><div class="card-body"><h3>Integração IoT</h3><p class="small muted" style="margin-top:6px">Endpoint <code>${esc(d.iot.endpoint)}</code> · ${esc(d.iot.auth)}</p>
        <p class="small">${d.iot.protocols.map(esc).join(" · ")}</p></div></div>
      <div class="card"><div class="card-body"><h3>BI / Big Data</h3><p class="small muted" style="margin-top:6px"><code>${esc(d.bi.endpoint)}</code></p>
        <p class="small">${d.bi.tools.map(esc).join(" · ")} · Banco atual: <code>${esc(d.database)}</code></p></div></div>
    </div>`;
}
