// Aplicação SPA: autenticação, layout, navegação e roteamento
import { api } from "./api.js";
import { destroyCharts } from "./charts.js";
import { can, esc, formFields, icon, initials, modal, state, toast } from "./ui.js";

import * as dashboard from "./views/dashboard.js";
import * as tickets from "./views/tickets.js";
import * as assets from "./views/assets.js";
import * as preventive from "./views/preventive.js";
import * as monitoring from "./views/monitoring.js";
import * as teams from "./views/teams.js";
import * as suppliers from "./views/suppliers.js";
import * as stock from "./views/stock.js";
import * as costs from "./views/costs.js";
import * as intelligence from "./views/intelligence.js";
import * as users from "./views/users.js";

const root = document.getElementById("root");

const NAV = [
  { section: "Operação" },
  { path: "dashboard", label: "Dashboard", icon: "dashboard", perm: "dashboard.view", view: dashboard },
  { path: "chamados", label: "Chamados", icon: "ticket", perm: "tickets.create", view: tickets, badge: "tickets" },
  { path: "ativos", label: "Inventário / Ativos", icon: "asset", perm: "assets.view", view: assets },
  { path: "preventivas", label: "Preventivas", icon: "calendar", perm: "preventive.view", view: preventive },
  { path: "monitoramento", label: "Monitoramento / IoT", icon: "activity", perm: "iot.view", view: monitoring },
  { section: "Recursos" },
  { path: "equipes", label: "Equipes e técnicos", icon: "users", perm: "teams.view", view: teams },
  { path: "fornecedores", label: "Fornecedores e contratos", icon: "truck", perm: "teams.view", view: suppliers },
  { path: "estoque", label: "Estoque", icon: "box", perm: "stock.view", view: stock },
  { path: "custos", label: "Custos", icon: "money", perm: "costs.view", view: costs },
  { section: "Gestão" },
  { path: "indicadores", label: "Indicadores e BI", icon: "chart", perm: "indicators.view", view: intelligence },
  { path: "usuarios", label: "Usuários e acessos", icon: "shield", perm: "users.manage", view: users },
];

let alertsCache = [];

// ------------------------------------------------------------------ Login
function renderLogin() {
  destroyCharts();
  root.innerHTML = `
  <div class="login-page">
    <section class="login-hero">
      <div class="brand" style="padding:0"><div class="brand-logo">RG</div>
        <div><div class="brand-name">Hospital Rio Grande</div><div class="brand-sub">Gestão de Manutenção</div></div></div>
      <div>
        <h1>Plataforma central de manutenção hospitalar</h1>
        <p>Do chamado ao indicador: abertura, recebimento, execução, materiais, custos, fechamento, histórico e inteligência — em um só lugar.</p>
      </div>
      <ul>
        <li>${icon("ticket")} Chamados com fluxo completo, SLA e histórico auditável</li>
        <li>${icon("calendar")} Preventivas, calibrações e alertas automáticos</li>
        <li>${icon("activity")} Monitoramento IoT de energia, água e gases</li>
        <li>${icon("chart")} Indicadores, custos, depreciação e base para BI/ML</li>
      </ul>
    </section>
    <section class="login-form-wrap">
      <form class="login-card card" style="padding:26px" id="login-form">
        <span class="badge b-warning" style="margin-bottom:12px">DEMONSTRAÇÃO</span>
        <h2>Entrar</h2>
        <p class="muted small" style="margin-bottom:16px">Use um dos acessos fictícios abaixo (senha <b>123456</b>).</p>
        <div class="stack" style="gap:12px">
          ${formFields([
            { name: "username", label: "Usuário", required: true, attrs: 'autocomplete="username" autocapitalize="none"' },
            { name: "password", label: "Senha", type: "password", required: true, attrs: 'autocomplete="current-password"' },
          ])}
          <button class="btn primary" type="submit" style="width:100%;padding:10px">Entrar</button>
        </div>
        <div class="demo-users">
          ${[["admin", "Administrador"], ["gestor", "Gestor de Manutenção"], ["operador", "Operador/Técnico"], ["usuario", "Solicitante"], ["estoque", "Estoque"], ["diretoria", "Diretoria"]]
            .map(([u, r]) => `<button type="button" data-user="${u}"><b>${u}</b><span>${r}</span></button>`).join("")}
        </div>
        <p class="muted small" style="margin-top:16px">Preparado para login corporativo (Active Directory, Microsoft 365 e Google Workspace).</p>
      </form>
    </section>
  </div>`;
  const form = document.getElementById("login-form");
  const submit = async () => {
    try {
      const { user } = await api.post("/api/auth/login", { username: form.username.value, password: form.password.value });
      state.user = user;
      await startApp();
    } catch (err) {
      toast(err.message, "err");
    }
  };
  form.addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  form.querySelectorAll("[data-user]").forEach((b) => b.addEventListener("click", () => {
    form.username.value = b.dataset.user;
    form.password.value = "123456";
    submit();
  }));
}

