(() => {
  "use strict";

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

  document.addEventListener("keydown", event => {
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
})();
