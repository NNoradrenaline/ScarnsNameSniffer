# Scarn's Name Sniffer Autofill Companion v2.5.1

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

Enter-to-submit defaults to **on**. Click the extension icon and uncheck **Press Enter to submit signup** if you want to disable it.

The Enter shortcut does not bypass CAPTCHA, verification, rate limits, disabled buttons, or any other Roblox checks. It only performs the same normal button activation you could do with the mouse.

Passwords are not stored in extension history or plaintext files. When secure saving succeeds, the password is stored by Windows Credential Manager under the current Windows account.

## Auto-add recovery email

The extension can optionally add one recovery email after a newly created account signs in.

1. Click the extension icon.
2. Enter your recovery email.
3. Enable **Automatically add email after signup**.
4. Save settings.
5. Use Name Sniffer normally.

After signup, the helper:

- waits until Roblox reports that the newly prepared username is the account currently logged in
- opens **Settings > Account Info**
- uses the normal **Add Email** control
- fills the saved email address
- fills the temporary signup password only if Roblox asks for it
- activates Roblox's normal **Add Email / Send Verification** button
- stops and tells you to check your inbox

The extension **does not read your inbox, click the verification link, enter an emailed code, or bypass any Roblox verification step**. You complete verification manually from your email.

The helper also refuses to use **Update Email / Change Email / Remove Email**. If an account already appears to have an email, it stops instead of replacing it.

The saved email is stored in Chrome/Edge extension local storage. A signup password needed by the Add Email dialog is kept only in extension **session** storage behind the background service worker, expires after 15 minutes, and is cleared after the verification request.

## Install from Releases

Download `ScarnsNameSniffer-Autofill-v2.5.zip` from the project's GitHub Releases page and extract it before loading the extension.

## Set your birthday

1. Click the **Scarn's Name Sniffer Autofill** extension icon in Chrome or Edge.
2. Choose the account holder's actual birthday.
3. Optionally enter a recovery email and enable **Automatically add email after signup**.
4. Click **Save settings**.
5. Leave **Press Enter to submit signup** enabled if you want the Enter shortcut.
6. Run Name Sniffer normally.

## Install in Chrome

1. Extract the extension ZIP to a folder.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

## Install in Edge

1. Extract the extension ZIP to a folder.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

After installation, click the extension icon once to save the birthday. Then choose an available name in Name Sniffer. Roblox Create Account should open with the username, password, and birthday filled in. Press **Enter** when you are ready to submit the normal Roblox form.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.

## Secure account storage

For single-name claim mode, passwords are saved by the Windows app in Windows Credential Manager under names such as:

```text
ScarnsNameSniffer:exampleuser
```

Name Sniffer v2.5 adds a **[c]redentials** menu where you can list saved usernames, copy or reveal a password on demand, open Roblox login, delete a saved credential, or export a usernames-only list.

The extension stores only non-secret account history. Bulk-open mode does not generate or save account passwords.
