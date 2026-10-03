@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== PAYE GAMES DUB STUDIO - TANILAMA =====
echo.
echo [1] Python var mi?
where python
where pythonw
echo.
echo [2] Surum:
python --version
echo.
echo [3] Gerekli paketler:
python -c "import faster_whisper; print('faster-whisper TAMAM')" 2>nul || echo faster-whisper YOK  (pip install faster-whisper)
python -c "import argostranslate; print('argostranslate TAMAM')" 2>nul || echo argostranslate YOK  (pip install argostranslate)
python -c "import numpy, av; print('numpy + av TAMAM')" 2>nul || echo numpy/av YOK  (pip install numpy av)
python -c "import tkinter; print('tkinter TAMAM (klasor secme penceresi icin)')" 2>nul || echo tkinter yok - klasor yolunu elle yazarsin
echo.
echo [4] Sunucu konsolla baslatiliyor - hata varsa asagida gorunecek.
echo     Tarayici acilacak; kapatmak icin bu pencerede Ctrl+C.
echo ------------------------------------------------------------
python "sunucu.py"
echo ------------------------------------------------------------
echo Cikis kodu: %errorlevel%
pause
