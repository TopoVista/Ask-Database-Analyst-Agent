# Local full environment

Docker Desktop must be running its Linux engine. Copy values into a local
environment file if required, then run:

```powershell
docker compose up --build -d --scale worker=2
docker compose ps
docker compose logs worker
```

The stack has independent metadata/source PostgreSQL databases, MinIO, an
idempotent bucket initializer, migration job, API, workers and frontend. Named
volumes retain metadata, source records and object storage across ordinary
container restarts. Use `docker compose down`; do not add `-v` unless you
intend to delete local data.

Current validation blocker: Docker Desktop's `dockerDesktopLinuxEngine` pipe
was unavailable on this machine, so no container-based PostgreSQL, MinIO or
multi-worker experiment has been executed here.
