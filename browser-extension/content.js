(() => {
  "use strict";

  const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
  const PAYLOAD_PREFIX = "SCARN_AUTOFILL_V2|";
  const LOWER = "abcdefghijkmnopqrstuvwxyz";
  const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
  const DIGITS = "23456789";
  const SYMBOLS = "!@#$%";
  const ALL = LOWER + UPPER + DIGITS + SYMBOLS;
  const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const MONTH_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  let generatedPassword = null;
  let mainFieldsFilled = false;
  let birthdayFilled = false;
  let lastUsername = null;

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

  function fromLabel(text, tag = "input") {
    const target = text.toLowerCase();
    for (const label of document.querySelectorAll("label")) {
      if (!label.textContent.toLowerCase().includes(target)) continue;
      if (label.htmlFor) {
        const field = document.getElementById(label.htmlFor);
        if (field && isVisible(field)) return field;
      }
      const nested = label.querySelector(tag);
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

  function findBirthdayFields() {
    const dateInput = firstVisible([
      'input[type="date"][name*="birth" i]',
      'input[type="date"][id*="birth" i]',
      'input[type="date"][autocomplete="bday"]'
    ]);

    const month = firstVisible([
      '#MonthDropdown',
      'select[name="birthdayMonth"]',
      'select[name*="month" i]',
      'select[id*="month" i]',
      'select[aria-label*="month" i]'
    ]) || fromLabel("month", "select");

    const day = firstVisible([
      '#DayDropdown',
      'select[name="birthdayDay"]',
      'select[name*="day" i]',
      'select[id*="day" i]',
      'select[aria-label*="day" i]'
    ]) || fromLabel("day", "select");

    const year = firstVisible([
      '#YearDropdown',
      'select[name="birthdayYear"]',
      'select[name*="year" i]',
      'select[id*="year" i]',
      'select[aria-label*="year" i]'
    ]) || fromLabel("year", "select");

    return { dateInput, month, day, year };
  }

  function setNativeValue(input, value) {
    const proto = input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    if (descriptor?.set) descriptor.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function normalize(value) {
    return String(value ?? "").trim().toLowerCase();
  }

  function selectOption(select, candidates) {
    if (!select) return false;
    const wanted = new Set(candidates.map(normalize));
    const option = [...select.options].find(opt => wanted.has(normalize(opt.value)) || wanted.has(normalize(opt.textContent)));
    if (!option) return false;
    setNativeValue(select, option.value);
    return true;
  }

  async function getBirthday() {
    return new Promise(resolve => {
      chrome.storage.local.get({ birthday: "" }, ({ birthday }) => resolve(birthday || ""));
    });
  }

  function fillBirthday(birthday) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(birthday)) return false;
    const [year, month, day] = birthday.split("-").map(Number);
    const fields = findBirthdayFields();

    if (fields.dateInput) {
      setNativeValue(fields.dateInput, birthday);
      return true;
    }

    if (!fields.month || !fields.day || !fields.year) return false;

    const monthOk = selectOption(fields.month, [
      month,
      String(month).padStart(2, "0"),
      month - 1,
      MONTH_SHORT[month - 1],
      MONTH_LONG[month - 1]
    ]);
    const dayOk = selectOption(fields.day, [day, String(day).padStart(2, "0")]);
    const yearOk = selectOption(fields.year, [year]);
    return monthOk && dayOk && yearOk;
  }

  async function readClipboardData() {
    try {
      const text = (await navigator.clipboard.readText()).trim();
      if (text.startsWith(PAYLOAD_PREFIX)) {
        const parts = text.split("|");
        const username = parts[1] || "";
        const password = parts[2] || "";
        const saved = parts[3] === "1";
        if (USERNAME_RE.test(username) && password.length >= 12) {
          try { await navigator.clipboard.writeText(""); } catch (_) {}
          return { username, password, saved, secureHandoff: true };
        }
      }
      if (USERNAME_RE.test(text)) {
        return { username: text, password: null, saved: false, secureHandoff: false };
      }
      return null;
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

  function rememberAccount(username, birthday, saved) {
    chrome.storage.local.get({ accountHistory: [] }, ({ accountHistory }) => {
      const history = Array.isArray(accountHistory) ? accountHistory : [];
      const entry = {
        username,
        birthday: birthday || "",
        passwordLocation: saved ? "Windows Credential Manager" : "Not saved by Name Sniffer",
        createdAt: new Date().toISOString()
      };
      const withoutDuplicate = history.filter(item => item.username !== username);
      withoutDuplicate.unshift(entry);
      chrome.storage.local.set({ accountHistory: withoutDuplicate.slice(0, 100) });
    });
  }

  function makePanel(username, password, birthday, birthdayStatus, saved) {
    document.getElementById("scarn-sniffer-autofill")?.remove();
    const box = document.createElement("div");
    box.id = "scarn-sniffer-autofill";
    box.style.cssText = [
      "position:fixed", "right:18px", "top:18px", "z-index:2147483647",
      "width:340px", "padding:16px", "border-radius:12px",
      "background:#0f141c", "color:#eef4ff", "border:1px solid #314052",
      "box-shadow:0 18px 50px rgba(0,0,0,.45)",
      "font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif"
    ].join(";");

    const birthdayLine = birthday
      ? `<div style="color:${birthdayStatus ? "#53f59a" : "#f6c85f"};margin-bottom:10px">Birthday: <b data-bday></b> ${birthdayStatus ? "✓" : "(couldn't fill)"}</div>`
      : `<div style="color:#f6c85f;margin-bottom:10px">Birthday not configured. Click the extension icon to set it.</div>`;

    box.innerHTML = `
      <div style="font-weight:800;font-size:15px;margin-bottom:10px">🔎 Scarn's Name Sniffer</div>
      <div style="color:#9fb0c2;margin-bottom:8px">Autofilled <b data-user style="color:#53f59a"></b></div>
      ${birthdayLine}
      <div style="color:${saved ? "#53f59a" : "#f6c85f"};margin-bottom:10px">Password storage: <b>${saved ? "Windows Credential Manager ✓" : "not securely saved"}</b></div>
      <div style="font-size:12px;color:#7f93a8;margin-bottom:4px">Generated password</div>
      <code data-pw style="display:block;padding:9px 10px;background:#080b10;border-radius:8px;color:#65d9ff;word-break:break-all">••••••••••••••••</code>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button data-show style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Show</button>
        <button data-copy style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:7px 10px;cursor:pointer;font-weight:700">Copy password</button>
      </div>
      <div style="margin-top:10px;color:#8fa1b3;font-size:12px">${saved ? "This password is already saved in Windows Credential Manager." : "Save this password before creating the account."} The companion never presses Create Account for you.</div>
    `;

    box.querySelector("[data-user]").textContent = username;
    if (birthday) box.querySelector("[data-bday]").textContent = birthday;

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
    box.innerHTML = `<b>🔎 Scarn's Name Sniffer</b><div style="margin:9px 0;color:#9fb0c2">I couldn't read the username/password handoff from the clipboard automatically.</div><button style="border:1px solid #314052;background:#18212d;color:#eef4ff;border-radius:8px;padding:8px 11px;cursor:pointer;font-weight:700">Autofill now</button>`;
    box.querySelector("button").addEventListener("click", async () => {
      const account = await readClipboardData();
      if (account) await startFill(account, true);
      else box.querySelector("div").textContent = "Clipboard doesn't contain a Name Sniffer handoff. Choose the name in Name Sniffer again.";
    });
    document.documentElement.appendChild(box);
  }

  async function attemptFill(account) {
    const username = account.username;
    lastUsername = username;
    const fields = findFields();
    if (fields.username && fields.password) {
      generatedPassword ||= account.password || makePassword();
      setNativeValue(fields.username, username);
      setNativeValue(fields.password, generatedPassword);
      mainFieldsFilled = true;
    }

    const birthday = await getBirthday();
    if (birthday && !birthdayFilled) birthdayFilled = fillBirthday(birthday);

    return { birthday };
  }

  async function startFill(account, userGesture = false) {
    if (!account || !USERNAME_RE.test(account.username)) return false;
    let birthday = "";

    for (let attempt = 0; attempt < 40; attempt++) {
      const result = await attemptFill(account);
      birthday = result.birthday;
      if (mainFieldsFilled && (!birthday || birthdayFilled)) {
        rememberAccount(account.username, birthday, account.saved);
        makePanel(account.username, generatedPassword, birthday, birthdayFilled, account.saved);
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    if (mainFieldsFilled) {
      rememberAccount(account.username, birthday, account.saved);
      makePanel(account.username, generatedPassword, birthday, birthdayFilled, account.saved);
      return true;
    }

    if (userGesture) makeRetryPanel();
    return false;
  }

  async function start() {
    let account = await readClipboardData();

    for (let attempt = 0; attempt < 40; attempt++) {
      if (!account) account = await readClipboardData();
      if (account && await startFill(account)) return;
      await new Promise(resolve => setTimeout(resolve, 250));
    }

    makeRetryPanel();
  }

  start();
})();
