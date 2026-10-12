@echo off
set GAME_DIR=D:\Jogos\steam\steamapps\common\DOOM

if exist "%~dp0DOOMx64.exe" (
    set EXE_PATH=%~dp0DOOMx64.exe
) else (
    set EXE_PATH=%GAME_DIR%\DOOMx64.exe
)

echo ========================================================
echo Starting DOOM with LAN / Multiplayer optimizations...
echo ========================================================
start "" "%EXE_PATH%" +com_skipIntroVideo 1 +net_dedicatedServerGate_Enable 0 +menu_allowPrivateMatch 1 +menu_startMatchAlwaysAllowed 1 +gc_minPlayersInPrivateMatch 1
