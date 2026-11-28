from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "release" / "build_sql_regression_guardian.py"


def test_generated_runner_is_self_contained_and_has_stable_gate_contract(tmp_path):
    runner = tmp_path / "run_regression.py"
    generated = subprocess.run(
        [sys.executable, str(BUILDER), "--output", str(runner)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.stdout.strip() == str(runner)
    source = runner.read_text(encoding="utf-8")
    assert "metrictrace_sdk" not in source
    assert len(source.encode("utf-8")) < 20_000

    dataset = tmp_path / "orders.csv"
    baseline = tmp_path / "before.sql"
    candidate = tmp_path / "after.sql"
    dataset.write_text("amount\n10\n", encoding="utf-8")
    baseline.write_text("SELECT SUM(amount) FROM source_data", encoding="utf-8")
    candidate.write_text("SELECT 0 FROM source_data", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--dataset",
            str(dataset),
            "--baseline-sql-file",
            str(baseline),
            "--candidate-sql-file",
            str(candidate),
            "--allow-root",
            str(tmp_path),
            "--max-absolute-difference",
            "1",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3
    body = json.loads(result.stdout)
    assert body["ok"] is False
    assert body["regression"]["gates"][0]["status"] == "FAIL"
