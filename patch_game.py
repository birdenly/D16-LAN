import os
import shutil
import struct
import sys

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

    action = "Restoration" if is_restore else "Patching"
    print(f"\n[SUMMARY] {action} complete! {success_count}/{len(TARGETS)} targets processed successfully.")

if __name__ == "__main__":
    main()

