# Snapshot object storage

`SnapshotStore` is the storage boundary for historical objects. Both local and
S3-compatible implementations accept only canonical generated keys under:

`workspaces/{workspace_id}/...`

Objects are immutable: a duplicate key is rejected. Local writes use a
temporary sibling object and atomic rename. S3/MinIO stores a SHA-256 in object
metadata and validates workspace namespace before every read, inspect or delete
operation. Cleanup accepts only generated staging prefixes; ready objects are
not eligible.

Production configuration rejects `HISTORICAL_STORAGE_BACKEND=local`. Configure
`HISTORICAL_STORAGE_BACKEND=s3`, bucket, endpoint and credentials to use MinIO
or S3. The original local Parquet writer remains the active capture adapter;
moving it to the new store's staged-object publication API is still required
before S3-backed capture can be claimed complete.
