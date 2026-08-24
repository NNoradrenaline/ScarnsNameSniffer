(() => {
  "use strict";

  const input = document.getElementById("birthday");
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const clear = document.getElementById("clear");
  const history = document.getElementById("history");

  chrome.storage.local.get({ birthday: "", accountHistory: [] }, ({ birthday, accountHistory }) => {
    input.value = birthday || "";
    const count = Array.isArray(accountHistory) ? accountHistory.length : 0;
    history.textContent = `${count} account${count === 1 ? "" : "s"} recorded locally. Passwords are kept in Windows Credential Manager.`;
  });

  save.addEventListener("click", () => {
    if (!input.value) {
      status.textContent = "Choose a birthday first.";
      return;
    }
    chrome.storage.local.set({ birthday: input.value }, () => {
      status.textContent = `Saved ${input.value} ✓`;
    });
  });

  clear.addEventListener("click", () => {
    chrome.storage.local.remove("birthday", () => {
      input.value = "";
      status.textContent = "Saved birthday cleared.";
    });
  });
})();
