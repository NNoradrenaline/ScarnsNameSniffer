# Scarn's Name Sniffer Autofill Companion v2.6

This optional Chrome/Edge extension ships with Scarn's Name Sniffer v2.6.

When you choose a single verified available name in Name Sniffer, the Windows app generates a strong password, saves the username/password pair in Windows Credential Manager, prepares a one-time clipboard handoff, and opens Roblox Create Account. The companion then:

- reads the one-time username/password handoff from the clipboard
- fills the Roblox username field
- fills the exact password already saved by the Windows app
- clears the one-time clipboard handoff after reading it
- fills your saved birthday
- records only non-secret account history locally
- shows a panel where you can reveal or copy the generated password
- lets you press **Enter** to activate Roblox's normal **Create Account / Sign Up** button once the form is filled

Enter-to-submit defaults to **on**. Click the extension icon and uncheck **Press Enter to submit signup** if you want to disable it.

The shortcut does not bypass CAPTCHA, verification, rate limits, disabled buttons, or other Roblox checks. It only activates the normal visible signup button after your keypress.

Passwords are not stored in extension history or plaintext scan files. When secure saving succeeds, the password is stored in Windows Credential Manager under the current Windows account.

## Install from Releases

Normal users should download `ScarnsNameSniffer-Autofill-v2.6.zip` from the project's GitHub Releases page.

### Chrome

1. Extract the ZIP.
2. Open `chrome://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

### Edge

1. Extract the ZIP.
2. Open `edge://extensions`.
3. Enable **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted folder containing `manifest.json`.

## Set your birthday

1. Click the **Scarn's Name Sniffer Autofill** extension icon.
2. Choose the account holder's actual birthday.
3. Click **Save birthday**.
4. Leave **Press Enter to submit signup** enabled if you want the keyboard shortcut.
5. Run Name Sniffer normally.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.

## Secure account storage

Single-name claims use Windows Credential Manager entries such as:

```text
ScarnsNameSniffer:exampleuser
```

Name Sniffer's `[c]redentials` menu can list saved usernames, copy or reveal one password on demand, open Roblox login, delete a saved credential, or export usernames only.

The extension stores only non-secret account history. Passwords remain in Windows Credential Manager.
