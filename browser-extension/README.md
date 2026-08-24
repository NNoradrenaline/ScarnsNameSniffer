# Scarn's Name Sniffer Autofill Companion v2.3

This optional Chrome/Edge extension works with the existing Name Sniffer Windows EXE.

When you choose a name in Name Sniffer, the EXE copies the username and opens Roblox Create Account. The companion then:

- reads that username from the clipboard
- fills the Roblox username field automatically
- generates a strong 16-character password locally in your browser
- fills the password field automatically
- fills your saved birthday automatically
- shows a small panel where you can reveal or copy the generated password
- never clicks or submits **Create Account**

The generated password is not sent to Name Sniffer and is not stored by the extension. Your configured birthday is stored locally in Chrome/Edge extension storage.

## Set your birthday

1. Click the **Scarn's Name Sniffer Autofill** extension icon in Chrome or Edge.
2. Choose the account holder's actual birthday.
3. Click **Save birthday**.
4. Run Name Sniffer normally.

Roblox uses birthday information for age-appropriate account features, so use the correct date for the person whose account is being created.

## Install in Chrome

1. Extract the extension ZIP to a folder.
2. Open `chrome://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted `browser-extension` folder.

## Install in Edge

1. Extract the extension ZIP to a folder.
2. Open `edge://extensions`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted `browser-extension` folder.

After installation, click the extension icon once to save the birthday. Then choose an available name in Name Sniffer and Roblox Create Account should open with the username, password, and birthday filled in.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.
