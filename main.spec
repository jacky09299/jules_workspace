# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Lib\\site-packages\\cefpython3\\subprocess.exe', '.'),
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Lib\\site-packages\\cefpython3\\libcef.dll', '.'),
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Lib\\site-packages\\cv2\\cv2.pyd', 'cv2'),
    ],
    datas=[
        ('modules', 'modules'),
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Lib\\site-packages\\cefpython3\\locales', 'cefpython3/locales'),
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Lib\\site-packages\\cefpython3\\icudtl.dat', 'cefpython3'),
        ('C:\\Users\\Jacky\\anaconda3\\envs\\tools\\Library\\bin\\ffmpeg.exe', '.'),
    ],
    hiddenimports=[
        'cv2',
        'tkinter.filedialog',
        'tkinter.colorchooser',
        'tkinter.simpledialog',
        'tkinter.scrolledtext',
        'pandas',
        'openpyxl',
        'psutil',
        'lmfit',
        'PyPDF2',
        'pdfrw',
        'moviepy',
        'moviepy.editor',
        'moviepy.video.io.ffmpeg_reader',
        'moviepy.audio.io.audiofile_clip',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.platypus',
        'reportlab.lib.colors',
        'reportlab.graphics.shapes',
        'reportlab.graphics.charts',
        'cefpython3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PySide6', 'PySide2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)