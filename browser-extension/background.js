(() => {
  "use strict";

  function replyAsync(sendResponse, task) {
    Promise.resolve()
      .then(task)
      .then(sendResponse)
      .catch(error => {
        sendResponse({
          ok: false,
          error: String(error?.message || error || "unknown error")
        });
      });
    return true;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "scarn:getAuthenticatedUser") {
      return replyAsync(sendResponse, async () => {
        const response = await fetch(
          "https://users.roblox.com/v1/users/authenticated",
          {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: { Accept: "application/json" }
          }
        );

        if (!response.ok) {
          return { ok: false, status: response.status };
        }

        const data = await response.json();
        return {
          ok: true,
          user: {
            id: data.id ?? null,
            name: data.name || "",
            displayName: data.displayName || ""
          }
        };
      });
    }

    if (message?.type === "scarn:storePendingSecret") {
      return replyAsync(sendResponse, async () => {
        const secret = message.secret || {};
        if (
          !secret.username ||
          !secret.password ||
          !secret.expiresAt
        ) {
          return { ok: false, error: "invalid secret payload" };
        }

        await chrome.storage.session.set({
          pendingSignupSecret: {
            username: String(secret.username),
            password: String(secret.password),
            armedAt: Number(secret.armedAt || Date.now()),
            expiresAt: Number(secret.expiresAt)
          }
        });
        return { ok: true };
      });
    }

    if (message?.type === "scarn:getPendingSecret") {
      return replyAsync(sendResponse, async () => {
        const { pendingSignupSecret } =
          await chrome.storage.session.get({
            pendingSignupSecret: null
          });

        if (!pendingSignupSecret) {
          return { ok: false, error: "no pending secret" };
        }

        if (Date.now() > Number(pendingSignupSecret.expiresAt || 0)) {
          await chrome.storage.session.remove("pendingSignupSecret");
          return { ok: false, error: "pending secret expired" };
        }

        if (
          message.username &&
          String(pendingSignupSecret.username).toLowerCase() !==
            String(message.username).toLowerCase()
        ) {
          return { ok: false, error: "pending username mismatch" };
        }

        return {
          ok: true,
          secret: pendingSignupSecret
        };
      });
    }

    if (message?.type === "scarn:clearPendingSecret") {
      return replyAsync(sendResponse, async () => {
        await chrome.storage.session.remove("pendingSignupSecret");
        return { ok: true };
      });
    }

    return false;
  });
})();
