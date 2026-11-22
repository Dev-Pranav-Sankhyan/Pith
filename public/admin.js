/* Pith admin desk. Every value from the server is placed with textContent, never innerHTML:
   reader names and forecast text are not ours to trust. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  };
  const day = (iso) => (iso ? String(iso).slice(0, 10) : "—");
  const webLink = (url, label) => {
    if (typeof url !== "string" || !/^https?:\/\//i.test(url)) return el("span", "cell-empty", "—");
    const a = el("a", "admin-link", label || "Link");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  };

  function ago(iso) {
    if (!iso) return "never";
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return day(iso);
    const mins = Math.round((Date.now() - t) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins} min ago`;
    const hours = Math.round(mins / 60);
    if (hours < 48) return `${hours} h ago`;
    return `${Math.round(hours / 24)} days ago`;
  }

  let toastTimer = null;
  function toast(msg) {
    const t = $("admin-toast");
    t.textContent = msg;
    t.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("is-on"), 4200);
  }

  function showError(msg) {
    const box = $("admin-error");
    box.textContent = msg;
    box.hidden = false;
  }

  function emptyRow(tbody, cols, text) {
    const tr = el("tr");
    const td = el("td", "cell-empty", text);
    td.colSpan = cols;
    tr.appendChild(td);
    tbody.appendChild(tr);
  }

  function forecastCell(f) {
    const td = el("td", "cell-statement");
    if (f.headline) td.appendChild(el("div", "admin-headline", f.headline));
    td.appendChild(el("div", "ledger-statement", f.statement));
    return td;
  }

  // ------------------------------------------------------------ sections
  function renderStats(s, fc) {
    $("stat-readers").textContent = s.readers;
    $("stat-readers-sub").textContent = `+${s.new_this_week} this week · ${s.admins} admin${s.admins === 1 ? "" : "s"}`;
    $("stat-active").textContent = s.active_this_week;
    $("stat-active-sub").textContent = `${s.signed_in_now} with a live session`;
    $("stat-due").textContent = fc.counts.due;
    $("stat-due-sub").textContent = `${fc.counts.open} open · ${fc.counts.resolved} resolved`;
    $("stat-articles").textContent = s.articles;
    const demo = s.demo_articles ? ` · ${s.demo_articles} offline demo` : "";
    $("stat-articles-sub").textContent = `Last fetch ${ago(s.last_fetch)}${demo}`;
    $("admin-stats").removeAttribute("aria-busy");
  }

  function renderDue(due, upcoming) {
    const box = $("admin-due");
    box.replaceChildren();
    if (!due.length) {
      const next = upcoming[0];
      box.appendChild(el("p", "admin-empty", next
        ? `Nothing is due. The next forecast resolves on ${day(next.resolves_at)}.`
        : "Nothing is due, and there are no open live forecasts."));
      return;
    }
    due.forEach((f) => box.appendChild(dueCard(f)));
  }

  function dueCard(f) {
    const card = el("article", "admin-forecast");
    const top = el("div", "admin-forecast-top");
    top.appendChild(el("span", "status-pill open", `Due ${day(f.resolves_at)}`));
    top.appendChild(el("span", "admin-prob", `${f.probability}%`));
    top.appendChild(el("span", "admin-meta", `made ${day(f.made_at)}`));
    card.appendChild(top);
    if (f.headline) card.appendChild(el("div", "admin-headline", f.headline));
    card.appendChild(el("p", "admin-statement", f.statement));
    const crit = el("p", "admin-criteria");
    crit.appendChild(el("strong", null, "Resolves when: "));
    crit.appendChild(document.createTextNode(f.criteria || "—"));
    card.appendChild(crit);
    if (f.source_url) {
      const src = el("p", "admin-meta");
      src.appendChild(document.createTextNode("Original source: "));
      let host = "link";
      try { host = new URL(f.source_url).hostname; } catch (_) { /* webLink still refuses non-web links */ }
      src.appendChild(webLink(f.source_url, host));
      card.appendChild(src);
    }

    const form = el("form", "admin-verdict");
    form.noValidate = false;
    const sel = el("select", "filter-select");
    sel.name = "status";
    sel.setAttribute("aria-label", "Verdict");
    [["correct", "Correct: it happened"], ["wrong", "Wrong: it didn't"], ["void", "Void: can't be judged"]]
      .forEach(([v, label]) => { const o = el("option", null, label); o.value = v; sel.appendChild(o); });
    const url = el("input", "admin-input");
    url.type = "url";
    url.name = "evidence_url";
    url.placeholder = "Evidence link (https://…)";
    url.required = true;
    url.maxLength = 2000;
    url.setAttribute("aria-label", "Evidence link");
    const note = el("textarea", "admin-input admin-note");
    note.name = "note";
    note.rows = 2;
    note.maxLength = 2000;
    note.placeholder = "What actually happened (optional, shown on the Ledger)";
    note.setAttribute("aria-label", "Note");
    const btn = el("button", "admin-submit", "Record verdict");
    btn.type = "submit";
    const err = el("p", "admin-form-error");
    err.hidden = true;
    sel.addEventListener("change", () => {
      url.required = sel.value !== "void";
      url.placeholder = sel.value === "void" ? "Evidence link (optional for void)" : "Evidence link (https://…)";
    });
    form.append(sel, url, note, btn, err);
    form.addEventListener("submit", (e) => submitVerdict(e, f, form, btn, err));
    card.appendChild(form);
    return card;
  }

  async function submitVerdict(e, f, form, btn, err) {
    e.preventDefault();
    err.hidden = true;
    const status = form.elements.status.value;
    const evidence = form.elements.evidence_url.value.trim();
    const note = form.elements.note.value.trim();
    const ok = window.confirm(
      `Record "${status}" for:\n\n${f.statement}\n\nThis is permanent and signed with your name. ` +
      "A later correction adds a new record; it never erases this one.");
    if (!ok) return;
    btn.disabled = true;
    btn.textContent = "Recording…";
    try {
      const res = await fetch("/api/admin/resolve", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prediction_id: f.id, status, evidence_url: evidence, note }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
      toast(`Recorded "${status}", signed ${data.resolved_by}. The Ledger page updates in a few seconds.`);
      await load();
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
      btn.disabled = false;
      btn.textContent = "Record verdict";
    }
  }

  function renderUpcoming(rows) {
    const tb = $("admin-upcoming");
    tb.replaceChildren();
    if (!rows.length) return emptyRow(tb, 4, "No open live forecasts.");
    rows.forEach((f) => {
      const tr = el("tr");
      tr.appendChild(el("td", "cell-mono", day(f.resolves_at)));
      tr.appendChild(forecastCell(f));
      tr.appendChild(el("td", "cell-prob", `${f.probability}%`));
      tr.appendChild(el("td", "cell-mono", day(f.made_at)));
      tb.appendChild(tr);
    });
  }

  function renderRecent(rows) {
    const tb = $("admin-recent");
    tb.replaceChildren();
    if (!rows.length) return emptyRow(tb, 5, "No live forecast has a verdict yet.");
    rows.forEach((f) => {
      const tr = el("tr");
      tr.appendChild(el("td", "cell-mono", day(f.resolved_at)));
      tr.appendChild(forecastCell(f));
      const pill = el("td");
      pill.appendChild(el("span", `status-pill ${["correct", "wrong", "void"].includes(f.status) ? f.status : ""}`, f.status));
      tr.appendChild(pill);
      tr.appendChild(el("td", null, f.resolved_by || "—"));
      const ev = el("td");
      ev.appendChild(webLink(f.evidence_url, "Evidence"));
      tr.appendChild(ev);
      tb.appendChild(tr);
    });
  }

  function renderReaders(rows, total) {
    const tb = $("admin-readers");
    tb.replaceChildren();
    $("admin-readers-note").textContent = rows.length < total
      ? `Newest ${rows.length} of ${total}.` : "Newest first.";
    if (!rows.length) return emptyRow(tb, 6, "No readers yet.");
    rows.forEach((r) => {
      const tr = el("tr");
      const who = el("td");
      const name = el("div", "cell-strong", r.display_name || r.username);
      if (r.is_admin) name.appendChild(el("span", "admin-badge", "Admin"));
      who.appendChild(name);
      who.appendChild(el("div", "admin-meta", `@${r.username}`));
      tr.appendChild(who);
      tr.appendChild(el("td", "cell-mono", day(r.created_at)));
      tr.appendChild(el("td", null, ago(r.last_active)));
      tr.appendChild(el("td", null, r.providers.length ? r.providers.join(", ") : "Username"));
      tr.appendChild(el("td", "cell-mono", r.events));
      tr.appendChild(el("td", null, r.onboarded ? "Set up" : "Not yet"));
      tb.appendChild(tr);
    });
  }

  // ------------------------------------------------------------ load
  async function load() {
    let res;
    try {
      res = await fetch("/api/admin/overview", { credentials: "same-origin" });
    } catch (_) {
      return showError("Couldn't reach the Pith server.");
    }
    if (res.status === 401) return location.replace("/about?next=%2Fadmin#access");
    if (res.status === 403) return showError("This account doesn't have admin rights.");
    if (!res.ok) return showError(`The admin data didn't load (${res.status}).`);
    const data = await res.json();
    $("admin-error").hidden = true;
    renderStats(data.stats, data.forecasts);
    renderDue(data.forecasts.due, data.forecasts.upcoming);
    renderUpcoming(data.forecasts.upcoming);
    renderRecent(data.forecasts.recent);
    renderReaders(data.readers, data.stats.readers);
  }

  document.addEventListener("DOMContentLoaded", load);
})();
