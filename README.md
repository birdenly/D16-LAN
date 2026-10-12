# DOOM (2016) LAN

This is Slop.

> DOOM (2016) LAN is a fan project. It is not affiliated with or endorsed by id Software or Bethesda Softworks.
> This was tested and made for a Steam copy.

A project to get DOOM (2016) Multiplayer working offline and over LAN. Currently, the game gets stuck in a loop when launched offline:

## Getting started

1. Download the release files.
2. Place the files next to your game executable (`DOOM\DOOMx64.exe` and `DOOMx64vk.exe`).
3. Run `patch_game.exe`. This patches both the OpenGL (`DOOMx64.exe`) and Vulkan (`DOOMx64vk.exe`) executables to work offline/locally and creates `.bak` backups of your original files.
4. Run `Start_game.bat` to launch the game. Alternatively, you can add these launch options in Steam:

   `+com_skipIntroVideo 1 +net_dedicatedServerGate_Enable 0 +menu_allowPrivateMatch 1 +menu_startMatchAlwaysAllowed 1 +gc_minPlayersInPrivateMatch 1 +metrics_allowStatsAndXPInPrivateMatch 1 +hud_showXPGainsInPrivateMatch 1 +metrics_xpMultiplier 1.0`

## How it works

### 1. Title Storage Loop
On startup and when entering Multiplayer, the game calls `idSessionLocal::UpdateTitleStorage` to download configuration data (`tss.bin`) from Bethesda / Hydra cloud servers. When offline, this request never completes and leaves the game stuck on `NOTICE: Loading title storage.`

The executable is patched to take the built-in disabled branch in `UpdateTitleStorage` and force `IsTitleStorageReady()` to return `true` immediately, dismissing the loading screen on the first frame.

### 2. Dedicated Server Gatekeeper & Endpoint Checks
Selecting **Private Match** normally queries Bethesda's gatekeeper server (`198.20.198.48/gatekeeper`) and pings dedicated server endpoints. When unreachable, the game blocks access with `Unable to reach dedicated server endpoints.`

Both `IsDedicatedServerGatePassed` and the endpoint ping check are patched to return `true` immediately, unlocking the Private Match menu without any network dependency.

### 3. Private Match checks
Starting a Private Match originally checked for cloud dedicated server allocation (`State_Find_Dedicated_Instance`) and failed with `Unable to find a dedicated server.` It also prevented starting a match with fewer than 2 players (`#str_dlg_mp_empty_team`).

The lobby and session start routines (`CanStartPrivateMatch`, `StartMatch`, and the minimum player check) were patched to bypass dedicated server allocation and jump directly into `StartLoading()` as a local listen server. The host loads the map locally and brings all connected lobby players into the match over P2P. In-game already was P2P, this doesnt implement it.

### 4. LAN Join & P2P Connection Fix
When a second player joins a Private Match lobby over LAN, the `OnP2PSessionRequest` callback called `SteamFriends()->GetFriendPersonaName()` before accepting the session. On LAN where players are not on an online friends list, this caused an access violation crash (`0xC0000005`) on the host and timed out the joining player.

The redundant persona name lookup was removed so `AcceptP2PSessionWithUser` executes immediately, allowing players to join lobbies and travel into matches seamlessly.

### 5. Local XP, Leveling & Progression
By default, Private Matches disabled all XP and stat gains (`metrics_allowStatsAndXPInPrivateMatch = 0`), hid HUD XP popups (`hud_showXPGainsInPrivateMatch = 0`), cleared the post-match summary (`idGameLocal::UpdateMatchResults`), and kept the Title Storage variable `giveXP` locked to `0` (preventing level-ups).

These defaults and checks were patched in the executable so kills, medals, challenges, post-match XP summaries, in-game taunts (`allowTaunts`), and level-ups are earned in Private Matches and saved directly to your local profile (`profile.bin`). You can also customize `XP_MULTIPLIER` inside `Start_game.bat` (`+metrics_xpMultiplier`) to adjust your progression speed.

---
