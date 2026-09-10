# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

hiddenimports = collect_submodules('worldsmith')
datas = []
binaries = []

# Runtime-loaded packages used by the world engine, AI providers and Windows auth/storage.
for package in ('amulet', 'google.genai', 'google.auth', 'google.oauth2', 'google_auth_oauthlib', 'keyring'):
    try:
        pkg_data, pkg_bins, pkg_hidden = collect_all(package)
        datas.extend(pkg_data)
        binaries.extend(pkg_bins)
        hiddenimports.extend(pkg_hidden)
    except Exception:
        pass

hiddenimports += [
    'google.genai',
    'google.auth',
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'google.oauth2.service_account',
    'google_auth_oauthlib.flow',
    'keyring.backends.Windows',
]

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
