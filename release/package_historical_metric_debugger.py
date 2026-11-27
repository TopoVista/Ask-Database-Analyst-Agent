"""Build a single-skill review ZIP without publishing or submitting it."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from build_agensi_adapter import build as build_agensi_adapter


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ROOT / "LICENSE",
    ROOT / "release" / "agensi_candidate" / "SKILL.md",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=ROOT / "release" / "historical-metric-debugger.zip")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output after the caller has explicitly approved it",
    )
    args = parser.parse_args()
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        print("Release ZIP not built: owner-approved files required: " + ", ".join(missing), file=sys.stderr)
        return 2
    output = args.output
    if output.exists() and not args.force:
        print(
            f"Refusing to replace existing release artifact: {output}. "
            "Choose a new versioned path or pass --force after explicit approval.",
            file=sys.stderr,
        )
        return 4
    output.parent.mkdir(parents=True, exist_ok=True)
    build_agensi_adapter(ROOT / "release" / "agensi_candidate" / "scripts" / "run_replay.py")
    include = [ROOT / "LICENSE", ROOT / "release" / "agensi_candidate"]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in include:
            paths = item.rglob("*") if item.is_dir() else (item,)
            for path in paths:
                if path.is_file() and "__pycache__" not in path.parts:
                    arcname = path.name if path == ROOT / "LICENSE" else path.relative_to(ROOT / "release" / "agensi_candidate")
                    archive.write(path, arcname)
    if output.stat().st_size > 50 * 1024 * 1024:
        output.unlink()
        print("Release ZIP exceeds the documented 50 MB submission limit.", file=sys.stderr)
        return 3
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
