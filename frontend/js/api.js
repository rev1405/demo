/* MallHaul API helper - the ONLY place the frontend talks to the backend.
   The backend then talks to MongoDB (see app/core/database.py). */
const API = {
  async req(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    let data = {};
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      const msg = typeof data.detail === "object" && data.detail !== null
        ? (data.detail.message || JSON.stringify(data.detail))
        : (data.detail || ("HTTP " + res.status));
      const err = new Error(msg);
      err.status = res.status;
      err.code = data.detail && data.detail.code;
      throw err;
    }
    return data;
  },
  get: (u) => API.req("GET", u),
  post: (u, b) => API.req("POST", u, b || {}),
  patch: (u, b) => API.req("PATCH", u, b),
  del: (u) => API.req("DELETE", u),
};

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function money(v) {
  const n = Number(v) || 0;
  return "R" + (Number.isInteger(n) ? n.toString() : n.toFixed(2));
}
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 3200);
}
function idem() {
  return (crypto.randomUUID ? crypto.randomUUID() : "k" + Date.now() + Math.random());
}