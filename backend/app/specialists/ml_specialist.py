"""ML Specialist for model training and evaluation."""

from __future__ import annotations

import math
from typing import Any

from app.core.registry import skill


def _mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def _std(values: list[float]) -> float:
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / max(len(values) - 1, 1)
    return math.sqrt(variance)


def _extract_column(data: list[dict], column: str) -> list[float]:
    return [float(row.get(column, 0)) for row in data if column in row]


def _linear_regression_fit(x: list[float], y: list[float]) -> dict[str, Any]:
    """Simple linear regression using least squares."""
    n = len(x)
    if n < 2:
        return {"error": "need at least 2 samples"}

    mean_x = _mean(x)
    mean_y = _mean(y)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den = sum((xi - mean_x) ** 2 for xi in x)
    if den == 0:
        return {"error": "zero variance in feature"}

    slope = num / den
    intercept = mean_y - slope * mean_x
    predictions = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - pi) ** 2 for yi, pi in zip(y, predictions))
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(max(r_squared, 0.0), 4),
        "method": "linear_regression",
    }


def _solve_linear_system(matrix: list[list[float]], target: list[float]) -> list[float] | None:
    """Solve a small dense system with Gauss-Jordan elimination.

    Worker input caps keep this intentionally small (at most five features),
    avoiding NumPy/scikit-learn memory overhead on a 512 MB service.
    """
    size = len(target)
    augmented = [matrix[i][:] + [target[i]] for i in range(size)]
    for pivot in range(size):
        best = max(range(pivot, size), key=lambda row: abs(augmented[row][pivot]))
        if abs(augmented[best][pivot]) < 1e-12:
            return None
        augmented[pivot], augmented[best] = augmented[best], augmented[pivot]
        divisor = augmented[pivot][pivot]
        augmented[pivot] = [value / divisor for value in augmented[pivot]]
        for row in range(size):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            augmented[row] = [value - factor * base for value, base in zip(augmented[row], augmented[pivot])]
    return [augmented[row][-1] for row in range(size)]


def _multivariate_regression_fit(data: list[dict], target: str, features: list[str]) -> dict[str, Any]:
    rows: list[tuple[list[float], float]] = []
    for row in data:
        try:
            rows.append(([float(row[feature]) for feature in features], float(row[target])))
        except (KeyError, TypeError, ValueError):
            continue
    if len(rows) < max(3, len(features) + 1):
        return {"error": "insufficient_valid_rows"}

    # X includes an intercept. A small ridge term makes correlated features
    # numerically stable without a heavyweight numerical dependency.
    width = len(features) + 1
    gram = [[0.0 for _ in range(width)] for _ in range(width)]
    cross = [0.0 for _ in range(width)]
    for values, outcome in rows:
        vector = [1.0, *values]
        for i in range(width):
            cross[i] += vector[i] * outcome
            for j in range(width):
                gram[i][j] += vector[i] * vector[j]
    for i in range(1, width):
        gram[i][i] += 1e-6
    coefficients = _solve_linear_system(gram, cross)
    if coefficients is None:
        return {"error": "singular_feature_matrix"}
    actual = [outcome for _, outcome in rows]
    predicted = [coefficients[0] + sum(weight * value for weight, value in zip(coefficients[1:], values)) for values, _ in rows]
    mean_y = _mean(actual)
    ss_res = sum((observed - estimate) ** 2 for observed, estimate in zip(actual, predicted))
    ss_tot = sum((observed - mean_y) ** 2 for observed in actual)
    return {
        "intercept": round(coefficients[0], 6),
        "coefficients": {feature: round(weight, 6) for feature, weight in zip(features, coefficients[1:])},
        "r_squared": round(max(0.0, 1 - ss_res / ss_tot) if ss_tot else 0.0, 4),
        "n_samples": len(rows),
        "method": "ridge_linear_regression",
    }


class MLSpecialist:
    """ML Specialist for model training and evaluation."""

    name: str = "ml_specialist"
    description: str = "Train/evaluate models: regression, classification, prediction"

    def __init__(self) -> None:
        self._model: dict[str, Any] | None = None

    @skill("train_model")
    async def train_model(
        self,
        data: list[dict],
        target: str,
        features: list[str],
        task: str = "regression",
    ) -> dict[str, Any]:
        """Train a model on row-based data.

        Args:
            data: List of dicts (rows).
            target: Name of the target column.
            features: Names of feature columns.
            task: 'regression' or 'classification'.
        """
        if not data or len(data) < 2:
            return {"error": "insufficient data", "model_type": task}

        y = _extract_column(data, target)
        if not y or len(y) < 2:
            return {"error": "target column not found or insufficient", "model_type": task}

        if not features or len(features) > 5:
            return {"error": "features_must_contain_between_1_and_5_columns"}
        result = _multivariate_regression_fit(data, target, features)
        result.update({"model_type": task, "target": target, "features": features})
        if "error" not in result:
            model = {
                "intercept": result["intercept"],
                "coefficients": result["coefficients"],
                "target": target,
                "features": features,
                "task": task,
                "method": result["method"],
            }
            self._model = model
            result["model"] = model  # portable: works across stateless workers
            result["feature_importance"] = {
                feature: round(abs(weight), 6) for feature, weight in result["coefficients"].items()
            }
        return result

    @skill("predict")
    async def predict(self, data: list[dict], model: dict[str, Any] | None = None) -> list[dict]:
        """Make predictions using the trained model."""
        active_model = model or self._model
        if active_model is None:
            return [{"error": "no model trained"}]

        predictions = []
        intercept = active_model.get("intercept")
        coefficients = active_model.get("coefficients")
        features = active_model.get("features", [])

        for row in data:
            try:
                if not isinstance(coefficients, dict) or intercept is None or not features:
                    raise ValueError("trained model has no prediction coefficients")
                pred = float(intercept) + sum(float(coefficients[feature]) * float(row[feature]) for feature in features)
                predictions.append({"prediction": round(pred, 4)})
            except (KeyError, TypeError, ValueError):
                predictions.append({"error": "row is missing a valid model feature"})

        return predictions


def register() -> MLSpecialist:
    return MLSpecialist()
