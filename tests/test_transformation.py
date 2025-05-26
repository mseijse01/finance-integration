import polars as pl
import pytest

from etl.transformation import transform_stock_data

sample_raw_data = {
    "Time Series (Daily)": {
        "2024-05-01": {
            "1. open": "10.0",
            "2. high": "10.5",
            "3. low": "9.8",
            "4. close": "10.2",
            "5. volume": "1000000",
        },
        "2024-04-30": {
            "1. open": "9.5",
            "2. high": "10.0",
            "3. low": "9.4",
            "4. close": "9.8",
            "5. volume": "900000",
        },
    }
}


def test_transform_stock_data():
    df = transform_stock_data(sample_raw_data, symbol="TEST")

    # Check shape and column presence
    assert isinstance(df, pl.DataFrame)
    assert df.shape[0] == 2
    assert set(
        [
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "moving_average_20",
            "volatility",
        ]
    ).issubset(df.columns)

    # Check values
    assert df[0, "symbol"] == "TEST"
    assert df[0, "close"] == 9.8  # Sorted ascending
