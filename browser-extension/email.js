(() => {
  "use strict";

  const SETTINGS_URL = "https://www.roblox.com/my/account#!/info";
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const POLL_MS = 250;
  const POLL_ATTEMPTS = 80;

  function visible(element) {
    if (!element) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      rect.width > 0 &&
      rect.height > 0;
  }

  function textOf(element) {
    return String(
      element?.innerText ||
      element?.textContent ||
      element?.value ||
      element?.getAttribute?.("aria-label") ||
      ""
    ).trim().replace(/\s+/g, " ").toLowerCase();
  }

  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function localGet(defaults) {
    return new Promise(resolve => chrome.storage.local.get(defaults, resolve));
  }

  function localSet(values) {
    return new Promise(resolve => chrome.storage.local.set(values, resolve));
  }

  function localRemove(keys) {
    return new Promise(resolve => chrome.storage.local.remove(keys, resolve));
  }

  function getPendingSecret(username) {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:getPendingSecret", username },
        response => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false });
        }
      );
    });
  }

  function clearPendingSecret() {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:clearPendingSecret" },
        () => resolve()
      );
    });
  }

  function getAuthenticatedUser() {
    return new Promise(resolve => {
      chrome.runtime.sendMessage(
        { type: "scarn:getAuthenticatedUser" },
        response => {
          if (chrome.runtime.lastError) {
            resolve({ ok: false, error: chrome.runtime.lastError.message });
            return;
          }
          resolve(response || { ok: false });
        }
      );
    });
  }

  function setNativeValue(input, value) {
    const prototype = input instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
    if (descriptor?.set) descriptor.set.call(input, value);
    else input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function findButtons() {
    return [
      ...document.querySelectorAll(
        'button, input[type="button"], input[type="submit"], [role="button"]'
      )
    ].filter(visible);
  }

  function findAddEmailButton() {
    const exact = new Set([
      "add email",
      "add email address",
      "add an email",
      "add an email address"
    ]);
    return findButtons().find(button => exact.has(textOf(button))) || null;
  }

  function findExistingEmailControl() {
    return findButtons().find(button => {
      const text = textOf(button);
      return (
        text.includes("update email") ||
        text.includes("change email") ||
        text.includes("edit email") ||
        text.includes("remove email")
      );
    }) || null;
  }

  function findEmailInput() {
    const selectors = [
      'input[type="email"]',
      'input[name*="email" i]',
      'input[id*="email" i]',
      'input[placeholder*="email" i]',
      'input[autocomplete="email"]'
    ];
    for (const selector of selectors) {
      for (const input of document.querySelectorAll(selector)) {
        if (visible(input)) return input;
      }
    }
    return null;
  }

  function findPasswordInput() {
    const selectors = [
      'input[type="password"]',
      'input[name*="password" i]',
      'input[id*="password" i]',
      'input[autocomplete="current-password"]'
    ];
    for (const selector of selectors) {
      for (const input of document.querySelectorAll(selector)) {
        if (visible(input)) return input;
      }
    }
    return null;
  }

  function findSubmitButton(emailInput) {
    const container =
      emailInput?.closest('[role="dialog"]') ||
      emailInput?.closest("form") ||
      document;

    const allowed = [
      "add email",
      "add email address",
      "send verification",
      "send verification email",
      "send email",
      "verify email",
      "continue",
      "save"
    ];

    const candidates = [
      ...container.querySelectorAll(
        'button, input[type="submit"], [role="button"]'
      )
    ].filter(visible);

    for (const candidate of candidates) {
      const text = textOf(candidate);
      if (
        text.includes("update") ||
        text.includes("change") ||
        text.includes("remove")
      ) {
        continue;
      }
      if (allowed.some(label => text === label || text.includes(label))) {
        return candidate;
      }
    }

    const submits = candidates.filter(candidate => {
      if (candidate instanceof HTMLInputElement) {
        return candidate.type === "submit";
      }
      return candidate.tagName === "BUTTON" &&
        (candidate.type === "submit" || candidate.getAttribute("type") === "submit");
    });
    return submits.length === 1 ? submits[0] : null;
  }

  function buttonEnabled(button) {
    if (!button) return false;
    return !button.disabled &&
      button.getAttribute("aria-disabled") !== "true";
  }

  async function waitFor(getter, attempts = POLL_ATTEMPTS) {
    for (let attempt = 0; attempt < attempts; attempt++) {
      const value = getter();
      if (value) return value;
      await wait(POLL_MS);
    }
    return null;
  }

  function showPanel(message, good = false) {
    document.getElementById("scarn-email-setup")?.remove();
    const panel = document.createElement("div");
    panel.id = "scarn-email-setup";
    panel.style.cssText = [
      "position:fixed",
      "right:18px",
      "bottom:18px",
      "z-index:2147483647",
      "width:330px",
      "padding:14px 15px",
      "border-radius:12px",
      "background:#0f141c",
      "color:#eef4ff",
      "border:1px solid #314052",
      "box-shadow:0 18px 50px rgba(0,0,0,.45)",
      "font:13px/1.45 system-ui,-apple-system,Segoe UI,sans-serif"
    ].join(";");

    const title = document.createElement("div");
    title.style.cssText = "font-weight:800;margin-bottom:7px";
    title.textContent = "✉️ Scarn's Email Helper";

    const body = document.createElement("div");
    body.style.color = good ? "#53f59a" : "#9fb0c2";
    body.textContent = message;

    panel.append(title, body);
    document.documentElement.appendChild(panel);
  }

  async function status(message) {
    await localSet({ emailSetupStatus: message });
  }

  async function finish(message, good = true) {
    await status(message);
    await localRemove("emailSetupPending");
    await clearPendingSecret();
    showPanel(message, good);
  }

  async function run() {
    if (/\/CreateAccount/i.test(location.pathname)) return;

    const {
      emailAddress,
      autoAddEmail,
      emailSetupPending
    } = await localGet({
      emailAddress: "",
      autoAddEmail: false,
      emailSetupPending: null
    });

    if (!autoAddEmail || !EMAIL_RE.test(String(emailAddress || ""))) return;
    if (!emailSetupPending) return;

    const pending = emailSetupPending;
    const now = Date.now();

    if (
      !pending.username ||
      !pending.email ||
      !pending.expiresAt ||
      now > pending.expiresAt
    ) {
      await finish("Email setup expired before signup completed.", false);
      return;
    }

    if (pending.status === "submitted") {
      showPanel(
        `Verification was requested for ${pending.email}. Check your inbox and complete it manually.`,
        true
      );
      return;
    }

    const auth = await getAuthenticatedUser();
    if (!auth?.ok || !auth.user?.name) {
      await status(
        `Waiting to confirm that ${pending.username} is logged in before adding the email.`
      );
      return;
    }

    if (
      String(auth.user.name).toLowerCase() !==
      String(pending.username).toLowerCase()
    ) {
      await status(
        `Email setup paused: expected ${pending.username}, but Roblox is logged in as ${auth.user.name}.`
      );
      return;
    }

    if (!/\/my\/account/i.test(location.pathname)) {
      await status(
        `Signup confirmed for ${pending.username}. Opening Account Info to add ${pending.email}.`
      );
      location.assign(SETTINGS_URL);
      return;
    }

    showPanel(`Adding ${pending.email} to ${pending.username}…`);

    let addButton = findAddEmailButton();
    if (!addButton) {
      const existing = findExistingEmailControl();
      if (existing) {
        await finish(
          "This account already has an email control. Scarn's helper will not replace or change an existing email.",
          false
        );
        return;
      }

      addButton = await waitFor(findAddEmailButton);
    }

    if (!addButton) {
      await status(
        "Could not find Roblox's Add Email button. The page may have changed; no existing email was modified."
      );
      showPanel(
        "Could not find the Add Email button. Nothing was changed.",
        false
      );
      return;
    }

    addButton.click();

    const emailInput = await waitFor(findEmailInput);
    if (!emailInput) {
      await status("Add Email opened, but the email field could not be located.");
      showPanel("Add Email opened, but I couldn't locate the email field.", false);
      return;
    }

    setNativeValue(emailInput, pending.email);

    const passwordInput = findPasswordInput();
    if (passwordInput) {
      const secretResponse = await getPendingSecret(pending.username);

      if (!secretResponse?.ok || !secretResponse.secret?.password) {
        await status(
          "Roblox requested the account password, but the temporary signup password is no longer available."
        );
        showPanel(
          "Email filled. Roblox also wants the password, but the temporary password is no longer available. Fill it manually.",
          false
        );
        return;
      }

      setNativeValue(passwordInput, secretResponse.secret.password);
    }

    let submit = findSubmitButton(emailInput);
    if (!submit) {
      submit = await waitFor(() => findSubmitButton(emailInput), 20);
    }

    if (!submit) {
      await status(
        "Email was filled, but the normal Add Email / Send Verification button could not be located."
      );
      showPanel(
        "Email filled. I couldn't find the final Add Email button, so nothing was submitted.",
        false
      );
      return;
    }

    for (let attempt = 0; attempt < 20 && !buttonEnabled(submit); attempt++) {
      await wait(POLL_MS);
    }

    if (!buttonEnabled(submit)) {
      await status(
        "Email was filled, but Roblox kept the Add Email button disabled."
      );
      showPanel(
        "Email filled, but Roblox kept the submit button disabled. Nothing was bypassed.",
        false
      );
      return;
    }

    submit.click();

    const submittedPending = {
      ...pending,
      status: "submitted",
      submittedAt: Date.now()
    };
    await localSet({
      emailSetupPending: submittedPending,
      emailSetupStatus:
        `Verification requested for ${pending.email}. Check your inbox and verify it manually.`
    });

    // Give Roblox a moment to surface a normal success/error response. We do
    // not interact with the verification email itself.
    await wait(1200);
    showPanel(
      `Verification requested for ${pending.email}. Check your inbox and complete the Roblox verification manually.`,
      true
    );

    await clearPendingSecret();
  }

  run().catch(async error => {
    const message =
      "Email helper stopped safely: " +
      String(error?.message || error || "unknown error");
    try {
      await status(message);
    } catch (_) {}
    showPanel(message, false);
  });
})();
