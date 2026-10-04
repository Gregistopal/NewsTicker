# NewsTicker 1.0.6

NewsTicker is a portable, professional animated news lower-third for OBS. It runs entirely on this PC, serves a transparent browser source at a stable local address, rotates through saved headlines, and can listen for a moderator-only Twitch command through Streamer.bot.

## Start it

1. Extract the **entire** ZIP to a permanent folder. Do not run the EXE from inside the ZIP.
2. Double-click **NewsTicker.exe**. The control room opens in your normal browser.
3. Keep NewsTicker.exe running while OBS is using the overlay. Closing the control-room tab does not stop the app; use **System → Quit NewsTicker** when finished.

NewsTicker needs no installation and does not need administrator rights. Windows may show an Unknown Publisher warning because this build is not code-signed.

## Add it to OBS

1. Add a **Browser Source** to the scene.
2. Set the URL to `http://127.0.0.1:18770/overlay`.
3. Set **Width** to `1920` and **Height** to `1080`.
4. Use 30 FPS or higher.
5. Leave **Shutdown source when not visible** off. Enabling **Refresh browser when scene becomes active** is fine.
6. Leave OBS custom CSS blank.

The page is transparent. By default, the ticker is flush against the bottom edge and spans the full 1920-pixel canvas width. Bottom offset, side margin, and corner radius remain adjustable if you want to inset it later.

## Control room

- **Headlines:** add, edit, enable, disable, reorder, delete, or immediately show saved headlines. A separate box can run a one-off unsaved headline.
- **Timing:** set how long the overlay remains hidden, the exact number of complete messages per appearance, the cube-flip interval, the Days Live start date, and entrance/exit timing. The default is two full saved messages per appearance.
- **Appearance:** change the breaking label, clock/Days Live cube, fonts, weight, crawl speed, sizes, colors, opacity, shadow, position, and geometry. Every saved and one-off item uses the scrolling news crawl.
- **System:** shows the portable data locations and provides a clean Quit button. A second Quit button is always available in the dashboard's top-right action bar.

The embedded preview is the same 1920 × 1080 layout used by OBS. **Show next**, **Show**, **Show custom headline**, and **Hide now** are live controls and therefore also affect OBS.

## Streamer.bot command

1. In Streamer.bot, open **Servers/Clients → WebSocket Server**.
2. Enable the server and **Auto Start**. The normal address is `127.0.0.1`, port `8080`, endpoint `/`.
3. If authentication is enforced, enter the same WebSocket password in NewsTicker.
4. In NewsTicker, enable the chat command and save. The default is `!news`.

NewsTicker reconnects automatically if Streamer.bot restarts. Only users reported by Streamer.bot as a Twitch moderator or broadcaster may trigger or edit the ticker. Commands that add or delete items update `data\settings.json` immediately.

- `!news` — show the next enabled saved headline.
- `!news 2` — show saved item number 2, using the numbering from `!news list`.
- `!news Server maintenance begins in ten minutes` — interrupt with that one-off text when **Allow custom text after the command** is enabled. Even if the ticker is already visible, the full BREAKING NEWS entrance replays; the one-off runs first, then regular items resume.
- `!news add Community game night starts Friday` — add and enable a persistent saved item.
- `!news delete 2` — permanently delete saved item number 2. `remove` and `del` are accepted aliases.
- `!news list` — post the numbered saved items in chat. Disabled items are marked `[off]`.
- `!news days` — post the current Days Live count and configured start date.
- `!news days 2025-01-15` — change and save the Days Live start date. `today` and U.S. `M/D/YYYY` dates are also accepted; the start date is day 1.
- `!news help` — post the available command syntax in chat.

No Streamer.bot action needs to be created. NewsTicker subscribes directly to the documented `Twitch.ChatMessage` WebSocket event and uses Streamer.bot's `SendMessage` request for command responses. Replies are sent through the connected Twitch broadcaster account, so a separate bot account is not required. If Streamer.bot authentication is enabled, its WebSocket password must be saved in NewsTicker for chat responses to work.

## Portable data

All user data stays inside this extracted folder:

- `data\settings.json` — saved configuration and headlines;
- `data\backups\` — up to ten automatic configuration backups; and
- `data\app.log` — bounded diagnostic log.

Copy the complete NewsTicker folder to move the app and its configuration. To update the app later while preserving the setup, keep a copy of the existing `data` folder.

The WebSocket password, if used, is stored as plain text in `data\settings.json` because the app is portable and does not use a machine-specific credential vault. Keep the folder private.

## Troubleshooting

- **Control room does not open:** run `Start-Diagnostics.cmd` and read the visible error. Also check `data\app.log`.
- **OBS is blank:** confirm NewsTicker.exe is running and the Browser Source URL is exactly `http://127.0.0.1:18770/overlay`.
- **Port 18770 is already in use:** close the other copy of NewsTicker. If a different program owns the port, close it before starting NewsTicker.
- **Streamer.bot stays disconnected:** confirm the WebSocket server is started, the address is `ws://127.0.0.1:8080/`, and the password matches when authentication is enforced.
- **Moderator command is ignored:** confirm the message is a normal Twitch chat message, the command matches, and Streamer.bot reports that account with moderator or broadcaster role.
- **Commands work but there is no chat reply:** check the Streamer.bot status text in the control room. If WebSocket authentication is enabled, save the same password in NewsTicker. Also confirm the Twitch broadcaster account is connected to chat in Streamer.bot.
- **The ticker stays visible longer than the configured time:** this is intentional. It waits for the configured number of messages and closes only after the current crawl has completely left the screen, so the next message is never shown partially.
- **The ticker remains empty after the last message:** version 1.0.4 starts the exit animation as soon as the final trailing edge leaves the message window. Refresh the OBS browser source after updating if it still has an older overlay page cached.
- **Old behavior appears after an update:** version 1.0.5 disables caching for the controller and overlay assets. Restart NewsTicker and refresh the OBS browser source once when installing this update.
- **The ticker immediately re-enters after closing:** version 1.0.6 keeps the server authoritative during the exit and retries a lost completion notice instead of locally hiding and accidentally replaying the same active appearance.
- **Settings were changed accidentally:** close NewsTicker, copy a suitable file from `data\backups\` over `data\settings.json`, and restart.

## Safety and network boundary

The web server binds only to `127.0.0.1`, so the control room and OBS source are not exposed to the LAN or internet. Headline text is inserted as text, not HTML. State-changing control requests require a per-launch local token.

Source files and automated tests are included for transparency. See `THIRD-PARTY-NOTICES.txt` for bundled runtime licenses.
