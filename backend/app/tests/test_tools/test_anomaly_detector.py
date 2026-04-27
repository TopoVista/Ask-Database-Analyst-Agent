from __future__ import annotations

from app.tools.anomaly_detector import AnomalyDetector


def test_detects_obvious_outlier():
    detector = AnomalyDetector()
    rows = [
        {"revenue": 1000},
        {"revenue": 1050},
        {"revenue": 980},
        {"revenue": 1020},
        {"revenue": 10000},
    ]
    anomalies = detector.detect(rows, ["revenue"])
    assert len(anomalies) > 0
    assert anomalies[0]["column"] == "revenue"
    assert anomalies[0]["value"] == 10000


def test_no_anomaly_in_uniform_data():
    detector = AnomalyDetector()
    rows = [{"revenue": v} for v in range(100, 200, 10)]
    anomalies = detector.detect(rows, ["revenue"])
    assert len(anomalies) == 0


def test_handles_empty_rows():
    detector = AnomalyDetector()
    anomalies = detector.detect([], ["revenue"])
    assert anomalies == []

