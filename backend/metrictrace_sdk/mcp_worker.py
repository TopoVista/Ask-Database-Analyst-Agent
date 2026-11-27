"""Clean subprocess worker for MCP local replay on platforms where nested spawn can deadlock."""
from __future__ import annotations

import json
import sys

from metrictrace_sdk.local_replay import LocalReplayError, LocalReplayLimits, run_local_four_way_in_process
from metrictrace_sdk.regression import RegressionError


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        limits = LocalReplayLimits(**payload["limits"])
        if payload.get("operation") == "regression":
            from metrictrace_sdk.regression import check_sql_regression

            report = check_sql_regression(
                payload["datasets"], payload["baseline_sql"], payload["candidate_sql"],
                max_absolute_difference=payload.get("max_absolute_difference"),
                max_percent_difference=payload.get("max_percent_difference"),
                parameters=payload.get("parameters"), limits=limits,
                allowed_roots=tuple(payload["allowed_roots"]),
            )
            print(json.dumps({"ok": True, "regression": report}, sort_keys=True))
            return 0
        replay = run_local_four_way_in_process(
            payload["old_datasets"], payload["new_datasets"], payload["old_sql"], payload["new_sql"],
            limits, payload.get("parameters"), tuple(payload["allowed_roots"]),
        )
        print(json.dumps({"ok": True, "replay": replay}, sort_keys=True))
        return 0
    except (KeyError, TypeError, ValueError, LocalReplayError, RegressionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)[:512]}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
