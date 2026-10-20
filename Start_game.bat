@echo off
set XP_MULTIPLIER=1.0

echo ========================================================
echo Starting DOOM
echo XP Multiplier: %XP_MULTIPLIER%x
echo ========================================================
start "" "DOOMx64.exe" +com_skipIntroVideo 1 +net_dedicatedServerGate_Enable 0 +net_peerTimeoutDisabled 1 +net_peerTimeoutDuringLoadMS 120000 +net_peerTimeoutInSeconds 120 +net_peerTimeoutInSeconds_Lobby 120 +net_connectTimeoutInSeconds 120 +net_waitOnPeerToLoadTimer_Seconds 120 +net_waitOnPeersToLoadMinimumCount 2 +net_forceStartMatchTimeLimit 120 +com_logFile 2 +menu_allowPrivateMatch 1 +menu_startMatchAlwaysAllowed 1 +gc_minPlayersInPrivateMatch 1 +metrics_allowStatsAndXPInPrivateMatch 1 +hud_showXPGainsInPrivateMatch 1 +metrics_xpMultiplier %XP_MULTIPLIER% +com_gameMode 1 +com_gameType 1
