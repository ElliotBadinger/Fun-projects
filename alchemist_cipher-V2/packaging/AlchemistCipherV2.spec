[
    ],
    binaries=[],
    datas=[
        ('alchemist_cipher-V2\\tutorial.py', '.'),
        ('alchemist_cipher-V2\\tutorial_content.html', '.'),
        ('alchemist_cipher-V2\\icons', 'icons'),
        ('alchemist_cipher-V2\\game_data', 'game_data')
    ],
    hiddenimports=['themes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

# Add the COLLECT step for one-directory builds
# coll = COLLECT(
#    exe,
#    a.binaries,
#    a.datas,
#    strip=False,
#    upx=True,
#    upx_exclude=[],
#    name='AlchemistCipherV2'
# )

# ... content of EXE(...) definition ...
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AlchemistCipherV2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='alchemist_cipher-V2/icons/app-logo(V2).ico'
) 