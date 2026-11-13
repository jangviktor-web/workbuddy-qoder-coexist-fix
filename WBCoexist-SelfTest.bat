@echo off
chcp 65001 >nul
set "EXE=D:\Apps\WBCoexist\portable\WBCoexist\WBCoexist.exe"
if not exist "%EXE%" set "EXE=D:\Apps\WBCoexist\WBCoexist.exe"
"%EXE%" --selftest
type "D:\Apps\WBCoexist\selftest.txt"
pause
