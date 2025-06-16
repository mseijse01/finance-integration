from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class StockPrice(Base):
    __tablename__ = "stock_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    moving_average_20 = Column(Float)  # 20-day moving average

    # Add performance indexes for common queries
    __table_args__ = (
        Index("idx_stock_symbol_date", "symbol", "date"),  # Most common query pattern
        Index("idx_stock_date", "date"),  # For date-based queries
        Index("idx_stock_symbol", "symbol"),  # For symbol-based queries
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    headline = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text)
    source = Column(String(100))
    datetime = Column(DateTime, nullable=False)
    sentiment = Column(Float)  # VADER sentiment score (-1 to 1)
    category = Column(String(50))
    related = Column(String(200))  # Related symbols
    image_url = Column(Text)

    # Add performance indexes for news queries
    __table_args__ = (
        Index(
            "idx_news_symbol_datetime", "symbol", "datetime"
        ),  # Primary query pattern
        Index("idx_news_datetime", "datetime"),  # For date-based sorting
        Index("idx_news_sentiment", "sentiment"),  # For sentiment analysis queries
    )


class FinancialReport(Base):
    __tablename__ = "financial_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer)  # NULL for annual reports
    report_type = Column(String(20), nullable=False)  # 'quarterly' or 'annual'
    filing_date = Column(Date)
    report_data = Column(JSON)  # Raw JSON data from API

    # Extracted key metrics for easier querying
    revenue = Column(Float)
    net_income = Column(Float)
    eps = Column(Float)
    total_assets = Column(Float)
    total_liabilities = Column(Float)

    # Add performance indexes for financial reports
    __table_args__ = (
        Index(
            "idx_financial_symbol_year_quarter", "symbol", "year", "quarter"
        ),  # Primary query pattern
        Index(
            "idx_financial_symbol_type", "symbol", "report_type"
        ),  # For quarterly vs annual queries
        Index("idx_financial_filing_date", "filing_date"),  # For date-based sorting
    )


class Earnings(Base):
    __tablename__ = "earnings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False)
    period = Column(Date, nullable=False)  # Earnings period date
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    eps_actual = Column(Float)
    eps_estimate = Column(Float)
    eps_surprise = Column(Float)  # actual - estimate
    eps_surprise_percent = Column(Float)  # (surprise / |estimate|) * 100
    revenue_actual = Column(Float)
    revenue_estimate = Column(Float)
    is_beat = Column(Boolean)  # True if actual > estimate

    # Add performance indexes for earnings queries
    __table_args__ = (
        Index(
            "idx_earnings_symbol_year_quarter", "symbol", "year", "quarter"
        ),  # Primary query pattern
        Index("idx_earnings_period", "period"),  # For date-based sorting
        Index(
            "idx_earnings_symbol_period", "symbol", "period"
        ),  # Combined symbol and period
    )


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Get a database session"""
    return SessionLocal()
