import os
from pathlib import Path

# Point the app at the sample decks before it is imported.
os.environ.setdefault("SLIDES_DECKS_DIR", str(Path(__file__).resolve().parent.parent / "decks"))
