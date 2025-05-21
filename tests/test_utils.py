from views.dashboard import extract_financial_metric


def test_extract_financial_metric_found():
    sample_report = {
        "ic": [
            {"concept": "TotalRevenue", "value": 123456},
            {"concept": "NetIncome", "value": 7890},
        ]
    }
    result = extract_financial_metric(sample_report, ["totalrevenue"])
    assert result == 123456


def test_extract_financial_metric_case_insensitive():
    sample_report = {
        "ic": [
            {"concept": "netINCOME", "value": -5000},
        ]
    }
    result = extract_financial_metric(sample_report, ["NetIncome"])
    assert result == -5000


def test_extract_financial_metric_not_found():
    sample_report = {
        "ic": [
            {"concept": "OperatingCost", "value": 1000},
        ]
    }
    result = extract_financial_metric(sample_report, ["NetIncome"])
    assert result == "N/A"


def test_extract_financial_metric_empty_input():
    result = extract_financial_metric({}, ["Revenue"])
    assert result == "N/A"
