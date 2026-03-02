@echo off
title Shaayari Backup — Google Drive Sync
color 0A

echo.
echo  ==========================================
echo    Shaayari Backup — Google Drive Sync
echo  ==========================================
echo.
echo  Connecting to Google Drive...
echo.

python "%~dp0shaayari_gdrive_sync.py"

echo.
echo  ==========================================
echo    Done! Check Documents\Shaayari_Backups\
echo  ==========================================
echo.

pause
