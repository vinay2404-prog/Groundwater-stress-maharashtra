from __future__ import annotations

import math

from data_loader import load_master_dataframe
from forecasting import evaluate_forecasting
from nlp_engine import extract_district, extract_taluka


def test_short_district_query_returns_none():
    df = load_master_dataframe()
    assert extract_district("hi", df) is None


def test_unknown_taluka_returns_none():
    df = load_master_dataframe()
    assert extract_taluka("NonExistentTalukaXYZ", df) is None


def test_chronological_evaluation_has_metrics():
    df = load_master_dataframe()
    result = evaluate_forecasting(df)
    assert result["n_observations"] > 0
    assert "xgboost" in result["metrics"]
    assert "persistence" in result["metrics"]
    for name in ("xgboost", "persistence"):
        assert result["metrics"][name]["mae"] is not None
        assert result["metrics"][name]["n"] == result["n_observations"]


def test_chatbot_numerical_response_accuracy():
    from chatbot import process_query

    df = load_master_dataframe()
    response = process_query("Show Pune recharge in 2024", df)
    assert "Pune" in response
    assert "Annual Recharge" in response