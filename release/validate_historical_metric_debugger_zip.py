"""Validate the reviewable contents of a Historical Metric Debugger ZIP.

This is a local release gate. It does not submit, upload, or certify an
archive for any marketplace.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "release" / "historical-metric-debugger.zip"
EXPECTED_FILES = frozenset(
    {
        "LICENSE",
        "COMMERCIAL_NOTICE.md",
        "README.md",
        "requirements.txt",
        "SKILL.md",
        "scripts/run_replay.py",
    }
)
PROHIBITED_SUFFIXES = frozenset({".whl", ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo"})
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
)
OFF_PLATFORM_ROUTING = re.compile(
    r"(?i)(?:use|install|download).{0,100}outside (?:this |the )?marketplace(?: delivery)?"
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    detail: str


@dataclass(frozen=True)
class ValidationResult:
    archive: str
    files: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]

    @property
    def status(self) -> str:
        return "pass" if not self.issues else "blocked"

    def as_json(self) -> str:
        return json.dumps(
            {
                "archive": self.archive,
                "files": list(self.files),
                "issues": [asdict(issue) for issue in self.issues],
                "status": self.status,
            },
            sort_keys=True,
        )


def _frontmatter_is_valid(skill: str) -> bool:
    if not skill.startswith("---\n"):
        return False
    frontmatter, separator, _ = skill[4:].partition("\n---\n")
    if not separator:
        return False
    fields = {line.split(":", 1)[0].strip() for line in frontmatter.splitlines() if ":" in line}
    return {"name", "description"}.issubset(fields)


def validate_archive(
    archive_path: Path, expected_files: frozenset[str] = EXPECTED_FILES
) -> ValidationResult:
    """Inspect an archive without extracting or executing its contents."""
    issues: list[ValidationIssue] = []
    if not archive_path.is_file():
        return ValidationResult(
            archive=str(archive_path),
            files=(),
            issues=(ValidationIssue("archive_missing", str(archive_path), "Archive does not exist."),),
        )

    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = tuple(sorted(info.filename for info in archive.infolist() if not info.is_dir()))
            unexpected = sorted(set(names) - expected_files)
            missing = sorted(expected_files - set(names))
            for path in unexpected:
                issues.append(ValidationIssue("unexpected_file", path, "Not part of the approved single-skill file set."))
            for path in missing:
                issues.append(ValidationIssue("required_file_missing", path, "Required for the single-skill archive."))

            for path in names:
                lower = path.lower()
                if lower.endswith(tuple(PROHIBITED_SUFFIXES)) or lower.startswith(".env") or "__pycache__" in lower:
                    issues.append(ValidationIssue("prohibited_file", path, "Binary, environment, or bytecode file is not allowed."))
                    continue
                try:
                    text = archive.read(path).decode("utf-8")
                except UnicodeDecodeError:
                    issues.append(ValidationIssue("non_text_file", path, "Archive content must be UTF-8 text/source."))
                    continue
                for pattern in SECRET_PATTERNS:
                    if pattern.search(text):
                        issues.append(ValidationIssue("secret_pattern", path, "Potential credential material found."))
                        break
                if "http://" in text or "https://" in text:
                    issues.append(ValidationIssue("external_link", path, "Marketplace package must not route buyers to an external URL."))
                if OFF_PLATFORM_ROUTING.search(text):
                    issues.append(
                        ValidationIssue(
                            "off_platform_routing",
                            path,
                            "Package directs buyers to use a workflow outside marketplace delivery.",
                        )
                    )

            if "SKILL.md" in names:
                skill = archive.read("SKILL.md").decode("utf-8")
                if not _frontmatter_is_valid(skill):
                    issues.append(ValidationIssue("invalid_skill_frontmatter", "SKILL.md", "Requires name and description frontmatter."))
    except zipfile.BadZipFile:
        return ValidationResult(
            archive=str(archive_path),
            files=(),
            issues=(ValidationIssue("invalid_zip", str(archive_path), "Not a readable ZIP archive."),),
        )
    return ValidationResult(archive=str(archive_path), files=names, issues=tuple(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument(
        "--expected-file",
        action="append",
        dest="expected_files",
        help="Exact archive file expected by the local release gate; repeat for each file.",
    )
    args = parser.parse_args()
    expected_files = frozenset(args.expected_files) if args.expected_files else EXPECTED_FILES
    result = validate_archive(args.archive, expected_files)
    print(result.as_json())
    return 0 if result.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
