# DOOM (2016) LAN

> DOOM (2016) LAN is a fan project. It is not affiliated with or endorsed by id Software or Bethesda Softworks.
> This was tested and made for a Steam copy.

A project to get DOOM (2016) Multiplayer and SnapMap working offline and over LAN with [GBE Fork](https://github.com/Detanup01/gbe_fork/releases). By default, the game gets stuck in loops or throws errors when launched without connection to Bethesda/Hydra online services.

Working exe version: `download_depot 379720 379721 7402417666934369131`

If you want to give a thanks: https://ko-fi.com/birden. No perks or help will be given to this, Ko-fi is actually for different non-AI projects I do.

---

## Getting Started

1. Download the release files from [HERE](https://github.com/birdenly/D16-LAN/releases).
2. Place the files next to your game executables (`DOOMx64.exe` and `DOOMx64vk.exe`).
3. Run `patch_game.exe`. This patches both the OpenGL (`DOOMx64.exe`) and Vulkan (`DOOMx64vk.exe`) executables to work offline/locally and creates `.bak` backups of your original clean files. (Nearly ALL test were done on OpenGL, use it if Vulkan is giving problems)
4. Run `Start_game.bat` to launch the game. Alternatively, you can add these launch options in Steam:

   `+com_skipIntroVideo 1 +net_dedicatedServerGate_Enable 0 +net_peerTimeoutDisabled 1 +net_peerTimeoutDuringLoadMS 120000 +net_peerTimeoutInSeconds 120 +net_peerTimeoutInSeconds_Lobby 120 +net_connectTimeoutInSeconds 120 +net_waitOnPeerToLoadTimer_Seconds 120 +net_waitOnPeersToLoadMinimumCount 2 +net_forceStartMatchTimeLimit 120 +com_logFile 2 +menu_allowPrivateMatch 1 +menu_startMatchAlwaysAllowed 1 +gc_minPlayersInPrivateMatch 1 +metrics_allowStatsAndXPInPrivateMatch 1 +hud_showXPGainsInPrivateMatch 1 +metrics_xpMultiplier 1.0`

---

## Playing Downloaded Maps in LAN Co-op
Maps in the Featured menu work without the setup below, simply start the lobby and invite other and they will work.

0. Download SnapMap maps from the main game (without the LAN patch), they will be placed in your savegame folder.

1. **Place the map files on each player's save folder:**
   Each player places their downloaded map folder (e.g. `SNAPMAPS...`) inside their own save directory:
   ```
   C:\Users\<YourUser>\Saved Games\id Software\DOOM\base\savegame.user\<SteamID>\
   ```

2. **Launch the game:**
   Launch the game using `Start_game.bat` (or use the launch options above. You can add `+com_gameMode 1 +com_gameType 1` to go directly into SnapMap).

3. **Pre-load the map in memory:**
   All players enter SnapMap, go to **PLAY** -> **Featured Maps** -> Select ANY map -> **CHANGE MAP** -> **DOWNLOADED MAPS**, and select the same map so the engine loads the map assets into RAM in each session. Sadly, this will need to be done for every map change, this pre-load into memory was done by the main server.

4. After that, simply invite other players into the lobby and play. When the match ends do step 3 again.

---

## How It Works

### 1. Title Storage Loop
On startup and when entering Multiplayer, the game calls `idSessionLocal::UpdateTitleStorage` to download configuration data (`tss.bin`) from Bethesda servers. When offline, this request never completes and leaves the game stuck on `NOTICE: Loading title storage.`

The executable is patched to take the built-in disabled routine in `UpdateTitleStorage` and force `IsTitleStorageReady()` to return `true`, skipping the loading screen on the first frame.

### 2. Dedicated Server Gatekeeper & Endpoint Checks
Selecting **Private Match** queries Bethesda's gatekeeper server (`198.20.198.48/gatekeeper`) and pings dedicated server endpoints. When unreachable, the game blocks access with `Unable to reach dedicated server endpoints.`

Both `IsDedicatedServerGatePassed` and the endpoint ping check are patched to return `true` immediately, unlocking the Private Match menu without any network dependency.

### 3. Private Match Local Hosting
Starting a Private Match originally required a cloud dedicated server (`State_Find_Dedicated_Instance`). If none was available, it failed with `Unable to find a dedicated server.` It also prevented starting a match with fewer than 2 players.

The lobby and session start routines (`CanStartPrivateMatch`, `StartMatch`, and minimum players) were patched to bypass dedicated server allocation and host locally as a listen server over P2P.

### 4. LAN Join & P2P Connection Fix
When a second player joins a Private Match lobby over LAN, the `OnP2PSessionRequest` callback called `SteamFriends()->GetFriendPersonaName()` before accepting the session. On LAN where players are not on an online Steam friends list, this caused an access violation crash (`0xC0000005`) on the host.

The redundant persona name lookup was removed so `AcceptP2PSessionWithUser` executes immediately, allowing players to join lobbies seamlessly.

### 5. Local XP, Leveling & Progression
By default, Private Matches disabled all XP and stat gains (`metrics_allowStatsAndXPInPrivateMatch = 0`), hid HUD XP popups (`hud_showXPGainsInPrivateMatch = 0`), cleared the post-match summary (`idGameLocal::UpdateMatchResults`), and kept the Title Storage variable `giveXP` locked to `0`.

These checks were patched in the executable so kills, medals, challenges, post-match XP summaries, in-game taunts (`allowTaunts`), and level-ups work in Private Matches and save directly to your local profile (`profile.bin`). You can customize `XP_MULTIPLIER` inside `Start_game.bat` (`+metrics_xpMultiplier`).

### 6. SnapMap LAN Co-op
Retail SnapMap was designed around Bethesda Hydra cloud servers for account authentication, hub menus, and map validation. Without internet connection, entering SnapMap would hang on `NOTICE: Signing into DOOM Services` (Dialog `0x97`), lock menu tabs, and prevent starting multiplayer lobbies.

The executable is patched to bypass online account and privilege checks, unlock all SnapMap tabs, disable HMAC signature validation (`CYBERDEMON`) to allow playing maps from any source, and redirect matchmaking into a local P2P listen server lobby. Network timeouts (`CheckHeartbeats`, `MapFinishedLoading`, `net_peerTimeoutDuringLoadMS`) and packet congestion drops were also patched to ensure players stay connected and load together smoothly over LAN.

