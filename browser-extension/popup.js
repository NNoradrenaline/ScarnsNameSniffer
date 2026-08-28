(() => {
  "use strict";

  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  const birthday = document.getElementById("birthday");
  const email = document.getElementById("email");
  const status = document.getElementById("status");
  const save = document.getElementById("save");
  const clearBirthday = document.getElementById("clear-birthday");
  const clearEmail = document.getElementById("clear-email");
  const history = document.getElementById("history");
  const enterSubmit = document.getElementById("enter-submit");
  const autoEmail = document.getElementById("auto-email");

  chrome.storage.local.get(
    {
      birthday: "",
      emailAddress: "",
      autoAddEmail: false,
      accountHistory: [],
      enterSubmit: true,
      emailSetupStatus: ""
    },
    values => {
      birthday.value = values.birthday || "";
      email.value = values.emailAddress || "";
      autoEmail.checked = values.autoAddEmail === true;
      enterSubmit.checked = values.enterSubmit !== false;

      const count = Array.isArray(values.accountHistory)
        ? values.accountHistory.length
        : 0;

      history.textContent =
        count + " account" + (count === 1 ? "" : "s") +
        " recorded locally." +
        (values.emailSetupStatus
          ? " Email helper: " + values.emailSetupStatus
          : "");
    }
  );

  enterSubmit.addEventListener("change", () => {
    chrome.storage.local.set({ enterSubmit: enterSubmit.checked }, () => {
      status.textContent = enterSubmit.checked
        ? "Enter-to-submit enabled ✓"
        : "Enter-to-submit disabled.";
    });
  });

  autoEmail.addEventListener("change", () => {
    const emailValue = email.value.trim();

    if (autoEmail.checked && !EMAIL_RE.test(emailValue)) {
      autoEmail.checked = false;
      status.textContent =
        "Enter and save a valid email before enabling Auto-add Email.";
      return;
    }

    chrome.storage.local.set(
      { autoAddEmail: autoEmail.checked },
      () => {
        status.textContent = autoEmail.checked
          ? "Auto-add Email enabled ✓"
          : "Auto-add Email disabled.";
      }
    );
  });

  save.addEventListener("click", () => {
    const emailValue = email.value.trim();

    if (emailValue && !EMAIL_RE.test(emailValue)) {
      status.textContent = "Enter a valid email address.";
      return;
    }

    if (autoEmail.checked && !emailValue) {
      status.textContent =
        "Auto-add Email needs a saved email address.";
      return;
    }

    chrome.storage.local.set(
      {
        birthday: birthday.value || "",
        emailAddress: emailValue,
        autoAddEmail: autoEmail.checked && Boolean(emailValue)
      },
      () => {
        status.textContent = "Settings saved ✓";
      }
    );
  });

  clearBirthday.addEventListener("click", () => {
    chrome.storage.local.remove("birthday", () => {
      birthday.value = "";
      status.textContent = "Saved birthday cleared.";
    });
  });

  clearEmail.addEventListener("click", () => {
    chrome.storage.local.remove(
      ["emailAddress", "emailSetupPending", "emailSetupStatus"],
      () => {
        chrome.storage.local.set({ autoAddEmail: false }, () => {
          chrome.storage.session.remove("pendingSignupSecret", () => {
            email.value = "";
            autoEmail.checked = false;
            status.textContent =
              "Saved email and pending email job cleared.";
          });
        });
      }
    );
  });
})();
