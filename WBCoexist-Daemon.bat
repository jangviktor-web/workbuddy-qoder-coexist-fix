@echo off
set "EXE=D:\Apps\WBCoexist\portable\WBCoexist\WBCoexist.exe"
if not exist "%EXE%" set "EXE=D:\Apps\WBCoexist\WBCoexist.exe"
start "" "%EXE%" --daemon
