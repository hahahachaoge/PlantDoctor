block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
        datas=[
        ('image', 'image'),
        ('avatars', 'avatars'),
        ('database', 'database'),
        ('screens', 'screens'),
        ('widgets', 'widgets'),
        ('config.py', '.'),
        ('utils.py', '.'),
        ('smart_agri.db', '.'),
    ],

    hiddenimports=[
        'kivy',
        'kivy.core.window',
        'kivy.core.window.window_sdl2',
        'kivy.core.image',
        'kivy.core.image.img_sdl2',
        'kivy.core.text',
        'kivy.core.text.text_sdl2',
        'kivy.core.audio',
        'kivy.core.clipboard',
        'kivy.core.clipboard.clipboard_sdl2',
        'kivy.graphics',
        'kivy.graphics.cgl_backend',
        'kivy.graphics.cgl_backend.cgl_glew',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'kivy_deps.gstreamer',
        'kivy_deps.angle',
        'kivy_deps.glew',
        'kivy_deps.sdl2',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='农智云警',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='农智云警',
)
