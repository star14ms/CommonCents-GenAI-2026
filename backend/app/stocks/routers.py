import pandas as pd
import pandas_ta as ta
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
import pytz
from .model import *

router = APIRouter()

@router.get("/analysis/{symbol}")
def get_stock_analysis(symbol: str, days: int = 30):
    if not symbol or not symbol.isalpha() or len(symbol) > 5:
        raise HTTPException(status_code=400, detail="Invalid stock symbol. Must be 1-5 alphabetic characters.")
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365.")
    
    try:
        df = get_stock_features(symbol, days)
        
        if df.empty:
            return {"error": "No data available for this symbol in the specified period."}
        
        # Drop target column as it's for ML, not display
        df = df.drop(columns=['target'], errors='ignore')
        
        # Use RSI for signal
        latest_rsi = df['RSI'].iloc[-1] if 'RSI' in df.columns else None
        if pd.isna(latest_rsi):
            signal = "Insufficient data for analysis"
        elif latest_rsi > 70:
            signal = "Overbought - Consider selling"
        elif latest_rsi < 30:
            signal = "Oversold - Consider buying"
        else:
            signal = "Neutral"
        
        # Convert DataFrame to dict for JSON response, replacing NaN with None
        import numpy as np
        data = df.tail(5).to_dict(orient='records')
        # Replace NaN with None for JSON compliance
        for record in data:
            for key, value in record.items():
                if isinstance(value, float) and np.isnan(value):
                    record[key] = None
        
        return {
            "data": data,
            "signal": signal,
            "latest_price": df['close'].iloc[-1] if not df.empty else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")