// ------------------------------------------------------------------ Layout
function renderShell() {
  const u = state.user;
  const nav = NAV.filter((n) => n.section || can(n.perm));
  // remove seções vazias
  const cleaned = nav.filter((n, i) => !n.section || (nav[i + 1] && !nav[i + 1].section));
  root.innerHTML = `
  <div class="app">
    <aside class="sidebar" id="sidebar">
      <a class="brand" href="#/" style="text-decoration:none"><div class="brand-logo">RG</div>
        <div><div class="brand-name">RG Manutenção</div><div class="brand-sub">Hospital Rio Grande</div></div></a>
      <nav class="nav" aria-label="Menu principal">
        ${cleaned.map((n) => n.section ? `<div class="nav-section">${n.section}</div>`
          : `<a href="#/${n.path}" data-path="${n.path}">${icon(n.icon)}<span>${n.label}</span>${n.badge ? '<span class="badge-count hidden" data-badge="' + n.badge + '"></span>' : ""}</a>`).join("")}
      </nav>
      <div class="sidebar-foot">Versão de demonstração · dados fictícios<br>© Hospital Rio Grande</div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button class="icon-btn menu-toggle" id="menu-toggle" aria-label="Abrir menu">${icon("menu")}</button>
        <div class="title" id="page-title"></div>
        <div class="spacer"></div>
        ${can("tickets.create") ? `<a class="btn primary sm" href="#/chamados/novo">${icon("plus")}<span class="hide-sm">Novo chamado</span></a>` : ""}
        <button class="icon-btn" id="theme-btn" aria-label="Alternar tema claro/escuro">${icon("moon")}</button>
        <button class="icon-btn" id="alerts-btn" aria-label="Alertas">${icon("bell")}<span class="dot hidden" id="alerts-dot"></span></button>
        <button class="user-chip" id="user-btn" aria-label="Menu do usuário">
          <span class="avatar">${esc(initials(u.name))}</span>
          <span class="meta"><b>${esc(u.name)}</b><span>${esc(u.role_label)}</span></span>
        </button>
      </header>
      <main class="content" id="view"></main>
    </div>
  </div>`;
  const sidebar = document.getElementById("sidebar");
  let scrim = null;
  const closeMenu = () => { sidebar.classList.remove("open"); if (scrim) { scrim.remove(); scrim = null; } };
  document.getElementById("menu-toggle").addEventListener("click", () => {
    sidebar.classList.add("open");
    scrim = document.createElement("div");
    scrim.className = "scrim";
    scrim.addEventListener("click", closeMenu);
    document.body.appendChild(scrim);
  });
  sidebar.addEventListener("click", (e) => { if (e.target.closest("a")) closeMenu(); });
  document.getElementById("theme-btn").addEventListener("click", toggleTheme);
  document.getElementById("alerts-btn").addEventListener("click", (e) => { e.stopPropagation(); showAlerts(); });
  document.getElementById("user-btn").addEventListener("click", (e) => { e.stopPropagation(); showUserMenu(); });
  document.addEventListener("click", (e) => {
    const dd = document.querySelector(".dropdown");
    if (dd && !dd.contains(e.target)) dd.remove();
  });
  updateThemeIcon();
}

function isDark() {
  const t = document.documentElement.dataset.theme;
  if (t) return t === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function updateThemeIcon() {
  const b = document.getElementById("theme-btn");
  if (b) b.innerHTML = icon(isDark() ? "sun" : "moon");
}
function toggleTheme() {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("rg-theme", next); } catch (e) { /* armazenamento indisponível */ }
  updateThemeIcon();
  route(); // redesenha gráficos com as cores do tema
}

function dropdown(html) {
  document.querySelector(".dropdown")?.remove();
  const dd = document.createElement("div");
  dd.className = "dropdown";
  dd.innerHTML = html;
  document.body.appendChild(dd);
  dd.addEventListener("click", (e) => { if (e.target.closest("a")) dd.remove(); });
  return dd;
}

