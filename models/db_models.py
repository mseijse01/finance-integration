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
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    date = Column(Date)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    moving_average_20 = Column(Float)
    volatility = Column(Float)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    headline = Column(String)
    summary = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    source = Column(String, nullable=True)
    datetime = Column(DateTime)
    sentiment = Column(Float)
    category = Column(String, nullable=True)
    related = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())


class FinancialReport(Base):
    __tablename__ = "financial_reports"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    year = Column(Integer)
    quarter = Column(Integer, nullable=True)  # Nullable for annual reports
    report_type = Column(String)  # 'quarterly' or 'annual'
    filing_date = Column(DateTime, nullable=True)
    report_data = Column(JSON)  # Store the full report data as JSON
    revenue = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())


class Earnings(Base):
    __tablename__ = "earnings"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    period = Column(DateTime, index=True)
    quarter = Column(Integer)
    year = Column(Integer)
    eps_actual = Column(Float, nullable=True)
    eps_estimate = Column(Float, nullable=True)
    eps_surprise = Column(Float, nullable=True)
    eps_surprise_percent = Column(Float, nullable=True)
    revenue_actual = Column(Float, nullable=True)
    revenue_estimate = Column(Float, nullable=True)
    revenue_surprise = Column(Float, nullable=True)
    revenue_surprise_percent = Column(Float, nullable=True)
    is_beat = Column(Boolean, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())


def create_tables():
    Base.metadata.create_all(bind=engine)
