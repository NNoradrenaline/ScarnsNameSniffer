(() => {
  "use strict";

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "scarn:getAuthenticatedUser") return false;

    (async () => {
      try {
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
          sendResponse({ ok: false, status: response.status });
          return;
        }

        const data = await response.json();
        sendResponse({
          ok: true,
          user: {
            id: data.id ?? null,
            name: data.name || "",
            displayName: data.displayName || ""
          }
        });
      } catch (error) {
        sendResponse({
          ok: false,
          error: String(error?.message || error || "unknown error")
        });
      }
    })();

    return true;
  });
})();
