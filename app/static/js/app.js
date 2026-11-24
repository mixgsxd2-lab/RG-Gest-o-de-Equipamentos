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

// rótulos curtos da barra de abas do celular
const TAB_LABELS = { dashboard: "Início", ativos: "Ativos", monitoramento: "Sensores", fornecedores: "Fornec.", indicadores: "BI", usuarios: "Usuários" };

let alertsCache = [];

// ------------------------------------------------------------------ Tema claro/escuro
function isDark() {
  const t = document.documentElement.dataset.theme;
  if (t) return t === "dark";
  return !window.matchMedia("(prefers-color-scheme: light)").matches;
}

function themeSwitch() {
  const dark = isDark();
  return `<div class="theme-switch" role="group" aria-label="Tema da interface">
    <button type="button" data-theme-set="light" class="${dark ? "" : "on"}" aria-pressed="${!dark}" title="Modo claro">${icon("sun")}</button>
    <button type="button" data-theme-set="dark" class="${dark ? "on" : ""}" aria-pressed="${dark}" title="Modo escuro">${icon("moon")}</button>
  </div>`;
}

function bindThemeSwitch(scope, after) {
  scope.querySelectorAll("[data-theme-set]").forEach((b) => b.addEventListener("click", () => {
    const next = b.dataset.themeSet;
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("rg-theme", next); } catch (e) { /* armazenamento indisponível */ }
    scope.querySelectorAll("[data-theme-set]").forEach((x) => {
      x.classList.toggle("on", x.dataset.themeSet === next);
      x.setAttribute("aria-pressed", x.dataset.themeSet === next);
    });
    if (after) after();
  }));
}

// ------------------------------------------------------------------ Tela de carregamento (ao entrar e ao sair)
let splashShownAt = 0;
function showSplash(text) {
  let el = document.getElementById("splash");
  if (!el) {
    el = document.createElement("div");
    el.id = "splash";
    el.className = "splash";
    el.setAttribute("role", "status");
    el.innerHTML = `<div class="splash-inner">
      <span class="logo-mask logo-wordmark" aria-hidden="true"></span>
      <div class="splash-bar"></div>
      <span class="splash-text"></span>
    </div>`;
    document.body.appendChild(el);
  }
  el.querySelector(".splash-text").textContent = text;
  el.classList.remove("out");
  splashShownAt = Date.now();
}
function hideSplash() {
  const el = document.getElementById("splash");
  if (!el) return;
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 450); }, Math.max(0, 1100 - (Date.now() - splashShownAt)));
}

// ------------------------------------------------------------------ Login
const DEMO_USERS = [["admin", "Administrador"], ["gestor", "Gestor"], ["operador", "Técnico"], ["usuario", "Solicitante"], ["estoque", "Estoque"], ["diretoria", "Diretoria"]];

