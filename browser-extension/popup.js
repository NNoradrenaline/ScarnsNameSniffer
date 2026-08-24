(() => {
  "use strict";

  const input = document.getElementById("birthday");
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const clear = document.getElementById("clear");

  chrome.storage.local.get({ birthday: "" }, ({ birthday }) => {
    input.value = birthday || "";
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
