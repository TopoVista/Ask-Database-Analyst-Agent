import asyncio
from app.workers.metrictrace import MetricTraceWorker

asyncio.run(MetricTraceWorker().run_forever())