function renderLogin() {
  destroyCharts();
  const demo = document.body.dataset.demo === "1";
  root.innerHTML = `
  <div class="login-page">
    <section class="login-panel glass">
      <div class="login-top">
        <span class="eyebrow">Engenharia &amp; Manutenção</span>
        ${themeSwitch()}
      </div>
      <div class="login-grid">
        <div class="login-hero">
          <span class="logo-mask logo-wordmark" role="img" aria-label="Hospital Rio Grande"></span>
          <h1>Gestão de<b>Manutenção</b></h1>
        </div>
        <form class="login-card" id="login-form">
          <h2>Entrar</h2>
          <div class="stack" style="gap:14px">
            ${formFields([
              { name: "username", label: "Usuário", required: true, attrs: 'autocomplete="username" autocapitalize="none"' },
              { name: "password", label: "Senha", type: "password", required: true, attrs: 'autocomplete="current-password"' },
            ])}
            <button class="btn primary" type="submit">Entrar</button>
          </div>
          ${demo ? `<div class="divider">Acesso de teste · senha 123456</div>
          <div class="demo-users">${DEMO_USERS.map(([u, r]) => `<button type="button" data-user="${u}"><b>${u}</b><span>${r}</span></button>`).join("")}</div>` : ""}
        </form>
      </div>
    </section>
  </div>`;
  bindThemeSwitch(root);
  const form = document.getElementById("login-form");
  const submit = async () => {
    showSplash("Entrando…");
    try {
      const { user } = await api.post("/api/auth/login", { username: form.username.value, password: form.password.value });
      state.user = user;
      await startApp();
    } catch (err) {
      toast(err.message, "err");
    }
    hideSplash();
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
  let collapsed = false;
  try { collapsed = localStorage.getItem("rg-sidebar") === "closed"; } catch (e) { /* sem armazenamento */ }
  const nav = NAV.filter((n) => n.section || can(n.perm));
  // remove seções vazias
  const cleaned = nav.filter((n, i) => !n.section || (nav[i + 1] && !nav[i + 1].section));
  const tabs = nav.filter((n) => !n.section).slice(0, 4);
  root.innerHTML = `
  <div class="app${collapsed ? " collapsed" : ""}" id="app">
    <aside class="sidebar" id="sidebar">
      <a class="brand" href="#/" aria-label="Hospital Rio Grande — início">
        <span class="logo-mask logo-wordmark" aria-hidden="true"></span>
        <span class="logo-mask logo-symbol" aria-hidden="true"></span>
      </a>
      <nav class="nav" aria-label="Menu principal">
        ${cleaned.map((n) => n.section ? `<div class="nav-section">${n.section}</div>`
          : `<a href="#/${n.path}" data-path="${n.path}" title="${n.label}">${icon(n.icon)}<span>${n.label}</span>${n.badge ? '<span class="badge-count hidden" data-badge="' + n.badge + '"></span>' : ""}</a>`).join("")}
      </nav>
      <div class="sidebar-foot">
        <button type="button" class="collapse-btn" id="collapse-btn" aria-expanded="${!collapsed}" title="${collapsed ? "Abrir menu" : "Recolher menu"}">
          ${icon("sidebar")}<span>Recolher menu</span>
        </button>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <button class="icon-btn menu-toggle" id="menu-toggle" aria-label="Abrir menu">${icon("menu")}</button>
        <span class="logo-mask logo-symbol" aria-hidden="true"></span>
        <div class="spacer"></div>
        ${can("tickets.create") ? `<a class="btn primary sm" href="#/chamados/novo">${icon("plus")}<span class="hide-sm">Novo chamado</span></a>` : ""}
        ${themeSwitch()}
        <button class="icon-btn" id="alerts-btn" aria-label="Alertas">${icon("bell")}<span class="dot hidden" id="alerts-dot"></span></button>
        <button class="user-chip" id="user-btn" aria-label="Menu do usuário">
          <span class="avatar">${esc(initials(u.name))}</span>
          <span class="meta"><b>${esc(u.name)}</b><span>${esc(u.role_label)}</span></span>
        </button>
      </header>
      <main class="content" id="view"></main>
    </div>
    <nav class="tabbar" aria-label="Navegação principal">
      ${tabs.map((n) => `<a href="#/${n.path}" data-path="${n.path}">${icon(n.icon)}<span>${TAB_LABELS[n.path] || n.label}</span></a>`).join("")}
      <button type="button" id="tab-menu">${icon("menu")}<span>Menu</span></button>
    </nav>
  </div>`;
  const sidebar = document.getElementById("sidebar");
  let scrim = null;
  const closeMenu = () => { sidebar.classList.remove("open"); if (scrim) { scrim.remove(); scrim = null; } };
  const openMenu = () => {
    sidebar.classList.add("open");
    scrim = document.createElement("div");
    scrim.className = "scrim";
    scrim.addEventListener("click", closeMenu);
    document.body.appendChild(scrim);
  };
  document.getElementById("menu-toggle").addEventListener("click", openMenu);
  document.getElementById("tab-menu").addEventListener("click", openMenu);
  sidebar.addEventListener("click", (e) => { if (e.target.closest("a")) closeMenu(); });
  const collapseBtn = document.getElementById("collapse-btn");
  collapseBtn.addEventListener("click", () => {
    const app = document.getElementById("app");
    const closed = app.classList.toggle("collapsed");
    collapseBtn.setAttribute("aria-expanded", String(!closed));
    collapseBtn.title = closed ? "Abrir menu" : "Recolher menu";
    try { localStorage.setItem("rg-sidebar", closed ? "closed" : "open"); } catch (e) { /* sem armazenamento */ }
    setTimeout(() => window.dispatchEvent(new Event("resize")), 260); // reajusta os gráficos
  });
  bindThemeSwitch(document.querySelector(".topbar"), () => route()); // redesenha gráficos com as cores do tema
  document.getElementById("alerts-btn").addEventListener("click", (e) => { e.stopPropagation(); showAlerts(); });
  document.getElementById("user-btn").addEventListener("click", (e) => { e.stopPropagation(); showUserMenu(); });
  document.addEventListener("click", (e) => {
    const dd = document.querySelector(".dropdown");
    if (dd && !dd.contains(e.target)) dd.remove();
  });
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
    dd.remove();
    showSplash("Saindo…");
    try { await api.post("/api/auth/logout"); } catch (e) { /* sessão já encerrada */ }
    state.user = null;
    location.hash = "";
    renderLogin();
    hideSplash();
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
  document.querySelectorAll(".nav a, .tabbar a").forEach((a) => a.classList.toggle("active", a.dataset.path === (path || home)));
  const view = document.getElementById("view");
  destroyCharts();
  document.querySelector(".dropdown")?.remove();
  if (!entry || !can(entry.perm)) {
    view.innerHTML = `<div class="card"><div class="empty">${icon("shield")}<p>Página não encontrada ou sem permissão para o seu perfil.</p><a class="btn" href="#/">Voltar ao início</a></div></div>`;
    setTitle("Acesso");
    return;
  }
  setTitle(entry.label);
  // rótulo da seção (serifa espaçada, como "H O S P I T A L") exibido acima do título via CSS
  const section = NAV.slice(0, NAV.indexOf(entry)).reverse().find((n) => n.section);
  view.style.setProperty("--section", JSON.stringify(section ? section.section : "Hospital Rio Grande"));
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
