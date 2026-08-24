# Scarn's Name Sniffer Autofill Companion v2.2

This optional Chrome/Edge extension works with the existing Name Sniffer v2.1.2 Windows EXE.

When you choose a name in Name Sniffer, the EXE copies the username and opens Roblox Create Account. The companion then:

- reads that username from the clipboard
- fills the Roblox username field automatically
- generates a strong 16-character password locally in your browser
- fills the password field automatically
- shows a small panel where you can reveal or copy the generated password
- never clicks or submits **Create Account**

The generated password is not sent to Name Sniffer and is not stored by the extension.

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

After installation, run Name Sniffer normally. Choose an available name and Roblox Create Account should open with the username and generated password filled in.

If Chrome blocks the automatic clipboard read on a particular run, the companion shows an **Autofill now** button. Clicking it retries with a user gesture.
