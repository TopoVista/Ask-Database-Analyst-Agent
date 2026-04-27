from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # pragma: no cover
    np = None


class AnomalyDetector:
    def detect(self, rows: list[dict], columns: list[str]) -> list[dict]:
        anomalies: list[dict] = []
        numeric_cols: list[str] = []
        for col in columns:
            values = [row.get(col) for row in rows if isinstance(row.get(col), (int, float))]
            if len(values) >= 4:
                numeric_cols.append(col)

        for col in numeric_cols:
            values = [float(row[col]) for row in rows if isinstance(row.get(col), (int, float))]
            if len(values) < 4:
                continue
            avg = mean(values)
            std = pstdev(values)
            if std > 0:
                for idx, value in enumerate(values):
                    z = abs((value - avg) / std)
                    if z > 2.5:
                        anomalies.append(
                            {
                                "column": col,
                                "value": float(value),
                                "z_score": float(round(z, 4)),
                                "severity": "high" if z > 3 else "medium",
                                "description": f"Value {value:.2f} in '{col}' is {z:.1f} standard deviations from the mean.",
                            }
                        )
            ordered = sorted(values)
            q1 = ordered[len(ordered) // 4]
            q3 = ordered[(len(ordered) * 3) // 4]
            iqr = q3 - q1
            if iqr > 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                for value in values:
                    if value < lower or value > upper:
                        anomalies.append(
                            {
                                "column": col,
                                "value": float(value),
                                "z_score": None,
                                "severity": "low",
                                "description": f"Value {value:.2f} in '{col}' is outside the IQR bounds.",
                            }
                        )
        return anomalies

