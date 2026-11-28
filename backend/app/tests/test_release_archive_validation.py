from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "release" / "validate_historical_metric_debugger_zip.py"
SPEC = importlib.util.spec_from_file_location("release_archive_validation", MODULE_PATH)
assert SPEC and SPEC.loader
release_validation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_validation
SPEC.loader.exec_module(release_validation)


def _write_archive(path: Path, skill: str, *, extra: dict[str, str] | None = None) -> None:
    contents = {
        "LICENSE": "MIT",
        "COMMERCIAL_NOTICE.md": "Commercial notice",
        "README.md": "Read me",
        "requirements.txt": "duckdb==1.1.3\n",
        "SKILL.md": skill,
        "scripts/run_replay.py": "print('ok')\n",
    }
    contents.update(extra or {})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in contents.items():
            archive.writestr(name, content)


def test_release_archive_validator_accepts_reviewable_single_skill_zip(tmp_path: Path):
    archive = tmp_path / "candidate.zip"
    _write_archive(archive, "---\nname: candidate\ndescription: deterministic replay\n---\n")

    result = release_validation.validate_archive(archive)

    assert result.status == "pass"
    assert result.issues == ()


def test_release_archive_validator_blocks_routing_and_unapproved_files(tmp_path: Path):
    archive = tmp_path / "candidate.zip"
    _write_archive(
        archive,
        "---\nname: candidate\ndescription: deterministic replay\n---\nUse the package outside marketplace delivery.",
        extra={"dist/tool.whl": "binary"},
    )

    result = release_validation.validate_archive(archive)

    assert result.status == "blocked"
    assert {issue.code for issue in result.issues} == {"unexpected_file", "prohibited_file", "off_platform_routing"}
