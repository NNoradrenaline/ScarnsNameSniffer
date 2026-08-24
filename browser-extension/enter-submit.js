(() => {
  "use strict";

  let enterSubmitEnabled = true;
  let armed = false;
  let countdownStartedAt = null;
  const ARM_DELAY_MS = 5000;

  chrome.storage.local.get({ enterSubmit: true }, ({ enterSubmit }) => {
    enterSubmitEnabled = enterSubmit !== false;
  });

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName === "local" && changes.enterSubmit) {
      enterSubmitEnabled = changes.enterSubmit.newValue !== false;
      if (!enterSubmitEnabled) resetArmState();
    }
  });

  function visible(element) {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function firstVisible(selectors) {
    for (const selector of selectors) {
      for (const element of document.querySelectorAll(selector)) {
        if (visible(element)) return element;
      }
    }
    return null;
  }

  function formLooksFilled() {
    const username = firstVisible([
      'input[name="username"]',
      'input[autocomplete="username"]',
      'input[id*="username" i]',
      'input[placeholder*="username" i]'
    ]);
    const password = firstVisible([
      'input[autocomplete="new-password"]',
      'input[name="password"]',
      'input[id*="password" i]',
      'input[type="password"]'
    ]);

    if (!username?.value?.trim() || !password?.value) return false;

    const dateInput = firstVisible([
      'input[type="date"][name*="birth" i]',
      'input[type="date"][id*="birth" i]',
      'input[type="date"][autocomplete="bday"]'
    ]);
    if (dateInput && !dateInput.value) return false;

    const month = firstVisible(['#MonthDropdown', 'select[name*="month" i]', 'select[id*="month" i]']);
    const day = firstVisible(['#DayDropdown', 'select[name*="day" i]', 'select[id*="day" i]']);
    const year = firstVisible(['#YearDropdown', 'select[name*="year" i]', 'select[id*="year" i]']);
    if ((month || day || year) && (!month?.value || !day?.value || !year?.value)) return false;

    return true;
  }

  function findCreateAccountButton() {
    const buttons = [...document.querySelectorAll("button")].filter(visible);
    const exact = buttons.find(button => {
      const text = (button.textContent || "").trim().toLowerCase();
      return text === "sign up" || text === "signup" || text === "create account";
    });
    if (exact) return exact;

    const submits = buttons.filter(button => button.type === "submit");
    return submits.length === 1 ? submits[0] : null;
  }

  function statusNode() {
    let node = document.getElementById("scarn-submit-arm-status");
    if (node) return node;

    node = document.createElement("div");
    node.id = "scarn-submit-arm-status";
    node.style.cssText = "margin-top:10px;padding:8px 10px;border-radius:8px;background:#080b10;color:#9fb0c2;font:12px/1.35 system-ui,-apple-system,Segoe UI,sans-serif";

    const panel = document.getElementById("scarn-sniffer-autofill");
    if (panel) {
      panel.appendChild(node);
    } else {
      node.style.position = "fixed";
      node.style.right = "18px";
      node.style.top = "18px";
      node.style.zIndex = "2147483647";
      document.documentElement.appendChild(node);
    }
    return node;
  }

  function setStatus(text, ready = false) {
    const node = statusNode();
    node.textContent = text;
    node.style.color = ready ? "#53f59a" : "#9fb0c2";
  }

  function resetArmState() {
    armed = false;
    countdownStartedAt = null;
    const node = document.getElementById("scarn-submit-arm-status");
    if (node) node.remove();
  }

  function tickArmState() {
    if (!enterSubmitEnabled) {
      resetArmState();
      return;
    }

    const button = findCreateAccountButton();
    const ready = formLooksFilled() && button && !button.disabled && button.getAttribute("aria-disabled") !== "true";

    if (!ready) {
      armed = false;
      countdownStartedAt = null;
      setStatus("Waiting for the signup form to be ready…");
      return;
    }

    if (armed) return;
    if (countdownStartedAt === null) countdownStartedAt = Date.now();

    const elapsed = Date.now() - countdownStartedAt;
    const remaining = Math.max(0, Math.ceil((ARM_DELAY_MS - elapsed) / 1000));

    if (elapsed < ARM_DELAY_MS) {
      setStatus(`Signup ready. Press Enter in ${remaining}s…`);
      return;
    }

    armed = true;
    try { button.focus({ preventScroll: true }); } catch (_) { button.focus(); }
    setStatus("Ready ✓ Press Enter to create the account.", true);
  }

  document.addEventListener("keydown", event => {
    if (!enterSubmitEnabled || !armed) return;
    if (event.key !== "Enter" || event.repeat) return;
    if (event.ctrlKey || event.altKey || event.metaKey || event.shiftKey) return;
    if (event.target instanceof HTMLTextAreaElement || event.target?.isContentEditable) return;
    if (!formLooksFilled()) return;

    const button = findCreateAccountButton();
    if (!button || button.disabled || button.getAttribute("aria-disabled") === "true") return;

    event.preventDefault();
    event.stopPropagation();
    button.click();
  }, true);

  setInterval(tickArmState, 250);
})();
