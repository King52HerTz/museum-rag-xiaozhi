@echo off
setlocal
chcp 65001 >nul
title 智博导览 RAG 一键启动
cd /d "%~dp0"

echo 正在启动智博导览管理平台、博物馆知识库和小智服务端，请稍候...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_museum_rag.ps1" -ForceRestart -OpenBrowser
set "START_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%START_EXIT_CODE%"=="0" (
    echo.
    echo 博物馆 RAG 启动失败，请查看上面的提示或 runtime-logs\museum-startup\logs。
) else (
    echo 启动完成。
    echo 管理端地址：http://127.0.0.1:8001/
    echo 登录后点击“博物馆知识库”即可进行上传和问答测试。
)

echo.
echo 按任意键关闭此窗口，关闭窗口不会停止已经启动的服务。
pause >nul

endlocal & exit /b %START_EXIT_CODE%
