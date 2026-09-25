// Cliente HTTP da API REST (JSON, sessão via cookie)
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function request(method, url, body) {
  const opts = { method, credentials: "same-origin", headers: {} };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) data = await res.json();
  if (!res.ok) {
    if (res.status === 401 && !url.includes("/auth/")) window.dispatchEvent(new Event("rg:unauthorized"));
    throw new ApiError((data && data.error) || `Erro ${res.status}`, res.status);
  }
  return data;
}

export const api = {
  get: (url, params) => {
    if (params) {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") q.set(k, v); });
      const s = q.toString();
      if (s) url += (url.includes("?") ? "&" : "?") + s;
    }
    return request("GET", url);
  },
  post: (url, body = {}) => request("POST", url, body),
  put: (url, body = {}) => request("PUT", url, body),
  del: (url) => request("DELETE", url),
};
