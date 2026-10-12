@echo off
set XP_MULTIPLIER=1.0

echo ========================================================
echo Starting DOOM
echo XP Multiplier: %XP_MULTIPLIER%x
echo ========================================================
start "" "DOOMx64.exe" +com_skipIntroVideo 1 +net_dedicatedServerGate_Enable 0 +menu_allowPrivateMatch 1 +menu_startMatchAlwaysAllowed 1 +gc_minPlayersInPrivateMatch 1 +metrics_allowStatsAndXPInPrivateMatch 1 +hud_showXPGainsInPrivateMatch 1 +metrics_xpMultiplier %XP_MULTIPLIER%
