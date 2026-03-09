@echo off
REM Build both GestureFlow apps using PyInstaller.
REM Run from project_final/ root.

echo === Building GestureFlow HCI ===
pyinstaller scripts/build_hci.spec --distpath dist/hci --workpath build/hci --clean -y
if %ERRORLEVEL% NEQ 0 (
    echo HCI build FAILED
    exit /b 1
)

echo.
echo === Building GestureFlow Canvas ===
pyinstaller scripts/build_canvas.spec --distpath dist/canvas --workpath build/canvas --clean -y
if %ERRORLEVEL% NEQ 0 (
    echo Canvas build FAILED
    exit /b 1
)

echo.
echo === Both builds complete ===
echo HCI:    dist\hci\GestureFlowHCI.exe
echo Canvas: dist\canvas\GestureFlowCanvas.exe
