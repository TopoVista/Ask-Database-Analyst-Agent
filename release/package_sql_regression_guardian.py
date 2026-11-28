"""Build and locally inspect the SQL Regression Guardian release archive.

This script only produces a local ZIP. It does not upload, submit, publish,
or contact a marketplace.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from build_sql_regression_guardian import build
from validate_historical_metric_debugger_zip import validate_archive


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "metric-regression-investigator"
EXPECTED_FILES = frozenset(
    {
        "LICENSE",
        "COMMERCIAL_NOTICE.md",
        "LISTING.md",
        "README.md",
        "requirements.txt",
        "SKILL.md",
        "scripts/run_regression.py",
    }
)
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def _write_deterministic(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, path.read_bytes())


def build_archive(output: Path, *, force: bool = False) -> Path:
    required = [ROOT / "LICENSE", *(SKILL / name for name in EXPECTED_FILES if name != "LICENSE")]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Release ZIP cannot be built; missing: " + ", ".join(missing))
    if output.exists() and not force:
        raise FileExistsError(f"Refusing to replace existing artifact: {output}")

    build(SKILL / "scripts" / "run_regression.py")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        _write_deterministic(archive, ROOT / "LICENSE", "LICENSE")
        for path in sorted(SKILL.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                _write_deterministic(archive, path, path.relative_to(SKILL).as_posix())
    if output.stat().st_size > 50 * 1024 * 1024:
        output.unlink()
        raise ValueError("Release ZIP exceeds the documented 50 MB submission limit.")

    validation = validate_archive(output, EXPECTED_FILES)
    if validation.status != "pass":
        output.unlink()
        raise ValueError("Release ZIP failed local validation: " + validation.as_json())
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=ROOT / "release" / "sql-regression-guardian-0.2.0.zip",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        print(build_archive(args.output, force=args.force))
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
