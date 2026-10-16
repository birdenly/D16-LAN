import os
import shutil
import struct
import sys
import json

TARGETS = [
    {
        "exe_name": "DOOMx64.exe",
        "description": "DOOM (OpenGL)",
        "patches": [
            {
                "name": "UpdateTitleStorage Server Skip (Disable Online TSS)",
                "offset": 0x159C510,
                "original": bytes.fromhex("75 20"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses online Hydra/Bethesda title storage check and jumps straight to built-in 'disabled' routine (sets bTitleStorageReady = 1 immediately)."
            },
            {
                "name": "IsTitleStorageReady Unlock (Force True)",
                "offset": 0x1597100,
                "original": bytes.fromhex("0f b6 81 00 06 03 00 c3"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3 90 90"),
                "description": "Forces idSessionLocal::IsTitleStorageReady() to return true (1) immediately, dismissing the 'Loading title storage' screen."
            },
            {
                "name": "DedicatedServerGate Pass (Skip Gatekeeper & Force Gate Passed)",
                "offset": 0xF9E350,
                "original": bytes.fromhex("48 83 ec 28 48 8b"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces IsDedicatedServerGatePassed to return 1 (true) immediately, preventing HTTP gatekeeper timeout (198.20.198.48/gatekeeper) and bypassing 'Unable to reach dedicated server endpoints' modal."
            },
            {
                "name": "CanStartPrivateMatch Bypass (Force Can Start)",
                "offset": 0xF89D30,
                "original": bytes.fromhex("4c 8b dc 55 57 48"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces idLobbyController::CanStartPrivateMatch to return 1 (true) immediately, bypassing player/server requirements."
            },
            {
                "name": "PrivateMatch MinPlayers Bypass (Allow Solo / Any Count)",
                "offset": 0x103DF99,
                "original": bytes.fromhex("75 69"),
                "patched":  bytes.fromhex("eb 69"),
                "description": "Bypasses the minimum player count check in lobby start action, preventing '#str_dlg_mp_empty_team' warning."
            },
            {
                "name": "StartMatch Force Local Host (Bypass Cloud Dedicated Route)",
                "offset": 0x159B9E0,
                "original": bytes.fromhex("0f 84 e1 02 00 00"),
                "patched":  bytes.fromhex("e9 e2 02 00 00 90"),
                "description": "Unconditionally routes idSessionLocal::StartMatch into local host map loading, bypassing cloud server allocation."
            },
            {
                "name": "EndpointPingCheck Pass (Fix 'Unable to reach dedicated server endpoints')",
                "offset": 0xF9DB80,
                "original": bytes.fromhex("48 83 ec 28 48 8b"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces the dedicated server endpoint ping check (checked when pressing PRIVATE MATCH) to pass, preventing dialog 0x70 #str_dlg_no_valid_endpoint."
            },
            {
                "name": "P2PSessionRequest Friends Crash Fix (Allow LAN Players to Join)",
                "offset": 0x1908793,
                "original": bytes.fromhex("ff 15 17 59 6d 00 48 8b 17 48 8b c8 4c 8b 00 41 ff 50 38"),
                "patched":  bytes.fromhex("90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90"),
                "description": "Bypasses SteamFriends::GetFriendPersonaName in OnP2PSessionRequest, preventing emulator crash 0xC0000005 when players join and allowing AcceptP2PSessionWithUser to complete."
            },
            {
                "name": "StartMatch Skip Dedicated Server Allocation (Force Local StartLoading)",
                "offset": 0x159BD17,
                "original": bytes.fromhex("77 26"),
                "patched":  bytes.fromhex("eb 26"),
                "description": "Bypasses SetState(0xC / State_Find_Dedicated_Instance) in idSessionLocal::StartMatch when starting a Private Match, jumping directly to StartLoading() as local listen server and preventing '#str_dlg_no_dedicated_servers_found' (dialog 0x58)."
            },
            {
                "name": "giveXP CVar Default True (Enable XP Gain & Level-Up)",
                "offset": 0x167B0F,
                "original": bytes.fromhex("4c 8d 05 52 8d e9 01"),
                "patched":  bytes.fromhex("4c 8d 05 1e 25 ea 01"),
                "description": "Changes the default value of Title Storage CVar 'giveXP' from '0' to '1', enabling the HUD XP bar, XP callouts, and level-up calculation in offline/LAN mode."
            },
            {
                "name": "metrics_allowStatsAndXPInPrivateMatch Default True (Enable Private Match XP)",
                "offset": 0x130DCF,
                "original": bytes.fromhex("4c 8d 05 92 fa ec 01"),
                "patched":  bytes.fromhex("4c 8d 05 5e 92 ed 01"),
                "description": "Changes the default value of 'metrics_allowStatsAndXPInPrivateMatch' from '0' to '1', allowing XP, stats, medals, and challenges to be earned and saved to profile.bin in Private Matches."
            },
            {
                "name": "hud_showXPGainsInPrivateMatch Default True (Show +XP Popups in Private Match)",
                "offset": 0x13015F,
                "original": bytes.fromhex("4c 8d 05 02 07 ed 01"),
                "patched":  bytes.fromhex("4c 8d 05 ce 9e ed 01"),
                "description": "Changes the default value of 'hud_showXPGainsInPrivateMatch' from '0' to '1', showing +XP popups on the HUD during Private Matches."
            },
            {
                "name": "UpdateMatchResults Private Match Post-Match XP Summary Enable",
                "offset": 0x3BE116,
                "original": bytes.fromhex("0f 85 14 03 00 00"),
                "patched":  bytes.fromhex("90 90 90 90 90 90"),
                "description": "Allows idGameLocal::UpdateMatchResults to populate the Post-Match XP Summary (previousXP, currentXP, levelsGainedInMatch, matchXP) at the end of Private Matches."
            },
            {
                "name": "allowTaunts CVar Default True (Enable In-Game Taunts)",
                "offset": 0x167A9F,
                "original": bytes.fromhex("4c 8d 05 c2 8d e9 01"),
                "patched":  bytes.fromhex("4c 8d 05 8e 25 ea 01"),
                "description": "Changes the default value of Title Storage CVar 'allowTaunts' from '0' to '1', enabling in-game taunts in offline/LAN mode."
            },
            {
                "name": "LaunchSnapmaps Skip Offline Error (Fix SnapMap Notice Dialog)",
                "offset": 0xF9FA38,
                "original": bytes.fromhex("0f 84 a3 00 00 00"),
                "patched":  bytes.fromhex("e9 a4 00 00 00 90"),
                "description": "Bypasses the Hydra signed-in check in idMenuManager_Shell::LaunchSnapmaps when IsTitleStorageReady() is true, jumping directly to ShowScreen(snapmaps-hub) and preventing 'There was an error connecting to Doom Online Services'."
            },
            {
                "name": "SnapmapHub OnError Silence (Suppress Hub Background Query Notice)",
                "offset": 0x1080770,
                "original": bytes.fromhex("48 89 5c 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapHub::OnError from popping up dialog 0x6c when online featured tiles cannot be fetched."
            },
            {
                "name": "SnapBrowserHelper OnError Silence (Suppress Browser Query Notice)",
                "offset": 0xFD0020,
                "original": bytes.fromhex("48 89 5c 24 10"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::OnError from popping up dialog 0x6c when browsing offline maps."
            },
            {
                "name": "SnapmapMapInfo Play Bypass Solo (Route Play to SnapMap Lobby)",
                "offset": 0x1129CBE,
                "original": bytes.fromhex("74 1d"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses the IsHydraSignedIn() branch in SnapmapMapInfo, routing map play actions to LaunchSnapMapLobbyForPublishedMap (Multiplayer Co-op Lobby) instead of LaunchPublishedSnapMapForOfflinePlay (solo offline play)."
            },
            {
                "name": "SnapBrowserHelper Play Bypass Solo (Route Browser Play to SnapMap Lobby)",
                "offset": 0xFD09A5,
                "original": bytes.fromhex("74 1c"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses the IsHydraSignedIn() branch in SnapBrowserHelper::OnLoadForPlayCallback, routing map load actions to LaunchSnapMapLobbyForPublishedMap instead of solo offline play."
            },
            {
                "name": "LaunchSnapMapLobby Force P2P Hosting 1 (Skip Cloud Search Parms)",
                "offset": 0xF9F6B8,
                "original": bytes.fromhex("75 16"),
                "patched":  bytes.fromhex("eb 16"),
                "description": "Bypasses matchmaking search parameters setup in LaunchSnapMapLobbyForPublishedMap."
            },
            {
                "name": "LaunchSnapMapLobby Force P2P Hosting 2 (Create Local Matchmaking Lobby)",
                "offset": 0xF9F7D8,
                "original": bytes.fromhex("75 1e"),
                "patched":  bytes.fromhex("eb 1e"),
                "description": "Unconditionally routes LaunchSnapMapLobbyForPublishedMap to session->CreateMatchmakingLobby (snap.host.published), creating an immediate local P2P hosting lobby instead of searching cloud matchmaking."
            },
            {
                "name": "SnapmapLobby MinPlayers Bypass (Allow Solo / Any Player Count to Start)",
                "offset": 0x108D2D0,
                "original": bytes.fromhex("75 57"),
                "patched":  bytes.fromhex("eb 57"),
                "description": "Bypasses the minimum player requirement check in idMenuScreen_Shell_SnapmapLobby::TryToStartMatch, allowing the host to start the SnapMap co-op match with any number of players."
            },
            {
                "name": "SnapmapHub IsOnline Force True (Enable Full Online Layout & Tabs)",
                "offset": 0x107D7A0,
                "original": bytes.fromhex("40 53 48 83 ec 20"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces idMenuScreen_Shell_SnapmapHub::IsOnline to return 1 (true). Enables full SnapMap online layout (MY MAPS, BROWSE, CREATE), removes the offline 'GO ONLINE' banner tile, and allows multiplayer lobbies."
            },
            {
                "name": "SnapmapMapInfo OnError Silence (Suppress Dialog 0xA1)",
                "offset": 0x1129900,
                "original": bytes.fromhex("48 89 5c 24 20"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapMapInfo::OnError from popping up dialog 0xA1 ('Failed to sign into DOOM Services')."
            },
            {
                "name": "SnapBrowserHelper OnDownloadError Silence (Suppress Dialog 0xA1)",
                "offset": 0xFCF720,
                "original": bytes.fromhex("48 89 5c 24 10"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::OnMapDownloadError from popping up dialog 0xA1 ('Failed to sign into DOOM Services')."
            },
            {
                "name": "SnapmapHub DOOM ID Prompt Silence (Suppress Dialog 0x73)",
                "offset": 0x1081EE0,
                "original": bytes.fromhex("40 53 48 81 ec"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapHub::ShowScreen from prompting to create a DOOM ID / Bethesda account (dialog 0x73)."
            },
            {
                "name": "SnapBrowserHelper HandleNoResults Silence (Suppress Dialog 0x48E)",
                "offset": 0xFCF250,
                "original": bytes.fromhex("48 89 74 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::HandleNoResults from displaying the modal popup 'NOTICE: No results were found.' (dialog 0x48E)."
            },
            {
                "name": "idLocalUser IsOnline Force True (Master Online Status)",
                "offset": 0x181C920,
                "original": bytes.fromhex("48 83 ec 28 48 8b 89 60 01 00 00"),
                "patched":  bytes.fromhex("b0 01 c3 90 90 90 90 90 90 90 90"),
                "description": "Forces idLocalUser::IsOnline() to return 1 (true) unconditionally across all 70+ callers in the engine, enabling full online access to SnapMap menus, browsers, downloaded maps, and multiplayer features."
            },
            {
                "name": "idHydraManager IsConnected Force True (Hydra Status Bypass)",
                "offset": 0x18AED00,
                "original": bytes.fromhex("83 b9 e0 01 00 00 01 0f 94 c0 c3"),
                "patched":  bytes.fromhex("b0 01 c3 90 90 90 90 90 90 90 90"),
                "description": "Forces idHydraManager::IsConnected() to return 1 (true), reporting an active cloud service connection to all query managers."
            },
            {
                "name": "idLocalUser SignInStatus Force OK (Authenticated State 0x16)",
                "offset": 0x181DB60,
                "original": bytes.fromhex("48 8b c4 55 41 54"),
                "patched":  bytes.fromhex("b8 16 00 00 00 c3"),
                "description": "Forces idLocalUser::SignInStatus() to return 0x16 (OK / Online / Authenticated), satisfying all login and sign-in status checks in LaunchSnapmaps and SnapmapHub."
            },
            {
                "name": "SnapmapHub GoOnline Action Instant Online (Bypass Network Auth)",
                "offset": 0x10816F0,
                "original": bytes.fromhex("40 53 48 83 ec 20 33 c0 48 8b d9 48"),
                "patched":  bytes.fromhex("c6 81 50 03 00 00 01 e9 54 11 00 00"),
                "description": "When clicking 'Go Online', immediately sets internal m_isOnline flag to 1 and triggers an instant Hub UI refresh without attempting network authentication."
            },
            {
                "name": "SnapmapMapInfo SetLoading Silence (Disable Map Info Loading Spinner)",
                "offset": 0x109139C,
                "original": bytes.fromhex("b2 01"),
                "patched":  bytes.fromhex("31 d2"),
                "description": "Disables the infinite red stopwatch 'Loading...' spinner in idMenuScreen_Shell_SnapmapMapInfo::ShowScreen by passing bLoading=false to SetLoading, preventing the screen from getting stuck in an infinite loading state."
            },
            {
                "name": "SnapmapMapInfo QueryMapDetails Instant Complete (Bypass Cloud Query & Populate Buttons)",
                "offset": 0x1090870,
                "original": bytes.fromhex("48 8b c4 56 57"),
                "patched":  bytes.fromhex("e9 1b 05 00 00"),
                "description": "Bypasses the asynchronous cloud query to unreachable Bethesda Hydra services in idMenuScreen_Shell_SnapmapMapInfo::QueryMapDetails, jumping immediately to OnSuccessCallback to set m_isMapLoaded = 1 and call PopulateButtons & PopulateUI, instantly displaying PLAY, EDIT, and other action buttons."
            },
            {
                "name": "SnapmapHub ShowModalDialog Silence (Instant Tab Response)",
                "offset": 0x107D664,
                "original": bytes.fromhex("e8 07 b6 f2 ff"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Silences the call to ShowModalDialog('#str_snap_server_request_wait') in idMenuScreen_Shell_SnapmapHub::SelectTab, preventing the screen from locking input or showing a waiting modal dialog while tabs are being populated."
            },
            {
                "name": "SnapmapHub SetLoading Silence (Disable Hub Loading Spinner)",
                "offset": 0x1083570,
                "original": bytes.fromhex("48 89 6c 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Neutralizes idMenuScreen_Shell_SnapmapHub::SetLoading, immediately returning without playing 'rollOn' on the loading widget and preventing the infinite red stopwatch 'Loading...' spinner on the Hub screen."
            },
            {
                "name": "SnapmapHub All Tabs Force Enabled & Clickable (Full Menu Interaction)",
                "offset": 0x1083223,
                "original": bytes.fromhex("41 b0 01"),
                "patched":  bytes.fromhex("45 31 c0"),
                "description": "Forces r8b = 0 in idMenuScreen_Shell_SnapmapHub::UpdateTabs, unconditionally clearing the disabled 0x10 bit on all menu tabs (FEATURED, PLAY, CREATE, ME, FIND MATCH) and top-bar icons (Search, Feed), making the entire menu fully interactive and clickable."
            },
            {
                "name": "SnapmapHub ShowScreen Skip Featured Cloud Query (Bypass Dead Hydra Requests)",
                "offset": 0x10824D7,
                "original": bytes.fromhex("e8 44 2a 15 00"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Bypasses asynchronous background query to unreachable Bethesda Hydra endpoints for online featured tiles in idMenuScreen_Shell_SnapmapHub::ShowScreen."
            },
            {
                "name": "SnapmapHub ShowScreen Skip Feed Cloud Query (Bypass Dead Hydra Requests)",
                "offset": 0x10825A0,
                "original": bytes.fromhex("e8 1b c8 13 00"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Bypasses asynchronous background query to unreachable Bethesda Hydra endpoints for feed items in idMenuScreen_Shell_SnapmapHub::ShowScreen."
            },
            {
                "name": "RequestTabTiles Force Offline (Instant Local Tile Population)",
                "offset": 0x11BEB9C,
                "original": bytes.fromhex("0f 84 c2 00 00 00"),
                "patched":  bytes.fromhex("e9 c3 00 00 00 90"),
                "description": "Forces RequestTabTiles to unconditionally take the offline path (0x1411bf664), instantly loading tab tiles from local snapmap_offline/broadcasts/ JSON files without querying dead Bethesda servers."
            }
        ]
    },
    {
        "exe_name": "DOOMx64vk.exe",
        "description": "DOOM (Vulkan)",
        "patches": [
            {
                "name": "UpdateTitleStorage Server Skip (Disable Online TSS)",
                "offset": 0x159B5A0,
                "original": bytes.fromhex("75 20"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses online Hydra/Bethesda title storage check and jumps straight to built-in 'disabled' routine (sets bTitleStorageReady = 1 immediately)."
            },
            {
                "name": "IsTitleStorageReady Unlock (Force True)",
                "offset": 0x1596190,
                "original": bytes.fromhex("0f b6 81 00 06 03 00 c3"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3 90 90"),
                "description": "Forces idSessionLocal::IsTitleStorageReady() to return true (1) immediately, dismissing the 'Loading title storage' screen."
            },
            {
                "name": "DedicatedServerGate Pass (Skip Gatekeeper & Force Gate Passed)",
                "offset": 0xF9EE20,
                "original": bytes.fromhex("48 83 ec 28 48 8b"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces IsDedicatedServerGatePassed to return 1 (true) immediately, preventing HTTP gatekeeper timeout (198.20.198.48/gatekeeper) and bypassing 'Unable to reach dedicated server endpoints' modal."
            },
            {
                "name": "CanStartPrivateMatch Bypass (Force Can Start)",
                "offset": 0xF8A840,
                "original": bytes.fromhex("4c 8b dc 55 57 48"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces idLobbyController::CanStartPrivateMatch to return 1 (true) immediately, bypassing player/server requirements."
            },
            {
                "name": "PrivateMatch MinPlayers Bypass (Allow Solo / Any Count)",
                "offset": 0x103E9B9,
                "original": bytes.fromhex("75 69"),
                "patched":  bytes.fromhex("eb 69"),
                "description": "Bypasses the minimum player count check in lobby start action, preventing '#str_dlg_mp_empty_team' warning."
            },
            {
                "name": "StartMatch Force Local Host (Bypass Cloud Dedicated Route)",
                "offset": 0x159AA70,
                "original": bytes.fromhex("0f 84 e1 02 00 00"),
                "patched":  bytes.fromhex("e9 e2 02 00 00 90"),
                "description": "Unconditionally routes idSessionLocal::StartMatch into local host map loading, bypassing cloud server allocation."
            },
            {
                "name": "EndpointPingCheck Pass (Fix 'Unable to reach dedicated server endpoints')",
                "offset": 0xF9E6E0,
                "original": bytes.fromhex("48 83 ec 28 48 8b"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces the dedicated server endpoint ping check (checked when pressing PRIVATE MATCH) to pass, preventing dialog 0x70 #str_dlg_no_valid_endpoint."
            },
            {
                "name": "P2PSessionRequest Friends Crash Fix (Allow LAN Players to Join)",
                "offset": 0x1913BC3,
                "original": bytes.fromhex("ff 15 af 03 6b 00 48 8b 17 48 8b c8 4c 8b 00 41 ff 50 38"),
                "patched":  bytes.fromhex("90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90"),
                "description": "Bypasses SteamFriends::GetFriendPersonaName in OnP2PSessionRequest, preventing emulator crash 0xC0000005 when players join and allowing AcceptP2PSessionWithUser to complete."
            },
            {
                "name": "StartMatch Skip Dedicated Server Allocation (Force Local StartLoading)",
                "offset": 0x159ADA7,
                "original": bytes.fromhex("77 26"),
                "patched":  bytes.fromhex("eb 26"),
                "description": "Bypasses SetState(0xC / State_Find_Dedicated_Instance) in idSessionLocal::StartMatch when starting a Private Match, jumping directly to StartLoading() as local listen server and preventing '#str_dlg_no_dedicated_servers_found' (dialog 0x58)."
            },
            {
                "name": "giveXP CVar Default True (Enable XP Gain & Level-Up)",
                "offset": 0x167B0F,
                "original": bytes.fromhex("4c 8d 05 7a ef e7 01"),
                "patched":  bytes.fromhex("4c 8d 05 4e 87 e8 01"),
                "description": "Changes the default value of Title Storage CVar 'giveXP' from '0' to '1', enabling the HUD XP bar, XP callouts, and level-up calculation in offline/LAN mode."
            },
            {
                "name": "metrics_allowStatsAndXPInPrivateMatch Default True (Enable Private Match XP)",
                "offset": 0x130DCF,
                "original": bytes.fromhex("4c 8d 05 ba 5c eb 01"),
                "patched":  bytes.fromhex("4c 8d 05 8e f4 eb 01"),
                "description": "Changes the default value of 'metrics_allowStatsAndXPInPrivateMatch' from '0' to '1', allowing XP, stats, medals, and challenges to be earned and saved to profile.bin in Private Matches."
            },
            {
                "name": "hud_showXPGainsInPrivateMatch Default True (Show +XP Popups in Private Match)",
                "offset": 0x13015F,
                "original": bytes.fromhex("4c 8d 05 2a 69 eb 01"),
                "patched":  bytes.fromhex("4c 8d 05 fe 00 ec 01"),
                "description": "Changes the default value of 'hud_showXPGainsInPrivateMatch' from '0' to '1', showing +XP popups on the HUD during Private Matches."
            },
            {
                "name": "UpdateMatchResults Private Match Post-Match XP Summary Enable",
                "offset": 0x3BE7B6,
                "original": bytes.fromhex("0f 85 14 03 00 00"),
                "patched":  bytes.fromhex("90 90 90 90 90 90"),
                "description": "Allows idGameLocal::UpdateMatchResults to populate the Post-Match XP Summary (previousXP, currentXP, levelsGainedInMatch, matchXP) at the end of Private Matches."
            },
            {
                "name": "allowTaunts CVar Default True (Enable In-Game Taunts)",
                "offset": 0x167A9F,
                "original": bytes.fromhex("4c 8d 05 ea ef e7 01"),
                "patched":  bytes.fromhex("4c 8d 05 be 87 e8 01"),
                "description": "Changes the default value of Title Storage CVar 'allowTaunts' from '0' to '1', enabling in-game taunts in offline/LAN mode."
            },
            {
                "name": "LaunchSnapmaps Skip Offline Error (Fix SnapMap Notice Dialog)",
                "offset": 0xFA0508,
                "original": bytes.fromhex("0f 84 a3 00 00 00"),
                "patched":  bytes.fromhex("e9 a4 00 00 00 90"),
                "description": "Bypasses the Hydra signed-in check in idMenuManager_Shell::LaunchSnapmaps when IsTitleStorageReady() is true, jumping directly to ShowScreen(snapmaps-hub) and preventing 'There was an error connecting to Doom Online Services'."
            },
            {
                "name": "SnapmapHub OnError Silence (Suppress Hub Background Query Notice)",
                "offset": 0x1081300,
                "original": bytes.fromhex("48 89 5c 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapHub::OnError from popping up dialog 0x6c when online featured tiles cannot be fetched."
            },
            {
                "name": "SnapBrowserHelper OnError Silence (Suppress Browser Query Notice)",
                "offset": 0xFD0B30,
                "original": bytes.fromhex("48 89 5c 24 10"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::OnError from popping up dialog 0x6c when browsing offline maps."
            },
            {
                "name": "SnapmapMapInfo Play Bypass Solo (Route Play to SnapMap Lobby)",
                "offset": 0x112AB0E,
                "original": bytes.fromhex("74 1d"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses the IsHydraSignedIn() branch in SnapmapMapInfo, routing map play actions to LaunchSnapMapLobbyForPublishedMap (Multiplayer Co-op Lobby) instead of LaunchPublishedSnapMapForOfflinePlay (solo offline play)."
            },
            {
                "name": "SnapBrowserHelper Play Bypass Solo (Route Browser Play to SnapMap Lobby)",
                "offset": 0xFD14B5,
                "original": bytes.fromhex("74 1c"),
                "patched":  bytes.fromhex("90 90"),
                "description": "Bypasses the IsHydraSignedIn() branch in SnapBrowserHelper::OnLoadForPlayCallback, routing map load actions to LaunchSnapMapLobbyForPublishedMap instead of solo offline play."
            },
            {
                "name": "LaunchSnapMapLobby Force P2P Hosting 1 (Skip Cloud Search Parms)",
                "offset": 0xFA0188,
                "original": bytes.fromhex("75 16"),
                "patched":  bytes.fromhex("eb 16"),
                "description": "Bypasses matchmaking search parameters setup in LaunchSnapMapLobbyForPublishedMap."
            },
            {
                "name": "LaunchSnapMapLobby Force P2P Hosting 2 (Create Local Matchmaking Lobby)",
                "offset": 0xFA02A8,
                "original": bytes.fromhex("75 1e"),
                "patched":  bytes.fromhex("eb 1e"),
                "description": "Unconditionally routes LaunchSnapMapLobbyForPublishedMap to session->CreateMatchmakingLobby (snap.host.published), creating an immediate local P2P hosting lobby instead of searching cloud matchmaking."
            },
            {
                "name": "SnapmapLobby MinPlayers Bypass (Allow Solo / Any Player Count to Start)",
                "offset": 0x108E180,
                "original": bytes.fromhex("75 57"),
                "patched":  bytes.fromhex("eb 57"),
                "description": "Bypasses the minimum player requirement check in idMenuScreen_Shell_SnapmapLobby::TryToStartMatch, allowing the host to start the SnapMap co-op match with any number of players."
            },
            {
                "name": "SnapmapHub IsOnline Force True (Enable Full Online Layout & Tabs)",
                "offset": 0x107E330,
                "original": bytes.fromhex("40 53 48 83 ec 20"),
                "patched":  bytes.fromhex("b8 01 00 00 00 c3"),
                "description": "Forces idMenuScreen_Shell_SnapmapHub::IsOnline to return 1 (true). Enables full SnapMap online layout (MY MAPS, BROWSE, CREATE), removes the offline 'GO ONLINE' banner tile, and allows multiplayer lobbies."
            },
            {
                "name": "SnapmapMapInfo OnError Silence (Suppress Dialog 0xA1)",
                "offset": 0x112A750,
                "original": bytes.fromhex("48 89 5c 24 20"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapMapInfo::OnError from popping up dialog 0xA1 ('Failed to sign into DOOM Services')."
            },
            {
                "name": "SnapBrowserHelper OnDownloadError Silence (Suppress Dialog 0xA1)",
                "offset": 0xFD0230,
                "original": bytes.fromhex("48 89 5c 24 10"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::OnMapDownloadError from popping up dialog 0xA1 ('Failed to sign into DOOM Services')."
            },
            {
                "name": "SnapmapHub DOOM ID Prompt Silence (Suppress Dialog 0x73)",
                "offset": 0x1082A70,
                "original": bytes.fromhex("40 53 48 81 ec"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idMenuScreen_Shell_SnapmapHub::ShowScreen from prompting to create a DOOM ID / Bethesda account (dialog 0x73)."
            },
            {
                "name": "SnapBrowserHelper HandleNoResults Silence (Suppress Dialog 0x48E)",
                "offset": 0xFCFD60,
                "original": bytes.fromhex("48 89 74 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Prevents idSnapBrowserHelper::HandleNoResults from displaying the modal popup 'NOTICE: No results were found.' (dialog 0x48E)."
            },
            {
                "name": "idLocalUser IsOnline Force True (Master Online Status)",
                "offset": 0x181BB50,
                "original": bytes.fromhex("48 83 ec 28 48 8b 89 60 01 00 00"),
                "patched":  bytes.fromhex("b0 01 c3 90 90 90 90 90 90 90 90"),
                "description": "Forces idLocalUser::IsOnline() to return 1 (true) unconditionally across all 70+ callers in the engine, enabling full online access to SnapMap menus, browsers, downloaded maps, and multiplayer features."
            },
            {
                "name": "idHydraManager IsConnected Force True (Hydra Status Bypass)",
                "offset": 0x18B8A30,
                "original": bytes.fromhex("83 b9 e0 01 00 00 01 0f 94 c0 c3"),
                "patched":  bytes.fromhex("b0 01 c3 90 90 90 90 90 90 90 90"),
                "description": "Forces idHydraManager::IsConnected() to return 1 (true), reporting an active cloud service connection to all query managers."
            },
            {
                "name": "idLocalUser SignInStatus Force OK (Authenticated State 0x16)",
                "offset": 0x181CB80,
                "original": bytes.fromhex("48 8b c4 55 41 54"),
                "patched":  bytes.fromhex("b8 16 00 00 00 c3"),
                "description": "Forces idLocalUser::SignInStatus() to return 0x16 (OK / Online / Authenticated), satisfying all login and sign-in status checks in LaunchSnapmaps and SnapmapHub."
            },
            {
                "name": "SnapmapHub GoOnline Action Instant Online (Bypass Network Auth)",
                "offset": 0x1082280,
                "original": bytes.fromhex("40 53 48 83 ec 20 33 c0 48 8b d9 48"),
                "patched":  bytes.fromhex("c6 81 50 03 00 00 01 e9 a4 14 00 00"),
                "description": "When clicking 'Go Online', immediately sets internal m_isOnline flag to 1 and triggers an instant Hub UI refresh without attempting network authentication."
            },
            {
                "name": "SnapmapMapInfo SetLoading Silence (Disable Map Info Loading Spinner)",
                "offset": 0x109228C,
                "original": bytes.fromhex("b2 01"),
                "patched":  bytes.fromhex("31 d2"),
                "description": "Disables the infinite red stopwatch 'Loading...' spinner in idMenuScreen_Shell_SnapmapMapInfo::ShowScreen by passing bLoading=false to SetLoading, preventing the screen from getting stuck in an infinite loading state."
            },
            {
                "name": "SnapmapMapInfo QueryMapDetails Instant Complete (Bypass Cloud Query & Populate Buttons)",
                "offset": 0x1091760,
                "original": bytes.fromhex("48 8b c4 56 57"),
                "patched":  bytes.fromhex("e9 1b 05 00 00"),
                "description": "Bypasses the asynchronous cloud query to unreachable Bethesda Hydra services in idMenuScreen_Shell_SnapmapMapInfo::QueryMapDetails, jumping immediately to OnSuccessCallback to set m_isMapLoaded = 1 and call PopulateButtons & PopulateUI, instantly displaying PLAY, EDIT, and other action buttons."
            },
            {
                "name": "SnapmapHub ShowModalDialog Silence (Instant Tab Response)",
                "offset": 0x107E1F4,
                "original": bytes.fromhex("e8 47 b5 f2 ff"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Silences the call to ShowModalDialog('#str_snap_server_request_wait') in idMenuScreen_Shell_SnapmapHub::SelectTab, preventing the screen from locking input or showing a waiting modal dialog while tabs are being populated."
            },
            {
                "name": "SnapmapHub SetLoading Silence (Disable Hub Loading Spinner)",
                "offset": 0x1084450,
                "original": bytes.fromhex("48 89 6c 24 18"),
                "patched":  bytes.fromhex("c3 90 90 90 90"),
                "description": "Neutralizes idMenuScreen_Shell_SnapmapHub::SetLoading, immediately returning without playing 'rollOn' on the loading widget and preventing the infinite red stopwatch 'Loading...' spinner on the Hub screen."
            },
            {
                "name": "SnapmapHub All Tabs Force Enabled & Clickable (Full Menu Interaction)",
                "offset": 0x1084103,
                "original": bytes.fromhex("41 b0 01"),
                "patched":  bytes.fromhex("45 31 c0"),
                "description": "Forces r8b = 0 in idMenuScreen_Shell_SnapmapHub::UpdateTabs, unconditionally clearing the disabled 0x10 bit on all menu tabs (FEATURED, PLAY, CREATE, ME, FIND MATCH) and top-bar icons (Search, Feed), making the entire menu fully interactive and clickable."
            },
            {
                "name": "SnapmapHub ShowScreen Skip Featured Cloud Query (Bypass Dead Hydra Requests)",
                "offset": 0x1083067,
                "original": bytes.fromhex("e8 b4 2b 15 00"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Bypasses asynchronous background query to unreachable Bethesda Hydra endpoints for online featured tiles in idMenuScreen_Shell_SnapmapHub::ShowScreen."
            },
            {
                "name": "SnapmapHub ShowScreen Skip Feed Cloud Query (Bypass Dead Hydra Requests)",
                "offset": 0x1083130,
                "original": bytes.fromhex("e8 bb c8 13 00"),
                "patched":  bytes.fromhex("90 90 90 90 90"),
                "description": "Bypasses asynchronous background query to unreachable Bethesda Hydra endpoints for feed items in idMenuScreen_Shell_SnapmapHub::ShowScreen."
            },
            {
                "name": "RequestTabTiles Force Offline (Instant Local Tile Population)",
                "offset": 0x11BF7CC,
                "original": bytes.fromhex("0f 84 c2 00 00 00"),
                "patched":  bytes.fromhex("e9 c3 00 00 00 90"),
                "description": "Forces RequestTabTiles to unconditionally take the offline path (0x1411c0294), instantly loading tab tiles from local snapmap_offline/broadcasts/ JSON files without querying dead Bethesda servers."
            }
        ]
    }
]

def find_game_dir():
    # If files exist in current directory, use it
    if os.path.exists("DOOMx64.exe"):
        return os.getcwd()
    return os.getcwd()

def backup_file(filepath):
    bak_path = filepath + ".bak"
    if not os.path.exists(bak_path):
        print(f"[+] Creating backup: {bak_path}")
        shutil.copy2(filepath, bak_path)
        print("[+] Backup created successfully!")
    else:
        print(f"[*] Backup already exists: {bak_path}")
    return bak_path

def patch_executable(game_dir, target_info):
    exe_path = os.path.join(game_dir, target_info["exe_name"])
    if not os.path.exists(exe_path):
        print(f"[-] Executable not found: {exe_path}")
        return False

    print(f"\n========================================================")
    print(f" Processing: {target_info['description']} ({target_info['exe_name']})")
    print(f"========================================================")

    bak_path = backup_file(exe_path)

    all_ok = True
    with open(exe_path, "r+b") as f:
        for p in target_info["patches"]:
            f.seek(p["offset"])
            current = f.read(len(p["original"]))
            if current == p["patched"]:
                print(f"[*] {p['name']} is already applied.")
            elif current == p["original"]:
                f.seek(p["offset"])
                f.write(p["patched"])
                print(f"[+] {p['name']} applied successfully at 0x{p['offset']:X}!")
            else:
                print(f"[-] Unexpected bytes at 0x{p['offset']:X} ({p['name']}): {current.hex(' ')}")
                all_ok = False

    return all_ok

def restore_executable(game_dir, target_info):
    exe_path = os.path.join(game_dir, target_info["exe_name"])
    bak_path = exe_path + ".bak"
    if not os.path.exists(bak_path):
        print(f"[-] Backup not found for {target_info['exe_name']}")
        return False
    print(f"[*] Restoring {target_info['exe_name']} from backup...")
    shutil.copy2(bak_path, exe_path)
    print(f"[+] Restored original {target_info['exe_name']} successfully!")
    return True

def deploy_offline_broadcasts(game_dir):
    broadcast_dir = os.path.join(game_dir, "base", "snapmap_offline", "broadcasts")
    try:
        os.makedirs(broadcast_dir, exist_ok=True)
        files = {
            "snapmaps-hub-play.json": [
                {"type": "SNAP_HUB_EDIT_DOWNLOADED_MAPS", "text": "DOWNLOADED MAPS", "subText": "Browse and play your downloaded maps", "large": True, "ordinal": 0},
                {"type": "SNAP_HUB_EDIT_SAVED_MAPS", "text": "MY MAPS", "subText": "Play your locally created maps", "large": True, "ordinal": 1},
                {"type": "SNAP_HUB_SEARCH", "text": "SEARCH MAPS", "subText": "Search local map database", "large": False, "ordinal": 2}
            ],
            "snapmaps-hub-make.json": [
                {"type": "SNAP_HUB_EDIT_NEW_MAP", "text": "CREATE NEW MAP", "subText": "Start building a new SnapMap", "large": True, "ordinal": 0},
                {"type": "SNAP_HUB_EDIT_SAVED_MAPS", "text": "MY MAPS", "subText": "Continue editing your custom maps", "large": True, "ordinal": 1},
                {"type": "SNAP_HUB_EDIT_DOWNLOADED_MAPS", "text": "DOWNLOADED MAPS", "subText": "View and edit downloaded maps", "large": False, "ordinal": 2},
                {"type": "SNAP_HUB_EDIT_TUTORIAL_MAPS", "text": "TUTORIALS", "subText": "Learn the basics of SnapMap creation", "large": False, "ordinal": 3}
            ],
            "snapmaps-hub-me.json": [
                {"type": "SNAP_HUB_EDIT_DOWNLOADED_MAPS", "text": "DOWNLOADED MAPS", "subText": "Your downloaded community maps", "large": True, "ordinal": 0},
                {"type": "SNAP_HUB_EDIT_SAVED_MAPS", "text": "MY MAPS", "subText": "Your published and local creations", "large": True, "ordinal": 1},
                {"type": "SNAP_HUB_EDIT_NEW_MAP", "text": "CREATE NEW MAP", "subText": "Create a new custom map", "large": False, "ordinal": 2}
            ],
            "snapmaps-hub-feature.json": [
                {"type": "SNAP_HUB_EDIT_DOWNLOADED_MAPS", "text": "DOWNLOADED MAPS", "subText": "Access your downloaded maps library", "large": True, "ordinal": 0},
                {"type": "SNAP_HUB_EDIT_SAVED_MAPS", "text": "MY MAPS", "subText": "Browse your local creations", "large": True, "ordinal": 1}
            ],
            "snapmaps-hub-quick-play.json": [
                {"type": "SNAP_HUB_EDIT_DOWNLOADED_MAPS", "text": "DOWNLOADED MAPS", "subText": "Quick play downloaded maps", "large": True, "ordinal": 0},
                {"type": "SNAP_HUB_EDIT_SAVED_MAPS", "text": "MY MAPS", "subText": "Quick play your local maps", "large": False, "ordinal": 1}
            ]
        }
        for fname, content in files.items():
            fpath = os.path.join(broadcast_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
        print(f"[+] Deployed {len(files)} offline SnapMap broadcasts to {broadcast_dir}")
        return True
    except Exception as e:
        print(f"[-] Failed to deploy offline broadcasts: {e}")
        return False

def main():
    game_dir = os.getcwd()
    print(f"[*] Game Directory: {game_dir}")

    is_restore = len(sys.argv) > 1 and sys.argv[1] == "--restore"

    success_count = 0
    for target in TARGETS:
        if is_restore:
            if restore_executable(game_dir, target):
                success_count += 1
        else:
            if patch_executable(game_dir, target):
                success_count += 1

    if not is_restore:
        deploy_offline_broadcasts(game_dir)

    action = "Restoration" if is_restore else "Patching"
    print(f"\n[SUMMARY] {action} complete! {success_count}/{len(TARGETS)} targets processed successfully.")

if __name__ == "__main__":
    main()

