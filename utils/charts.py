"""
Chart creation utilities for the finance dashboard.
Extracted from dashboard.py to improve code organization and maintainability.
"""

import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime


def create_stock_comparison_chart(timeframe="6m"):
    """
    Create the main stock comparison chart with price and volume subplots.

    Args:
        timeframe: Time period for chart ('1m', '3m', '6m', '1y', 'all')

    Returns:
        plotly.graph_objs.Figure: Configured chart figure
    """
    # Create figure with subplots for price and volume
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=("Price History", "Trading Volume"),
    )

    # Configure layout
    fig.update_layout(
        title=None,
        height=600,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=False), type="date"),
        xaxis2=dict(type="date", rangeslider=dict(visible=True)),
        yaxis=dict(title="Price ($)", tickprefix="$", gridcolor="rgba(0,0,0,0.05)"),
        yaxis2=dict(title="Volume", gridcolor="rgba(0,0,0,0.05)"),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    # Add range selector buttons
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            ),
            bgcolor="white",
            activecolor="#000000",
        ),
        row=1,
        col=1,
    )

    return fig


def add_stock_price_trace(fig, df, symbol, colors, default_visibility):
    """
    Add price and moving average traces for a stock to the chart.

    Args:
        fig: Plotly figure object
        df: DataFrame with stock data
        symbol: Stock symbol
        colors: Dictionary of colors for each symbol
        default_visibility: Dictionary of visibility settings for each symbol
    """
    # Price chart
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            name=f"{symbol} Price",
            line=dict(color=colors.get(symbol, "#000000"), width=2),
            hovertemplate="<b>%{x}</b><br>Price: $%{y:.2f}<extra></extra>",
            visible=default_visibility.get(symbol, True),
        ),
        row=1,
        col=1,
    )

    # Add moving average - always as legendonly to reduce initial load
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["moving_average_20"],
            mode="lines",
            name=f"{symbol} 20-Day MA",
            line=dict(color=colors.get(symbol, "#000000"), width=1, dash="dash"),
            opacity=0.7,
            visible="legendonly",  # Always hidden by default
            hovertemplate="<b>%{x}</b><br>MA-20: $%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )


def add_stock_volume_trace(fig, df, symbol, colors, default_visibility):
    """
    Add volume trace for a stock to the chart.

    Args:
        fig: Plotly figure object
        df: DataFrame with stock data
        symbol: Stock symbol
        colors: Dictionary of colors for each symbol
        default_visibility: Dictionary of visibility settings for each symbol
    """
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name=f"{symbol} Volume",
            marker=dict(color=colors.get(symbol, "#000000"), opacity=0.7),
            hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<extra></extra>",
            visible=default_visibility.get(symbol, True),
        ),
        row=2,
        col=1,
    )


def get_stock_colors():
    """
    Get the color scheme for different stocks.

    Returns:
        dict: Color mapping for stock symbols
    """
    return {
        "SBUX": "#00704A",  # Starbucks Green
        "KDP": "#1f4e79",  # Professional Blue
        "BROS": "#7D5A50",  # Sophisticated minimalist brown
        "FARM": "#B8860B",  # Dark goldenrod
    }


def get_default_visibility():
    """
    Get default visibility settings for stock traces.

    Returns:
        dict: Visibility settings for each stock
    """
    return {
        "SBUX": True,  # Only show the first stock's price trace by default
        "KDP": "legendonly",
        "BROS": "legendonly",
        "FARM": "legendonly",
    }


def get_timeframe_days(timeframe):
    """
    Convert timeframe string to number of days.

    Args:
        timeframe: String timeframe ('1m', '3m', '6m', '1y', 'all')

    Returns:
        int: Number of days to show
    """
    return {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "all": 3650,  # ~10 years max
    }.get(timeframe, 180)


def create_timeframe_tabs_html(current_timeframe):
    """
    Create HTML for timeframe selection tabs.

    Args:
        current_timeframe: Currently selected timeframe

    Returns:
        str: HTML string for timeframe tabs
    """
    timeframes = [
        ("1m", "1 Month"),
        ("3m", "3 Months"),
        ("6m", "6 Months"),
        ("1y", "1 Year"),
        ("all", "All Data"),
    ]

    buttons = []
    for tf_key, tf_label in timeframes:
        active_class = (
            " active"
            if current_timeframe == tf_key or (not current_timeframe and tf_key == "6m")
            else ""
        )
        buttons.append(
            f'<a href="?timeframe={tf_key}" class="btn btn-outline-primary{active_class}">{tf_label}</a>'
        )

    return f"""
    <div class="card mb-4">
        <div class="card-body p-2">
            <div class="btn-group w-100" role="group">
                {"".join(buttons)}
            </div>
        </div>
    </div>
    """


def downsample_chart_data(records, target_points=100):
    """
    Downsample data to approximately target_points to improve chart rendering performance.
    Uses a simple method that preserves important points like min/max values.

    Args:
        records: List of stock price records
        target_points: Target number of data points

    Returns:
        list: Downsampled records
    """
    if len(records) <= target_points:
        return records

    # Calculate sampling factor
    sample_factor = max(1, len(records) // target_points)

    # Create sampled data with regular intervals
    sampled = records[::sample_factor]

    # Always include the first and last points
    if records[0] not in sampled:
        sampled.insert(0, records[0])
    if records[-1] not in sampled:
        sampled.append(records[-1])

    # Find extreme values that might be missed in the sampling
    all_values = np.array([r["close"] for r in records])
    min_idx = np.argmin(all_values)
    max_idx = np.argmax(all_values)

    # Add extremes if they're not in the sample
    for idx in [min_idx, max_idx]:
        if idx % sample_factor != 0:  # Not already in our sample
            # Insert at the right position to maintain date order
            insert_pos = 0
            for i, r in enumerate(sampled):
                if r["date"] > records[idx]["date"]:
                    insert_pos = i
                    break
            sampled.insert(insert_pos, records[idx])

    return sampled
