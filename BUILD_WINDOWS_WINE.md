# Windows EXE build with Wine

WorldSmith's GUI entry point is `worldsmith/__main__.py`.

PyInstaller is platform-specific: its documentation says it is not a general cross-compiler, so a Windows executable should be built in a Windows environment. On Linux, this repository's Wine script uses a real Windows Python installation inside Wine and runs Windows PyInstaller there. Wine is a compatibility layer for running Windows applications on POSIX systems.

## Prerequisites

- Linux host
- Wine
- A Windows Python 3.11/3.12 installation available inside the Wine prefix
- Internet access for pip dependencies

Set `WINEPREFIX` if needed and `WINPY` to the Windows Python executable, for example `C:/Python311/python.exe`.

Then run:

```bash
chmod +x build_windows_wine.sh
WINEPREFIX="$PWD/.wine-worldsmith" WINPY='C:/Python311/python.exe' ./build_windows_wine.sh
```

Output: `dist/WorldSmith.exe`.

For the most reliable release build, also run the same PyInstaller build on native Windows and launch-test the resulting EXE there. The Wine build is a reproducible Linux-hosted Windows build path, not a claim that PyInstaller natively cross-compiles Linux to Windows.
