# Durable job execution

`durable_jobs` stores independently claimable work with a workspace scope,
idempotency key, priority, retry state, lease owner, expiry, heartbeat and
monotonic fencing token.

```text
API enqueue → QUEUED
worker claim (FOR UPDATE SKIP LOCKED on PostgreSQL) → RUNNING + token N
worker publishes only when owner/token/lease still match → SUCCEEDED
lease expires → another worker claim → RUNNING + token N+1
old worker publish → rejected as stale
```

Claims are short metadata transactions; no long execution runs while a claim
transaction is open. The worker loop is in `app/workers/runner.py` and must
be run as a separate process in deployed environments.

## Guarantees and limits

- At-least-once delivery with idempotent enqueue keys.
- A stale worker cannot use its old lease token to publish through the queue.
- Retryable categories use bounded exponential backoff with jitter.
- The current Phase 2 increment does **not yet** dispatch Replay Lab cells to
  this queue. Queue-to-replay wiring and worker recovery integration are the
  next implementation step, so replay remains synchronous today.
