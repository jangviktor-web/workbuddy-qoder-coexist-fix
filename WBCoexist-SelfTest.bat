@echo off
chcp 65001 >nul
"D:\Apps\WBCoexist\WBCoexist.exe" --selftest
type "D:\Apps\WBCoexist\selftest.txt"
pause
