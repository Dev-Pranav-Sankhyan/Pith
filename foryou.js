/* ==========================================================================
   Pith For You: client controller
   - auth + onboarding
   - feed rendering with explanations
   - behavioural telemetry: impressions (≥60% visible for 1s), clicks,
     dwell time (time away reading the article tab), reactions, saves,
     shares, hides, mutes, topic steering, searches
   All learning happens server-side in core/recommender.py.
   ========================================================================== */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const TOPIC_ICONS = {
    AI: "◎", Technology: "⌘", Business: "◆", Markets: "↗", Politics: "⚖", World: "◍", Science: "⚛",
    Space: "✦", Health: "✚", Climate: "☁", Sports: "◉", Entertainment: "★", Gaming: "▶",
  };

  const state = {
    user: null,
    tab: "foryou",
    topic: null,
    query: "",
    shown: new Set(),
    loading: false,
    exhausted: false,
    queue: [],
    pendingDwell: null,
    impressed: new Set(),
    allTopics: [],
  };

  // ------------------------------------------------------------------ utils
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const localHour = () => new Date().getHours();

  async function api(path, body) {
    const opts = body === undefined
      ? { credentials: "same-origin" }
      : { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { status: res.status });
    return data;
  }

  function timeAgo(iso) {
    const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m ago`;
    if (s < 86400) return `${Math.round(s / 3600)}h ago`;
    return `${Math.round(s / 86400)}d ago`;
  }

  let toastTimer;
  function toast(msg) {
    const t = $("fy-toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
  }

  function show(section) {
    for (const id of ["fy-gate", "fy-onboard", "fy-app"]) $(id).hidden = id !== section;
  }

  // ------------------------------------------------------------------ telemetry
  function track(kind, extra = {}) {
    state.queue.push({ kind, local_hour: localHour(), ...extra });
    if (["like", "dislike", "save", "hide", "mute_source", "less_topic", "more_topic", "share", "click"].includes(kind)) {
      flush();
    }
  }

  let profileTimer;
  async function flush(useKeepalive = false) {
    if (!state.queue.length || !state.user) return;
    const events = state.queue.splice(0, state.queue.length);
    try {
      await fetch("/api/events", {
        method: "POST",
        credentials: "same-origin",
        keepalive: useKeepalive,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events }),
      });
      clearTimeout(profileTimer);
      profileTimer = setTimeout(loadProfile, 900);
    } catch (_) {
      if (!useKeepalive) state.queue.unshift(...events); // retry on next tick
    }
  }
  setInterval(flush, 4000);
  window.addEventListener("pagehide", () => { settleDwell(); flush(true); });

  // Dwell: the reader opens the story in a new tab; time until they come back ≈ reading time.
  function settleDwell() {
    if (!state.pendingDwell) return;
    const secs = Math.min(900, (Date.now() - state.pendingDwell.start) / 1000);
    track("dwell", { article_id: state.pendingDwell.id, value: Math.round(secs) });
    state.pendingDwell = null;
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") settleDwell(); });
  window.addEventListener("focus", () => {
    // Ignore the focus event fired immediately after the click itself.
    if (state.pendingDwell && Date.now() - state.pendingDwell.start > 1500) settleDwell();
  });

  // Impressions: card must be ≥60% visible for a full second.
  const impressionTimers = new Map();
  const observer = new IntersectionObserver((entries) => {
    for (const e of entries) {
      const id = e.target.dataset.id;
      if (state.impressed.has(id) || state.tab !== "foryou" && state.tab !== "trending") continue;
      if (e.isIntersecting) {
        impressionTimers.set(id, setTimeout(() => {
          state.impressed.add(id);
          track("impression", { article_id: id });
          observer.unobserve(e.target);
        }, 1000));
      } else {
        clearTimeout(impressionTimers.get(id));
      }
    }
  }, { threshold: 0.6 });

  // ------------------------------------------------------------------ auth
  let authMode = "login";
  function setAuthMode(mode) {
    authMode = mode;
    document.querySelectorAll(".fy-auth-tab").forEach((b) => {
      const on = b.dataset.mode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on);
    });
    document.querySelectorAll(".fy-signup-only").forEach((el) => (el.hidden = mode !== "signup"));
    $("fy-auth-submit").textContent = mode === "signup" ? "Create account" : "Sign in";
    $("fy-auth-form").password.autocomplete = mode === "signup" ? "new-password" : "current-password";
    $("fy-auth-error").textContent = "";
  }

  async function submitAuth(e) {
    e.preventDefault();
    const f = e.target;
    const btn = $("fy-auth-submit");
    btn.disabled = true;
    $("fy-auth-error").textContent = "";
    try {
      const { user } = await api(`/api/auth/${authMode}`, {
        username: f.username.value.trim(),
        password: f.password.value,
        display_name: f.display_name.value.trim(),
      });
      f.password.value = "";
      await enter(user);
    } catch (err) {
      $("fy-auth-error").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  }

  async function logout() {
    await flush();
    await api("/api/auth/logout", {});
    state.user = null;
    $("fy-user-chip").hidden = true;
    window.location.href = "about.html";
  }

  // ------------------------------------------------------------------ onboarding
  function renderOnboarding(topics) {
    const chosen = new Set();
    const grid = $("fy-topic-grid");
    grid.innerHTML = topics.map((t) => `
      <button type="button" class="fy-topic-pick" data-topic="${esc(t)}" aria-pressed="false">
        <span class="fy-topic-icon">${TOPIC_ICONS[t] || "•"}</span>${esc(t)}
      </button>`).join("");
    grid.onclick = (e) => {
      const b = e.target.closest(".fy-topic-pick");
      if (!b) return;
      const t = b.dataset.topic;
      chosen.has(t) ? chosen.delete(t) : chosen.add(t);
      b.setAttribute("aria-pressed", chosen.has(t));
      const go = $("fy-onboard-go");
      go.disabled = chosen.size < 3;
      go.textContent = chosen.size < 3 ? `Pick ${3 - chosen.size} more` : "Build my front page →";
    };
    $("fy-onboard-go").textContent = "Pick 3 more";
    $("fy-onboard-go").onclick = async () => {
      await api("/api/onboard", { topics: [...chosen] });
      state.user.onboarded = 1;
      startApp();
    };
  }

  // ------------------------------------------------------------------ feed
  function cardHTML(a) {
    const topics = a.topics.slice(0, 2).map((t) => `<button type="button" class="fy-chip" data-act="filter" data-topic="${esc(t)}">${esc(t)}</button>`).join("");
    const img = a.image_url ? `<a class="fy-card-img" href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" data-act="open" tabindex="-1"><img src="${esc(a.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.remove()"></a>` : "";
    const primary = a.topics[0] || "";
    return `
      <article class="fy-card${a.image_url ? " has-img" : ""}" data-id="${esc(a.id)}" data-publisher="${esc(a.publisher)}" data-topic="${esc(primary)}">
        ${img}
        <div class="fy-card-body">
          <div class="fy-card-meta">
            <span class="fy-pub">${esc(a.publisher)}</span><span>·</span><span>${timeAgo(a.published_at)}</span><span>·</span><span>${a.read_minutes} min</span>
            ${a.is_demo ? '<span class="fy-demo-tag">DEMO</span>' : ""}
          </div>
          <h2 class="fy-card-title"><a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" data-act="open">${esc(a.title)}</a></h2>
          ${a.summary ? `<p class="fy-card-summary">${esc(a.summary)}</p>` : ""}
          <div class="fy-why fy-why--${esc(a.why.type)}"><span aria-hidden="true">✦</span> ${esc(a.why.text)}</div>
          <div class="fy-card-foot">
            <div class="fy-chips">${topics}</div>
            <div class="fy-actions">
              <button type="button" class="fy-act${a.state.reaction > 0 ? " on" : ""}" data-act="like" title="More like this" aria-label="More like this">♥</button>
              <button type="button" class="fy-act" data-act="dislike" title="Not for me" aria-label="Not for me">✕</button>
              <button type="button" class="fy-act${a.state.saved ? " on" : ""}" data-act="save" title="Save for later" aria-label="Save">${a.state.saved ? "★" : "☆"}</button>
              <button type="button" class="fy-act" data-act="share" title="Copy link" aria-label="Share">↗</button>
              <div class="fy-menu-wrap">
                <button type="button" class="fy-act" data-act="menu" aria-haspopup="true" aria-label="More options">⋯</button>
                <div class="fy-menu" hidden>
                  <button type="button" data-act="hide">Hide this story</button>
                  ${primary ? `<button type="button" data-act="more_topic">More ${esc(primary)}</button>
                  <button type="button" data-act="less_topic">Less ${esc(primary)}</button>` : ""}
                  <button type="button" data-act="mute_source">Mute ${esc(a.publisher)}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </article>`;
  }

  async function loadFeed(reset = true) {
    if (state.loading) return;
    if (reset) {
      state.shown.clear();
      state.exhausted = false;
      $("fy-feed").innerHTML = "";
      $("fy-feed-status").innerHTML = '<span class="fy-spinner"></span> Ranking stories for you…';
    }
    if (state.exhausted) return;
    state.loading = true;
    const params = new URLSearchParams({ tab: state.tab, hour: localHour(), limit: 24 });
    if (state.topic && state.tab === "foryou") params.set("topic", state.topic);
    if (state.tab === "search") params.set("q", state.query);
    if (state.shown.size && ["foryou", "trending"].includes(state.tab)) params.set("exclude", [...state.shown].join(","));
    try {
      const { items } = await api(`/api/feed?${params}`);
      const feed = $("fy-feed");
      const frag = document.createElement("div");
      frag.innerHTML = items.map(cardHTML).join("");
      [...frag.children].forEach((el, i) => {
        el.style.animationDelay = `${Math.min(i, 8) * 35}ms`;
        feed.appendChild(el);
        observer.observe(el);
      });
      items.forEach((a) => state.shown.add(a.id));
      $("fy-demo-banner").hidden = !items.some((a) => a.is_demo);
      const paged = ["foryou", "trending"].includes(state.tab);
      state.exhausted = !paged || items.length < 24;
      $("fy-more").hidden = state.exhausted;
      $("fy-feed-status").textContent = !feed.children.length
        ? emptyMessage()
        : state.exhausted && paged ? "You're all caught up. Check back soon for fresh stories." : "";
    } catch (err) {
      if (err.status === 401) return boot();
      $("fy-feed-status").textContent = `Couldn't load the feed: ${err.message}`;
    } finally {
      state.loading = false;
    }
  }

  function emptyMessage() {
    return {
      saved: "Nothing saved yet. Tap ☆ on any story to keep it here.",
      history: "Your reading history will appear here.",
      search: `No stories match “${state.query}”.`,
    }[state.tab] || "No stories yet. The server is still fetching the news. Try again in a minute.";
  }

  function removeCard(card, msg) {
    card.classList.add("fy-card--leaving");
    setTimeout(() => card.remove(), 320);
    if (msg) toast(msg);
  }

  function onFeedClick(e) {
    const el = e.target.closest("[data-act]");
    const card = e.target.closest(".fy-card");
    if (!el || !card) return;
    const id = card.dataset.id;
    const act = el.dataset.act;
    const topic = card.dataset.topic;
    const publisher = card.dataset.publisher;

    switch (act) {
      case "open":
        track("click", { article_id: id });
        state.pendingDwell = { id, start: Date.now() };
        card.classList.add("fy-card--read");
        return; // let the link open normally
      case "like": {
        const on = !el.classList.contains("on");
        el.classList.toggle("on", on);
        if (on) { track("like", { article_id: id }); toast("Noted. More stories like this."); }
        return;
      }
      case "dislike":
        track("dislike", { article_id: id });
        return removeCard(card, "Got it. Fewer stories like this.");
      case "save": {
        const on = !el.classList.contains("on");
        el.classList.toggle("on", on);
        el.textContent = on ? "★" : "☆";
        track(on ? "save" : "unsave", { article_id: id });
        toast(on ? "Saved for later" : "Removed from saved");
        if (!on && state.tab === "saved") removeCard(card);
        return;
      }
      case "share": {
        const url = card.querySelector(".fy-card-title a").href;
        const done = () => { track("share", { article_id: id }); toast("Link copied"); };
        if (navigator.share) navigator.share({ url }).then(done).catch(() => {});
        else navigator.clipboard?.writeText(url).then(done, () => toast(url));
        return;
      }
      case "menu": {
        const m = el.nextElementSibling;
        document.querySelectorAll(".fy-menu").forEach((x) => { if (x !== m) x.hidden = true; });
        m.hidden = !m.hidden;
        return;
      }
      case "hide":
        track("hide", { article_id: id });
        return removeCard(card, "Story hidden");
      case "more_topic":
        track("more_topic", { topic });
        el.closest(".fy-menu").hidden = true;
        return toast(`You'll see more ${topic}`);
      case "less_topic":
        track("less_topic", { topic });
        document.querySelectorAll(`.fy-card[data-topic="${CSS.escape(topic)}"]`).forEach((c) => removeCard(c));
        return toast(`You'll see less ${topic}`);
      case "mute_source":
        track("mute_source", { publisher });
        document.querySelectorAll(".fy-card").forEach((c) => { if (c.dataset.publisher === publisher) removeCard(c); });
        return toast(`Muted ${publisher}`);
      case "filter":
        return setTopic(el.dataset.topic);
    }
  }

  function setTab(tab) {
    state.tab = tab;
    document.querySelectorAll(".fy-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    $("fy-topic-filter").hidden = tab !== "foryou";
    if (tab !== "search") $("fy-search-input").value = "";
    loadFeed(true);
  }

  function setTopic(topic) {
    state.topic = state.topic === topic ? null : topic;
    if (state.tab !== "foryou") { state.tab = "foryou"; document.querySelectorAll(".fy-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === "foryou")); }
    renderTopicFilter();
    loadFeed(true);
  }

  function renderTopicFilter() {
    const el = $("fy-topic-filter");
    el.hidden = state.tab !== "foryou";
    el.innerHTML = `<button type="button" class="fy-filter${state.topic ? "" : " active"}" data-topic="">All</button>` +
      state.allTopics.map((t) => `<button type="button" class="fy-filter${state.topic === t ? " active" : ""}" data-topic="${esc(t)}">${esc(t)}</button>`).join("");
  }

  // ------------------------------------------------------------------ taste DNA
  async function loadProfile() {
    if (!state.user) return;
    let p;
    try { p = await api("/api/profile"); } catch (_) { return; }
    state.allTopics = p.all_topics;
    if (!$("fy-topic-filter").children.length) renderTopicFilter();

    const pct = Math.round(p.stats.confidence * 100);
    $("fy-confidence").textContent = `${pct}%`;
    $("fy-meter-fill").style.width = `${pct}%`;

    $("fy-dna-stats").innerHTML = [
      ["Stories read", p.stats.reads], ["Minutes reading", p.stats.minutes_read],
      ["Saved", p.stats.saved], ["Signals learned", p.stats.events],
    ].map(([k, v]) => `<div><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("");

    const max = Math.max(1, ...p.topics.map((t) => t.weight));
    $("fy-dna-topics").innerHTML = p.topics.length
      ? p.topics.slice(0, 8).map((t) => `
          <div class="fy-bar"><span>${TOPIC_ICONS[t.key] || "•"} ${esc(t.key)}</span>
            <i style="--w:${Math.round((t.weight / max) * 100)}%"></i></div>`).join("") +
        (p.avoided_topics.length ? `<div class="fy-avoid">Avoiding: ${p.avoided_topics.map((t) => esc(t.key)).join(", ")}</div>` : "")
      : '<p class="fy-dna-empty">Start reading and your topics will show up here.</p>';

    const cloud = (items, empty) => items.length
      ? items.map((k, i) => `<span class="fy-tag" style="--s:${(1 - i / (items.length + 2)).toFixed(2)}">${esc(k.label ?? k.key)}</span>`).join("")
      : `<p class="fy-dna-empty">${empty}</p>`;
    $("fy-dna-keywords").innerHTML = cloud(p.keywords, "Keywords from stories you read and like.");
    $("fy-dna-entities").innerHTML = cloud(p.entities, "People and companies you follow.");
    $("fy-dna-sources").innerHTML = cloud(p.sources, "Publishers you keep coming back to.");

    const parts = ["morning", "afternoon", "evening", "night"];
    $("fy-dna-rhythm").innerHTML = parts.map((part) => {
      const tops = Object.keys(p.dayparts[part] || {});
      return `<div class="fy-rhythm-row"><span>${part}</span><b>${tops.length ? tops.map(esc).join(" · ") : "—"}</b></div>`;
    }).join("");

    $("fy-dna-muted-wrap").hidden = !p.muted_sources.length;
    $("fy-dna-muted").innerHTML = p.muted_sources.map((s) =>
      `<button type="button" class="fy-tag fy-unmute" data-publisher="${esc(s)}" title="Unmute">${esc(s)} ✕</button>`).join("");
  }

  // ------------------------------------------------------------------ boot
  function greeting(name) {
    const h = localHour();
    const part = h < 5 ? "Up late" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
    return `${part}, <em>${esc(name)}</em>`;
  }

  function startApp() {
    show("fy-app");
    $("fy-date").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }).toUpperCase();
    $("fy-greeting").innerHTML = greeting(state.user.display_name || state.user.username);
    loadProfile().then(() => setTab("foryou"));
  }

  async function enter(user) {
    state.user = user;
    $("fy-user-chip").hidden = false;
    $("fy-username").textContent = user.display_name || user.username;
    $("fy-avatar").textContent = (user.display_name || user.username || "?").charAt(0).toUpperCase();
    if (!user.onboarded) {
      const { all_topics } = await api("/api/profile");
      renderOnboarding(all_topics);
      show("fy-onboard");
    } else {
      startApp();
    }
  }

  async function boot() {
    try {
      const { user } = await api("/api/me");
      if (user) return enter(user);
    } catch (_) { /* server offline: fall through to gate */ }
    show("fy-gate");
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".fy-auth-tab").forEach((b) => b.addEventListener("click", () => setAuthMode(b.dataset.mode)));
    $("fy-auth-form").addEventListener("submit", submitAuth);
    $("fy-logout").addEventListener("click", logout);
    $("fy-feed").addEventListener("click", onFeedClick);
    $("fy-feed").addEventListener("auxclick", (e) => { if (e.button === 1) onFeedClick(e); });
    document.querySelectorAll(".fy-tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
    $("fy-topic-filter").addEventListener("click", (e) => {
      const b = e.target.closest(".fy-filter");
      if (b) setTopic(b.dataset.topic || state.topic);
    });
    $("fy-more").addEventListener("click", () => loadFeed(false));
    $("fy-search").addEventListener("submit", (e) => {
      e.preventDefault();
      const q = $("fy-search-input").value.trim();
      if (!q) return setTab("foryou");
      state.query = q;
      track("search", { query: q });
      document.querySelectorAll(".fy-tab").forEach((b) => b.classList.remove("active"));
      state.tab = "search";
      $("fy-topic-filter").hidden = true;
      loadFeed(true);
    });
    $("fy-dna").addEventListener("click", async (e) => {
      const un = e.target.closest(".fy-unmute");
      if (un) { track("unmute_source", { publisher: un.dataset.publisher }); await flush(); loadProfile(); toast(`Unmuted ${un.dataset.publisher}`); }
    });
    $("fy-reset").addEventListener("click", async () => {
      if (!confirm("Erase everything your feed has learned about you? This can't be undone.")) return;
      await api("/api/profile/reset", {});
      state.user.onboarded = 0;
      enter(state.user);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".fy-menu-wrap")) document.querySelectorAll(".fy-menu").forEach((m) => (m.hidden = true));
    });
    // Infinite scroll
    new IntersectionObserver((ents) => {
      if (ents[0].isIntersecting && !$("fy-more").hidden) loadFeed(false);
    }, { rootMargin: "600px" }).observe($("fy-more"));

    boot();
  });
})();
