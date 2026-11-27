"""Write stable SHA-256 checksums for the final, locally built release artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = (
    ROOT / "backend" / "dist" / "metrictrace_lite-0.1.0-py3-none-any.whl",
    ROOT / "backend" / "dist" / "metrictrace_lite-0.1.0.tar.gz",
    ROOT / "release" / "historical-metric-debugger.zip",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "SHA256SUMS.txt")
    args = parser.parse_args()
    missing = [path for path in DEFAULT_ARTIFACTS if not path.is_file()]
    if missing:
        parser.error("Missing release artifacts: " + ", ".join(str(path.relative_to(ROOT)) for path in missing))
    args.output.write_text(
        "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in DEFAULT_ARTIFACTS),
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