const SEV = { critico: ["b-critical", "Crítico"], alto: ["b-serious", "Alto"], medio: ["b-warning", "Médio"], info: ["b-info", "Info"] };
function showAlerts() {
  dropdown(`<div class="dd-head">Alertas <span class="muted small">${alertsCache.length}</span></div>
    ${alertsCache.length ? alertsCache.slice(0, 40).map((a) => `
      <a class="dd-item" href="${a.link}">
        <span class="badge ${SEV[a.severity][0]}">${SEV[a.severity][1]}</span>
        <span><b>${esc(a.title)}</b><br><span class="muted">${esc(a.message)}</span></span>
      </a>`).join("") : '<div class="empty">Nenhum alerta no momento</div>'}`);
}

function showUserMenu() {
  const u = state.user;
  const dd = dropdown(`<div class="dd-head"><span>${esc(u.name)}<br><span class="muted small">${esc(u.username)} · ${esc(u.role_label)}</span></span></div>
    <button class="dd-item" data-act="pwd">${icon("key")} Alterar senha</button>
    <button class="dd-item" data-act="logout">${icon("logout")} Sair</button>`);
  dd.querySelector('[data-act="logout"]').addEventListener("click", async () => {
    await api.post("/api/auth/logout");
    state.user = null;
    dd.remove();
    location.hash = "";
    renderLogin();
  });
  dd.querySelector('[data-act="pwd"]').addEventListener("click", () => {
    dd.remove();
    modal({
      title: "Alterar senha",
      body: `<div class="form-grid">${formFields([
        { name: "current", label: "Senha atual", type: "password", required: true, full: true },
        { name: "new", label: "Nova senha", type: "password", required: true, full: true, help: "Mínimo de 6 caracteres" },
      ])}</div>`,
      onSubmit: async (_f, data) => { await api.post("/api/auth/change-password", data); toast("Senha alterada", "ok"); },
    });
  });
}

export async function refreshAlerts() {
  try {
    const data = await api.get("/api/alerts");
    alertsCache = data.items;
    const dot = document.getElementById("alerts-dot");
    if (dot) {
      const n = data.items.filter((a) => a.severity === "critico" || a.severity === "alto").length || data.items.length;
      dot.textContent = n > 99 ? "99+" : n;
      dot.classList.toggle("hidden", !data.items.length);
    }
    const open = document.querySelector('[data-badge="tickets"]');
    if (open && can("tickets.manage")) {
      const t = await api.get("/api/tickets", { status: "aberto", per_page: 1 });
      open.textContent = t.total;
      open.classList.toggle("hidden", !t.total);
    }
  } catch (e) { /* silencioso */ }
}

export function setTitle(t) {
  const el = document.getElementById("page-title");
  if (el) el.textContent = t;
  document.title = `${t} · RG Manutenção`;
}

// ------------------------------------------------------------------ Roteamento
let routeSeq = 0;
async function route() {
  if (!state.user) return;
  const seq = ++routeSeq;
  const [hash, qs] = location.hash.replace(/^#\/?/, "").split("?");
  const [path, ...rest] = hash.split("/");
  const query = Object.fromEntries(new URLSearchParams(qs || ""));
  const home = can("dashboard.view") ? "dashboard" : "chamados";
  const entry = NAV.find((n) => n.path === (path || home));
  document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.path === (path || home)));
  const view = document.getElementById("view");
  destroyCharts();
  document.querySelector(".dropdown")?.remove();
  if (!entry || !can(entry.perm)) {
    view.innerHTML = `<div class="card"><div class="empty">${icon("shield")}<p>Página não encontrada ou sem permissão para o seu perfil.</p><a class="btn" href="#/">Voltar ao início</a></div></div>`;
    setTitle("Acesso");
    return;
  }
  setTitle(entry.label);
  window.scrollTo(0, 0);
  try {
    await entry.view.render(view, rest, { isCurrent: () => seq === routeSeq, query });
  } catch (err) {
    if (seq !== routeSeq) return;
    view.innerHTML = `<div class="card"><div class="empty">${icon("alert")}<p>${esc(err.message)}</p></div></div>`;
  }
}

export function navigate(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

async function startApp() {
  state.lookups = await api.get("/api/lookups");
  renderShell();
  await route();
  refreshAlerts();
}

window.addEventListener("hashchange", route);
window.addEventListener("rg:unauthorized", () => { state.user = null; renderLogin(); });
window.addEventListener("rg:data-changed", async () => {
  state.lookups = await api.get("/api/lookups");
  refreshAlerts();
});
setInterval(() => { if (state.user) refreshAlerts(); }, 60000);

(async function boot() {
  try {
    const { user } = await api.get("/api/auth/me");
    state.user = user;
    await startApp();
  } catch (e) {
    renderLogin();
  }
})();
