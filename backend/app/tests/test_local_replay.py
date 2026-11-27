from __future__ import annotations

from app.domain.local_replay import LocalReplayLimits, run_local_four_way


def test_local_file_replay_uses_exact_queries_and_shared_attribution(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    old.write_text("amount_inr,status,channel\n2100000,paid,direct\n300000,paid,marketplace\n", encoding="utf-8")
    new.write_text("amount_inr,status,channel\n1800000,paid,direct\n420000,paid,marketplace\n", encoding="utf-8")
    replay = run_local_four_way(str(old), str(new), "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid'", "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid' AND channel <> 'marketplace'", LocalReplayLimits(timeout_seconds=15))
    assert replay["cells"]["old_data_old_definition"] == "2400000"
    assert replay["cells"]["new_data_new_definition"] == "1800000"
    assert replay["attribution"]["reconciles"] is True
