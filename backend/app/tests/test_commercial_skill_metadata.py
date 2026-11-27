from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    closing = lines.index("---", 1)
    return dict(line.split(": ", 1) for line in lines[1:closing])


def test_first_commercial_expansion_skills_have_valid_metadata_and_shared_engine_boundary():
    expected = {
        "dataset-diff-inspector": "dataset-diff",
        "sql-join-auditor": "join-audit",
        "data-lineage-inspector": "lineage-inspect",
    }

    for skill_name, command in expected.items():
        skill_root = ROOT / "skills" / skill_name
        metadata = _frontmatter(skill_root / "SKILL.md")
        body = (skill_root / "SKILL.md").read_text(encoding="utf-8")

        assert metadata["name"] == skill_name
        assert metadata["description"]
        assert f"metrictrace {command}" in body
        assert "Security" in body
        assert "Deterministic verification" in body
        assert (skill_root / "README.md").is_file()
        assert (skill_root / "COMMERCIAL_NOTICE.md").is_file()
