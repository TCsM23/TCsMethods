# PyInstaller recipe for the desktop app: python -m PyInstaller packaging/pixel-slides.spec
# Builds dist/Pixel Slides/ (one folder: starts faster than a one-file exe and
# is what the installer wizard copies).
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "slidedeck" / "templates"), "slidedeck/templates"),
        (str(ROOT / "slidedeck" / "static"), "slidedeck/static"),
        (str(ROOT / "decks"), "decks"),
    ],
    hiddenimports=["slidedeck.app", "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Pixel Slides",
    icon=str(ROOT / "packaging" / "icons" / "pixel-slides.ico"),
    console=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Pixel Slides")
