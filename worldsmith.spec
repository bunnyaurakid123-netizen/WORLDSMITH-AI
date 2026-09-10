# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

hiddenimports = collect_submodules('worldsmith')

# Runtime-loaded packages used by WorldSmith's provider/auth layers.
for package in ('amulet', 'google.genai', 'google.auth', 'google.oauth2', 'keyring'):
    try:
        pkg_data, pkg_bins, pkg_hidden = collect_all(package)
        hiddenimports += pkg_hidden
        datas += pkg_data if 'datas' in globals() else pkg_data
        binaries += pkg_bins if 'binaries' in globals() else pkg_bins
    except Exception:
        pass

try:
    datas, binaries, amulet_hidden = collect_all('amulet')
    hiddenimports += amulet_hidden
except Exception:
    datas, binaries = [], []

hiddenimports += [
    'google.genai',
    'google.auth',
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'google.oauth2.service_account',
    'google_auth_oauthlib.flow',
    'keyring.backends.Windows',
]

datas = datas or []
binaries = binaries or []

analysis = Analysis(
    ['run_worldsmith.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests'],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='WorldSmithAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
