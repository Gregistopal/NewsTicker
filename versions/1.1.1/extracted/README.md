# NewsTicker 1.1.1

NewsTicker is a portable, professional animated news lower-third for OBS. It runs entirely on this PC, serves a transparent browser source at a stable local address, rotates through saved headlines, and can listen for a moderator-only Twitch command through Streamer.bot.

## Start it

1. Extract the **entire** ZIP to a permanent folder. Do not run the EXE from inside the ZIP.
2. Double-click **Start-NewsTicker.cmd**. The control room opens in your normal browser and the small command window closes automatically.
3. Closing the control-room tab does not stop the app; use **System → Quit NewsTicker** when finished.

NewsTicker needs no installation and does not need administrator rights. Version 1.1.1 uses a readable command script and the official bundled Python runtime instead of a custom unsigned launcher executable. This avoids the hidden-process behavior that can cause false-positive browser or antivirus warnings.

## Add it to OBS

1. Add a **Browser Source** to the scene.
2. Set the URL to `http://127.0.0.1:18770/overlay`.
3. Set **Width** to `1920` and **Height** to `1080`.
4. Use 30 FPS or higher.
5. Leave **Shutdown source when not visible** off. Enabling **Refresh browser when scene becomes active** is fine.
6. Leave OBS custom CSS blank.

The page is transparent. By default, the ticker is flush against the bottom edge and spans the full 1920-pixel canvas width. Bottom offset, side margin, and corner radius remain adjustable if you want to inset it later.

### Optional second OBS layer

NewsTicker also serves a synchronized mirror-only output at `http://127.0.0.1:18770/overlay-secondary`. Add it as another 1920 × 1080 Browser Source when mirrored content needs to live on a different OBS layer from the ticker. Keep **Shutdown source when not visible** off for both NewsTicker sources.

In **Sources & API**, each of the four mirrored URLs can be assigned to:

- **Primary** — embedded behind the ticker in the normal `/overlay` output;
- **Secondary only** — shown only by `/overlay-secondary`, with no ticker rendered there; or
- **Both outputs** — embedded in both pages. This creates two live instances of that URL, so use it only when the source safely supports duplicate connections.

Both outputs use the same server-issued entrance and exit timestamps and the same animation values. An assigned source moves up by the ticker height plus its bottom offset, placing the source's bottom content directly above the ticker's gold top bar. The top of its 1920 × 1080 canvas is clipped while raised. Once a URL is mirrored through NewsTicker, remove or hide its old standalone OBS Browser Source unless you intentionally want another copy.

The dashboard preview deliberately does not load mirrored URLs. This avoids consuming alerts twice or opening duplicate WebSocket connections. A source must permit normal iframe embedding; a site that sends restrictive frame-security headers cannot be mirrored this way.

## Control room

- **Headlines:** add, edit, enable, disable, reorder, delete, or immediately show saved headlines. A separate box can run a one-off unsaved headline.
- **Timing:** set how long the overlay remains hidden, the exact number of complete messages per appearance, the cube-flip interval, the Days Live start date, and entrance/exit timing. The default is two full saved messages per appearance.
- **Sources & API:** configure four mirrored Browser Source URLs, assign each to the primary output, secondary output, or both, and configure the entrance-complete API callback.
- **Appearance:** change the breaking label, clock/Days Live cube, fonts, weight, crawl speed, sizes, colors, opacity, shadow, position, and geometry. Every saved and one-off item uses the scrolling news crawl.
- **System:** shows the portable data locations and provides a clean Quit button. A second Quit button is always available in the dashboard's top-right action bar.

The embedded preview is the same 1920 × 1080 layout used by OBS. **Show next**, **Show**, **Show custom headline**, and **Hide now** are live controls and therefore also affect OBS.

## Local API callback

Enable **POST when entrance completes** under **Sources & API**, enter an HTTP or HTTPS endpoint, and set the message template. NewsTicker sends one JSON POST after the OBS entrance animation reaches its exact completed state. Reports from two open OBS outputs are de-duplicated server-side.

Available message placeholders are `{headline}`, `{source}`, `{triggeredBy}`, and `{activeId}`. The JSON body includes those fields plus `event`, `message`, and `timestamp`. The dashboard shows whether the latest callback succeeded or failed; the request times out after three seconds so an unavailable API cannot stall the ticker.

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
- **OBS is blank:** run `Start-NewsTicker.cmd` and confirm the Browser Source URL is exactly `http://127.0.0.1:18770/overlay`.
- **The secondary layer is blank:** assign at least one mirrored URL to **Secondary only** or **Both outputs**, then use `http://127.0.0.1:18770/overlay-secondary` in a 1920 × 1080 OBS Browser Source.
- **A mirrored source is blank:** open its URL directly to confirm it is running. Sources that prohibit iframe embedding cannot be mirrored by a browser page.
- **Two layers move at different times:** keep both NewsTicker Browser Sources active and disable **Shutdown source when not visible**. Both pages use shared server timestamps, but an OBS source that is shut down cannot animate until OBS recreates it.
- **The API callback fails:** confirm the endpoint begins with `http://` or `https://`, is listening, and accepts a JSON POST. The current result appears under **Sources & API**.
- **Port 18770 is already in use:** close the other copy of NewsTicker. If a different program owns the port, close it before starting NewsTicker.
- **Streamer.bot stays disconnected:** confirm the WebSocket server is started, the address is `ws://127.0.0.1:8080/`, and the password matches when authentication is enforced.
- **Moderator command is ignored:** confirm the message is a normal Twitch chat message, the command matches, and Streamer.bot reports that account with moderator or broadcaster role.
- **Commands work but there is no chat reply:** check the Streamer.bot status text in the control room. If WebSocket authentication is enabled, save the same password in NewsTicker. Also confirm the Twitch broadcaster account is connected to chat in Streamer.bot.
- **The ticker stays visible longer than the configured time:** this is intentional. It waits for the configured number of messages and closes only after the current crawl has completely left the screen, so the next message is never shown partially.
- **The ticker remains empty after the last message:** version 1.0.4 starts the exit animation as soon as the final trailing edge leaves the message window. Refresh the OBS browser source after updating if it still has an older overlay page cached.
- **Old behavior appears after an update:** version 1.0.5 disables caching for the controller and overlay assets. Restart NewsTicker and refresh the OBS browser source once when installing this update.
- **The ticker immediately re-enters after closing:** version 1.0.6 keeps the server authoritative during the exit and retries a lost completion notice instead of locally hiding and accidentally replaying the same active appearance.
- **An older copy is still running during an update:** version 1.0.7 and later show a normal browser help page rather than a native Windows warning dialog. Use Quit in the running dashboard, then launch the new version again.
- **Installing 1.1.1 over an older copy:** copy the old `data` folder into the new extracted NewsTicker folder and allow Windows to replace the new placeholder files. Your existing settings are automatically extended with the new source and API options.
- **Browser or antivirus warns about the download:** use the 1.1.1 package, which removes the custom unsigned `NewsTicker.exe`. Start the app with the transparent `Start-NewsTicker.cmd` script instead.
- **Settings were changed accidentally:** close NewsTicker, copy a suitable file from `data\backups\` over `data\settings.json`, and restart.

## Safety and network boundary

The web server binds only to `127.0.0.1`, so the control room and OBS source are not exposed to the LAN or internet. Headline text is inserted as text, not HTML. State-changing control requests require a per-launch local token.

Source files and automated tests are included for transparency. See `THIRD-PARTY-NOTICES.txt` for bundled runtime licenses.
