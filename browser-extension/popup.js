(() => {
  "use strict";

  const input = document.getElementById("birthday");
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const clear = document.getElementById("clear");
  const history = document.getElementById("history");
  const enterSubmit = document.getElementById("enter-submit");

  chrome.storage.local.get(
    { birthday: "", accountHistory: [], enterSubmit: true },
    ({ birthday, accountHistory, enterSubmit: savedEnterSubmit }) => {
      input.value = birthday || "";
      enterSubmit.checked = savedEnterSubmit !== false;
      const count = Array.isArray(accountHistory) ? accountHistory.length : 0;
      history.textContent = `${count} account${count === 1 ? "" : "s"} recorded locally. Passwords are kept in Windows Credential Manager.`;
    }
  );

  enterSubmit.addEventListener("change", () => {
    chrome.storage.local.set({ enterSubmit: enterSubmit.checked }, () => {
      status.textContent = enterSubmit.checked
        ? "Enter-to-submit enabled ✓"
        : "Enter-to-submit disabled.";
    });
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
