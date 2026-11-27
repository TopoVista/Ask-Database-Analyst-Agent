# MetricTrace UX contract

## Canonical owners

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Navigation | `Sidebar` and `Header` | Route shell | Route links | Current route visible in both layouts. |
| Primary action | `Button` | Shared primitive | Default / outline / secondary | Disabled and `aria-busy` during replay submission. |
| Status | `Badge` and inline alert | Shared primitives | Completed / failed | Completed/failed status always includes text. |
| Evidence table | Replay Lab route | Replay API response | Horizontal overflow | All four inputs remain visible on narrow screens. |
| Select/Listbox | Native `<select>` | Platform control | Native only | Keyboard and popup behavior remain browser-owned. |

## Replay Lab behavior

`Run canonical replay` makes one server mutation, preserves previous evidence
while another run is pending, and exposes server failure in a page-scoped
alert. The server, not the UI, determines all values and statuses. The route
title follows the root MetricTrace title until route metadata is expanded.
