"use strict";
/* Visual effects: intro curtain, generative artwork, custom cursor, scroll reveals,
   magnetic buttons, card tilt, parallax, progress bar and theme switch.
   Everything is switched off for people who prefer reduced motion. */
(() => {
  const root = document.documentElement;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const get = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const put = (key, value) => { try { localStorage.setItem(key, value); } catch { /* storage unavailable */ } };

  /* ---------- theme ---------- */
  const savedTheme = get("das:theme");
  if (savedTheme) root.dataset.theme = savedTheme;
  function toggleTheme() {
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    put("das:theme", root.dataset.theme);
  }

  /* ---------- generative artwork ---------- */
  const INK = "#0c0c10", PAPER = "#f3f0ea", BLUE = "#2323ff", LIME = "#d6ff3d", LAV = "#c9c6ff", CORAL = "#ff6b4a";
  const PALETTES = [
    [BLUE, PAPER, INK, LIME], [INK, LIME, BLUE, PAPER], [LIME, INK, BLUE, PAPER],
    [PAPER, BLUE, INK, LAV], [LAV, INK, BLUE, LIME], [BLUE, LAV, LIME, INK],
    [CORAL, INK, PAPER, BLUE], [INK, PAPER, BLUE, CORAL],
  ];
  const hash = (text) => { let h = 2166136261; for (const c of text) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function rng(seed) {
    let a = seed;
    return () => {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const el = (tag, attrs = {}, ...kids) => {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    node.append(...kids);
    return node;
  };
  const PATTERNS = {
    tiles(r, [bg, a, b, c]) { // Bauhaus quarter-circles
      const g = el("g"); const cols = [a, b, c, a];
      for (let y = 0; y < 3; y++) for (let x = 0; x < 4; x++) {
        const fill = cols[Math.floor(r() * cols.length)], kind = Math.floor(r() * 5);
        const cx = x * 100, cy = y * 100 + 0;
        if (kind === 0) g.append(el("circle", { cx: cx + 50, cy: cy + 50, r: 46, fill }));
        else if (kind === 1) g.append(el("path", { d: `M${cx} ${cy + 100}A100 100 0 0 1 ${cx + 100} ${cy}V${cy + 100}Z`, fill }));
        else if (kind === 2) g.append(el("path", { d: `M${cx} ${cy}h100a100 100 0 0 1 -100 100Z`, fill }));
        else if (kind === 3) g.append(el("rect", { x: cx + 12, y: cy + 12, width: 76, height: 76, rx: 38, fill }));
      }
      return g;
    },
    rings(r, [bg, a, b, c]) {
      const g = el("g"), cx = 120 + r() * 160, cy = 90 + r() * 120;
      for (let i = 9; i > 0; i--) g.append(el("circle", { cx: cx + (9 - i) * 6, cy: cy - (9 - i) * 4, r: i * 22, fill: i % 3 === 0 ? c : i % 2 ? a : b }));
      return g;
    },
    stripes(r, [bg, a, b, c]) {
      const g = el("g", { transform: `rotate(${-20 + r() * 40} 200 150)` });
      let y = -120;
      while (y < 420) { const h = 14 + r() * 52; g.append(el("rect", { x: -120, y, width: 640, height: h, fill: [a, b, c][Math.floor(r() * 3)] })); y += h + 8 + r() * 24; }
      return g;
    },
    dots(r, [bg, a, b, c]) {
      const g = el("g"), size = 5 + Math.floor(r() * 3);
      for (let y = 0; y < size; y++) for (let x = 0; x < size * 1.4; x++) {
        const d = Math.hypot(x / (size * 1.4) - 0.5, y / size - 0.5);
        g.append(el("circle", { cx: 20 + x * (360 / (size * 1.4)), cy: 20 + y * (260 / size), r: Math.max(1.5, 22 * (1 - d * 1.4) * (0.5 + r() * 0.7)), fill: d < 0.28 ? c : a }));
      }
      return g;
    },
    waves(r, [bg, a, b, c]) {
      const g = el("g");
      for (let i = 0; i < 7; i++) {
        const y = 30 + i * 38, amp = 14 + r() * 36, ph = r() * 6;
        let d = `M-10 ${y}`;
        for (let x = 0; x <= 410; x += 10) d += `L${x} ${y + Math.sin(x / 38 + ph) * amp}`;
        g.append(el("path", { d: `${d}L410 320L-10 320Z`, fill: [a, b, c][i % 3], opacity: 0.92 }));
      }
      return g;
    },
    arches(r, [bg, a, b, c]) {
      const g = el("g"), n = 3 + Math.floor(r() * 2), w = 400 / n;
      for (let i = 0; i < n; i++) {
        const h = 120 + r() * 150;
        g.append(el("path", { d: `M${i * w + 8} 310V${310 - h + w / 2}a${w / 2 - 8} ${w / 2 - 8} 0 0 1 ${w - 16} 0V310Z`, fill: [a, b, c][i % 3] }));
      }
      g.append(el("circle", { cx: 60 + r() * 280, cy: 70 + r() * 40, r: 26 + r() * 20, fill: c }));
      return g;
    },
  };
  const PATTERN_NAMES = Object.keys(PATTERNS);
  function thumb(name, category = "") {
    const seed = hash(name), r = rng(seed);
    const palette = PALETTES[(hash(category || name) + (seed % 3)) % PALETTES.length];
    const picture = el("svg", { viewBox: "0 0 400 300", preserveAspectRatio: "xMidYMid slice", role: "img", "aria-hidden": "true" },
      el("rect", { width: 400, height: 300, fill: palette[0] }),
      PATTERNS[PATTERN_NAMES[seed % PATTERN_NAMES.length]](r, palette));
    picture.classList.add("art");
    return picture;
  }

  /* ---------- intro curtain ---------- */
  function intro() {
    let seen = false;
    try { seen = sessionStorage.getItem("das:seen") === "1"; sessionStorage.setItem("das:seen", "1"); } catch { /* ignore */ }
    if (reduce || seen) { root.classList.add("ready"); return; }
    const num = document.createElement("span");
    num.className = "loader-num";
    num.textContent = "0";
    const word = document.createElement("span");
    word.className = "loader-word";
    word.textContent = "Daily Automation";
    const curtain = document.createElement("div");
    curtain.className = "loader";
    curtain.setAttribute("aria-hidden", "true");
    curtain.append(word, num);
    document.body.prepend(curtain);
    const started = performance.now(), length = 1000;
    const tick = (now) => {
      const p = Math.min(1, (now - started) / length);
      num.textContent = String(Math.round((1 - (1 - p) ** 3) * 100));
      if (p < 1) { requestAnimationFrame(tick); return; }
      curtain.classList.add("done");
      root.classList.add("ready");
      setTimeout(() => curtain.remove(), 1100);
    };
    requestAnimationFrame(tick);
  }

  /* ---------- scroll, cursor and pointer effects ---------- */
  const bound = new WeakSet();
  let io, parallaxItems = [];
  function counter(node) {
    const target = Number(node.dataset.count) || 0;
    if (reduce) { node.textContent = String(target); return; }
    const started = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - started) / 1100);
      node.textContent = String(Math.round((1 - (1 - p) ** 4) * target));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  function observe(scope = document) {
    io ??= new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("in");
        if (entry.target.dataset.count) counter(entry.target);
        io.unobserve(entry.target);
      }
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    for (const node of scope.querySelectorAll("[data-reveal], [data-count]")) {
      if (bound.has(node)) continue;
      bound.add(node);
      if (reduce) { node.classList.add("in"); if (node.dataset.count) node.textContent = node.dataset.count; } else io.observe(node);
    }
    parallaxItems = [...document.querySelectorAll("[data-parallax]")];
    if (reduce || !fine) return;
    for (const node of scope.querySelectorAll("[data-magnetic]")) {
      if (bound.has(node)) continue;
      bound.add(node);
      node.addEventListener("pointermove", (e) => {
        const box = node.getBoundingClientRect();
        node.style.setProperty("--tx", `${(e.clientX - box.left - box.width / 2) * 0.22}px`);
        node.style.setProperty("--ty", `${(e.clientY - box.top - box.height / 2) * 0.3}px`);
      });
      node.addEventListener("pointerleave", () => { node.style.setProperty("--tx", "0px"); node.style.setProperty("--ty", "0px"); });
    }
    for (const node of scope.querySelectorAll("[data-tilt]")) {
      if (bound.has(node)) continue;
      bound.add(node);
      node.addEventListener("pointermove", (e) => {
        const box = node.getBoundingClientRect();
        node.style.setProperty("--ry", `${((e.clientX - box.left) / box.width - 0.5) * 7}deg`);
        node.style.setProperty("--rx", `${-((e.clientY - box.top) / box.height - 0.5) * 7}deg`);
      });
      node.addEventListener("pointerleave", () => { node.style.setProperty("--rx", "0deg"); node.style.setProperty("--ry", "0deg"); });
    }
  }

  function setup() {
    const progress = document.querySelector(".progress i");
    let lastY = 0, ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const y = window.scrollY, max = document.documentElement.scrollHeight - innerHeight;
        if (progress) progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
        const top = document.querySelector(".top");
        if (top) {
          top.classList.toggle("stuck", y > 8);
          top.classList.toggle("hide", y > 160 && y > lastY + 4);
          if (y < lastY - 4) top.classList.remove("hide");
        }
        if (!reduce) for (const item of parallaxItems) {
          const box = item.parentElement.getBoundingClientRect();
          const offset = (box.top + box.height / 2 - innerHeight / 2) * Number(item.dataset.parallax || 0.1);
          item.style.setProperty("--py", `${offset.toFixed(1)}px`);
        }
        lastY = y;
        ticking = false;
      });
    };
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("resize", onScroll);
    onScroll();
    if (reduce || !fine) return;

    const dot = Object.assign(document.createElement("div"), { className: "cursor" });
    const ring = Object.assign(document.createElement("div"), { className: "cursor-ring" });
    const label = Object.assign(document.createElement("span"), { textContent: "" });
    ring.append(label);
    document.body.append(ring, dot);
    document.body.classList.add("has-cursor");
    let mx = innerWidth / 2, my = innerHeight / 2, rx = mx, ry = my, queued = false;
    addEventListener("pointermove", (e) => {
      mx = e.clientX; my = e.clientY;
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0)`;
      if (!queued) {
        queued = true;
        requestAnimationFrame(() => { root.style.setProperty("--mx", `${mx}px`); root.style.setProperty("--my", `${my}px`); queued = false; });
      }
    });
    const follow = () => {
      rx += (mx - rx) * 0.18; ry += (my - ry) * 0.18;
      ring.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      requestAnimationFrame(follow);
    };
    follow();
    document.addEventListener("pointerover", (e) => {
      const card = e.target.closest?.(".card-link");
      const link = e.target.closest?.("a, button, label, summary, select");
      const field = e.target.closest?.("input[type=text], input[type=number], input[type=search], textarea");
      ring.classList.toggle("on-card", !!card);
      ring.classList.toggle("on-link", !!link && !card);
      ring.classList.toggle("on-field", !!field);
      label.textContent = card ? "Open" : "";
    });
    document.addEventListener("pointerleave", () => ring.classList.add("gone"));
    document.addEventListener("pointerenter", () => ring.classList.remove("gone"));
    document.addEventListener("pointerdown", () => ring.classList.add("press"));
    document.addEventListener("pointerup", () => ring.classList.remove("press"));
  }

  intro();
  document.addEventListener("DOMContentLoaded", setup);
  window.FX = { thumb, observe, toggleTheme, reduce };
})();
