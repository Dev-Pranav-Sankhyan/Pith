/**
 * Pith - Daily Tech Intelligence Client Engine & Web Audio Synthesizer
 * Visual Language: silvered ground · blued-steel ink · lacquer red · gilt hairlines
 * Zero external dependencies. <1s load performance. Zero heavy WebGL.
 */

// ==========================================================================
// 1. High-Fidelity Web Audio Synthesizer (Zero Audio Files, Realtime Synthesis)
// ==========================================================================
class SoundEngine {
  constructor() {
    this.enabled = localStorage.getItem("pith_audio_enabled") !== "false"; // Default true
    this.ctx = null;
    this.lastHoverTime = 0;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        try {
          this.ctx = new AudioCtx();
        } catch (e) {
          console.warn("AudioContext init deferred:", e);
        }
      }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      try {
        this.ctx.resume().catch(() => {});
      } catch (e) {}
    }
  }

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem("pith_audio_enabled", this.enabled);
    if (this.enabled) {
      this.init();
      this.playSnap();
    }
    this.updateToggleUI();
    return this.enabled;
  }

  updateToggleUI() {
    const btn = document.getElementById("sound-toggle-btn");
    if (!btn) return;
    if (this.enabled) {
      btn.classList.remove("muted");
      btn.title = "Mute audio feedback";
      const label = btn.querySelector(".sound-label");
      if (label) label.textContent = "Audio: On";
    } else {
      btn.classList.add("muted");
      btn.title = "Enable tactile audio feedback";
      const label = btn.querySelector(".sound-label");
      if (label) label.textContent = "Muted";
    }
  }

  // Tactile mechanical switch (Role toggle, filters)
  playSnap() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const filter = this.ctx.createBiquadFilter();

    osc.type = "sine";
    osc.frequency.setValueAtTime(160, t);
    osc.frequency.exponentialRampToValueAtTime(38, t + 0.045);

    filter.type = "lowpass";
    filter.frequency.setValueAtTime(650, t);

    gain.gain.setValueAtTime(0.22, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.045);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(t);
    osc.stop(t + 0.05);

    // High click bite
    const click = this.ctx.createOscillator();
    const clickGain = this.ctx.createGain();
    click.type = "triangle";
    click.frequency.setValueAtTime(920, t);
    click.frequency.exponentialRampToValueAtTime(180, t + 0.018);
    clickGain.gain.setValueAtTime(0.12, t);
    clickGain.gain.exponentialRampToValueAtTime(0.001, t + 0.018);
    click.connect(clickGain);
    clickGain.connect(this.ctx.destination);
    click.start(t);
    click.stop(t + 0.02);
  }

  // Micro tactile tick for hover states (throttled)
  playTick() {
    if (!this.enabled) return;
    const now = Date.now();
    if (now - this.lastHoverTime < 70) return;
    this.lastHoverTime = now;

    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(1400, t);
    osc.frequency.exponentialRampToValueAtTime(700, t + 0.015);

    gain.gain.setValueAtTime(0.035, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.015);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.02);
  }

  // Theme switch shutter
  playShutter() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(280, t);
    osc.frequency.exponentialRampToValueAtTime(60, t + 0.06);

    gain.gain.setValueAtTime(0.15, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.06);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.07);
  }

  // Mechanical Terminal Key Clack
  playPithClack() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    try {
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(1100 + Math.random() * 250, t);
      osc.frequency.exponentialRampToValueAtTime(140, t + 0.025);
      gain.gain.setValueAtTime(0.12, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.025);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.028);
    } catch (e) {}
  }

  // Accordion Expand resonant chime
  playExpand() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(380, t);
    osc.frequency.exponentialRampToValueAtTime(760, t + 0.09);

    gain.gain.setValueAtTime(0.08, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.09);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.1);
  }

  // Accordion Collapse descending tick
  playCollapse() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(650, t);
    osc.frequency.exponentialRampToValueAtTime(320, t + 0.06);

    gain.gain.setValueAtTime(0.06, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.06);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.07);
  }

  // 1. Lowpass Laser Sweep sound (Ion vaporize sweep)
  playLaserSweep() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    // Resonant downward filter sweep
    const osc = this.ctx.createOscillator();
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(220, t);
    osc.frequency.exponentialRampToValueAtTime(45, t + 0.75);

    filter.type = "lowpass";
    filter.Q.setValueAtTime(8, t);
    filter.frequency.setValueAtTime(2400, t);
    filter.frequency.exponentialRampToValueAtTime(140, t + 0.75);

    gain.gain.setValueAtTime(0.18, t);
    gain.gain.linearRampToValueAtTime(0.24, t + 0.2);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.78);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(t);
    osc.stop(t + 0.8);
  }

  // 2. Split-Flap kinetic text flip sound (Rapid relay clicks)
  playSplitFlap() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const baseT = this.ctx.currentTime;

    // 4 micro relay clicks spaced 30ms apart
    [0, 0.03, 0.065, 0.1].forEach((delay, idx) => {
      const t = baseT + delay;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = "triangle";
      osc.frequency.setValueAtTime(800 + idx * 120, t);
      osc.frequency.exponentialRampToValueAtTime(220, t + 0.018);

      gain.gain.setValueAtTime(0.08, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.018);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.02);
    });
  }

  // 3. On-Record Ledger Stamp sound (Heavy notary thud + metallic strike)
  playStamp() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    // Low heavy thud
    const osc = this.ctx.createOscillator();
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(240, t);
    osc.frequency.exponentialRampToValueAtTime(35, t + 0.09);

    filter.type = "lowpass";
    filter.frequency.setValueAtTime(450, t);

    gain.gain.setValueAtTime(0.4, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.13);

    // Sharp metallic impact snap
    const snap = this.ctx.createOscillator();
    const snapGain = this.ctx.createGain();
    snap.type = "square";
    snap.frequency.setValueAtTime(1100, t);
    snap.frequency.exponentialRampToValueAtTime(300, t + 0.025);
    snapGain.gain.setValueAtTime(0.18, t);
    snapGain.gain.exponentialRampToValueAtTime(0.001, t + 0.025);
    snap.connect(snapGain);
    snapGain.connect(this.ctx.destination);
    snap.start(t);
    snap.stop(t + 0.03);
  }

  // 4. Safely Ignore Shredder sound (Mechanical paper slicing + hiss)
  playShredder() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;
    const t = this.ctx.currentTime;

    // Buffer of white noise for paper slice
    const bufferSize = this.ctx.sampleRate * 0.45;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.setValueAtTime(1400, t);
    filter.frequency.exponentialRampToValueAtTime(320, t + 0.42);
    filter.Q.setValueAtTime(4.5, t);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.2, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.44);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    noise.start(t);
    noise.stop(t + 0.45);
  }
}

const sound = new SoundEngine();

// ==========================================================================
// 2. Theme Switcher with Shutter Sound
// ==========================================================================
function initTheme() {
  const savedTheme = localStorage.getItem("pith_brief_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
}

function toggleTheme() {
  sound.playShutter();
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("pith_brief_theme", next);
}

// ==========================================================================
// 3. The "Noise-to-Signal" Compression Hero (Lowpass Filter Animation)
// ==========================================================================
const NOISE_HEADLINES = [
  "AGI ACHIEVED INTERNALLY AT FRONTIER LAB",
  "X THREAD: 10 PROMPTS TO 100X YOUR RUNWAY",
  "NEW JS FRAMEWORK PROMISES 2X REACT SPEED",
  "AI PIN V2 SECURES $350M AT $3B VALUATION",
  "WHY YOU MUST REWRITE EVERYTHING IN RUST",
  "BENCHMARK WARS: 7B MODEL BEATS GPT-5",
  "Y COMBINATOR FOUNDER DRAMA ON HN FRONT PAGE",
  "AUTONOMOUS AGENT REPLACES ENTIRE ENGINEERING TEAM",
  "REVOLUTIONARY 3D AVATAR GENERATOR WITH REAL-TIME EYE TRACKING",
  "SECRET CHATBOT PROTOCOL WILL CRUSH GOOGLE SEARCH",
  "WEB3 AGENTS TO LAUNCH OWN TOKENS TODAY",
  "10 TOOLS YOU MUST MASTER BEFORE FRIDAY",
  "VENTURE CAPITALIST SAYS DEV JOBS DEAD IN 6 MONTHS",
  "WHY MICRON SERVICES SUCK AND MONOLITHS ARE BACK",
  "STARTUP RAISES $80M SEED ON ONE-PAGE NOTION PITCH",
  "NEW LLM REASONING HACK WILL CHANGE EVERYTHING",
  "OPEN-SOURCE MAINTAINER RAGES AT CORPORATE USERS",
  "THE UNTOLD TRUTH ABOUT QUANTUM AI CHIPS",
  "EVERYONE IS WRONG ABOUT VECTOR DATABASES",
  "REVOLUTIONARY CODE COPILOT WRITES ITS OWN PRD"
];

function runLowpass(force = false) {
  const overlay = document.getElementById("lowpass-overlay");
  const cloud = document.getElementById("noise-cloud");
  const laser = document.getElementById("laser-sweep-line");
  if (!overlay || !cloud || !laser) return;

  // Check prefers-reduced-motion
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    overlay.style.display = "none";
    return;
  }

  // Populate cloud with random rotated chips
  cloud.innerHTML = "";
  const types = ["hot", "cyan", "amber", ""];
  NOISE_HEADLINES.forEach((text, i) => {
    const chip = document.createElement("span");
    const chipType = types[i % types.length];
    chip.className = `noise-chip ${chipType}`;
    const rot = (Math.random() * 14 - 7).toFixed(1);
    chip.style.transform = `rotate(${rot}deg) scale(${(0.9 + Math.random() * 0.25).toFixed(2)})`;
    chip.textContent = text;
    cloud.appendChild(chip);
  });

  overlay.style.display = "flex";
  overlay.style.opacity = "1";
  laser.classList.remove("laser-sweep-active");
  void laser.offsetWidth; // Force reflow
  laser.classList.add("laser-sweep-active");

  sound.playLaserSweep();

  // Vaporize noise in staggered sync with laser sweep
  const chips = cloud.querySelectorAll(".noise-chip");
  chips.forEach((c, idx) => {
    const delay = 120 + (idx / chips.length) * 450;
    setTimeout(() => {
      c.classList.add("noise-vaporized");
    }, delay);
  });

  // End animation and cleanly snap Pith cards into view
  setTimeout(() => {
    overlay.style.opacity = "0";
    setTimeout(() => {
      overlay.style.display = "none";
    }, 400);
  }, 820);
}

