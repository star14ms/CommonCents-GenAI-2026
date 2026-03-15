import os
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Initialize the client (None if keys not configured - allows app to start without Alpaca)
load_dotenv()

API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

if API_KEY and SECRET_KEY:
    data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
else:
    data_client = None