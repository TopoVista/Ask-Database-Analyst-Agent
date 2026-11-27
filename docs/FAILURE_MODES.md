# Failure modes

| Scenario | Current behavior | Validation |
| --- | --- | --- |
| Duplicate enqueue | Existing workspace/idempotency key returns the existing job | Unit test |
| Worker lease expires | A later claim increments fencing token | Unit test |
| Stale worker publishes | Queue rejects old owner/token | Unit test |
| Local object overwrite | Store rejects it | Unit test |
| Staging cleanup targets ready object | Store rejects it | Unit test |
| Existing synchronous replay cell fails | Cell remains failed with no numeric value | Existing replay code |

PostgreSQL concurrent claims, MinIO outage recovery, worker crash during an
actual replay, and PostgreSQL repeatable-read snapshot consistency are not yet
executed in this environment. They remain required integration experiments.
