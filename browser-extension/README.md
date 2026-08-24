# Scarn's Name Sniffer Autofill Companion v2.5

This optional Chrome/Edge extension works with the Name Sniffer v2.5 Windows EXE.

When you choose a single name in Name Sniffer, the Windows app generates a strong password, saves the username/password pair in Windows Credential Manager, prepares a one-time clipboard handoff, and opens Roblox Create Account. The companion then:

- reads the one-time username/password handoff from the clipboard
- fills the Roblox username field automatically
- fills the exact password already saved by the Windows app
- clears the one-time clipboard handoff after reading it
- fills your saved birthday automatically
- records only non-secret account history locally (username, birthday, timestamp, and credential location)
- shows a small panel where you can reveal or copy the generated password
- lets you press **Enter** to activate Roblox's normal **Create Account / Sign Up** button once the form is filled

The Enter shortcut does not bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox checks. It only performs the same normal button activation you could do with the mouse.

Passwords are not stored in extension history or plaintext files. When secure saving succeeds, the password is stored by Windows Credential Manager under the current Windows account.

## Set your birthday

1. Click the **Scarn's Name Sniffer Autofill** extension icon in Chrome or Edge.
2. Choose the account holder's actual birthday.
3. Click **Save birthday**.
4. Run Name Sniffer normally.

## Install in Chrome

1. Extract the extension ZIP or build artifact to a folder.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted `browser-extension` folder.

## Install in Edge

1. Extract the extension ZIP or build artifact to a folder.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted `browser-extension` folder.

After installation, click the extension icon once to save the birthday. Then choose an available name in Name Sniffer. Roblox Create Account should open with the username, password, and birthday filled in. Press **Enter** when you are ready to submit the normal Roblox form.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.

## Secure account storage

For single-name claim mode, passwords are saved by the Windows app in Windows Credential Manager under names such as:

```text
ScarnsNameSniffer:exampleuser
```

Name Sniffer v2.5 adds a **[c]redentials** menu where you can list saved usernames, copy or reveal a password on demand, open Roblox login, delete a saved credential, or export a usernames-only list.

The extension stores only non-secret account history. Bulk-open mode does not generate or save account passwords.
