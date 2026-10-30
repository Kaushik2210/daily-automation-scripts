"use strict";
(() => {
  const meta = (name) => document.querySelector(`meta[name="app-${name}"]`)?.content ?? "";
  const MODE = meta("mode"); // "static" (GitHub Pages, runs in the browser) or "server" (local dashboard)
  const ROOT = meta("root") || "./";
  const TOKEN = meta("token");
  const PRESET = meta("tool");
  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  const CATS = {
    files: ["🗂️", "Files"], "pdf-docs": ["📄", "PDF & Docs"], github: ["🐙", "GitHub"],
    email: ["📬", "Email"], "web-scraping": ["🕷️", "Web"], "notion-productivity": ["🧠", "Productivity"],
    data: ["📊", "Data"], system: ["🖥️", "System"], security: ["🔐", "Security"],
    media: ["🎞️", "Media"], text: ["✍️", "Text"], devops: ["🚀", "DevOps"],
  };
  const SAMPLES = {
    "notes.txt": "buy milk\nbuy eggs\nbuy milk\ncall mum\n",
    "notes copy.txt": "buy milk\nbuy eggs\nbuy milk\ncall mum\n",
    "Report Final (1).CSV": "name,score\nada,10\nlin,7\nada,10\n",
    "Holiday Photo 01.JPG": "fake-image-bytes-1",
    "Holiday Photo 02.JPG": "fake-image-bytes-2",
    "readme.md": "# Sample\n\nHello from the sample workspace.\n\n## Usage\n\nRun a tool on this folder.\n",
  };
  const app = document.getElementById("app");
  const toastEl = document.getElementById("toast");
  let catalog = { tools: [], repo: "", cwd: "" };

  /* ---------- helpers ---------- */
  function h(tag, props = {}, ...kids) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value == null || value === false) continue;
      if (key === "class") el.className = value;
      else if (key === "text") el.textContent = value;
      else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? "" : value);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid);
    return el;
  }
  const quote = (s) => (/^[\w@%+=:,./\\-]+$/.test(s) ? s : `"${s.replace(/"/g, '\\"')}"`);
  const pyFile = (tool) => `${tool.name.replaceAll("-", "_")}.py`;
  const toolHref = (tool) => (MODE === "static" ? `${ROOT}tools/${tool.id}/` : `#${tool.id}`);
  let toastTimer;
  function toast(message) {
    toastEl.textContent = message;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 2200);
  }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied!");
    } catch {
      toast("Couldn't copy. Select the text and copy it.");
    }
  }
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ } },
  };

  /* ---------- argument handling (mirrors web/dashboard.py build_argv) ---------- */
  function buildArgv(args, values) {
    const options = [], positionals = [];
    for (const arg of args) {
      const value = values[arg.dest];
      const items = (Array.isArray(value) ? value : [value]).filter((v) => v !== null && v !== undefined && v !== "" && v !== false).map(String);
      if (arg.positional) {
        if (arg.required && !items.length) throw new Error(`${arg.metavar || arg.dest} is required`);
        positionals.push(...items);
        continue;
      }
      const flag = [...arg.flags].sort((a, b) => b.length - a.length)[0];
      if (arg.kind === "flag") { if (value === true) options.push(flag); continue; }
      if (arg.required && !items.length) throw new Error(`${flag} is required`);
      if (arg.kind === "multi" && arg.nargs) { if (items.length) options.push(flag, ...items); }
      else for (const item of items) options.push(flag, item);
    }
    return positionals.length ? [...options, "--", ...positionals] : options;
  }

  /* ---------- Pyodide (in-browser Python) ---------- */
  let pyodidePromise;
  function getPyodide() {
    pyodidePromise ??= new Promise((resolve, reject) => {
      const script = h("script", { src: `${PYODIDE}pyodide.js` });
      script.onload = () => window.loadPyodide({ indexURL: PYODIDE }).then(resolve, reject);
      script.onerror = () => reject(new Error("Couldn't download Python for the browser. Check your connection."));
      document.head.append(script);
    });
    return pyodidePromise;
  }
  const RUNNER = `
import contextlib, io, json, os, runpy, sys, traceback
os.chdir('/work')
sys.argv = [tool_path] + json.loads(argv_json)
sys.path.insert(0, os.path.dirname(tool_path))
sys.stdin = io.StringIO(stdin_text)
out, err = io.StringIO(), io.StringIO()
code = 0
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    try:
        runpy.run_path(tool_path, run_name='__main__')
    except SystemExit as exc:
        if exc.code is None:
            code = 0
        elif isinstance(exc.code, int):
            code = exc.code
        else:
            print(exc.code, file=sys.stderr)
            code = 1
    except BaseException:
        traceback.print_exc()
        code = 1
files = []
for base, _, names in os.walk('/work'):
    for name in names:
        full = os.path.join(base, name)
        files.append([full[len('/work/'):], os.path.getsize(full)])
json.dumps({'code': code, 'stdout': out.getvalue(), 'stderr': err.getvalue(), 'files': sorted(files)})
`;
  async function runInBrowser(tool, argv, stdin, uploads) {
    const started = performance.now();
    const py = await getPyodide();
    if (tool.browser?.packages?.length) await py.loadPackage(tool.browser.packages);
    const response = await fetch(ROOT + tool.source);
    if (!response.ok) throw new Error("Couldn't load the tool's source code.");
    py.FS.mkdirTree("/tool");
    py.FS.writeFile(`/tool/${pyFile(tool)}`, await response.text());
    py.runPython("import os, shutil\nshutil.rmtree('/work', ignore_errors=True)\nos.makedirs('/work')");
    for (const [path, file] of uploads) {
      const dir = path.split("/").slice(0, -1).join("/");
      if (dir) py.FS.mkdirTree(`/work/${dir}`);
      py.FS.writeFile(`/work/${path}`, new Uint8Array(await file.arrayBuffer()));
    }
    py.globals.set("tool_path", `/tool/${pyFile(tool)}`);
    py.globals.set("argv_json", JSON.stringify(argv));
    py.globals.set("stdin_text", stdin);
    const result = JSON.parse(py.runPython(RUNNER));
    return {
      exit_code: result.code, stdout: result.stdout, stderr: result.stderr, timed_out: false,
      seconds: Math.round((performance.now() - started) / 10) / 100,
      files: result.files.map(([path, size]) => ({ path, size, isNew: !uploads.has(path) || uploads.get(path).size !== size })),
    };
  }
  async function runOnServer(tool, values, stdin) {
    const reply = await fetch("api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Dashboard-Token": TOKEN },
      body: JSON.stringify({ script: tool.id, values, stdin }),
    });
    const body = await reply.json();
    if (!reply.ok) throw new Error(body.error || "The server refused that request.");
    return body;
  }

  /* ---------- catalog ---------- */
  async function loadCatalog() {
    const reply = await fetch(MODE === "static" ? `${ROOT}data/tools.json` : "api/scripts");
    if (!reply.ok) throw new Error("Couldn't load the tool list.");
    const data = await reply.json();
    catalog = { tools: data.tools || data.scripts || [], repo: data.repo || "", cwd: data.cwd || "" };
  }

  /* ---------- shared chrome ---------- */
  function topbar() {
    return h("header", { class: "topbar" },
      h("a", { class: "logo", href: MODE === "static" ? ROOT : "#" }, "⚡ DAS"),
      h("nav", { class: "nav", "aria-label": "Site" },
        catalog.repo && h("a", { class: "pill", href: catalog.repo, rel: "noopener" }, "★ GitHub"),
        h("a", { class: "pill", href: MODE === "static" ? ROOT : "#" }, "All tools")));
  }
  function footer() {
    return h("footer", { class: "foot" },
      h("span", {}, "Made with way too much colour. MIT licensed."),
      h("span", {}, MODE === "static" ? "Runs in your browser. Files never leave your device." : "Running locally on your computer."));
  }
  function mount(...nodes) {
    app.replaceChildren(h("div", { class: "wrap" }, topbar(), h("main", { id: "main" }, nodes), footer()));
    window.scrollTo(0, 0);
  }
  function badges(tool) {
    const ok = MODE === "server" || tool.browser?.ok;
    return h("div", { class: "badges" },
      tool.day && h("span", { class: "badge day" }, `Day ${tool.day}`),
      h("span", { class: `badge ${ok ? "ok" : "local"}` }, MODE === "server" ? "Runs here" : ok ? "Runs in browser" : "Local only"));
  }

  /* ---------- home ---------- */
  function renderHome() {
    document.title = "Daily Automation Scripts";
    const tools = catalog.tools;
    const cats = [...new Set(tools.map((t) => t.category))].sort();
    let query = "", active = "all";
    const grid = h("ul", { class: "grid", "aria-label": "Tools" });
    const count = h("p", { class: "count", role: "status" });
    const chips = h("div", { class: "chips", role: "group", "aria-label": "Filter by category" });

    const card = (t) => {
      const [emoji] = CATS[t.category] || ["🧩"];
      return h("li", { class: `card cat-${t.category}` },
        h("a", { class: "card-link", href: toolHref(t) },
          h("span", { class: "emoji", "aria-hidden": "true" }, emoji),
          h("h3", {}, t.name),
          h("p", {}, t.summary || "Open to see what it does."),
          badges(t)));
    };
    const draw = () => {
      const q = query.trim().toLowerCase();
      const shown = tools.filter((t) => (active === "all" || t.category === active)
        && (!q || `${t.name} ${t.summary} ${t.category}`.toLowerCase().includes(q)));
      grid.replaceChildren(...shown.map(card));
      if (!shown.length) grid.replaceChildren(h("li", { class: "empty" }, "Nothing matches. Try another word!"));
      count.textContent = `${shown.length} of ${tools.length} tools`;
      for (const chip of chips.children) chip.setAttribute("aria-pressed", String(chip.dataset.cat === active));
    };
    for (const cat of ["all", ...cats]) {
      const label = cat === "all" ? "🌈 All" : `${CATS[cat]?.[0] || "🧩"} ${CATS[cat]?.[1] || cat}`;
      chips.append(h("button", { class: "chip", type: "button", "data-cat": cat, "aria-pressed": "false",
        onclick: () => { active = cat; draw(); } }, label));
    }
    const words = ["RENAME", "DEDUPE", "ORGANIZE", "CLEAN", "COUNT", "CONVERT", "SORT", "SCAN", "BACK UP", "REPORT"];
    const strip = [...words, ...words].map((w) => h("span", {}, `✦ ${w}`));
    mount(
      h("section", { class: "hero" },
        h("div", { class: "sticker", "aria-hidden": "true" }, "30 days", h("br"), "300 tools"),
        h("h1", {}, "Daily Automation Scripts"),
        h("p", {}, MODE === "static"
          ? "Small, tested Python tools for the boring stuff. Pick one and run it right here in your browser. No install, no upload."
          : "Small, tested Python tools for the boring stuff. Pick one and run it on this computer."),
        h("div", { class: "stats" },
          h("div", { class: "stat" }, h("b", {}, String(tools.length)), h("span", {}, "tools live")),
          h("div", { class: "stat" }, h("b", {}, String(cats.length)), h("span", {}, "categories")),
          h("div", { class: "stat" }, h("b", {}, String(tools.filter((t) => MODE === "server" || t.browser?.ok).length)), h("span", {}, "run in browser")),
          h("div", { class: "stat" }, h("b", {}, "MIT"), h("span", {}, "free to use")))),
      h("div", { class: "marquee", "aria-hidden": "true" }, h("div", {}, strip)),
      h("section", { class: "controls" },
        h("input", { class: "search", type: "search", placeholder: "🔍 Search tools…", "aria-label": "Search tools",
          oninput: (e) => { query = e.target.value; draw(); } }),
        chips, count),
      grid);
    draw();
  }

  /* ---------- tool page ---------- */
  function field(arg, getters, saved) {
    const id = `f-${arg.dest}`;
    const label = arg.flags.length ? arg.flags[arg.flags.length - 1] : (arg.metavar || arg.dest);
    const start = saved[arg.dest] ?? arg.default;
    const help = arg.help && h("p", { class: "help", id: `${id}-help` }, arg.help);
    const describedBy = arg.help ? `${id}-help` : null;
    if (arg.kind === "flag") {
      const box = h("input", { type: "checkbox", id, role: "switch", "aria-describedby": describedBy, checked: start === true });
      getters[arg.dest] = () => box.checked;
      return h("div", { class: "field" }, h("div", { class: "switch" }, h("label", { for: id }, h("code", {}, label)), box), help);
    }
    let control;
    if (arg.choices && arg.choices.length <= 5) {
      const name = `r-${arg.dest}`;
      const choose = start ?? arg.choices[0];
      control = h("div", { class: "seg", role: "radiogroup", "aria-labelledby": `${id}-l` },
        arg.choices.flatMap((c, i) => [
          h("input", { type: "radio", name, id: `${id}-${i}`, value: c, checked: String(c) === String(choose) }),
          h("label", { for: `${id}-${i}` }, String(c))]));
      getters[arg.dest] = () => control.querySelector("input:checked")?.value ?? "";
    } else if (arg.choices) {
      control = h("select", { id, "aria-describedby": describedBy }, arg.choices.map((c) => h("option", { value: c, selected: String(c) === String(start) }, String(c))));
      getters[arg.dest] = () => control.value;
    } else if (arg.kind === "multi") {
      const text = Array.isArray(start) ? start.join("\n") : "";
      control = h("textarea", { id, "aria-describedby": describedBy, placeholder: "One value per line", spellcheck: "false" });
      control.value = text;
      getters[arg.dest] = () => control.value.split("\n").map((s) => s.trim()).filter(Boolean);
    } else {
      const numeric = arg.type === "int" || arg.type === "float";
      control = h("input", { id, type: numeric ? "number" : "text", step: arg.type === "float" ? "any" : numeric ? "1" : null,
        "aria-describedby": describedBy, spellcheck: "false", autocomplete: "off",
        placeholder: arg.metavar || (arg.type === "Path" ? "path/to/it" : "") });
      control.value = start ?? "";
      getters[arg.dest] = () => control.value;
    }
    return h("div", { class: "field" },
      h("label", { for: id, id: `${id}-l` }, h("code", {}, label), arg.required && h("span", { class: "req" }, "required")), control, help);
  }

  async function renderTool(id) {
    let tool = catalog.tools.find((t) => t.id === id);
    if (!tool) {
      mount(h("div", { class: "panel" }, h("h2", {}, "Not found"), h("p", {}, "That tool doesn't exist (yet)."), h("p", {}, h("a", { href: MODE === "static" ? ROOT : "#" }, "Back to all tools"))));
      return;
    }
    if (!tool.schema) Object.assign(tool, await (await fetch(`api/scripts/${id}`)).json());
    document.title = `${tool.name} · Daily Automation Scripts`;
    const schema = tool.schema || { arguments: [] };
    const sections = tool.sections || {};
    const canRun = MODE === "server" || tool.browser?.ok;
    const args = schema.arguments || [];
    const applyArg = args.find((a) => a.dest === "apply" && a.kind === "flag");
    const saved = store.get(`das:${id}`) || {};
    const getters = {};
    const uploads = new Map();

    const form = h("form", { novalidate: true, autocomplete: "off" });
    const cmd = h("pre", { class: "cmd", "aria-label": "Equivalent command" });
    const results = h("section", { class: "panel results", "aria-live": "polite" },
      h("h2", {}, "Results"), h("p", { class: "help" }, "Hit run and the output shows up here."));

    const put = (...nodes) => results.replaceChildren(...nodes.flat().filter(Boolean));
    const collect = () => {
      const values = {};
      for (const [dest, get] of Object.entries(getters)) values[dest] = get();
      if (applyArg) values.apply = form.querySelector("input[name=mode]:checked")?.value === "apply";
      return values;
    };
    const updateCmd = () => {
      let text;
      try { text = ["python", `scripts/${tool.category}/${tool.name}/${pyFile(tool)}`, ...buildArgv(args, collect()).map(quote)].join(" "); }
      catch (err) { text = `# ${err.message}`; }
      cmd.textContent = text;
      store.set(`das:${id}`, collect());
    };

    for (const arg of args) {
      if (arg === applyArg) continue;
      form.append(field(arg, getters, saved));
    }
    if (!args.length || (args.length === 1 && applyArg)) form.prepend(h("p", { class: "help" }, "This tool has no extra options."));
    let runLabel = "▶ Run";
    if (applyArg) {
      runLabel = "👀 Preview";
      form.prepend(h("div", { class: "field mode" }, h("div", { class: "label" }, h("code", {}, "mode")),
        h("div", { class: "seg", role: "radiogroup", "aria-label": "Mode" },
          h("input", { type: "radio", name: "mode", id: "m-prev", value: "preview", checked: !saved.apply }),
          h("label", { for: "m-prev" }, "👀 Preview (dry run)"),
          h("input", { type: "radio", name: "mode", id: "m-apply", value: "apply", checked: saved.apply === true }),
          h("label", { for: "m-apply" }, "⚡ Apply changes")),
        h("p", { class: "help" }, "Preview shows what would happen and changes nothing. Apply really does it.")));
    }
    const runBtn = h("button", { class: "btn", type: "submit", disabled: !canRun }, runLabel);
    const syncLabel = () => { runBtn.textContent = applyArg && collect().apply ? "⚡ Apply" : applyArg ? "👀 Preview" : "▶ Run"; };

    /* workspace panel (browser mode only) */
    let workspace = null;
    if (MODE === "static" && canRun) {
      const list = h("div", { class: "files" });
      const drawFiles = () => list.replaceChildren(...[...uploads].map(([path, file]) =>
        h("div", { class: "file" }, h("span", {}, `${path} · ${file.size} B`),
          h("button", { class: "btn alt", type: "button", onclick: () => { uploads.delete(path); drawFiles(); } }, "Remove"))));
      const add = (files) => { for (const f of files) uploads.set(f.webkitRelativePath || f.name, f); drawFiles(); };
      const pick = (dir) => { const i = h("input", { type: "file", multiple: true, webkitdirectory: dir || null, hidden: true, onchange: () => add(i.files) }); i.click(); };
      workspace = h("section", { class: "panel" }, h("h2", {}, "Workspace"),
        h("p", {}, "Add files or a folder. They stay inside your browser and show up to the tool as the current folder (use ", h("code", {}, "."), " as the path)."),
        h("div", { class: "actions" },
          h("button", { class: "btn alt", type: "button", onclick: () => pick(false) }, "📎 Add files"),
          h("button", { class: "btn alt", type: "button", onclick: () => pick(true) }, "📁 Add a folder"),
          h("button", { class: "btn alt", type: "button", onclick: () => { for (const [n, c] of Object.entries(SAMPLES)) uploads.set(n, new File([c], n)); drawFiles(); toast("Sample files added"); } }, "🎲 Sample files")),
        list);
    }

    const dialog = h("dialog", {}, h("h2", {}, "Apply changes?"),
      h("p", { class: "help" }, "This will really change files on your computer. Run a preview first if you aren't sure."),
      h("div", { class: "actions" },
        h("button", { class: "btn", type: "button", onclick: () => dialog.close() }, "Cancel"),
        h("button", { class: "btn danger", type: "button", onclick: () => { dialog.close(); go(); } }, "Yes, apply")));

    async function go() {
      const values = collect();
      let argv;
      try { argv = buildArgv(args, values); } catch (err) { toast(err.message); return; }
      runBtn.disabled = true;
      put(h("h2", {}, "Results"), h("span", { class: "status wait" }, MODE === "static" ? "⏳ Warming up Python…" : "⏳ Running…"), h("div", { class: "bar" }));
      try {
        const stdin = "";
        const res = MODE === "static" ? await runInBrowser(tool, argv, stdin, uploads) : await runOnServer(tool, values, stdin);
        const good = res.exit_code === 0;
        put(h("h2", {}, "Results"),
          h("span", { class: `status ${good ? "" : "bad"}` }, res.timed_out ? "⏱ Timed out" : good ? "✅ Done" : `❌ Exit ${res.exit_code}`),
          h("span", { class: "help" }, ` ${res.seconds}s`),
          res.stdout ? h("pre", { class: "out" }, res.stdout) : h("p", { class: "help" }, "No output."),
          res.stderr && h("pre", { class: "out err" }, res.stderr),
          res.files?.length ? h("div", { class: "files" }, h("p", { class: "help" }, "Workspace after the run:"),
            res.files.map((f) => h("div", { class: "file" }, h("span", {}, f.path, f.isNew && h("span", { class: "badge ok" }, "new or changed")),
              h("button", { class: "btn alt", type: "button", onclick: async () => {
                const py = await getPyodide();
                const url = URL.createObjectURL(new Blob([py.FS.readFile(`/work/${f.path}`)]));
                h("a", { href: url, download: f.path.split("/").pop() }).click();
                setTimeout(() => URL.revokeObjectURL(url), 5000);
              } }, "Download")))) : null);
      } catch (err) {
        put(h("h2", {}, "Results"), h("span", { class: "status bad" }, "❌ Couldn't run"), h("pre", { class: "out err" }, err.message));
      } finally { runBtn.disabled = !canRun; }
    }
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (MODE === "server" && applyArg && collect().apply) dialog.showModal(); else go();
    });
    form.addEventListener("input", () => { updateCmd(); syncLabel(); });
    form.addEventListener("change", () => { updateCmd(); syncLabel(); });

    const [emoji, label] = CATS[tool.category] || ["🧩", tool.category];
    const sourceUrl = catalog.repo && `${catalog.repo}/blob/main/scripts/${tool.category}/${tool.name}/${pyFile(tool)}`;
    mount(
      h("p", { class: "crumbs" }, h("a", { class: "pill", href: MODE === "static" ? ROOT : "#" }, "← All tools")),
      h("section", { class: `tool-head cat-${tool.category}` },
        h("h1", {}, tool.name),
        h("p", {}, `${emoji} ${label} · ${tool.summary || ""}`), badges(tool)),
      !canRun && h("div", { class: "notice", style: null }, `This one can't run in a browser (${tool.browser?.reason || "it needs your computer"}). Run it locally with the command below.`),
      h("div", { class: `layout cat-${tool.category}` },
        h("div", {},
          h("section", { class: "panel" }, h("h2", {}, "About"),
            h("p", { class: "about" }, sections.Purpose || tool.summary || ""),
            sections.Notes && h("p", { class: "help about" }, sections.Notes)),
          workspace,
          h("section", { class: "panel" }, h("h2", {}, "Options"), form,
            h("div", { class: "actions" }, runBtn, sourceUrl && h("a", { class: "pill", href: sourceUrl, rel: "noopener" }, "{ } Source"))),
          h("section", { class: "panel" }, h("h2", {}, "Command"), cmd,
            h("div", { class: "actions" }, h("button", { class: "btn alt", type: "button", onclick: () => copy(cmd.textContent) }, "📋 Copy")))),
        h("div", {}, results)),
      dialog);
    updateCmd();
    syncLabel();
  }

  /* ---------- boot ---------- */
  function route() {
    const id = PRESET || location.hash.slice(1);
    return id ? renderTool(id) : renderHome();
  }
  loadCatalog().then(route).catch((err) => {
    app.replaceChildren(h("div", { class: "wrap" }, h("div", { class: "panel" }, h("h2", {}, "Oops"), h("p", {}, err.message))));
  });
  if (MODE === "server") window.addEventListener("hashchange", route);
})();
