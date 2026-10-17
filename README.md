# DOOM (2016) LAN

> DOOM (2016) LAN is a fan project. It is not affiliated with or endorsed by id Software or Bethesda Softworks.
> This was tested and made for a Steam copy.

A project to get DOOM (2016) Multiplayer working offline and over LAN. Currently, the game gets stuck in a loop when launched offline.

Working version: download_depot 379720 379721 7402417666934369131

If you want to give a thanks: https://ko-fi.com/birden. No perks or help will be given to this, Ko-fi is actually for different non-AI projects i do.

## Getting started

1. Download the release files from [HERE](https://github.com/birdenly/D16-LAN/releases) 
2. Place the files next to your game executable (`DOOMx64.exe` and `DOOMx64vk.exe`).
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

### 6. SnapMap P2P & Online Emulation
Entering SnapMap previously attempted to query Bethesda's Hydra cloud services, throwing notice dialogs (`There was an error connecting to Doom Online Services. Please try again. [RETRY] [STAY OFFLINE]`) and dropping the player into a restricted solo offline mode. In solo offline mode, selecting maps launched directly into singleplayer offline play without creating a multiplayer lobby. Furthermore, when entering with online tabs, the game asked for a Bethesda DOOM ID account (`#str_dlg_snapmap_doom_id_notice`, dialog `0x73`) and failed on username registration with *"Network request failed"*.

The executables are patched to:
- Bypass the Hydra query error when entering SnapMap (`idMenuManager_Shell::LaunchSnapmaps`), launching directly into the Hub.
- Force master online status across the engine (`idLocalUser::IsOnline` and `idHydraManager::IsConnected`), making all 70+ online checks in SnapMap recognize the player as online.
- Force `idLocalUser::SignInStatus` to return `0x16` (`USER_ONLINE_AND_AUTHENTICATED`), satisfying all login status checks in `LaunchSnapmaps` and `SnapmapHub`.
- Set `SnapmapHub::IsOnline` to true and rewire the `GoOnline` action to immediately mark `m_isOnline = 1` and refresh the hub locally, bypassing defunct cloud authentication.
- Silence the DOOM ID registration prompt (`#str_dlg_snapmap_doom_id_notice`, dialog `0x73`), completely bypassing the account creation screen.
- Silence background query failure dialogs (`SnapmapHub::OnError`, `SnapBrowserHelper::OnError`, `SnapmapMapInfo::OnError`, and `SnapBrowserHelper::OnMapDownloadError`), suppressing dialog `0x6C` and dialog `0xA1` ("Failed to sign into DOOM Services").
- Silence `idSnapBrowserHelper::HandleNoResults`, preventing the blocking modal notice `NOTICE: No results were found.` (dialog `0x48E`) from interrupting map browsing or downloaded map lists.
- Load local and downloaded maps (`idLocalSavedMapModel` / `savegame.user/.../SNAPMAPS*`) cleanly under **MY MAPS**.
- Eliminate the infinite `Loading...` stopwatch spinner on map detail screens (`SnapmapMapInfo::ShowScreen` `SetLoading` silence).
- Bypass the asynchronous cloud query to offline Bethesda Hydra endpoints in `SnapmapMapInfo::QueryMapDetails`, jumping straight to the success callback to set `m_isMapLoaded = 1` and instantly generate and enable the `PLAY`, `EDIT`, and map action buttons.
- Eliminate the infinite `Loading...` stopwatch spinner on the main Hub navigation bar (`SnapmapHub::SetLoading` silence).
- Bypass `#str_snap_server_request_wait` waiting modal in `SnapmapHub::SelectTab`, allowing tabs to load and switch immediately without freezing or locking user clicks.
- Force all SnapMap menu tabs (`FEATURED`, `PLAY`, `CREATE`, `ME`, `FIND MATCH`) and top-bar actions (Search, Feed) to remain permanently enabled and interactive (`SnapmapHub::UpdateTabs`).
- Bypass dead Hydra cloud queries for featured tiles and news feeds in `SnapmapHub::ShowScreen`.
- Force `RequestTabTiles` to take the engine's built-in offline route, instantly loading menu tiles for all tabs from local `snapmap_offline/broadcasts/` definitions (`DOWNLOADED MAPS`, `MY MAPS`, `CREATE NEW MAP`, `SEARCH`) without querying dead servers or leaving menus blank.
- Redirect map selection actions (`SnapmapMapInfo` and `SnapBrowserHelper`) from solo offline play into `LaunchSnapMapLobbyForPublishedMap` (SnapMap Multiplayer Game Lobby).
- Force the SnapMap lobby to create an immediate local P2P listen server lobby (`session->CreateMatchmakingLobby`) instead of searching for cloud matchmaking lobbies.
- Allow the host to start the SnapMap co-op match with any number of players (`SnapmapLobby MinPlayers Bypass`).
Connected players can join via Steam invite over LAN and load into co-op SnapMap matches seamlessly over P2P.
---


