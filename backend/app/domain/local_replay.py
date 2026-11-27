"""Platform compatibility exports for the shared Lite local replay engine."""

from metrictrace_sdk.local_replay import (
    LocalReplayError,
    LocalReplayLimits,
    compare_dataset_schemas,
    execute_local_scalar,
    inspect_datasets,
    run_local_four_way,
)

__all__ = [
    "LocalReplayError",
    "LocalReplayLimits",
    "compare_dataset_schemas",
    "execute_local_scalar",
    "inspect_datasets",
    "run_local_four_way",
]
