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
    your5: null,
    profile: null,
    freshFollows: 0,
    budget: Number(safeLocal("pith_fy_budget")) || 0,
  };

  function safeLocal(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, String(value));
    } catch (_) { /* private mode: the default is fine */ }
    return null;
  }

  const PROVIDER_ICONS = {
    google: '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>',
    github: '<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>',
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18.24 2.25h3.31l-7.23 8.26 8.5 11.24h-6.66l-5.21-6.82-5.97 6.82H1.68l7.73-8.84L1.25 2.25h6.83l4.71 6.23zm-1.16 17.52h1.83L7.08 4.13H5.12z"/></svg>',
    linkedin: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#0A66C2" d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 110-4.13 2.06 2.06 0 010 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>',
  };
  const PROVIDER_NAMES = { google: "Google", github: "GitHub", x: "X", linkedin: "LinkedIn" };
  const oauthStart = (id, link) => `/api/auth/oauth/${id}/start?next=${encodeURIComponent("/foryou")}${link ? "&link=1" : ""}`;

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
    if (["like", "dislike", "save", "hide", "mute_source", "less_topic", "more_topic", "share", "click",
         "worth_time", "not_worth_time", "clear_worth"].includes(kind)) {
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

  async function setupSocial() {
    let providers = [];
    try { ({ providers } = await api("/api/auth/providers")); } catch (_) { providers = []; }
    const on = new Set(providers.filter((p) => p.configured).map((p) => p.id));
    document.querySelectorAll("#fy-social .social-btn").forEach((a) => {
      const ok = on.has(a.dataset.provider);
      a.classList.toggle("is-disabled", !ok);
      a.setAttribute("aria-disabled", String(!ok));
      a.title = ok ? "" : "Not set up on this server yet";
    });
    const note = $("fy-social-note");
    note.hidden = on.size > 0;
    note.textContent = "Google, GitHub, X and LinkedIn sign-in switch on once this server has their OAuth keys. Use a username for now.";
  }

  function readUrlMessages() {
    const params = new URLSearchParams(location.search);
    const err = params.get("auth_error");
    const connected = params.get("connected");
    if (err) { $("fy-oauth-error").textContent = err; $("fy-oauth-error").hidden = false; }
    if (err || connected) history.replaceState(null, "", location.pathname);
    return connected;
  }

  async function logout() {
    await flush();
    await api("/api/auth/logout", {});
    state.user = null;
    $("fy-user-chip").hidden = true;
    stopAudio();
    window.location.href = "foryou.html";
  }

  // ------------------------------------------------------------------ onboarding
  // Step 1: "which would you rather read?" between real headlines. Step 2: optional topics.
  async function startOnboarding(topics, imported = []) {
    const choices = [];
    let pairs = [];
    try { ({ pairs } = await api("/api/onboard/pairs")); } catch (_) { pairs = []; }
    show("fy-onboard");
    if (!pairs.length) return renderTopics(topics, choices, imported);
    $("fy-onboard-pairs").hidden = false;
    $("fy-onboard-topics").hidden = true;
    let i = 0;
    const next = () => {
      if (i >= pairs.length) return renderTopics(topics, choices, imported);
      $("fy-pair-progress").textContent = `${i + 1} OF ${pairs.length}`;
      $("fy-pair").innerHTML = pairs[i].map((a) => `
        <button type="button" class="fy-pair-option" data-id="${esc(a.id)}">
          ${a.image_url ? `<span class="fy-pair-img"><img src="${esc(a.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.remove()"></span>` : ""}
          <span class="fy-pair-topic">${TOPIC_ICONS[a.topic] || "•"} ${esc(a.topic)} · ${esc(a.publisher)}</span>
          <span class="fy-pair-title">${esc(a.title)}</span>
          ${a.summary ? `<span class="fy-pair-summary">${esc(a.summary)}</span>` : ""}
        </button>`).join("");
    };
    $("fy-pair").onclick = (e) => {
      const b = e.target.closest(".fy-pair-option");
      if (!b) return;
      const other = pairs[i].find((a) => a.id !== b.dataset.id);
      choices.push({ chosen: b.dataset.id, rejected: other ? other.id : null });
      i += 1;
      next();
    };
    $("fy-pair-skip").onclick = () => { i += 1; next(); };
    next();
  }

  function renderTopics(topics, choices, imported = []) {
    $("fy-onboard-pairs").hidden = true;
    $("fy-onboard-topics").hidden = false;
    const fromAccounts = imported.filter((t) => topics.includes(t));
    const needed = choices.length >= 3 || fromAccounts.length >= 2 ? 0 : 3;
    $("fy-topics-step").textContent = choices.length ? "STEP 2 OF 2" : "ONE STEP";
    $("fy-topics-title").innerHTML = needed ? "What do you <em>actually</em> read?" : "Anything you <em>always</em> want?";
    $("fy-topics-lede").textContent = fromAccounts.length
      ? `We've already picked ${fromAccounts.join(", ")} from your connected account. Add or remove anything, then build your page.`
      : needed
        ? "Pick at least three topics. This only seeds your feed. Your reading habits take over within a few sessions."
        : "Optional. Add topics on top of your picks, or go straight to your front page.";
    const chosen = new Set(fromAccounts);
    const grid = $("fy-topic-grid");
    const go = $("fy-onboard-go");
    const refresh = () => {
      const left = Math.max(0, needed - chosen.size);
      go.disabled = left > 0;
      go.textContent = left ? `Pick ${left} more` : "Build my front page →";
    };
    grid.innerHTML = topics.map((t) => `
      <button type="button" class="fy-topic-pick" data-topic="${esc(t)}" aria-pressed="${chosen.has(t)}">
        <span class="fy-topic-icon">${TOPIC_ICONS[t] || "•"}</span>${esc(t)}
      </button>`).join("");
    grid.onclick = (e) => {
      const b = e.target.closest(".fy-topic-pick");
      if (!b) return;
      const t = b.dataset.topic;
      chosen.has(t) ? chosen.delete(t) : chosen.add(t);
      b.setAttribute("aria-pressed", chosen.has(t));
      refresh();
    };
    refresh();
    go.onclick = async () => {
      go.disabled = true;
      await api("/api/onboard", { topics: [...chosen], choices });
      state.user.onboarded = 1;
      startApp();
    };
  }

  // ------------------------------------------------------------------ feed
  function cardHTML(a) {
    const topics = a.topics.slice(0, 2).map((t) => `<button type="button" class="fy-chip" data-act="filter" data-topic="${esc(t)}">${esc(t)}</button>`).join("") +
      (a.entities || []).slice(0, 2).map((e) => `<button type="button" class="fy-chip fy-chip--entity${isFollowing("entity", e) ? " on" : ""}" data-act="follow_entity" data-entity="${esc(e)}" title="Follow ${esc(e)}">${isFollowing("entity", e) ? "✓" : "+"} ${esc(e)}</button>`).join("");
    const img = a.image_url ? `<a class="fy-card-img" href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" data-act="open" tabindex="-1"><img src="${esc(a.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.remove()"></a>` : "";
    const primary = a.topics[0] || "";
    return `
      <article class="fy-card${a.image_url ? " has-img" : ""}" data-id="${esc(a.id)}" data-publisher="${esc(a.publisher)}" data-topic="${esc(primary)}" data-minutes="${esc(a.read_minutes)}">
        ${img}
        <div class="fy-card-body">
          <div class="fy-card-meta">
            <span class="fy-pub">${esc(a.publisher)}</span><span>·</span><span>${timeAgo(a.published_at)}</span><span>·</span><span>${a.read_minutes} min</span>
            ${a.source_count > 1 ? `<span class="fy-source-pill" title="Corroborated across ${esc(a.sources.join(', '))}">✦ ${a.source_count} sources: ${esc(a.sources.slice(0, 2).join(", "))}${a.sources.length > 2 ? ` +${a.sources.length - 2}` : ""}</span>` : ""}
            ${a.is_demo ? '<span class="fy-demo-tag">DEMO</span>' : ""}
          </div>
          <h2 class="fy-card-title"><a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer" data-act="open">${esc(a.title)}</a></h2>
          ${a.summary ? `<p class="fy-card-summary">${esc(a.summary)}</p>` : ""}
          <div class="fy-why fy-why--${esc(a.why.type)}"><span aria-hidden="true">✦</span> ${esc(a.why.text)}${a.is_new ? ' <span class="fy-new-pill">NEW</span>' : ""}</div>
          <div class="fy-card-foot">
            <div class="fy-chips">
              ${topics}
              <button type="button" class="fy-worth-btn${a.state.reaction > 0 ? " on" : ""}" data-act="worth_time" title="Rate this shift as worth your time">✦ Worth my time</button>
            </div>
            <div class="fy-actions">
              <button type="button" class="fy-act${a.state.reaction > 0 ? " on" : ""}" data-act="like" title="More like this" aria-label="More like this">♥</button>
              <button type="button" class="fy-act" data-act="dislike" title="Not for me" aria-label="Not for me">✕</button>
              <button type="button" class="fy-act${a.state.saved ? " on" : ""}" data-act="save" title="Save for later" aria-label="Save">${a.state.saved ? "★" : "☆"}</button>
              <button type="button" class="fy-act" data-act="share" title="Copy link" aria-label="Share">↗</button>
              <div class="fy-menu-wrap">
                <button type="button" class="fy-act" data-act="menu" aria-haspopup="true" aria-label="More options">⋯</button>
                <div class="fy-menu" hidden>
                  <button type="button" data-act="follow_story">${isFollowing("story", a.id) ? "Following this story" : "Follow this story"}</button>
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
      applyBudget();
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
      following: "Nothing new on what you follow. Follow a story from its ⋯ menu, tap + on a name, or add a phrase in the sidebar.",
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
      case "worth_time": {
        const on = !el.classList.contains("on");
        el.classList.toggle("on", on);
        // Switching it off undoes the rating; it is not a "not worth it" vote.
        track(on ? "worth_time" : "clear_worth", { article_id: id });
        toast(on ? "Noted: worth your time." : "Rating removed.");
        return;
      }
      case "follow_entity":
        return toggleFollow("entity", el.dataset.entity, el.dataset.entity);
      case "follow_story":
        el.closest(".fy-menu").hidden = true;
        return toggleFollow("story", id, card.querySelector(".fy-card-title a").textContent, id);
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

  // ------------------------------------------------------------------ reading-time budget
  // "I have 15 minutes": keep the ranked order, but show only what fits.
  function applyBudget() {
    const active = state.budget > 0 && state.tab === "foryou";
    let used = 0, shown = 0, over = 0;
    document.querySelectorAll("#fy-feed .fy-card").forEach((c) => {
      const m = Number(c.dataset.minutes) || 2;
      const fits = !active || used + m <= state.budget || shown === 0;
      if (active && fits) { used += m; shown += 1; }
      if (active && !fits) over += 1;
      c.classList.toggle("fy-card--over", active && !fits);
    });
    const note = $("fy-budget-note");
    note.hidden = !active;
    if (active) {
      note.innerHTML = `<span><b>${shown} ${shown === 1 ? "story" : "stories"}</b> · about ${used} min, picked to fit your ${state.budget} minutes${over ? `. ${over} more held back.` : "."}</span>
        <button type="button" class="fy-link-btn" data-budget-clear>Show everything</button>`;
    }
    $("fy-more").hidden = active || state.exhausted;
    document.querySelectorAll("#fy-budget .seg-btn").forEach((b) => b.classList.toggle("active", Number(b.dataset.budget) === state.budget));
  }

  function setBudget(minutes) {
    state.budget = minutes;
    safeLocal("pith_fy_budget", minutes);
    if (state.tab !== "foryou") return setTab("foryou");
    applyBudget();
  }

  function setTab(tab) {
    state.tab = tab;
    document.querySelectorAll(".fy-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
    $("fy-topic-filter").hidden = tab !== "foryou";
    if (tab !== "search") $("fy-search-input").value = "";
    syncYour5Visibility();
    loadFeed(true);
    if (tab === "following") {
      api("/api/follows", { action: "seen" }).catch(() => {});
      $("fy-follow-badge").hidden = true;
    }
  }

  function setTopic(topic) {
    state.topic = state.topic === topic ? null : topic;
    if (state.tab !== "foryou") { state.tab = "foryou"; document.querySelectorAll(".fy-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === "foryou")); }
    renderTopicFilter();
    syncYour5Visibility();
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

    let roleEl = $("fy-inferred-role-card");
    if (!roleEl) {
      roleEl = document.createElement("div");
      roleEl.id = "fy-inferred-role-card";
      roleEl.className = "fy-inferred-role-box";
      const dnaHead = document.querySelector(".fy-dna-head");
      if (dnaHead) dnaHead.after(roleEl);
    }
    if (p.inferred_role) {
      roleEl.innerHTML = `
        <div class="fy-role-badge-row">
          <span class="fy-role-title">INFERRED LENS</span>
          <span class="fy-role-pill">✦ ${esc(p.inferred_role.toUpperCase())} (${Math.round((p.role_confidence || 0.75) * 100)}%)</span>
        </div>
        <p class="fy-role-reason">${esc(p.role_reason || "")}</p>
      `;
    }

    $("fy-dna-stats").innerHTML = [
      ["Stories read", p.stats.reads], ["Minutes reading", p.stats.minutes_read],
      ["Saved", p.stats.saved], ["Signals learned", p.stats.events],
    ].map(([k, v]) => `<div><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("");

    try {
      const d = await api("/api/digest");
      if (d && d.summary_text) {
        let digestEl = $("fy-weekly-digest");
        if (!digestEl) {
          digestEl = document.createElement("div");
          digestEl.id = "fy-weekly-digest";
          digestEl.className = "fy-weekly-digest-box";
          $("fy-dna-stats").after(digestEl);
        }
        digestEl.innerHTML = `
          <div class="fy-digest-head">✦ WEEKLY SATISFACTION DIGEST</div>
          <p class="fy-digest-body">${esc(d.summary_text)}</p>
        `;
      }
    } catch (_) {}

    const max = Math.max(1, ...p.topics.map((t) => t.weight));
    const steer = (t) => `<span class="fy-steer"><button type="button" data-steer="less_topic" data-topic="${esc(t)}" aria-label="Less ${esc(t)}" title="Less ${esc(t)}">−</button><button type="button" data-steer="more_topic" data-topic="${esc(t)}" aria-label="More ${esc(t)}" title="More ${esc(t)}">+</button></span>`;
    $("fy-dna-topics").innerHTML = p.topics.length
      ? p.topics.slice(0, 8).map((t) => `
          <div class="fy-bar"><span>${TOPIC_ICONS[t.key] || "•"} ${esc(t.key)}</span>
            <i style="--w:${Math.round((t.weight / max) * 100)}%"></i>${steer(t.key)}</div>`).join("") +
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

    state.profile = p;
    renderConnections(p.connections);
    renderSummary();
    renderFollows(p.follows || []);
    renderFeeds(p.feeds || []);
    renderSettings(p);
    loadForecasts();

    $("fy-dna-muted-wrap").hidden = !p.muted_sources.length;
    $("fy-dna-muted").innerHTML = p.muted_sources.map((s) =>
      `<button type="button" class="fy-tag fy-unmute" data-publisher="${esc(s)}" title="Unmute">${esc(s)} ✕</button>`).join("");
  }

  // ------------------------------------------------------------------ connected accounts
  const REGION_NAME = (r) => ({ global: "Everywhere", americas: "The Americas", europe: "Europe", uk: "UK", india: "India",
    asia: "Asia", africa: "Africa", "middle-east": "Middle East" }[r] || r);

  function renderConnections(c) {
    const el = $("fy-connections");
    if (!c) { el.innerHTML = ""; return; }
    const rows = c.accounts.map((a) => {
      const imp = a.imported;
      const chips = imp ? [...(imp.topics || []), ...(imp.entities || []).slice(0, 4), ...(imp.keywords || []).slice(0, 5)] : [];
      return `
        <div class="fy-conn" data-provider="${esc(a.provider)}">
          <div class="fy-conn-head">
            <span class="fy-conn-icon">${PROVIDER_ICONS[a.provider] || ""}</span>
            <div class="fy-conn-who"><b>${esc(a.name)}</b><span>${a.handle ? "@" + esc(a.handle) : esc(a.display_name || "Connected")}</span></div>
          </div>
          ${imp ? `
            <div class="fy-cloud fy-conn-chips">${chips.length ? chips.map((x) => `<span class="fy-tag">${esc(x)}</span>`).join("") : '<span class="fy-dna-empty">No interests to import from this account.</span>'}</div>
            ${imp.region && imp.region_applied ? `<p class="fy-conn-note">More news from ${esc(REGION_NAME(imp.region))}, from your account's location.</p>` : ""}
            ${(imp.evidence || []).length ? `<p class="fy-conn-note">Read from: ${esc(imp.evidence.join(" · "))}.</p>` : ""}
            ${(imp.notes || []).map((n) => `<p class="fy-conn-note fy-conn-note--warn">${esc(n)}</p>`).join("")}`
          : '<p class="fy-conn-note">Imported interests removed. Your reading still teaches the feed.</p>'}
          <div class="fy-conn-actions">
            ${imp ? '<button type="button" class="fy-link-btn" data-conn="forget">Remove imported interests</button>' : ""}
            ${a.can_disconnect ? '<button type="button" class="fy-link-btn" data-conn="disconnect">Disconnect</button>' : ""}
          </div>
        </div>`;
    }).join("");
    const add = c.available.map((p) => `<a class="social-btn social-btn--compact" href="${oauthStart(p.id, true)}"><span class="social-icon">${PROVIDER_ICONS[p.id] || ""}</span><span>Connect ${esc(p.name)}</span></a>`).join("");
    el.innerHTML = (rows || '<p class="fy-dna-empty">Connect an account and your feed starts from your interests. We read it once and keep only the interests.</p>') +
      (add ? `<div class="fy-conn-add">${add}</div>` : "");
  }

  async function connectionAction(provider, action) {
    const name = PROVIDER_NAMES[provider] || provider;
    if (action === "disconnect" && !confirm(`Disconnect ${name}? Its imported interests are removed too.`)) return;
    try {
      await api("/api/connections", { action, provider });
      toast(action === "disconnect" ? `${name} disconnected` : `Removed what ${name} added`);
      await loadProfile();
      loadYour5();
      if (state.tab === "foryou") loadFeed(true);
    } catch (err) { toast(err.message); }
  }

  // ------------------------------------------------------------------ the line under the greeting
  function renderSummary() {
    const el = $("fy-summary");
    const p = state.profile;
    if (!el || !p) return;
    const parts = [];
    const top = (p.topics || [])[0];
    const cards = (state.your5 && state.your5.cards) || [];
    if (top && cards.length) {
      const n = cards.filter((c) => (c.topics || []).includes(top.key)).length;
      parts.push(n ? `<span><b>${n} of your 5</b> ${n === 1 ? "is" : "are"} on ${esc(top.key)}, what you read most</span>`
                   : `<span>Today's 5 reach past ${esc(top.key)}, your usual</span>`);
    } else if (cards.length) {
      parts.push(`<span>Your 5 is ready through the <b>${esc(state.your5.inferred_role)}</b> lens</span>`);
    }
    if (state.freshFollows) {
      parts.push(`<button type="button" class="fy-summary-link" data-summary="following">${state.freshFollows} new on what you follow</button>`);
    }
    const accounts = (p.connections && p.connections.accounts) || [];
    if (accounts.length && p.stats.reads < 5) {
      parts.push(`<span>Started from your ${esc(accounts.map((a) => a.name).join(" and "))}</span>`);
    } else if (p.stats.events) {
      parts.push(`<span>Tuned by ${p.stats.events} signal${p.stats.events === 1 ? "" : "s"}</span>`);
    }
    el.innerHTML = parts.join('<span class="fy-summary-sep" aria-hidden="true">·</span>');
  }

  // ------------------------------------------------------------------ follows
  function isFollowing(kind, key) {
    const list = (state.profile && state.profile.follows) || [];
    const k = kind === "story" ? key : String(key || "").toLowerCase().trim();
    return list.some((f) => f.kind === kind && f.key === k);
  }

  async function toggleFollow(kind, key, label, articleId) {
    const on = isFollowing(kind, key);
    try {
      if (on) {
        await api("/api/follows", { action: "unfollow", kind, key });
        toast(`Unfollowed ${kind === "story" ? "this story" : label}`);
      } else {
        await api("/api/follows", { action: "follow", kind, key, label, article_id: articleId });
        toast(kind === "story" ? "Following this story. Updates land in the Following tab." : `Following ${label}`);
      }
    } catch (err) {
      return toast(err.message);
    }
    await loadProfile();
    if (kind === "entity") {
      document.querySelectorAll(".fy-chip--entity").forEach((c) => {
        if (c.dataset.entity !== label) return;
        const now = isFollowing("entity", label);
        c.classList.toggle("on", now);
        c.textContent = `${now ? "✓" : "+"} ${label}`;
      });
    }
  }

  function renderFollows(list) {
    $("fy-follow-list").innerHTML = list.length
      ? list.map((f) => `<button type="button" class="fy-tag fy-unfollow" data-kind="${esc(f.kind)}" data-key="${esc(f.key)}" title="Unfollow">${f.kind === "story" ? "Story: " : ""}${esc(f.label.length > 40 ? f.label.slice(0, 40) + "…" : f.label)} ✕</button>`).join("")
      : '<p class="fy-dna-empty">Follow a name from any card, a story from its ⋯ menu, or type a phrase below.</p>';
  }

  async function refreshFollowBadge() {
    try {
      const { updates } = await api("/api/follows");
      const fresh = updates.filter((u) => u.is_new).length;
      state.freshFollows = fresh;
      renderSummary();
      $("fy-follow-badge").textContent = fresh;
      $("fy-follow-badge").hidden = !fresh || state.tab === "following";
    } catch (_) { /* badge is optional */ }
  }

  // ------------------------------------------------------------------ reader feeds
  function renderFeeds(list) {
    $("fy-feed-list").innerHTML = list.length
      ? list.map((f) => `
          <div class="fy-feed-row">
            <div><b>${esc(f.title)}</b><span>${esc(f.url)}</span>${f.last_error ? `<em>Last fetch failed: ${esc(f.last_error)}</em>` : ""}</div>
            <button type="button" class="fy-link-btn fy-feed-remove" data-feed="${esc(f.feed_id)}" aria-label="Remove ${esc(f.title)}">✕</button>
          </div>`).join("")
      : '<p class="fy-dna-empty">Add any public RSS or Atom feed: a local paper, a newsletter, a blog. Only you see its stories.</p>';
  }

  // ------------------------------------------------------------------ settings
  const REGION_LABELS = { global: "Everywhere", americas: "The Americas", europe: "Europe", uk: "UK", india: "India",
    asia: "Asia", africa: "Africa", "middle-east": "Middle East" };
  const cap = (x) => x.charAt(0).toUpperCase() + x.slice(1);

  function renderSettings(p) {
    const prefs = p.prefs || {};
    const depth = p.depth || {};
    $("fy-pref-depth").innerHTML = (p.depths || []).map((d) => `<option value="${d}"${prefs.depth === d ? " selected" : ""}>${
      d === "auto" ? `Auto (${esc(depth.source === "inferred" ? depth.depth : "standard")})` : cap(d)}</option>`).join("");
    $("fy-depth-reason").textContent = depth.reason || "";
    $("fy-pref-region").innerHTML = (p.regions || []).map((r) =>
      `<option value="${r}"${prefs.region === r ? " selected" : ""}>${esc(REGION_LABELS[r] || r)}</option>`).join("");
    const hours = [`<option value=""${prefs.delivery_hour == null ? " selected" : ""}>Off</option>`];
    for (let h = 0; h < 24; h++) hours.push(`<option value="${h}"${prefs.delivery_hour === h ? " selected" : ""}>${String(h).padStart(2, "0")}:00</option>`);
    $("fy-pref-hour").innerHTML = hours.join("");
  }

  async function savePref(key, value) {
    try {
      await api("/api/prefs", { [key]: value });
      toast("Saved");
      await loadProfile();
      if (key === "depth") loadYour5();
      if (key === "region" && state.tab === "foryou") loadFeed(true);
    } catch (err) {
      toast(err.message);
    }
  }

  function syncTimezone() {
    const offset = -new Date().getTimezoneOffset();
    const current = state.profile && state.profile.prefs ? state.profile.prefs.tz_offset_minutes : null;
    if (current !== offset) api("/api/prefs", { tz_offset_minutes: offset }).catch(() => {});
  }

  // ------------------------------------------------------------------ personal forecast record
  async function loadForecasts() {
    const box = $("fy-forecast-box");
    let r;
    try { r = await api("/api/forecasts/me"); } catch (_) { box.innerHTML = ""; return; }
    const s = r.stats;
    const head = '<div class="fy-fc-head">YOUR FORECAST RECORD</div>';
    if (!r.calls.length) {
      box.innerHTML = `${head}<p class="fy-fc-note">Call Pith's forecasts on <a href="index.html">Daily News</a> (higher, agree or lower). When they resolve, you'll see whether you beat the brief.</p>`;
      return;
    }
    let body = "";
    if (s.scored) {
      const verdict = s.verdict === "ahead" ? "You're ahead of Pith." : s.verdict === "behind" ? "Pith is ahead of you." :
        s.verdict === "level" ? "You and Pith are level." : `Verdict after ${r.rules.min_scored_for_verdict} resolved calls.`;
      body += `<div class="fy-fc-big"><b>${s.beat}</b> of ${s.scored} resolved calls beat Pith</div>
        <div class="fy-fc-brier">Brier: you ${s.your_brier} · Pith ${s.pith_brier} <small>(lower is better)</small></div>
        <div class="fy-fc-verdict">${esc(verdict)}</div>`;
    } else {
      body += '<p class="fy-fc-note">None of your calls has resolved yet.</p>';
    }
    body += `<div class="fy-fc-meta">${s.open_calls} open call${s.open_calls === 1 ? "" : "s"}${s.late_calls ? ` · ${s.late_calls} late (not scored)` : ""}</div>`;
    if (r.newly_resolved.length) {
      body = `<div class="fy-fc-new"><div class="fy-fc-new-head">Resolved since your last visit</div>${r.newly_resolved.map((i) => `
        <div class="fy-fc-item"><span class="fy-fc-status fy-fc-status--${esc(i.status)}">${i.status === "correct" ? "✓ HAPPENED" : "✕ DIDN'T"}</span>
          ${esc(i.statement)} <em>${i.beat_pith ? "You beat Pith" : "Pith was closer"}</em></div>`).join("")}
        <button type="button" class="fy-mini-btn" id="fy-fc-seen">Got it</button></div>` + body;
    }
    body += `<p class="fy-fc-fine">Your probability is implied: Pith's, moved ${Math.round(r.rules.implied_shift * 100)} points the way you called it. Calls count if made within ${r.rules.call_window_days} days of publication.</p>`;
    box.innerHTML = head + body;
    const seen = $("fy-fc-seen");
    if (seen) seen.onclick = async () => { await api("/api/forecasts/seen", {}); loadForecasts(); };
  }

  // ------------------------------------------------------------------ Your 5
  function syncYour5Visibility() {
    $("fy-your5").hidden = !(state.tab === "foryou" && !state.topic && state.your5 && state.your5.cards && state.your5.cards.length);
  }

  async function loadYour5() {
    try {
      state.your5 = await api(`/api/your5?hour=${localHour()}`);
    } catch (_) {
      state.your5 = null;
    }
    renderYour5();
  }

  function your5ItemHTML(c, i, depth) {
    const open = depth === "deep" || (depth === "standard" && i === 0);
    const rv = c.role_view || {};
    const pred = c.prediction;
    const reaction = (c.user_state && c.user_state.reaction) || 0;
    const actionType = rv.action_type || c.action_type;
    const links = (c.evidence_links || []).slice(0, 3).map((l) =>
      `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" data-y5="open">${esc(l.publisher || l.title || "Source")}</a>`).join(" · ");
    return `
      <li class="fy-y5-item${open ? " open" : ""}" data-id="${esc(c.id)}">
        <button type="button" class="fy-y5-headline" data-y5="toggle" aria-expanded="${open}">
          <span class="fy-y5-num">${i + 1}</span><span class="fy-y5-text">${esc(c.headline)}</span><span class="fy-y5-caret" aria-hidden="true">▾</span>
        </button>
        <div class="fy-y5-why fy-y5-why--${esc(c.slot)}">✦ ${esc(c.why_chosen)}</div>
        <div class="fy-y5-body">
          <p class="fy-y5-what">${esc(c.what_happened)}</p>
          ${rv.impact ? `<p class="fy-y5-impact"><b>For you (${esc(c.inferred_role)}):</b> ${esc(rv.impact)}</p>` : ""}
          ${rv.action_text ? `<p class="fy-y5-action"><span class="fy-y5-tag fy-y5-tag--${esc(actionType)}">${esc(actionType)}</span> ${esc(rv.action_text)}</p>` : ""}
          <div class="fy-y5-deep">
            <p class="fy-y5-matters">${esc(c.why_it_matters)}</p>
            ${(c.second_order || []).length ? `<ul class="fy-y5-second">${c.second_order.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
          </div>
          ${pred ? `<div class="fy-y5-forecast"><b>${Math.round(pred.probability * 100)}%</b> ${esc(pred.statement)} <span>resolves ${esc(pred.resolves_at)} · <a href="index.html#${esc(c.id)}">call it</a></span></div>` : ""}
          ${links ? `<div class="fy-y5-links">Sources: ${links}</div>` : ""}
        </div>
        <div class="fy-y5-foot">
          <button type="button" class="fy-worth-btn${reaction > 0 ? " on" : ""}" data-y5="worth">✦ Worth my time</button>
          <button type="button" class="fy-worth-btn fy-worth-btn--no${reaction < 0 ? " on" : ""}" data-y5="notworth">Not worth it</button>
          <button type="button" class="fy-worth-btn" data-y5="follow">${isFollowing("story", c.id) ? "✓ Following" : "+ Follow story"}</button>
          <button type="button" class="fy-worth-btn fy-listen-btn" data-y5="listen-from" aria-label="Listen from this story">▶ Listen</button>
        </div>
      </li>`;
  }

  function renderYour5() {
    const el = $("fy-your5");
    const d = state.your5;
    stopAudio();
    if (!d || !d.cards || !d.cards.length) { el.innerHTML = ""; syncYour5Visibility(); return; }
    const depth = (d.depth && d.depth.depth) || "standard";
    el.className = `fy-your5 fy-your5--${depth}`;
    el.innerHTML = `
      <div class="fy-y5-head">
        <div>
          <div class="eyebrow"><span class="gilt-dot"></span> YOUR 5 · ${esc(d.date)}</div>
          <h2 class="fy-y5-title">Today's brief, picked for you</h2>
          <p class="fy-y5-sub">Chosen from ${d.pool_size} verified shift${d.pool_size === 1 ? "" : "s"} through the <b>${esc(d.inferred_role)}</b> lens.
            ${d.depth && d.depth.source === "inferred" ? esc(d.depth.reason) + "." : ""}</p>
        </div>
      </div>
      <div class="fy-player-host" id="fy-player-host"></div>
      <ol class="fy-y5-list">${d.cards.map((c, i) => your5ItemHTML(c, i, depth)).join("")}</ol>`;
    syncYour5Visibility();
    renderSummary();
    loadBrief();
  }

  // ------------------------------------------------------------------ the spoken brief
  // Chapters come from /api/your5/script. The device voice reads them one by one, so the player
  // can show progress and highlight the story being read. With the studio voice configured, the
  // server renders one MP3 and the chapters become seek points.
  const RATES = [1, 1.25, 1.5, 0.85];
  const audio = { data: null, mode: "speech", playing: false, paused: false, index: 0, frac: 0, rate: 1,
                  token: 0, el: null, preparing: false };

  const words = (t) => t.split(/\s+/).filter(Boolean).length;
  const fmtTime = (sec) => { sec = Math.max(0, Math.round(sec)); return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`; };

  async function loadBrief() {
    try { audio.data = await api(`/api/your5/script?hour=${localHour()}`); } catch (_) { audio.data = null; }
    renderPlayer();
  }

  function renderPlayer() {
    const host = $("fy-player-host");
    const d = audio.data;
    if (!host) return;
    if (!d || !d.segments || !d.segments.length) { host.innerHTML = ""; return; }
    const voice = d.studio_voice ? "Studio voice" : "Device voice";
    host.innerHTML = `
      <div class="fy-player" id="fy-player">
        <button type="button" class="fy-player-play" data-player="toggle" aria-label="Play your audio brief"><span class="fy-player-icon" aria-hidden="true">▶</span></button>
        <div class="fy-player-main">
          <div class="fy-player-top">
            <span class="fy-player-title">Your audio brief</span>
            <span class="fy-player-meta" id="fy-player-meta">${fmtTime(d.seconds)} · ${esc(d.depth)} · ${voice}</span>
          </div>
          <div class="fy-player-track" data-player="seek" id="fy-player-track" role="slider" tabindex="0" aria-label="Seek" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
            <i class="fy-player-fill" id="fy-player-fill"></i>
            ${d.chapters.slice(1).map((c) => `<span class="fy-player-tick" style="left:${(c.start * 100).toFixed(2)}%" title="${esc(c.label)}"></span>`).join("")}
          </div>
          <div class="fy-player-now" id="fy-player-now">${esc(d.segments.length)} chapters · ${esc(d.segments.filter((x) => x.kind === "story").length)} stories${d.segments.some((x) => x.kind === "follows") ? " · updates you follow" : ""}</div>
        </div>
        <button type="button" class="fy-player-btn" data-player="speed" aria-label="Playback speed">${audio.rate}×</button>
        <button type="button" class="fy-player-btn" data-player="transcript" aria-expanded="false">Transcript</button>
      </div>
      <ol class="fy-transcript" id="fy-transcript" hidden>
        ${d.segments.map((x, i) => `<li data-seg="${i}"><button type="button" data-player="jump" data-seg="${i}"><b>${esc(x.label)}</b><span>${esc(x.text)}</span></button></li>`).join("")}
      </ol>`;
    paintPlayer();
  }

  function pickVoice() {
    const voices = speechSynthesis.getVoices().filter((v) => /^en([-_]|$)/i.test(v.lang));
    return voices.find((v) => /natural|neural|premium|enhanced/i.test(v.name)) ||
      voices.find((v) => /google|samantha|daniel|serena|karen|moira/i.test(v.name)) ||
      voices.find((v) => v.default) || voices[0] || null;
  }

  function fraction() {
    const d = audio.data;
    if (!d) return 0;
    if (audio.mode === "studio" && audio.el && audio.el.duration) return audio.el.currentTime / audio.el.duration;
    const counts = d.segments.map((x) => words(x.text));
    const total = counts.reduce((a, b) => a + b, 0) || 1;
    const before = counts.slice(0, audio.index).reduce((a, b) => a + b, 0);
    return Math.min(1, (before + audio.frac * (counts[audio.index] || 0)) / total);
  }

  function currentIndex() {
    if (audio.mode !== "studio") return audio.index;
    const f = fraction();
    let idx = 0;
    audio.data.chapters.forEach((c, i) => { if (c.start <= f + 0.0001) idx = i; });
    return idx;
  }

  function paintPlayer() {
    const d = audio.data;
    if (!d || !$("fy-player")) return;
    const f = fraction();
    const active = audio.playing;
    const idx = currentIndex();
    $("fy-player-fill").style.width = `${(f * 100).toFixed(2)}%`;
    $("fy-player-track").setAttribute("aria-valuenow", String(Math.round(f * 100)));
    const icon = document.querySelector(".fy-player-play .fy-player-icon");
    icon.textContent = audio.preparing ? "…" : active && !audio.paused ? "❚❚" : "▶";
    document.querySelector(".fy-player-play").setAttribute("aria-label", active && !audio.paused ? "Pause" : "Play your audio brief");
    $("fy-player").classList.toggle("is-playing", active && !audio.paused);
    if (active) {
      const seg = d.segments[idx];
      const remaining = (audio.mode === "studio" && audio.el && audio.el.duration)
        ? audio.el.duration - audio.el.currentTime : d.seconds * (1 - f) / audio.rate;
      $("fy-player-now").innerHTML = `<b>Now:</b> ${esc(seg ? seg.label : "")} <span class="fy-player-left">${fmtTime(remaining)} left</span>`;
    }
    const seg = active ? d.segments[idx] : null;
    document.querySelectorAll(".fy-y5-item").forEach((li) => li.classList.toggle("is-speaking", !!seg && seg.card_id === li.dataset.id));
    document.querySelectorAll("#fy-transcript li").forEach((li) => li.classList.toggle("is-active", active && Number(li.dataset.seg) === idx));
  }

  function speakFrom(i) {
    const segs = audio.data.segments;
    const t = ++audio.token;
    speechSynthesis.cancel();
    if (i >= segs.length) return finishAudio();
    Object.assign(audio, { mode: "speech", index: i, frac: 0, playing: true, paused: false });
    const u = new SpeechSynthesisUtterance(segs[i].text);
    const v = pickVoice();
    if (v) { u.voice = v; u.lang = v.lang; }
    u.rate = audio.rate;
    u.onboundary = (e) => { if (t === audio.token) { audio.frac = Math.min(1, e.charIndex / segs[i].text.length); paintPlayer(); } };
    u.onend = () => { if (t === audio.token && audio.playing) speakFrom(i + 1); };
    u.onerror = (e) => {
      if (t !== audio.token || ["interrupted", "canceled"].includes(e.error)) return;
      finishAudio();
      toast("Your device couldn't read this aloud.");
    };
    setTimeout(() => { if (t === audio.token) speechSynthesis.speak(u); }, 40);
    setMediaSession();
    paintPlayer();
  }

  async function startStudio(atFraction) {
    const d = audio.data;
    if (!d.studio_audio_ready) {
      audio.preparing = true;
      paintPlayer();
      $("fy-player-now").textContent = "Recording your brief in the studio voice…";
      try {
        await api("/api/your5/audio", { hour: localHour() });
        d.studio_audio_ready = true;
      } catch (err) {
        audio.preparing = false;
        d.studio_voice = false;
        toast(`${err.message} Playing it in your device's voice instead.`);
        return false;
      }
      audio.preparing = false;
    }
    if (!audio.el) {
      audio.el = new Audio();
      audio.el.preload = "auto";
      audio.el.addEventListener("timeupdate", paintPlayer);
      audio.el.addEventListener("ended", finishAudio);
      audio.el.addEventListener("error", () => { if (audio.mode === "studio" && audio.playing) { finishAudio(); toast("The studio audio couldn't play."); } });
    }
    audio.el.src = `/api/your5/audio.mp3?hour=${localHour()}&t=${Date.now()}`;
    audio.el.playbackRate = audio.rate;
    Object.assign(audio, { mode: "studio", playing: true, paused: false });
    if (atFraction > 0) {
      audio.el.addEventListener("loadedmetadata", () => { audio.el.currentTime = atFraction * audio.el.duration; }, { once: true });
    }
    try { await audio.el.play(); } catch (_) { finishAudio(); return false; }
    setMediaSession();
    paintPlayer();
    return true;
  }

  async function playFrom(i) {
    if (!audio.data) return;
    if (audio.mode === "studio" && audio.playing && audio.el && audio.el.duration) {
      audio.el.currentTime = audio.data.chapters[i].start * audio.el.duration;
      if (audio.paused) { audio.el.play(); audio.paused = false; }
      return paintPlayer();
    }
    if (audio.mode === "speech" && audio.playing) return speakFrom(i);
    if (audio.data.studio_voice && await startStudio(audio.data.chapters[i].start)) return;
    if (!("speechSynthesis" in window)) return toast("This browser can't read aloud.");
    speakFrom(i);
  }

  function togglePlay() {
    if (!audio.data || audio.preparing) return;
    if (!audio.playing) return playFrom(0);
    if (audio.mode === "studio") {
      if (audio.paused) { audio.el.play(); audio.paused = false; } else { audio.el.pause(); audio.paused = true; }
    } else if (audio.paused) {
      audio.paused = false;
      speechSynthesis.resume();
      // Some engines can't resume a paused utterance; start the chapter again if nothing is speaking.
      setTimeout(() => { if (audio.playing && !audio.paused && !speechSynthesis.speaking) speakFrom(audio.index); }, 250);
    } else {
      speechSynthesis.pause();
      audio.paused = true;
    }
    paintPlayer();
  }

  function finishAudio() {
    audio.token += 1;
    Object.assign(audio, { playing: false, paused: false, index: 0, frac: 0 });
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    if (audio.el) audio.el.pause();
    paintPlayer();
    if (audio.data && $("fy-player-now")) $("fy-player-now").textContent = "That's your five. Tap play to hear it again.";
  }

  function stopAudio() {
    if (audio.playing) finishAudio();
    audio.data = null;
  }

  function cycleSpeed(btn) {
    audio.rate = RATES[(RATES.indexOf(audio.rate) + 1) % RATES.length];
    btn.textContent = `${audio.rate}×`;
    if (audio.el) audio.el.playbackRate = audio.rate;
    if (audio.mode === "speech" && audio.playing && !audio.paused) speakFrom(audio.index);
    paintPlayer();
  }

  function seekTo(e) {
    const track = $("fy-player-track");
    const rect = track.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (audio.mode === "studio" && audio.playing && audio.el && audio.el.duration) {
      audio.el.currentTime = f * audio.el.duration;
      return paintPlayer();
    }
    let idx = 0;
    audio.data.chapters.forEach((c, i) => { if (c.start <= f) idx = i; });
    playFrom(idx);
  }

  function setMediaSession() {
    if (!("mediaSession" in navigator) || typeof MediaMetadata === "undefined") return;
    navigator.mediaSession.metadata = new MediaMetadata({ title: "Your Pith brief", artist: "Pith · For You",
      album: (state.your5 && state.your5.date) || "" });
    navigator.mediaSession.setActionHandler("play", () => { if (audio.paused || !audio.playing) togglePlay(); });
    navigator.mediaSession.setActionHandler("pause", () => { if (audio.playing && !audio.paused) togglePlay(); });
    navigator.mediaSession.setActionHandler("nexttrack", () => playFrom(Math.min(audio.data.segments.length - 1, currentIndex() + 1)));
    navigator.mediaSession.setActionHandler("previoustrack", () => playFrom(Math.max(0, currentIndex() - 1)));
  }

  function onPlayerClick(el, e) {
    const act = el.dataset.player;
    if (act === "toggle") return togglePlay();
    if (act === "speed") return cycleSpeed(el);
    if (act === "seek") return seekTo(e);
    if (act === "jump") return playFrom(Number(el.dataset.seg));
    if (act === "transcript") {
      const t = $("fy-transcript");
      t.hidden = !t.hidden;
      el.setAttribute("aria-expanded", String(!t.hidden));
    }
  }

  function onYour5Click(e) {
    const p = e.target.closest("[data-player]");
    if (p) return onPlayerClick(p, e);
    const el = e.target.closest("[data-y5]");
    if (!el) return;
    const act = el.dataset.y5;
    const item = e.target.closest(".fy-y5-item");
    if (!item) return;
    const id = item.dataset.id;
    const c = state.your5.cards.find((x) => x.id === id);
    if (act === "listen-from") {
      const idx = audio.data ? audio.data.segments.findIndex((x) => x.card_id === id) : -1;
      return idx >= 0 ? playFrom(idx) : toast("The audio brief is still loading.");
    }
    if (act === "toggle") {
      const open = !item.classList.contains("open");
      item.classList.toggle("open", open);
      el.setAttribute("aria-expanded", open);
      if (open && !item.dataset.opened) { item.dataset.opened = "1"; track("click", { article_id: id }); }
      return;
    }
    if (act === "open") {
      track("click", { article_id: id });
      state.pendingDwell = { id, start: Date.now() };
      return; // let the link open
    }
    if (act === "worth" || act === "notworth") {
      const want = act === "worth" ? 1 : -1;
      const now = c.user_state.reaction === want ? 0 : want;
      c.user_state.reaction = now;
      track(now === 1 ? "worth_time" : now === -1 ? "not_worth_time" : "clear_worth", { article_id: id });
      item.querySelector('[data-y5="worth"]').classList.toggle("on", now === 1);
      item.querySelector('[data-y5="notworth"]').classList.toggle("on", now === -1);
      toast(now === 1 ? "Noted: worth your time." : now === -1 ? "Noted: fewer like this." : "Rating removed.");
      return;
    }
    if (act === "follow") {
      toggleFollow("story", id, c.headline, id).then(() => {
        el.textContent = isFollowing("story", id) ? "✓ Following" : "+ Follow story";
      });
    }
  }

  // ------------------------------------------------------------------ boot
  function greeting(name) {
    name = String(name || "").trim().split(/\s+/)[0] || name;
    const h = localHour();
    const part = h < 5 ? "Up late" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
    return `${part}, <em>${esc(name)}</em>`;
  }

  function startApp() {
    show("fy-app");
    $("fy-date").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }).toUpperCase();
    $("fy-greeting").innerHTML = greeting(state.user.display_name || state.user.username);
    loadProfile().then(() => {
      syncTimezone();
      setTab("foryou");
      loadYour5();
      refreshFollowBadge();
    });
  }

  async function enter(user) {
    state.user = user;
    $("fy-user-chip").hidden = false;
    $("fy-username").textContent = user.display_name || user.username;
    const av = $("fy-avatar");
    av.textContent = (user.display_name || user.username || "?").charAt(0).toUpperCase();
    if (user.avatar_url) {
      const img = new Image();
      img.alt = "";
      img.referrerPolicy = "no-referrer";
      img.onload = () => { av.textContent = ""; av.appendChild(img); av.classList.add("has-img"); };
      img.src = user.avatar_url;
    }
    if (!user.onboarded) {
      const { all_topics, imported_topics } = await api("/api/profile");
      await startOnboarding(all_topics, imported_topics || []);
    } else {
      startApp();
    }
  }

  async function boot() {
    const connected = readUrlMessages();
    try {
      const { user } = await api("/api/me");
      if (user) {
        if (connected) toast(`${PROVIDER_NAMES[connected] || "Account"} connected. Your front page starts from your interests now.`);
        return enter(user);
      }
    } catch (_) { /* server offline: fall through to gate */ }
    show("fy-gate");
    setupSocial();
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
      if (un) { track("unmute_source", { publisher: un.dataset.publisher }); await flush(); loadProfile(); toast(`Unmuted ${un.dataset.publisher}`); return; }
      const st = e.target.closest("[data-steer]");
      if (st) {
        const topic = st.dataset.topic;
        track(st.dataset.steer, { topic });
        await flush();
        toast(st.dataset.steer === "more_topic" ? `More ${topic} from now on` : `Less ${topic} from now on`);
        await loadProfile();
        loadYour5();
        if (state.tab === "foryou") loadFeed(true);
        return;
      }
      const conn = e.target.closest("[data-conn]");
      if (conn) connectionAction(conn.closest(".fy-conn").dataset.provider, conn.dataset.conn);
    });
    $("fy-budget").addEventListener("click", (e) => {
      const b = e.target.closest("[data-budget]");
      if (b) setBudget(Number(b.dataset.budget));
    });
    $("fy-budget-note").addEventListener("click", (e) => { if (e.target.closest("[data-budget-clear]")) setBudget(0); });
    $("fy-summary").addEventListener("click", (e) => { if (e.target.closest('[data-summary="following"]')) setTab("following"); });
    document.querySelectorAll("#fy-social .social-btn").forEach((a) => a.addEventListener("click", (e) => {
      if (a.classList.contains("is-disabled")) { e.preventDefault(); toast("That sign-in isn't set up on this server yet."); }
    }));
    $("fy-your5").addEventListener("click", onYour5Click);
    $("fy-your5").addEventListener("keydown", (e) => {
      if (e.target.id !== "fy-player-track" || !audio.data) return;
      if (e.key === "ArrowRight") { e.preventDefault(); playFrom(Math.min(audio.data.segments.length - 1, currentIndex() + 1)); }
      if (e.key === "ArrowLeft") { e.preventDefault(); playFrom(Math.max(0, currentIndex() - 1)); }
    });
    if ("speechSynthesis" in window) speechSynthesis.getVoices();   // warms the voice list in Chrome
    $("fy-follow-list").addEventListener("click", async (e) => {
      const b = e.target.closest(".fy-unfollow");
      if (!b) return;
      await api("/api/follows", { action: "unfollow", kind: b.dataset.kind, key: b.dataset.key });
      toast("Unfollowed");
      loadProfile();
    });
    $("fy-follow-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const phrase = $("fy-follow-input").value.trim();
      if (!phrase) return;
      try {
        await api("/api/follows", { action: "follow", kind: "keyword", key: phrase, label: phrase });
        $("fy-follow-input").value = "";
        toast(`Following “${phrase}”`);
        await loadProfile();
        refreshFollowBadge();
      } catch (err) { toast(err.message); }
    });
    $("fy-feedurl-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const url = $("fy-feedurl-input").value.trim();
      if (!url) return;
      $("fy-feedurl-error").textContent = "";
      const btn = e.target.querySelector("button");
      btn.disabled = true;
      btn.textContent = "Adding…";
      try {
        const { feed } = await api("/api/feeds", { action: "add", url });
        $("fy-feedurl-input").value = "";
        toast(`Added ${feed.title} (${feed.items} stories)`);
        await loadProfile();
        if (state.tab === "foryou") loadFeed(true);
      } catch (err) {
        $("fy-feedurl-error").textContent = err.message;
      } finally {
        btn.disabled = false;
        btn.textContent = "Add";
      }
    });
    $("fy-feed-list").addEventListener("click", async (e) => {
      const b = e.target.closest(".fy-feed-remove");
      if (!b) return;
      await api("/api/feeds", { action: "remove", feed_id: b.dataset.feed });
      toast("Feed removed");
      loadProfile();
    });
    $("fy-pref-depth").addEventListener("change", (e) => savePref("depth", e.target.value));
    $("fy-pref-region").addEventListener("change", (e) => savePref("region", e.target.value));
    $("fy-pref-hour").addEventListener("change", (e) => savePref("delivery_hour", e.target.value === "" ? null : Number(e.target.value)));
    $("fy-reset").addEventListener("click", async () => {
      if (!confirm("Erase everything your feed has learned about you? This can't be undone.")) return;
      await api("/api/profile/reset", {});
      stopAudio();
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
