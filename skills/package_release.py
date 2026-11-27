"""Create a local, inspectable skill-pack ZIP; never performs a submission."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
destination = Path(sys.argv[1] if len(sys.argv) > 1 else root / "metrictrace-skill-pack.zip")
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob("*"):
        if path.is_file() and path.name != destination.name and path.suffix in {".md", ".py", ".txt"}:
            archive.write(path, path.relative_to(root.parent))
print(destination)
