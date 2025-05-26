import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
