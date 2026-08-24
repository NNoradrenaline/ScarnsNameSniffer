(() => {
  "use strict";

  const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
  const LOWER = "abcdefghijkmnopqrstuvwxyz";
  const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const DIGITS = "23456789";
  const SYMBOLS = "!@#$%";
  const ALL = LOWER + UPPER + DIGITS + SYMBOLS;
  let finished = false;
  let generatedPassword = null;

  function randomIndex(max) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    return buf[0] % max;
  }

  function pick(chars) {
    return chars[randomIndex(chars.length)];
  }

  function makePassword(length = 16) {
    const chars = [pick(LOWER), pick(UPPER), pick(DIGITS), pick(SYMBOLS)];
    while (chars.length < length) chars.push(pick(ALL));
    for (let i = chars.length - 1; i > 0; i--) {
      const j = randomIndex(i + 1);
      [chars[i], chars[j]] = [chars[j], chars[i]];
    }
    return chars.join("");
  }

  function isVisible(el) {
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function firstVisible(selectors) {
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        if (isVisible(el)) return el;
      }
    }
    return null;
  }

  function fromLabel(text) {
    const target = text.toLowerCase();
    for (const label of document.querySelectorAll("label")) {
      if (!label.textContent.toLowerCase().includes(target)) continue;
      if (label.htmlFor) {
        const input = document.getElementById(label.htmlFor);
        if (input && isVisible(input)) return input;
      }
      const nested = label.querySelector("input");
      if (nested && isVisible(nested)) return nested;
    }
    return null;
  }

  function findFields() {
    const username = firstVisible([
      'input[name="username"]',
      'input[autocomplete="username"]',
      'input[id*="username" i]',
      'input[placeholder*="username" i]'
    ]) || fromLabel("username");

    const password = firstVisible([
      'input[autocomplete="new-password"]',
      'input[name="password"]',
      'input[id*="password" i]',
      'input[placeholder*="password" i]',
      'input[type="password"]'
    ]) || fromLabel("password");

    return { username, password };
  }

  function setNativeValue(input, value) {
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    if (descriptor?.set) descriptor.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function readClipboard() {
    try {
      const text = (await navigator.clipboard.readText()).trim();
      return USERNAME_RE.test(text) ? text : null;
    } catch (_) {
      return null;
    }
  }

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;opacity:0;pointer-events:none";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    }
  }

  function makePanel(username, password) {
    document.getElementById("scarn-sniffer-autofill")?.remove();
    const box = document.createElement("div");
    box.id = "scarn-sniffer-autofill";
    box.style.cssText = [
      "position:fixed", "right:18px", "top:18px", "z-index:2147483647",
      "width:330px", "padding:16px", "border-radius:12px",
      "background:#0f141c", "color:#eef4ff", "border:1px solid #314052",
      "box-shadow:0 18px 50px rgba(0,0,0,.45)",
      "font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif"
    ].join(";");

    box.innerHTML = `
      <div style="font-weight:800;font-size:15px;margin-bottom:10px">🔎 Scarn's Name Sniffer</div>
      <div style="color:#9fb0c2;margin-bottom:10px">Autofilled <b style="color:#53f59a"></b></div>
      <div style="font-size:12px;color:#7f93a8;margin-bottom:4px">Generated password</div>
      <code data-pw style="display:block;padding:9px 10px;background:#080b10;border-radius:8px;color:#65d9ff;word-break:break-all">••••••••••••••••</code>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button data-show style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Show</button>
        <button data-copy style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Copy password</button>
      </div>
      <div style="margin-top:10px;color:#8fa1b3;font-size:12px">Save this password before creating the account. The companion never presses Create Account for you.</div>
    `;
    box.querySelector("b").textContent = username;

    const pw = box.querySelector("[data-pw]");
    const show = box.querySelector("[data-show]");
    const copy = box.querySelector("[data-copy]");
    let visible = false;

    show.addEventListener("click", () => {
      visible = !visible;
      pw.textContent = visible ? password : "••••••••••••••••";
      show.textContent = visible ? "Hide" : "Show";
    });

    copy.addEventListener("click", async () => {
      const ok = await writeClipboard(password);
      copy.textContent = ok ? "Copied ✓" : "Copy failed";
      setTimeout(() => { copy.textContent = "Copy password"; }, 1600);
    });

    document.documentElement.appendChild(box);
  }

  function makeRetryPanel() {
    if (document.getElementById("scarn-sniffer-autofill")) return;
    const box = document.createElement("div");
    box.id = "scarn-sniffer-autofill";
    box.style.cssText = "position:fixed;right:18px;top:18px;z-index:2147483647;width:300px;padding:15px;border-radius:12px;background:#0f141c;color:#eef4ff;border:1px solid #314052;font:14px system-ui;box-shadow:0 18px 50px rgba(0,0,0,.45)";
    box.innerHTML = `<b>🔎 Scarn's Name Sniffer</b><div style="margin:9px 0;color:#9fb0c2">I couldn't read the username from the clipboard automatically.</div><button style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:8px 11px;cursor:pointer;font-weight:700">Autofill now</button>`;
    box.querySelector("button").addEventListener("click", async () => {
      const username = await readClipboard();
      if (username) await fill(username);
      else box.querySelector("div").textContent = "Clipboard doesn't contain a Roblox-style username. Choose a name in Name Sniffer again.";
    });
    document.documentElement.appendChild(box);
  }

  async function fill(username) {
    if (finished || !USERNAME_RE.test(username)) return false;
    const fields = findFields();
    if (!fields.username || !fields.password) return false;

    generatedPassword ||= makePassword();
    setNativeValue(fields.username, username);
    setNativeValue(fields.password, generatedPassword);
    finished = true;
    makePanel(username, generatedPassword);
    return true;
  }

  async function start() {
    let username = await readClipboard();

    for (let attempt = 0; attempt < 40 && !finished; attempt++) {
      if (!username) username = await readClipboard();
      if (username && await fill(username)) return;
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    if (!finished) makeRetryPanel();
  }

  start();
})();