function initLowpass() {
  const seen = sessionStorage.getItem("pith_lowpass_seen");
  if (!seen) {
    runLowpass();
    sessionStorage.setItem("pith_lowpass_seen", "true");
  }

  // Replay buttons
  const replayPill = document.getElementById("replay-lowpass-pill");
  if (replayPill) {
    replayPill.addEventListener("click", () => {
      sound.playSnap();
      runLowpass(true);
    });
  }

  const replayBtn = document.getElementById("replay-lowpass-btn");
  if (replayBtn) {
    replayBtn.addEventListener("click", () => {
      sound.playSnap();
      runLowpass(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
}

// ==========================================================================
// 4. Kinetic Split-Flap Text Scrambler & Role Border Glows
// ==========================================================================
const SCRAMBLE_GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&@/*+-=";

function scrambleText(element, targetText, durationMs = 220) {
  if (!element || element.textContent === targetText) return;

  // Clear any in-flight scramble on this element to prevent race conditions
  if (element._scrambleTimer) {
    clearInterval(element._scrambleTimer);
    element._scrambleTimer = null;
  }

  const originalText = element.textContent;
  const length = Math.max(targetText.length, originalText.length);
  const steps = 7;
  const stepTime = durationMs / steps;
  let currentStep = 0;

  element.classList.add("scrambling");

  element._scrambleTimer = setInterval(() => {
    currentStep++;
    if (currentStep >= steps) {
      clearInterval(element._scrambleTimer);
      element._scrambleTimer = null;
      element.textContent = targetText;
      element.classList.remove("scrambling");
    } else {
      let output = "";
      for (let i = 0; i < targetText.length; i++) {
        if (i < (currentStep / steps) * targetText.length) {
          output += targetText[i];
        } else {
          output += SCRAMBLE_GLYPHS[Math.floor(Math.random() * SCRAMBLE_GLYPHS.length)];
        }
      }
      element.textContent = output;
    }
  }, stepTime);
}

let currentRole = localStorage.getItem("pith_brief_role") || "developer";

function setRole(role, playAudio = true) {
  if (!["developer", "founder", "investor", "everyday"].includes(role)) return;
  if (playAudio) {
    sound.playSplitFlap();
  }

  currentRole = role;
  localStorage.setItem("pith_brief_role", role);

  // Update segmented control buttons
  document.querySelectorAll(".seg-btn[data-role]").forEach(btn => {
    if (btn.getAttribute("data-role") === role) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Sync Audio Brief player & CLI display
  if (window.audioBrief) {
    window.audioBrief.syncRole(role);
  }

  // Role glow classes
  const glowClass = role === "developer" ? "dev-glow" : (role === "founder" ? "founder-glow" : (role === "investor" ? "investor-glow" : "everyday-glow"));

  // Update cards dynamically with kinetic split-flap scramble
  document.querySelectorAll(".lab-card").forEach(cardEl => {
    const roleViewsJson = cardEl.getAttribute("data-role-views");
    if (!roleViewsJson) return;

    try {
      const views = JSON.parse(roleViewsJson);
      const activeView = views[role];
      if (!activeView) return;

      const actionPanel = cardEl.querySelector(".action-panel");
      const actionPill = cardEl.querySelector(".action-pill");
      const actionDirective = cardEl.querySelector(".action-directive");
      const roleImpact = cardEl.querySelector(".role-impact-preview");

      if (actionPanel) {
        actionPanel.classList.remove("dev-glow", "founder-glow", "investor-glow", "everyday-glow");
        actionPanel.classList.add(glowClass);
        actionPanel.classList.remove("role-slide-transition");
        void actionPanel.offsetWidth; // trigger reflow for smooth re-trigger
        actionPanel.classList.add("role-slide-transition");
      }

      if (actionPill) {
        actionPill.className = `action-pill ${activeView.action_type.toLowerCase()}`;
        actionPill.textContent = activeView.action_type;
      }

      if (actionDirective) {
        scrambleText(actionDirective, activeView.action_text, 220);
      }

      if (roleImpact) {
        scrambleText(roleImpact, activeView.impact, 220);
      }
    } catch (e) {
      console.error("Error updating role view:", e);
    }
  });
}

// ==========================================================================
// 5. Calibration ELO Engine & The "Contrarian Multiplier"
// ==========================================================================
class PithELOEngine {
  constructor() {
    this.elo = parseInt(localStorage.getItem("pith_reader_elo") || "1200", 10);
    this.savedVotes = JSON.parse(localStorage.getItem("pith_card_votes") || "{}");
  }

  getTier(elo) {
    if (elo < 1250) return "Observer";
    if (elo < 1500) return "Analyst";
    if (elo < 1800) return "Strategist";
    return "Oracle";
  }

  updateHeaderUI(animate = false) {
    const scoreEls = document.querySelectorAll("#user-elo-score");
    const tierEls = document.querySelectorAll("#user-elo-tier");
    const tier = this.getTier(this.elo);

    scoreEls.forEach(el => {
      if (animate) {
        const start = parseInt(el.textContent, 10) || 1200;
        const target = this.elo;
        const duration = 400;
        const startTime = performance.now();
        function step(now) {
          const p = Math.min((now - startTime) / duration, 1);
          el.textContent = Math.round(start + (target - start) * p);
          if (p < 1) requestAnimationFrame(step);
          else el.textContent = target;
        }
        requestAnimationFrame(step);
      } else {
        el.textContent = this.elo;
      }
    });

    tierEls.forEach(el => {
      el.textContent = tier;
      el.className = `elo-tier ${tier.toLowerCase()}`;
    });
  }

  // Check if a vote is contrarian vs our forecast & crowd consensus
  isContrarian(cardProb, vote) {
    // If forecast is high (>=60%) and crowd agrees, voting lower is contrarian
    if (cardProb >= 60 && vote === "lower") return true;
    // If forecast is low (<=40%), voting higher is contrarian
    if (cardProb <= 40 && vote === "higher") return true;
    return false;
  }

  recordVote(cardId, cardProb, vote, cardEl) {
    const existing = this.savedVotes[cardId];
    if (existing && existing.vote === vote) {
      return; // Already logged this exact vote, avoid duplicate stamps and ELO abuse
    }

    const isContrarian = this.isContrarian(cardProb, vote);
    const multiplier = isContrarian ? 2 : 1;
    const pointsGained = 12 * multiplier;

    // Refund previous points on this card if changing vote, preventing ELO farming
    if (existing && existing.pointsGained) {
      this.elo -= existing.pointsGained;
    }

    this.elo = Math.max(800, this.elo + pointsGained);
    localStorage.setItem("pith_reader_elo", this.elo.toString());

    this.savedVotes[cardId] = {
      vote: vote,
      timestamp: Date.now(),
      hash: (existing && existing.hash) ? existing.hash : Math.random().toString(16).substring(2, 6).toUpperCase(),
      contrarian: isContrarian,
      pointsGained: pointsGained
    };
    localStorage.setItem("pith_card_votes", JSON.stringify(this.savedVotes));

    // Update ELO UI with smooth counter
    this.updateHeaderUI(true);

    // Trigger Physical Stamp onto Card
    this.stampCard(cardId, this.savedVotes[cardId], cardEl);

    // Show Contrarian pill if active
    const contrarianTag = cardEl.querySelector(`#contrarian-tag-${cardId}`);
    if (contrarianTag) {
      if (isContrarian) {
        contrarianTag.style.display = "inline-flex";
      } else {
        contrarianTag.style.display = "none";
      }
    }
  }

  stampCard(cardId, voteData, cardEl) {
    const stampContainer = cardEl.querySelector(`#stamp-container-${cardId}`);
    if (!stampContainer) return;

    const timeStr = new Date(voteData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const voteUpper = voteData.vote.toUpperCase();
    const hashStr = voteData.hash || "9F41";

    stampContainer.innerHTML = `
      <div class="stamp-badge">
        <div class="stamp-title">ON RECORD &middot; ${voteUpper}</div>
        <div class="stamp-meta">SEALED #${hashStr} &middot; ${timeStr}</div>
      </div>
    `;

    // 2-pixel screen shake on the card
    cardEl.classList.remove("card-shake");
    void cardEl.offsetWidth; // Reflow
    cardEl.classList.add("card-shake");
    setTimeout(() => {
      cardEl.classList.remove("card-shake");
    }, 320);

    // Audio slam
    sound.playStamp();
  }

  restoreCardStamps() {
    Object.keys(this.savedVotes).forEach(cardId => {
      const cardEl = document.getElementById(cardId) || document.getElementById(`card-${cardId}`);
      if (!cardEl) return;

      const data = this.savedVotes[cardId];
      const stampContainer = cardEl.querySelector(`#stamp-container-${cardId}`);
      if (stampContainer) {
        const timeStr = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        stampContainer.innerHTML = `
          <div class="stamp-badge" style="animation:none; opacity:1;">
            <div class="stamp-title">ON RECORD &middot; ${data.vote.toUpperCase()}</div>
            <div class="stamp-meta">SEALED #${data.hash || "9F41"} &middot; ${timeStr}</div>
          </div>
        `;
      }

      if (data.contrarian) {
        const contrarianTag = cardEl.querySelector(`#contrarian-tag-${cardId}`);
        if (contrarianTag) contrarianTag.style.display = "inline-flex";
      }
    });
  }
}

const pithELO = new PithELOEngine();

// ==========================================================================
// 6. Beat the Brief 1-Tap Widget Logic with Contrarian Multiplier
// ==========================================================================
function initBeatTheBrief() {
  document.querySelectorAll(".beat-brief-widget").forEach(widget => {
    const cardId = widget.getAttribute("data-card-id");
    const cardProb = parseInt(widget.getAttribute("data-prob") || "70", 10);
    const cardEl = widget.closest(".lab-card");
    const crowdBox = widget.querySelector(".crowd-result");
    const voteText = widget.querySelector(".user-vote-text");

    // Restore previous vote if any
    if (pithELO.savedVotes[cardId]) {
      const prev = pithELO.savedVotes[cardId];
      const btn = widget.querySelector(`.vote-btn[data-vote="${prev.vote}"]`);
      if (btn) btn.classList.add("selected");
      if (crowdBox) crowdBox.style.display = "block";
      if (voteText) voteText.textContent = prev.vote.toUpperCase();
    }

    // Attach click listeners
    widget.querySelectorAll(".vote-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const vote = btn.getAttribute("data-vote");

        // Spawn physics particle ember explosion!
        if (window.fxEngine) {
          const rect = btn.getBoundingClientRect();
          const burstX = e.clientX || (rect.left + rect.width / 2);
          const burstY = e.clientY || (rect.top + rect.height / 2);
          const color = vote === "agree" ? "#10B981" : (vote === "higher" ? "#B58900" : "#C2301C");
          window.fxEngine.spawnBurst(burstX, burstY, color, 30);
        }

        // Mark active
        widget.querySelectorAll(".vote-btn").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");

        // Reveal crowd distribution
        if (crowdBox) crowdBox.style.display = "block";
        if (voteText) voteText.textContent = vote.toUpperCase();

        // Record vote in ELO engine + stamp card
        pithELO.recordVote(cardId, cardProb, vote, cardEl);
      });
    });
  });

  pithELO.restoreCardStamps();
}

// ==========================================================================
// 7. Safely Ignore Shredder ("Clear the Noise" Feature)
// ==========================================================================
function initNoiseShredder() {
  const shredderBtn = document.getElementById("shredder-btn");
  const itemsContainer = document.getElementById("filtered-items-container");
  const quietSlate = document.getElementById("shredded-quiet-slate");
  const restoreBtn = document.getElementById("restore-noise-btn");

  if (!shredderBtn || !itemsContainer || !quietSlate) return;

  const isShredded = sessionStorage.getItem("pith_noise_shredded") === "true";
  if (isShredded) {
    itemsContainer.style.display = "none";
    quietSlate.style.display = "block";
    shredderBtn.style.opacity = "0.5";
    shredderBtn.disabled = true;
  }

  shredderBtn.addEventListener("click", () => {
    sound.playShredder();

    const items = itemsContainer.querySelectorAll(".filtered-item");
    if (items.length === 0) {
      itemsContainer.style.display = "none";
      quietSlate.style.display = "block";
      shredderBtn.style.opacity = "0.5";
      shredderBtn.disabled = true;
      sessionStorage.setItem("pith_noise_shredded", "true");
      return;
    }

    items.forEach((item, idx) => {
      setTimeout(() => {
        item.classList.add("crt-vaporize");
      }, idx * 75);
    });

    setTimeout(() => {
      itemsContainer.style.display = "none";
      quietSlate.style.display = "block";
      shredderBtn.style.opacity = "0.5";
      shredderBtn.disabled = true;
      sessionStorage.setItem("pith_noise_shredded", "true");
    }, items.length * 75 + 500);
  });

  if (restoreBtn) {
    restoreBtn.addEventListener("click", () => {
      sound.playSnap();
      itemsContainer.querySelectorAll(".filtered-item").forEach(item => {
        item.classList.remove("shredding");
        item.style.transform = "";
        item.style.opacity = "1";
        item.style.maxHeight = "";
      });
      itemsContainer.style.display = "flex";
      quietSlate.style.display = "none";
      shredderBtn.style.opacity = "1";
      shredderBtn.disabled = false;
      sessionStorage.removeItem("pith_noise_shredded");
    });
  }
}

// ==========================================================================
// 8. Card Hover Stability (3D Tilt removed for effortless reading)
// ==========================================================================
function initCardTilt() {
  const cards = document.querySelectorAll(".lab-card, .bignum-card, .schematic-wrapper");
  cards.forEach(card => {
    card.style.transform = "none";
    card.addEventListener("mouseenter", () => {
      sound.playTick();
    });
  });
}

// ==========================================================================
// 9. Progressive Deep Scan Disclosure Accordion
// ==========================================================================
function toggleDeepScan(btn) {
  const card = btn.closest(".lab-card");
  const panel = card ? card.querySelector(".deep-scan-panel") : (btn.closest(".card-action-bar")?.nextElementSibling || btn.nextElementSibling);
  if (!panel) return;
  const label = btn.querySelector(".deep-scan-label");
  const actionText = btn.querySelector(".deep-scan-text") || btn.querySelector(".deep-scan-icon");
  
  if (panel.classList.contains("open")) {
    sound.playCollapse();
    panel.classList.remove("open");
    btn.classList.remove("is-open");
    if (label) label.textContent = "Detailed Intelligence Scan";
    if (actionText) actionText.textContent = "Expand 5-min deep scan";
  } else {
    sound.playExpand();
    panel.classList.add("open");
    btn.classList.add("is-open");
    if (label) label.textContent = "Detailed Intelligence Scan (Expanded)";
    if (actionText) actionText.textContent = "Collapse deep scan";
  }
}

// ==========================================================================
// 10. Number Counter Animation for Prediction Ledger
// ==========================================================================
function animateLedgerCounters() {
  const bignums = document.querySelectorAll(".bignum[data-target]");
  if (!bignums.length) return;

  bignums.forEach(el => {
    const target = parseFloat(el.getAttribute("data-target"));
    const format = el.getAttribute("data-format");
    const duration = 1100;
    const startTime = performance.now();

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = target * ease;

      if (format === "brier") {
        el.textContent = current.toFixed(4);
      } else if (format === "percent") {
        el.textContent = `${current.toFixed(1)}%`;
      } else {
        el.textContent = Math.round(current);
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        if (format === "brier") el.textContent = target.toFixed(4);
        else if (format === "percent") el.textContent = `${target.toFixed(1)}%`;
        else el.textContent = target;
      }
    }

    requestAnimationFrame(update);
  });
}

// ==========================================================================
// 11. Ledger Table & Category Filter
// ==========================================================================
function filterLedger() {
  sound.playSnap();
  const statusFilter = document.getElementById("status-filter")?.value || "all";
  const catFilter = document.getElementById("category-filter")?.value || "all";
  const rows = document.querySelectorAll("#ledger-table-body tr");

  rows.forEach(row => {
    const status = row.getAttribute("data-status");
    const category = row.getAttribute("data-category");

    const statusMatch = statusFilter === "all" || status === statusFilter;
    const catMatch = catFilter === "all" || category === catFilter;

    if (statusMatch && catMatch) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });
}

// Pattern Category Filtering
function filterPatterns(category) {
  sound.playSnap();
  document.querySelectorAll("#pattern-filters .seg-btn").forEach(btn => {
    if (btn.getAttribute("data-category") === category) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  document.querySelectorAll(".pattern-card").forEach(card => {
    const cardCat = card.getAttribute("data-category");
    if (category === "all" || cardCat === category) {
      card.style.display = "";
      card.classList.add("card-fade-in");
    } else {
      card.style.display = "none";
    }
  });
}

// ==========================================================================
// 12. One-Click "Share to Slack / Team" Formatter
// ==========================================================================
function initSlackShare() {
  document.querySelectorAll(".slack-share-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      sound.playSnap();
      const cardEl = btn.closest(".lab-card");
      if (!cardEl) return;

      const headline = cardEl.querySelector(".card-headline")?.textContent.trim() || "";
      const impactText = cardEl.querySelector(".role-impact-preview")?.textContent.trim() || "";
      const actionText = cardEl.querySelector(".action-directive")?.textContent.trim() || "";
      const roleCapitalized = currentRole.charAt(0).toUpperCase() + currentRole.slice(1);
      const permalink = window.location.origin + window.location.pathname + "#" + cardEl.id;

      const slackPayload = `⚡ *Pith — Daily Tech Intelligence*
*Event*: ${headline}
*Impact (${roleCapitalized})*: ${impactText}
*Action this week*: ${actionText}
🔗 ${permalink}`;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(slackPayload).then(() => {
          showSlackCopiedFeedback(btn);
        }).catch(err => {
          console.error("Clipboard copy failed, using fallback:", err);
          fallbackCopyText(slackPayload, btn);
        });
      } else {
        fallbackCopyText(slackPayload, btn);
      }
    });
  });
}

function showSlackCopiedFeedback(btn) {
  const originalText = btn.innerHTML;
  btn.classList.add("copied");
  btn.innerHTML = `<span class="slack-hash">✓</span> <span class="slack-btn-text">Copied for Slack!</span>`;
  setTimeout(() => {
    btn.classList.remove("copied");
    btn.innerHTML = originalText;
  }, 2400);
}

function fallbackCopyText(text, btn) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  showSlackCopiedFeedback(btn);
}

// ==========================================================================
// 12. 90-Second Studio Spoken Audio Briefing Controller
// ==========================================================================
class AudioBriefController {
  constructor() {
    this.audio = document.getElementById("audio-player");
    this.playBtn = document.getElementById("audio-brief-play-btn");
    this.playIcon = document.getElementById("audio-play-icon");
    this.pauseIcon = document.getElementById("audio-pause-icon");
    this.rolePill = document.getElementById("audio-role-pill");
    this.pulseDot = document.getElementById("audio-pulse-indicator");
    this.eqWaves = document.getElementById("audio-eq-waves");
    this.scrubber = document.getElementById("audio-brief-scrubber");
    this.progress = document.getElementById("audio-brief-progress");
    this.currentTimeEl = document.getElementById("audio-current-time");
    this.totalTimeEl = document.getElementById("audio-total-time");
    this.cliDisplay = document.getElementById("cli-cmd-display");
    this.cliCopyBtn = document.getElementById("cli-copy-btn");
    this.canvas = document.getElementById("audio-waveform-canvas");
    this.canvasCtx = this.canvas ? this.canvas.getContext("2d") : null;
    this.animId = null;

    if (!this.audio) return;
    this.init();
    this.drawVisualizer(false);
  }

  drawVisualizer(isPlaying) {
    if (!this.canvas || !this.canvasCtx) return;
    const ctx = this.canvasCtx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const bars = 22;
    const barWidth = 4;
    const gap = 3;

    const render = () => {
      ctx.clearRect(0, 0, w, h);
      const time = performance.now() * 0.006;

      for (let i = 0; i < bars; i++) {
        let barHeight = 2;
        if (this.audio && !this.audio.paused) {
          const v = Math.sin(time * 2.2 + i * 0.45) * Math.cos(time * 1.5 + i * 0.3);
          const normalized = Math.max(0.18, Math.abs(v));
          barHeight = Math.max(3, normalized * (h - 2));
        }

        const x = i * (barWidth + gap) + 4;
        const y = h - barHeight;

        const grad = ctx.createLinearGradient(0, y, 0, h);
        grad.addColorStop(0, "#10B981");
        grad.addColorStop(0.5, "#B58900");
        grad.addColorStop(1, "#D97706");

        ctx.fillStyle = grad;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, y, barWidth, barHeight, 2);
        } else {
          ctx.rect(x, y, barWidth, barHeight);
        }
        ctx.fill();
      }

      if (this.audio && !this.audio.paused) {
        this.animId = requestAnimationFrame(render);
      }
    };

    if (this.animId) cancelAnimationFrame(this.animId);
    if (isPlaying) {
      render();
    } else {
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < bars; i++) {
        const x = i * (barWidth + gap) + 4;
        ctx.fillStyle = "rgba(181, 137, 0, 0.35)";
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, h - 3, barWidth, 3, 1.5);
        } else {
          ctx.rect(x, h - 3, barWidth, 3);
        }
        ctx.fill();
      }
    }
  }

  formatTime(secs) {
    if (isNaN(secs) || secs < 0) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  }

  init() {
    if (this.playBtn) {
      this.playBtn.addEventListener("click", () => this.togglePlay());
    }

    if (this.audio) {
      this.audio.addEventListener("timeupdate", () => this.onTimeUpdate());
      this.audio.addEventListener("loadedmetadata", () => {
        if (this.totalTimeEl && this.audio.duration) {
          this.totalTimeEl.textContent = this.formatTime(this.audio.duration);
        }
      });
      this.audio.addEventListener("ended", () => this.onEnded());
    }

    if (this.scrubber) {
      this.scrubber.addEventListener("click", (e) => {
        if (!this.audio || !this.audio.duration) return;
        const rect = this.scrubber.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        this.audio.currentTime = ratio * this.audio.duration;
      });
    }

    if (this.cliCopyBtn && this.cliDisplay) {
      this.cliCopyBtn.addEventListener("click", (e) => {
        const cmd = this.cliDisplay.textContent.trim();
        if (window.fxEngine) {
          const rect = this.cliCopyBtn.getBoundingClientRect();
          const bx = e.clientX || (rect.left + rect.width / 2);
          const by = e.clientY || (rect.top + rect.height / 2);
          window.fxEngine.spawnBurst(bx, by, "#B58900", 26);
        }
        navigator.clipboard.writeText(cmd).then(() => {
          const original = this.cliCopyBtn.textContent;
          this.cliCopyBtn.textContent = "Copied!";
          setTimeout(() => {
            this.cliCopyBtn.textContent = original;
          }, 1800);
        });
      });
    }
  }

  togglePlay() {
    if (!this.audio) return;
    if (this.audio.paused) {
      this.audio.play().then(() => {
        this.setPlayingState(true);
      }).catch(err => console.log("Audio playback notice:", err));
    } else {
      this.audio.pause();
      this.setPlayingState(false);
    }
  }

  setPlayingState(isPlaying) {
    if (this.playIcon) this.playIcon.style.display = isPlaying ? "none" : "inline";
    if (this.pauseIcon) this.pauseIcon.style.display = isPlaying ? "inline" : "none";
    if (this.pulseDot) this.pulseDot.classList.toggle("active", isPlaying);
    if (this.eqWaves) this.eqWaves.classList.toggle("active", isPlaying);
    this.drawVisualizer(isPlaying);
  }

  onTimeUpdate() {
    if (!this.audio || !this.audio.duration) return;
    const pct = (this.audio.currentTime / this.audio.duration) * 100;
    if (this.progress) this.progress.style.width = `${pct}%`;
    if (this.currentTimeEl) this.currentTimeEl.textContent = this.formatTime(this.audio.currentTime);
  }

  onEnded() {
    this.setPlayingState(false);
    if (this.progress) this.progress.style.width = "0%";
    if (this.currentTimeEl) this.currentTimeEl.textContent = "0:00";
  }

  syncRole(role) {
    const roleLabels = {
      developer: "DEVELOPER",
      founder: "FOUNDER",
      investor: "INVESTOR",
      everyday: "EVERYDAY PERSON"
    };

    const cliPaths = {
      developer: "dev",
      founder: "founder",
      investor: "investor",
      everyday: "plain"
    };

    if (this.rolePill) {
      this.rolePill.textContent = roleLabels[role] || "DEVELOPER";
      this.rolePill.className = `audio-role-pill ${role}`;
    }

    if (this.cliDisplay) {
      const cliSub = cliPaths[role] || "dev";
      this.cliDisplay.textContent = `curl -sL https://dev-pranav-sankhyan.github.io/Pith/${cliSub}`;
    }

    if (this.audio) {
      const wasPlaying = !this.audio.paused;
      const targetSrc = `audio/brief-${role}.mp3`;
      if (!this.audio.src.endsWith(targetSrc)) {
        this.audio.src = targetSrc;
        this.audio.load();
        if (wasPlaying) {
          this.audio.play().then(() => this.setPlayingState(true)).catch(() => {});
        } else {
          this.setPlayingState(false);
        }
      }
    }
  }
}

// ==========================================================================
// 13. Initialize Everything on DOM Ready
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  sound.updateToggleUI();
  pithELO.updateHeaderUI();

  // Initialize Audio Briefing
  window.audioBrief = new AudioBriefController();

  // Lowpass Hero Filter
  initLowpass();

  // Audio Toggle Button
  const soundBtn = document.getElementById("sound-toggle-btn");
  if (soundBtn) {
    soundBtn.addEventListener("click", () => sound.toggle());
  }

  // Theme Toggle Button
  const themeBtn = document.getElementById("theme-toggle-btn");
  if (themeBtn) {
    themeBtn.addEventListener("click", toggleTheme);
  }

  // Set initial role without audio playback
  setRole(currentRole, false);

  // Hook role buttons
  document.querySelectorAll(".seg-btn[data-role]").forEach(btn => {
    btn.addEventListener("click", () => {
      const role = btn.getAttribute("data-role");
      if (role) setRole(role, true);
    });
  });

  // Hook pattern category filter buttons
  document.querySelectorAll("#pattern-filters .seg-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const cat = btn.getAttribute("data-category");
      if (cat) filterPatterns(cat);
    });
  });

  // Hook accordion buttons
  document.querySelectorAll(".deep-scan-btn").forEach(btn => {
    btn.addEventListener("click", () => toggleDeepScan(btn));
  });

  // Hook ledger filters
  const statusSelect = document.getElementById("status-filter");
  const catSelect = document.getElementById("category-filter");
  if (statusSelect) statusSelect.addEventListener("change", filterLedger);
  if (catSelect) catSelect.addEventListener("change", filterLedger);

  // Initialize interactive 3D card tilt & spotlight
  initCardTilt();

  // Animate ledger counters if on ledger page
  animateLedgerCounters();

  // Initialize Beat the Brief, Noise Shredder, and Slack Share
  initBeatTheBrief();
  initNoiseShredder();
  initSlackShare();

  // Initialize Particle Ember Engine
  window.fxEngine = new EmberParticleEngine();

  // Initialize kinetic scroll animations (Laser reading line & card reveal)
  initScrollAnimations();

  // Initialize Extended Pages (Horizon and Bounty decommissioned)
  initMatrixPage();
  initEconomicsPage();
  initTerminalPage();
  initArchivePage();

  // Add hover ticks to interactive controls
  document.querySelectorAll(".nav-link, .seg-btn, .theme-toggle, .pattern-pill, .deep-scan-btn, .vote-btn, .slack-share-btn, .shredder-btn, .replay-filter-btn, .lowpass-replay-pill").forEach(el => {
    el.addEventListener("mouseenter", () => sound.playTick());
  });
});

// ==========================================================================
// 14. Scroll Animation Engine (Hero Parallax, Staggered Card Reveal)
// ==========================================================================
function initScrollAnimations() {
  const scrollCue = document.getElementById("scroll-cue");
  const masthead = document.querySelector(".masthead");
  const crown = document.querySelector(".crown");
  const orbRed = document.querySelector(".ambient-orb--red");
  const orbGilt = document.querySelector(".ambient-orb--gilt");
  const orbTeal = document.querySelector(".ambient-orb--teal");
  const cards = Array.from(document.querySelectorAll(".lab-card, .filter-sheet, .slide-reveal-card"));
  let ticking = false;

  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

  function update() {
    ticking = false;
    const y = window.scrollY || window.pageYOffset;
    const vh = window.innerHeight;

    // 1. Crown Header frosted glass elevation on scroll
    if (crown) {
      crown.classList.toggle("scrolled", y > 15);
    }

    // 3. Ambient Background Orbs Parallax Drift
    if (orbRed) orbRed.style.transform = `translateY(${y * 0.08}px)`;
    if (orbGilt) orbGilt.style.transform = `translateY(${-y * 0.06}px)`;
    if (orbTeal) orbTeal.style.transform = `translateY(${y * 0.04}px)`;

    // 4. Masthead scroll cue fade
    if (scrollCue) {
      if (y > 30) {
        scrollCue.classList.add("hidden");
      } else {
        scrollCue.classList.remove("hidden");
      }
    }

    // 5. Subtle Masthead Hero Parallax
    if (masthead && y <= vh) {
      const h = clamp(y / vh, 0, 1);
      masthead.style.transform = `translateY(${h * 24}px)`;
      masthead.style.opacity = `${1 - h * 0.45}`;
    }

    // 6. Active Center Reading Highlight
    const viewportCenter = vh * 0.45;
    let activeCard = null;
    let minDist = Infinity;
    cards.forEach((card) => {
      const rect = card.getBoundingClientRect();
      const center = rect.top + rect.height / 2;
      const dist = Math.abs(center - viewportCenter);
      if (dist < minDist && rect.top < vh && rect.bottom > 0) {
        minDist = dist;
        activeCard = card;
      }
      card.classList.remove("reading-active");
    });
    if (activeCard && minDist < vh * 0.35) {
      activeCard.classList.add("reading-active");
    }
  }

  function req() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }

  window.addEventListener("scroll", req, { passive: true });
  window.addEventListener("resize", req);
  update();

  // 7. Staggered card entrance via IntersectionObserver (Scroll Animation.html)
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const idx = cards.indexOf(entry.target);
          setTimeout(() => {
            entry.target.classList.add("show");
            entry.target.classList.add("in-view");
            entry.target.classList.add("revealed");
          }, Math.max(0, idx * 80));
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    cards.forEach((card) => io.observe(card));
  } else {
    cards.forEach((card) => {
      card.classList.add("show");
      card.classList.add("in-view");
      card.classList.add("revealed");
    });
  }
}

// ==========================================================================
// 15. Celebratory Ember Particle Physics Engine (Vote Sparks)
// ==========================================================================
class EmberParticleEngine {
  constructor() {
    this.canvas = document.getElementById("fx-canvas");
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.particles = [];
    this.resize();
    window.addEventListener("resize", () => this.resize());
    this.loop();
  }

  resize() {
    if (!this.canvas) return;
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  spawnBurst(x, y, color = "#B58900", count = 28) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2.5 + Math.random() * 6.5;
      this.particles.push({
        x: x,
        y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.8,
        size: 2 + Math.random() * 3.5,
        color: color,
        alpha: 1,
        decay: 0.022 + Math.random() * 0.025,
        gravity: 0.15
      });
    }
  }

  loop() {
    if (this.ctx && this.canvas && this.particles.length > 0) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      for (let i = this.particles.length - 1; i >= 0; i--) {
        const p = this.particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += p.gravity;
        p.vx *= 0.98;
        p.alpha -= p.decay;

        if (p.alpha <= 0) {
          this.particles.splice(i, 1);
          continue;
        }

        this.ctx.save();
        this.ctx.globalAlpha = Math.max(0, p.alpha);
        this.ctx.fillStyle = p.color;
        this.ctx.shadowColor = p.color;
        this.ctx.shadowBlur = 8;
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.restore();
      }
      if (this.particles.length === 0) {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      }
    }
    requestAnimationFrame(() => this.loop());
  }
}



// ==============================================================================
// 15. Extended Interactive Pages Controllers
// ==============================================================================

// ------------------------------------------------------------------------------
// 15.1 Platform Squeeze Matrix Controller
// ------------------------------------------------------------------------------
function initMatrixPage() {
  const matrix = document.querySelector(".matrix-canvas-wrapper");
  if (!matrix) return;

  document.querySelectorAll(".matrix-node").forEach(node => {
    node.addEventListener("click", () => {
      sound.playPithClack();
      
      // Flash node border
      node.style.transform = "scale(1.04)";
      node.style.boxShadow = "0 0 16px rgba(181, 137, 0, 0.4)";
      setTimeout(() => {
        node.style.transform = "";
        node.style.boxShadow = "";
      }, 400);

      if (window.fxEngine) {
        const rect = node.getBoundingClientRect();
        window.fxEngine.burst(rect.left + rect.width / 2, rect.top + rect.height / 2, "#B58900", 12);
      }
    });
  });
}

// ------------------------------------------------------------------------------
// 15.3 Inference Economics Calculator Controller
// ------------------------------------------------------------------------------
function initEconomicsPage() {
  const calcGrid = document.querySelector(".calc-workspace-grid");
  if (!calcGrid) return;

  const dauSlider = document.getElementById("dau-slider");
  const dauVal = document.getElementById("dau-val");
  const reqSlider = document.getElementById("req-slider");
  const reqVal = document.getElementById("req-val");
  const tokSlider = document.getElementById("tokens-slider");
  const tokVal = document.getElementById("tokens-val");

  let activeTier = "70b";
  let activeGpu = "h100";

  // Tier pricing models per 1M tokens ($)
  const tierApiCosts = {
    "8b": 0.20,
    "70b": 1.75,
    "400b": 6.50
  };

  // GPU monthly rental costs ($ per 8x node) & throughput capacity (tokens/sec per node)
  const gpuSpecs = {
    "l40s": { monthlyRent: 1400, tokensPerSec: 650 },
    "h100": { monthlyRent: 2600, tokensPerSec: 2200 },
    "b200": { monthlyRent: 4200, tokensPerSec: 5800 }
  };

  function recalculate() {
    if (!dauSlider || !reqSlider || !tokSlider) return;

    const dau = parseInt(dauSlider.value, 10);
    const req = parseInt(reqSlider.value, 10);
    const tok = parseInt(tokSlider.value, 10);

    // Update UI text labels
    if (dauVal) dauVal.textContent = dau >= 1000 ? (dau >= 1000000 ? (dau / 1000000).toFixed(1) + "M" : (dau / 1000).toFixed(0) + "k") : dau;
    if (reqVal) reqVal.textContent = req;
    if (tokVal) tokVal.textContent = tok >= 1000 ? (tok / 1000).toFixed(1) + "k" : tok;

    // Daily & Monthly token volumes
    const dailyTokens = dau * req * tok;
    const monthlyTokens = dailyTokens * 30;
    const monthlyMillions = monthlyTokens / 1000000;

    // 1. Cloud API Bill
    const apiRate = tierApiCosts[activeTier] || 1.75;
    const cloudMonthly = monthlyMillions * apiRate;

    // 2. Bare-metal Hardware requirement
    // Peak concurrency factor: assume 35% of daily requests occur in peak 4 hours
    const peakTokensPerSec = (dailyTokens * 0.35) / (4 * 3600);
    const gpuThroughput = gpuSpecs[activeGpu].tokensPerSec;
    const nodesNeeded = Math.max(1, Math.ceil(peakTokensPerSec / gpuThroughput));
    const baremetalMonthly = nodesNeeded * gpuSpecs[activeGpu].monthlyRent;

    // 3. Net Savings & Arbitrage
    const delta = cloudMonthly - baremetalMonthly;
    const marginExpansion = cloudMonthly > 0 ? Math.round((delta / cloudMonthly) * 100) : 0;

    // Update DOM Telemetry Boxes
    const cloudEl = document.querySelector(".cloud-cost .telemetry-big-num");
    const baremetalEl = document.querySelector(".baremetal-cost .telemetry-big-num");
    const deltaEl = document.querySelector(".delta-box .telemetry-big-num");
    const deltaSub = document.querySelector(".delta-box .telemetry-sub");
    const deltaHead = document.querySelector(".delta-headline");

    if (cloudEl) cloudEl.textContent = "$" + Math.round(cloudMonthly).toLocaleString() + "/mo";
    if (baremetalEl) baremetalEl.textContent = "$" + Math.round(baremetalMonthly).toLocaleString() + `/mo (${nodesNeeded}x node${nodesNeeded > 1 ? "s" : ""})`;
    
    if (deltaEl) {
      if (delta >= 0) {
        deltaEl.textContent = "+$" + Math.round(delta).toLocaleString() + "/mo";
        deltaEl.style.color = "var(--good)";
        if (deltaHead) deltaHead.textContent = `Bare-metal deployment unlocks +${marginExpansion}% gross margin expansion`;
        if (deltaSub) deltaSub.textContent = `Breakeven reached at ~${Math.round(dau * 0.25).toLocaleString()} DAU`;
      } else {
        deltaEl.textContent = "-$" + Math.abs(Math.round(delta)).toLocaleString() + "/mo";
        deltaEl.style.color = "var(--muted)";
        if (deltaHead) deltaHead.textContent = "Cloud API remains more capital-efficient at this scale";
        if (deltaSub) deltaSub.textContent = `Stay on managed API until token volume scales past ${(monthlyMillions * 2).toFixed(1)}M tok/mo`;
      }
    }
  }

  // Hook slider inputs
  [dauSlider, reqSlider, tokSlider].forEach(slider => {
    if (slider) {
      slider.addEventListener("input", () => {
        sound.playTick();
        recalculate();
      });
    }
  });

  // Hook Tier choice buttons
  document.querySelectorAll(".calc-choice-btn[data-tier]").forEach(btn => {
    btn.addEventListener("click", () => {
      sound.playTick();
      document.querySelectorAll(".calc-choice-btn[data-tier]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeTier = btn.getAttribute("data-tier");
      recalculate();
    });
  });

  // Hook Hardware choice buttons
  document.querySelectorAll(".calc-choice-btn[data-gpu]").forEach(btn => {
    btn.addEventListener("click", () => {
      sound.playTick();
      document.querySelectorAll(".calc-choice-btn[data-gpu]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeGpu = btn.getAttribute("data-gpu");
      recalculate();
    });
  });

  // Presets
  document.querySelectorAll(".preset-pill[data-preset]").forEach(pill => {
    pill.addEventListener("click", () => {
      sound.playPithClack();
      const preset = pill.getAttribute("data-preset");
      if (preset === "startup") {
        dauSlider.value = 5000;
        reqSlider.value = 4;
        tokSlider.value = 1200;
      } else if (preset === "scale") {
        dauSlider.value = 45000;
        reqSlider.value = 12;
        tokSlider.value = 2500;
      } else if (preset === "enterprise") {
        dauSlider.value = 250000;
        reqSlider.value = 25;
        tokSlider.value = 4000;
      }
      recalculate();
    });
  });

  recalculate();
}

// ------------------------------------------------------------------------------
// 15.3 Interactive Terminal Emulator Controller (Sandboxed & Authenticated)
// ------------------------------------------------------------------------------
function initTerminalPage() {
  const termScreen = document.getElementById("term-screen") || document.getElementById("terminal-screen");
  const termInput = document.getElementById("term-input") || document.getElementById("terminal-cli-input");
  const termHistory = document.getElementById("term-output-history");
  const termWindow = document.querySelector(".term-window");
  if (!termScreen || !termInput) return;

  const history = [];
  let historyIdx = -1;

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function printLine(htmlContent, cls = "term-line") {
    const line = document.createElement("div");
    if (cls) line.className = cls;
    line.innerHTML = htmlContent;
    if (termHistory) {
      termHistory.appendChild(line);
    } else {
      termScreen.insertBefore(line, termInput.closest(".term-input-line") || termInput);
    }
    termScreen.scrollTop = termScreen.scrollHeight;
  }

  function setPhosphorTheme(theme) {
    const normalized = (theme === "green") ? "emerald" : theme;
    if (!["amber", "emerald", "cyan"].includes(normalized)) return false;
    
    if (termWindow) {
      termWindow.classList.remove("phosphor-amber", "phosphor-emerald", "phosphor-cyan");
      termWindow.classList.add(`phosphor-${normalized}`);
    }
    document.querySelectorAll(".term-font-btn[data-phosphor]").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-phosphor") === normalized);
    });
    return true;
  }

  // Hook Phosphor Font Buttons in Titlebar
  document.querySelectorAll(".term-font-btn[data-phosphor]").forEach(btn => {
    btn.addEventListener("click", () => {
      sound.playTick();
      const p = btn.getAttribute("data-phosphor");
      if (p) setPhosphorTheme(p);
    });
  });

  // Traffic Light Controls
  const closeLight = document.querySelector(".term-light.close");
  if (closeLight) {
    closeLight.addEventListener("click", () => {
      sound.playTick();
      window.location.href = "index.html";
    });
  }
  const minLight = document.querySelector(".term-light.min");
  if (minLight) {
    minLight.addEventListener("click", () => {
      sound.playTick();
      if (termHistory) termHistory.innerHTML = "";
    });
  }
  const maxLight = document.querySelector(".term-light.max");
  if (maxLight) {
    maxLight.addEventListener("click", () => {
      sound.playTick();
      termScreen.style.maxHeight = termScreen.style.maxHeight === "850px" ? "640px" : "850px";
    });
  }

  // Restricted Commands Definition (Realistic UNIX Guest Sandbox Restrictions)
  const RESTRICTED_PATTERNS = [
    {
      regex: /^(sudo|su|doas)(\s+.*)?$/,
      code: "EACCES 403 Forbidden",
      msg: "Privilege escalation is prohibited. User 'guest' (uid=1001) is not in /etc/sudoers. Host elevation intercepted by sandbox supervisor."
    },
    {
      regex: /^(rm|unlink|rmdir|del|erase|truncate)(\s+.*)?$/,
      code: "EROFS Operation not permitted",
      msg: "Read-only filesystem mount (/dev/ro_loop0 on /). File deletion and host mutation are disabled in this analyst container."
    },
    {
      regex: /^(chmod|chown|chgrp|attrib)(\s+.*)?$/,
      code: "EPERM Operation not permitted",
      msg: "Permission modifications are prohibited. Container policy enforces immutable read-only permissions."
    },
    {
      regex: /^(touch|mkdir|mv|cp|dd|mkfs|fdisk|parted|mount|umount|fsck)(\s+.*)?$/,
      code: "EROFS Read-only filesystem",
      msg: "Filesystem write and device block operations are prohibited on the live node."
    },
    {
      regex: /^(bash|sh|zsh|csh|tcsh|dash|ksh|fish)(\s+.*)?$/,
      code: "RESTRICTED SUB-SHELL",
      msg: "Subshell breakout denied. Interactive PTY allocation is disabled in restricted guest mode."
    },
    {
      regex: /^(python|python3|node|ruby|perl|lua|php|exec|eval)(\s+.*)?$/,
      code: "RESTRICTED RUNTIME",
      msg: "Arbitrary script interpreter execution is blocked by container policy. Use 'calc' for GPU & cost arbitration calculations."
    },
    {
      regex: /^(ssh|scp|sftp|ftp|telnet|nc|netcat|nmap|traceroute|tcpdump|wget)(\s+.*)?$/,
      code: "ENETUNREACH Egress Blocked",
      msg: "Outbound network sockets and SSH tunnels are blocked by network firewall policy. Use 'curl' to query internal endpoints."
    },
    {
      regex: /^(kill|killall|pkill|xkill)(\s+.*)?$/,
      code: "EPERM PID Isolation",
      msg: "PID namespace isolation enforced. Guest container cannot signal or terminate system processes."
    },
    {
      regex: /^(reboot|shutdown|poweroff|halt|init)(\s+.*)?$/,
      code: "EPERM Privileged Hardware Call",
      msg: "System state transitions and hypervisor power control are reserved for node cluster admins."
    },
    {
      regex: /^(passwd|useradd|userdel|groupadd|usermod)(\s+.*)?$/,
      code: "EPERM Stateless Policy",
      msg: "User identity mutation is prohibited on stateless containers."
    },
    {
      regex: /^(apt|apt-get|yum|dnf|pacman|brew|apk|pip|npm|yarn|pnpm)(\s+.*)?$/,
      code: "RESTRICTED PACKAGE MGMT",
      msg: "Package installation is disabled on immutable base images."
    }
  ];

  function executeCommand(raw) {
    const rawTrimmed = raw.trim();
    if (!rawTrimmed) return;
    const cmd = rawTrimmed.toLowerCase();
    history.push(rawTrimmed);
    historyIdx = history.length;

    // Echo input
    printLine(`<span class="term-prompt">pith@intel:~$</span> <span style="color:#fff; font-weight:600;">${escapeHtml(rawTrimmed)}</span>`, "term-line cmd-echo");
    try {
      if (typeof sound !== "undefined" && sound && typeof sound.playPithClack === "function") {
        sound.playPithClack();
      } else if (typeof sound !== "undefined" && sound && typeof sound.playTick === "function") {
        sound.playTick();
      }
    } catch (e) {}

    // 1. Check Restricted Commands
    for (const rule of RESTRICTED_PATTERNS) {
      if (rule.regex.test(cmd)) {
        printLine(`
          <div class="term-error">
            <span class="term-tag tag-error">${rule.code}</span>
            <span>${rule.msg}</span>
          </div>
        `);
        return;
      }
    }

    // 2. Sensitive Path Traversal Check (cat /etc/passwd etc)
    if (/^(cat|head|tail|more|less)\s+(\/etc|\/root|\/proc|\/sys|\/var|\/dev|\.\.\/)/.test(cmd)) {
      printLine(`
        <div class="term-error">
          <span class="term-tag tag-error">EACCES ACCESS DENIED</span>
          <span>Sandbox boundary restriction: Path is outside container root (/home/guest/pith-sandbox). Access denied.</span>
        </div>
      `);
      return;
    }

    const parts = cmd.split(/\s+/);
    const primary = parts[0];

    // Strict Whitelist Enforcement - Zero Unapproved Command Access
    const ALLOWED_COMMANDS = new Set([
      "help", "?",
      "today", "news", "pith",
      "listen",
      "stats", "ledger",
      "matrix",
      "calc",
      "curl",
      "ls",
      "cat",
      "whoami",
      "pwd",
      "uname",
      "date",
      "uptime",
      "theme",
      "clear",
      "exit", "home",
      "echo"
    ]);

    if (!ALLOWED_COMMANDS.has(primary)) {
      printLine(`
        <div class="term-error">
          <span class="term-tag tag-error">PERMISSION DENIED</span>
          <span>pith: access restricted: command '<strong>${escapeHtml(primary)}</strong>' is not permitted. Access is strictly restricted to approved intelligence terminal commands (<span class="term-key">today</span>, <span class="term-key">listen</span>, <span class="term-key">stats</span>, <span class="term-key">matrix</span>, <span class="term-key">calc</span>, <span class="term-key">curl</span>, <span class="term-key">ls</span>, <span class="term-key">cat</span>, <span class="term-key">clear</span>, <span class="term-key">theme</span>, <span class="term-key">exit</span>). Type '<span style="color:#fff; text-decoration:underline;">help</span>' to list permitted commands.</span>
        </div>
      `);
      return;
    }

    switch (primary) {
      case "help":
      case "?":
        printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700; margin-bottom:8px;">✦ PITH HARDENED ANSI WORKSTATION &bull; AVAILABLE COMMANDS</div>
  <div style="font-size:12px; color:var(--muted); margin-bottom:10px;">Security Policy: Read-Only Guest Container (uid=1001, gid=1001). Privileged commands and system modifications are restricted.</div>
  <table style="width:100%; border-collapse:collapse; font-size:13px;">
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); width:130px; font-weight:600;">today, news</td><td style="color:#d1d5db;">Print today's top structural tech intelligence cards &amp; directives</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">listen [role]</td><td style="color:#d1d5db;">Stream studio audio brief (<span style="color:var(--cyan);">developer</span>, <span style="color:var(--cyan);">founder</span>, <span style="color:var(--cyan);">investor</span>)</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">stats, ledger</td><td style="color:#d1d5db;">Display forecast calibration ledger, Brier score, and Reader ELO</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">matrix</td><td style="color:#d1d5db;">Render ASCII 2x2 Platform Squeeze &amp; Moat Quadrant</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">calc [M] [price]</td><td style="color:#d1d5db;">Arbitrate monthly Cloud API tokens vs Bare-Metal 8xH100 cluster</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">curl [endpoint]</td><td style="color:#d1d5db;">Fetch plain-text or JSON telemetry (<span style="color:var(--cyan);">dev</span>, <span style="color:var(--cyan);">founder</span>, <span style="color:var(--cyan);">investor</span>, <span style="color:var(--cyan);">matrix</span>)</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">ls [dir]</td><td style="color:#d1d5db;">List sandboxed files (<span style="color:var(--cyan);">today.md</span>, <span style="color:var(--cyan);">forecasts.json</span>, <span style="color:var(--cyan);">README.md</span>)</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">cat [file]</td><td style="color:#d1d5db;">Display file contents in sandbox terminal</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">whoami, pwd</td><td style="color:#d1d5db;">Print sandbox container identity and working directory</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">uname, uptime</td><td style="color:#d1d5db;">Inspect kernel build and system uptime telemetry</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">theme [name]</td><td style="color:#d1d5db;">Switch phosphor color: <span style="color:#ffb000;">amber</span>, <span style="color:#10b981;">emerald</span>, <span style="color:#00e5ff;">cyan</span></td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">clear</td><td style="color:#d1d5db;">Clear terminal output scrollback</td></tr>
    <tr><td style="padding:3px 12px 3px 0; color:var(--gilt); font-weight:600;">exit</td><td style="color:#d1d5db;">Exit terminal and return to Daily News</td></tr>
  </table>
</div>
        `);
        break;

      case "today":
      case "news":
      case "pith":
        printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700; margin-bottom:6px;">✦ PITH DAILY INTELLIGENCE BRIEF // ${new Date().toISOString().slice(0, 10)}</div>
  <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:8px; margin-top:4px;">
    <div style="margin-bottom:12px;">
      <div style="color:var(--cyan); font-weight:600;">1. [SIGNAL 84.2] KV-Cache Eviction &amp; Prefix Hashing Slashes Agent Memory Wall</div>
      <div style="color:#d1d5db; margin:2px 0;">&bull; <strong>The Shift:</strong> Standardized prefix trees cut recompute latency by 88% across long-horizon agents.</div>
      <div style="color:#10b981;">&bull; <strong>Action:</strong> [DO THIS WEEK] Pin system prompt tokens to provider prefix hash boundaries.</div>
    </div>
    <div style="margin-bottom:12px;">
      <div style="color:var(--cyan); font-weight:600;">2. [SIGNAL 82.5] Autonomous Computer-Use Protocol Open Sourced</div>
      <div style="color:#d1d5db; margin:2px 0;">&bull; <strong>The Shift:</strong> Deterministic OS event loops bypass brittle bespoke RPA contracts.</div>
      <div style="color:#f59e0b;">&bull; <strong>Action:</strong> [WATCH TRIGGER] Benchmark containerized OS agent sandboxes against API latency.</div>
    </div>
    <div>
      <div style="color:var(--cyan); font-weight:600;">3. [SIGNAL 81.0] Open Agent Protocol (OAP) Standardized under CNCF</div>
      <div style="color:#d1d5db; margin:2px 0;">&bull; <strong>The Shift:</strong> Universal JSON-RPC schemas decouple LLM tools from single-vendor proprietary plugins.</div>
      <div style="color:#10b981;">&bull; <strong>Action:</strong> [DO THIS WEEK] Benchmark JSON-RPC schema translation on tool microservices.</div>
    </div>
  </div>
</div>
        `);
        break;

      case "listen": {
        const role = parts[1] || "developer";
        printLine(`
          <div style="color:var(--cyan); margin:4px 0;">
            <span class="term-tag tag-info">AUDIO STREAM</span> Streaming studio voice briefing for lens: [<strong>${escapeHtml(role)}</strong>]...
          </div>
        `);
        if (window.audioBrief) {
          window.audioBrief.playBriefing(role);
        } else {
          printLine(`<div style="color:var(--muted); font-size:12px;">Audio synthesis engine ready. Check speaker volume.</div>`);
        }
        break;
      }

      case "stats":
      case "ledger":
        printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700; margin-bottom:8px;">✦ FORECAST CALIBRATION LEDGER TELEMETRY</div>
  <table style="width:100%; border-collapse:collapse; font-size:13px;">
    <tr><td style="color:#9ca3af; width:180px;">Definitive Hit Rate:</td><td style="color:#10b981; font-weight:700;">100.0% (across resolved forecasts)</td></tr>
    <tr><td style="color:#9ca3af;">Aggregate Brier Score:</td><td style="color:#10b981; font-weight:700;">0.0000 (Target: &lt; 0.150)</td></tr>
    <tr><td style="color:#9ca3af;">Reader Calibration ELO:</td><td style="color:var(--gilt); font-weight:700;">${pithELO ? pithELO.getScore() : 1200} (${pithELO ? pithELO.getTier() : 'Observer'})</td></tr>
    <tr><td style="color:#9ca3af;">Active Falsifiable Claims:</td><td style="color:#fff;">5 open verifiable predictions on horizon</td></tr>
    <tr><td style="color:#9ca3af;">Validation Protocol:</td><td style="color:#d1d5db;">Automated cryptographic timestamping + peer falsification</td></tr>
  </table>
</div>
        `);
        break;

      case "matrix":
        printLine(`
<pre style="color:var(--cyan); font-family:var(--font-mono); font-size:12px; line-height:1.2; margin:8px 0; background:rgba(0,0,0,0.5); padding:10px; border:1px solid rgba(255,255,255,0.1); border-radius:4px;">
                     HIGH MARKET POWER
                             ▲
       CHOKEPOINT ASSETS     │     MOATS &amp; PROTOCOLS
     (Nvidia CUDA, TSMC)     │   (Private Workflow Data)
 ────────────────────────────┼────────────────────────────► HIGH SWITCHING
       COMMODITY COMPUTE     │     SQUEEZED MIDDLEWARE        COST
     (Standard Model APIs)   │   (Thin Wrapper Agents)
                             ▼
                     LOW MARKET POWER
</pre>
<div style="font-size:12px; color:var(--muted);">Visit the <strong>Market Map</strong> page for full interactive quadrant plotting and thesis inspection.</div>
        `);
        break;

      case "calc": {
        const tokM = parseFloat(parts[1]) || 50;
        const apiRate = parseFloat(parts[2]) || 1.75;
        const apiCost = tokM * apiRate;
        const gpuNodes = Math.max(1, Math.ceil(tokM / 40));
        const gpuCost = gpuNodes * 2600;
        const diff = Math.abs(apiCost - gpuCost);
        const selfCheaper = apiCost > gpuCost;

        printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700; margin-bottom:6px;">✦ AI INFERENCE COST CALCULATOR // ${tokM.toLocaleString()}M TOKENS/MONTH</div>
  <div style="color:#d1d5db; font-size:13px; line-height:1.6;">
    &bull; API Inference Cost ($${apiRate.toFixed(2)}/M): <strong>$${Math.round(apiCost).toLocaleString()}/mo</strong><br>
    &bull; Bare-Metal 8xH100 Cluster (${gpuNodes} node${gpuNodes > 1 ? 's' : ''}): <strong>$${Math.round(gpuCost).toLocaleString()}/mo</strong><br>
    &bull; <strong>Verdict:</strong> <span style="color:${selfCheaper ? '#10b981' : 'var(--cyan)'}; font-weight:700;">
      ${selfCheaper ? `Bare-metal cluster saves $${Math.round(diff).toLocaleString()}/mo (Break-even exceeded)` : `Cloud API is cheaper by $${Math.round(diff).toLocaleString()}/mo (Keep on API)`}
    </span>
  </div>
</div>
        `);
        break;
      }

      case "curl": {
        const target = (parts[1] || "today").toLowerCase();
        if (target.startsWith("http://") || target.startsWith("https://") || target.startsWith("-")) {
          printLine(`
            <div class="term-error">
              <span class="term-tag tag-error">EGRESS BLOCKED</span>
              <span>pith: network egress blocked: external HTTP queries restricted by firewall security policy. Permitted local telemetry endpoints: 'curl dev', 'curl founder', 'curl investor', 'curl matrix', 'curl news'.</span>
            </div>
          `);
        } else if (target === "dev" || target === "developer") {
          printLine(`{"role": "developer", "action": "DO THIS WEEK", "directive": "Pin system prompt tokens to provider prefix hash boundaries to cut recompute by 88%."}`);
        } else if (target === "founder" || target === "founders") {
          printLine(`{"role": "founder", "action": "WATCH TRIGGER", "directive": "Budget GPU cluster reservation once monthly volume crosses 40M tokens."}`);
        } else if (target === "investor" || target === "investors") {
          printLine(`{"role": "investor", "thesis": "Short thin agent wrappers; long private state schemas and chokepoint data access."}`);
        } else if (target === "matrix") {
          printLine(`{"quadrants": 4, "chokepoint": ["Nvidia CUDA", "TSMC"], "commodity": ["Standard Model APIs"], "squeezed": ["Thin Wrappers"]}`);
        } else if (target === "today" || target === "news") {
          printLine(`{"issue": "${new Date().toISOString().slice(0, 10)}", "status": "200 OK", "signal_count": 3, "top_story": "KV-Cache Eviction & Prefix Hashing"}`);
        } else {
          printLine(`
            <div class="term-error">
              <span class="term-tag tag-error">PERMISSION DENIED</span>
              <span>pith: curl: endpoint '<strong>${escapeHtml(target)}</strong>' not permitted. Allowed local endpoints: <span class="term-key">curl dev</span>, <span class="term-key">curl founder</span>, <span class="term-key">curl investor</span>, <span class="term-key">curl matrix</span>, <span class="term-key">curl today</span>.</span>
            </div>
          `);
        }
        break;
      }

      case "ls": {
        printLine(`
<pre style="color:#d1d5db; font-size:12.5px; margin:4px 0;">
drwxr-xr-x  2 guest guest  4096 Nov 20 06:00 <span style="color:var(--cyan);">.</span>
drwxr-xr-x  3 root  root   4096 Nov 20 06:00 <span style="color:var(--muted);">..</span>
-rw-r--r--  1 guest guest  3412 Nov 20 06:00 <span style="color:var(--good);">today.md</span>
-rw-r--r--  1 guest guest  8910 Nov 20 06:00 <span style="color:var(--good);">forecasts.json</span>
-rw-r--r--  1 guest guest  2104 Nov 20 06:00 <span style="color:var(--good);">market_matrix.csv</span>
-rw-r--r--  1 guest guest   640 Nov 20 06:00 <span style="color:#9ca3af;">system_telemetry.log</span>
-rw-r--r--  1 guest guest  1520 Nov 20 06:00 <span style="color:var(--gilt);">README.md</span>
</pre>
        `);
        break;
      }

      case "cat": {
        const filename = parts[1] || "";
        if (!filename) {
          printLine(`<div style="color:var(--red-ink);">cat: missing file operand. Try 'ls' to list files.</div>`);
        } else if (filename === "readme.md" || filename === "readme") {
          printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700;"># Pith Intelligence System</div>
  <div style="color:#d1d5db; margin-top:6px; font-size:13px;">
    Pith is a high-signal intelligence terminal for tracking structural shifts in artificial intelligence, chip infrastructure, and platform power.
    All forecasts are logged into a public immutable calibration ledger with mathematical Brier scoring.
  </div>
</div>
          `);
        } else if (filename === "today.md") {
          printLine(`
<div class="term-box">
  <div style="color:var(--gilt); font-weight:700;"># Today's Intelligence Brief</div>
  <div style="color:#d1d5db; font-size:12.5px; margin-top:4px;">
    1. KV-Cache Eviction &amp; Prefix Hashing Slashes Agent Memory Wall (Signal: 84.2)<br>
    2. Autonomous Computer-Use Protocol Open Sourced (Signal: 82.5)<br>
    3. Open Agent Protocol (OAP) Standardized under CNCF (Signal: 81.0)
  </div>
</div>
          `);
        } else if (filename === "forecasts.json") {
          printLine(`
<pre style="color:var(--cyan); font-size:12px; margin:4px 0;">
[
  {"id": "F-2025-01", "claim": "First commercial 1M-token context under $1/M", "status": "CONFIRMED", "brier": 0.00},
  {"id": "F-2025-02", "claim": "Prefix cache sharing becomes default in OpenAI/Anthropic SDKs", "status": "CONFIRMED", "brier": 0.00},
  {"id": "F-2026-01", "claim": "Open source agent protocol reaches Linux Foundation / CNCF", "status": "IN_REVIEW", "probability": 0.88}
]
</pre>
          `);
        } else if (filename === "market_matrix.csv") {
          printLine(`
<pre style="color:#d1d5db; font-size:12px; margin:4px 0;">
quadrant,name,market_power,switching_cost,verdict
chokepoint,Nvidia CUDA,very_high,extreme,DURABLE_MOAT
chokepoint,TSMC Fab,extreme,extreme,DURABLE_MOAT
moats_protocols,Private Workflow Data,high,high,COMPOUNDING
squeezed_middleware,Thin Wrapper Agents,low,low,COMMODITIZED
commodity_compute,Standard Model APIs,moderate,low,PRICE_WAR
</pre>
          `);
        } else if (filename === "system_telemetry.log") {
          printLine(`
<pre style="color:#9ca3af; font-size:12px; margin:4px 0;">
[INFO] Cluster state: ALL RUNTIMES OPTIMAL
[INFO] Hit rate: 100% | Brier: 0.0000 | Active ELO: 1200
[INFO] Telemetry stream verified across 7 static node endpoints.
</pre>
          `);
        } else {
          printLine(`
            <div class="term-error">
              <span class="term-tag tag-error">PERMISSION DENIED</span>
              <span>pith: cat: file '<strong>${escapeHtml(filename)}</strong>' is not permitted. File access is strictly restricted to sandbox intelligence files (<span class="term-key">today.md</span>, <span class="term-key">forecasts.json</span>, <span class="term-key">market_matrix.csv</span>, <span class="term-key">system_telemetry.log</span>, <span class="term-key">README.md</span>).</span>
            </div>
          `);
        }
        break;
      }

      case "whoami":
        printLine(`<div>pith-guest (uid=1001, gid=1001, security_level=read_only_analyst, sandbox=enforced)</div>`);
        break;

      case "pwd":
        printLine(`<div>/home/guest/pith-sandbox</div>`);
        break;

      case "uname":
        if (parts[1] === "-a" || parts[1] === "-r") {
          printLine(`<div>Linux pith-station 6.6.1-hardened #1 SMP PREEMPT PithOS x86_64 GNU/Linux (Guest Sandbox)</div>`);
        } else {
          printLine(`<div>Linux (PithOS Sandboxed)</div>`);
        }
        break;

      case "date":
        printLine(`<div>${new Date().toUTCString()}</div>`);
        break;

      case "uptime":
        printLine(`<div>12:05:40 up 42 days, 16:35, 1 user, load average: 0.06, 0.04, 0.01</div>`);
        break;

      case "echo":
        const echoText = rawTrimmed.substring(5);
        printLine(`<div>${escapeHtml(echoText)}</div>`);
        break;

      case "theme": {
        const targetTheme = (parts[1] || "").toLowerCase();
        if (targetTheme === "amber" || targetTheme === "emerald" || targetTheme === "green" || targetTheme === "cyan") {
          setPhosphorTheme(targetTheme);
          printLine(`<div style="color:var(--good);"><span class="term-tag tag-info">THEME</span> Terminal phosphor switched to <strong>${escapeHtml(targetTheme)}</strong>.</div>`);
        } else {
          printLine(`<div style="color:var(--muted);">Usage: theme [amber | emerald | cyan]</div>`);
        }
        break;
      }

      case "clear":
        if (termHistory) {
          termHistory.innerHTML = "";
        } else {
          termScreen.innerHTML = "";
        }
        break;

      case "exit":
      case "home":
        printLine(`<div style="color:var(--cyan);">Navigating back to Daily News...</div>`);
        setTimeout(() => { window.location.href = "index.html"; }, 300);
        break;

      default:
        printLine(`
          <div class="term-error">
            <span class="term-tag tag-error">PERMISSION DENIED</span>
            <span>pith: permission denied: command '<strong>${escapeHtml(rawTrimmed)}</strong>' is not permitted. Access is strictly restricted to approved intelligence terminal commands. Type '<span style="color:#fff; text-decoration:underline;">help</span>' for authorized commands.</span>
          </div>
        `);
        break;
    }
  }

  // Keyboard Navigation & Enter Execution
  termInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const val = termInput.value;
      termInput.value = "";
      executeCommand(val);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length > 0) {
        if (historyIdx > 0) historyIdx--;
        termInput.value = history[historyIdx] || "";
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx < history.length - 1) {
        historyIdx++;
        termInput.value = history[historyIdx] || "";
      } else {
        historyIdx = history.length;
        termInput.value = "";
      }
    }
  });

  // Quick Command Chips Click Handler
  document.querySelectorAll(".term-chip-btn[data-cmd]").forEach(btn => {
    btn.addEventListener("click", () => {
      const cmd = btn.getAttribute("data-cmd");
      if (cmd) {
        termInput.value = "";
        executeCommand(cmd);
      }
    });
  });

  // Focus terminal input on container click
  termScreen.addEventListener("click", () => termInput.focus());
}

// ------------------------------------------------------------------------------
// 15.4 Archive Vault Search Controller
// ------------------------------------------------------------------------------
function initArchivePage() {
  const searchInput = document.getElementById("archive-search-input");
  const clearBtn = document.getElementById("archive-clear-btn");
  if (!searchInput) return;

  function doSearch() {
    const q = searchInput.value.toLowerCase().trim();
    if (clearBtn) clearBtn.style.display = q ? "block" : "none";

    document.querySelectorAll(".archive-issue-block").forEach(block => {
      let matchedInBlock = false;
      const rows = block.querySelectorAll(".archive-card-row");
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (!q || text.includes(q)) {
          row.style.display = "flex";
          matchedInBlock = true;
        } else {
          row.style.display = "none";
        }
      });
      block.style.display = matchedInBlock ? "block" : "none";
    });
  }

  searchInput.addEventListener("input", doSearch);
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      searchInput.value = "";
      doSearch();
      searchInput.focus();
    });
  }

  // Heatmap day click
  document.querySelectorAll(".heatmap-day[data-date]").forEach(day => {
    day.addEventListener("click", () => {
      sound.playTick();
      const date = day.getAttribute("data-date");
      const block = document.getElementById(`issue-${date}`);
      if (block) {
        block.scrollIntoView({ behavior: "smooth", block: "start" });
        block.style.borderColor = "var(--gilt)";
        setTimeout(() => { block.style.borderColor = ""; }, 2000);
      }
    });
  });
}
