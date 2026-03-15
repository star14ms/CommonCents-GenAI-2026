from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import yfinance as yf

from ..llm import ChatMessage, get_provider

from .model import get_stock_features
from .predict import predict_next_close, train_linear_model


def _clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _fetch_company_profile(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        return {}

    return {
        "symbol": symbol,
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "quote_type": info.get("quoteType"),
        "market_cap": info.get("marketCap"),
        "country": info.get("country"),
        "currency": info.get("currency"),
    }


def _fetch_google_news(query: str, limit: int = 3, topic: str | None = None) -> list[dict]:
    url = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(
            {
                "q": query,
                "hl": "en-US",
                "gl": "US",
                "ceid": "US:en",
            }
        )
    )
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = response.read()
    except Exception:
        return []

    try:
        root = ET.fromstring(payload)
    except Exception:
        return []

    items: list[dict] = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source = ""
        source_node = item.find("source")
        if source_node is not None and source_node.text:
            source = source_node.text.strip()

        if not title:
            continue

        items.append(
            {
                "topic": topic,
                "query": query,
                "title": title,
                "source": source,
                "published_at": pub_date,
                "link": link,
            }
        )
    return items


def _fetch_yfinance_news(symbol: str, limit: int = 3, topic: str | None = None) -> list[dict]:
    try:
        raw_items = yf.Ticker(symbol).news or []
    except Exception:
        return []

    items: list[dict] = []
    for raw in raw_items[:limit]:
        content = raw.get("content", {})
        provider = (content.get("provider") or {}).get("displayName", "")
        canonical = content.get("canonicalUrl") or {}
        clickthrough = content.get("clickThroughUrl") or {}
        link = canonical.get("url") or clickthrough.get("url") or ""

        title = (content.get("title") or "").strip()
        if not title:
            continue

        items.append(
            {
                "topic": topic,
                "query": symbol,
                "title": title,
                "source": provider,
                "published_at": content.get("pubDate") or content.get("displayTime") or "",
                "summary": content.get("summary") or content.get("description") or "",
                "link": link,
            }
        )
    return items


def _collect_market_news(symbol: str, company_name: str, limit: int = 8) -> list[dict]:
    queries = [
        (f'"{symbol}" stock OR "{company_name}" stock', "company"),
        (f'"{company_name}" earnings OR guidance OR outlook', "company"),
        ("geopolitics OR war OR sanctions global markets equities", "geopolitics"),
        ("oil prices OR OPEC OR crude global markets stocks", "energy"),
        ("inflation OR interest rates OR Federal Reserve macroeconomics stocks", "macro"),
    ]

    seen: set[tuple[str, str]] = set()
    headlines: list[dict] = []

    for query, topic in queries:
        for item in _fetch_google_news(query, limit=3, topic=topic):
            key = (item.get("title", ""), item.get("link", ""))
            if key in seen:
                continue
            seen.add(key)
            headlines.append(item)
            if len(headlines) >= limit:
                return headlines

    fallback_symbols = [
        (symbol, "company"),
        ("SPY", "macro"),
        ("USO", "energy"),
        ("^TNX", "rates"),
    ]

    for fallback_symbol, topic in fallback_symbols:
        for item in _fetch_yfinance_news(fallback_symbol, limit=3, topic=topic):
            key = (item.get("title", ""), item.get("link", ""))
            if key in seen:
                continue
            seen.add(key)
            headlines.append(item)
            if len(headlines) >= limit:
                return headlines

    return headlines


def _build_quant_snapshot(df: pd.DataFrame) -> dict:
    latest = df.tail(1)
    if latest.empty:
        return {}

    latest_row = latest.iloc[0]
    close_series = df["close"].dropna() if "close" in df.columns else pd.Series(dtype=float)

    def _return_over(period: int):
        if len(close_series) <= period:
            return None
        current = close_series.iloc[-1]
        base = close_series.iloc[-(period + 1)]
        if base == 0:
            return None
        return ((current / base) - 1) * 100

    model = train_linear_model(df)
    prediction_3m_avg = predict_next_close(df, model)
    latest_close = _clean_value(latest_row.get("close"))
    upside = None
    if prediction_3m_avg is not None and latest_close not in (None, 0):
        upside = ((prediction_3m_avg / latest_close) - 1) * 100

    fields = [
        "close",
        "volume",
        "returns",
        "SMA_10",
        "SMA_20",
        "SMA_50",
        "EMA_12",
        "EMA_26",
        "RSI",
        "MACD",
        "MACD_signal",
        "ATR",
        "volatility",
        "pe_ratio",
        "forward_pe",
        "eps",
        "forward_eps",
        "beta",
        "market_cap",
        "profit_margin",
        "debt_to_equity",
        "current_ratio",
        "dividend_yield",
        "quote_type",
        "is_etf",
        "sector",
        "industry",
    ]

    latest_metrics = {
        field: _clean_value(latest_row.get(field))
        for field in fields
        if field in df.columns
    }

    return {
        "latest_metrics": latest_metrics,
        "return_1m_pct": _return_over(21),
        "return_3m_pct": _return_over(63),
        "prediction_3m_avg": prediction_3m_avg,
        "prediction_vs_latest_pct": upside,
        "model_features_used": model.get("feature_cols", []),
    }


def _normalize_mode(mode: str) -> str:
    return "expert" if str(mode).strip().lower() == "expert" else "beginner"


def _build_qualitative_prompt(payload: dict, mode: str) -> str:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "expert":
        return (
            "You are a stock strategist writing for advanced users. Use only the provided JSON context.\n\n"
            "Create a concise debate between 3 risk personas:\n"
            "- HighRisk (aggressive growth)\n"
            "- MediumRisk (balanced)\n"
            "- LowRisk (capital preservation)\n\n"
            "Each persona gives 2 specific bullets grounded in BOTH news/macro context and quantitative signals.\n"
            "Then provide a FINAL QUALITATIVE SUMMARY with:\n"
            "- News & macro regime\n"
            "- Cross-asset/geopolitics implications\n"
            "- Event risks and catalysts\n"
            "- Near-term watchlist\n\n"
            "Rules: keep it tight (<=260 words), use precise language, do not invent facts, if data missing say 'data unavailable', end with 'Not financial advice.'\n\n"
            f"Context JSON:\n{json.dumps(payload, default=str, indent=2)}"
        )

    return (
        "You are explaining the stock update to someone with zero finance or technical background. Use only the JSON context.\n\n"
        "Write in calm, everyday language for a first-time reader.\n"
        "Create a short debate between 3 voices:\n"
        "- HighRisk (more comfortable with bigger ups and downs)\n"
        "- MediumRisk (balanced)\n"
        "- LowRisk (more focused on stability)\n\n"
        "Each voice gives exactly 2 short bullet points.\n"
        "After the debate, write FINAL QUALITATIVE SUMMARY with exactly 3 bullets:\n"
        "- What is happening now\n"
        "- Why this could be risky\n"
        "- What to watch next\n\n"
        "Hard rules:\n"
        "- Do NOT use technical terms, formulas, theorems, indicator names, or stock metric names.\n"
        "- Do NOT mention terms such as RSI, MACD, beta, PE, ATR, volatility, market cap, earnings per share, moving average, momentum, or valuation.\n"
        "- Keep sentences short and clear.\n"
        "- Keep total length <=190 words.\n"
        "- If data is missing, say 'data unavailable'.\n"
        "- End with 'Not financial advice.'\n"
        "- Keep the output neat with clear section titles and bullet points.\n\n"
        f"Context JSON:\n{json.dumps(payload, default=str, indent=2)}"
    )


def _build_quantitative_prompt(payload: dict, mode: str) -> str:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "expert":
        return (
            "You are a quantitative stock strategist writing for advanced users. Use only the provided JSON context.\n\n"
            "Create a concise debate between 3 risk personas:\n"
            "- HighRisk (aggressive growth)\n"
            "- MediumRisk (balanced)\n"
            "- LowRisk (capital preservation)\n\n"
            "Each persona gives 2 specific bullets grounded in BOTH quant_snapshot and current-event context.\n"
            "Then provide FINAL QUANTITATIVE SUMMARY with:\n"
            "- Return profile (1M/3M)\n"
            "- Signal state (trend/momentum/risk)\n"
            "- 3-month average prediction interpretation\n"
            "- Data-driven risks and assumptions\n\n"
            "Rules: <=260 words, use precise language, do not invent facts, if data missing say 'data unavailable', end with 'Not financial advice.'\n\n"
            f"Context JSON:\n{json.dumps(payload, default=str, indent=2)}"
        )

    return (
        "You are explaining the stock numbers to someone with zero finance or technical background. Use only the JSON context.\n\n"
        "Write in calm, everyday language for a first-time reader.\n"
        "Create a short debate between 3 voices:\n"
        "- HighRisk (more comfortable with bigger ups and downs)\n"
        "- MediumRisk (balanced)\n"
        "- LowRisk (more focused on stability)\n\n"
        "Each voice gives exactly 2 short bullet points.\n"
        "After the debate, write FINAL QUANTITATIVE SUMMARY with exactly 3 bullets:\n"
        "- Is the stock generally rising or falling lately (plain words)\n"
        "- What the 3-month estimate means (plain words)\n"
        "- Main risk to pay attention to\n\n"
        "Hard rules:\n"
        "- Do NOT use technical terms, formulas, theorems, indicator names, or stock metric names.\n"
        "- Do NOT mention terms such as RSI, MACD, beta, PE, ATR, volatility, market cap, earnings per share, moving average, momentum, or valuation.\n"
        "- Keep sentences short and clear.\n"
        "- Keep total length <=190 words.\n"
        "- If data is missing, say 'data unavailable'.\n"
        "- End with 'Not financial advice.'\n"
        "- Keep the output neat with clear section titles and bullet points.\n\n"
        f"Context JSON:\n{json.dumps(payload, default=str, indent=2)}"
    )


def generate_qualitative_summary(
    symbol: str,
    provider_id: str = "chatgpt",
    news_limit: int = 8,
    mode: str = "beginner",
) -> dict:
    clean_symbol = symbol.strip().upper()
    provider = get_provider(provider_id)
    if not provider:
        raise ValueError("Unknown provider. Available: gemini, claude, chatgpt")

    profile = _fetch_company_profile(clean_symbol)
    headlines = _collect_market_news(
        clean_symbol,
        profile.get("company_name") or clean_symbol,
        limit=news_limit,
    )
    df = get_stock_features(clean_symbol, 252)
    quant_snapshot = _build_quant_snapshot(df)

    news_payload = {
        "symbol": clean_symbol,
        "profile": profile,
        "headlines": headlines,
        "quant_snapshot": quant_snapshot,
    }

    news_prompt = _build_qualitative_prompt(news_payload, mode)

    qualitative_summary = provider.chat([ChatMessage(role="user", content=news_prompt)])
    return {
        "symbol": clean_symbol,
        "provider": provider.id,
        "mode": _normalize_mode(mode),
        "qualitative_summary": qualitative_summary,
        "profile": profile,
        "headlines": headlines,
        "quant_snapshot": quant_snapshot,
    }


def generate_qualitative_summary_stream(
    symbol: str,
    provider_id: str = "chatgpt",
    news_limit: int = 8,
    mode: str = "beginner",
):
    """Stream qualitative summary. First yields a metadata dict (for headlines), then text chunks."""
    clean_symbol = symbol.strip().upper()
    provider = get_provider(provider_id)
    if not provider:
        raise ValueError("Unknown provider. Available: gemini, claude, chatgpt")

    profile = _fetch_company_profile(clean_symbol)
    headlines = _collect_market_news(
        clean_symbol,
        profile.get("company_name") or clean_symbol,
        limit=news_limit,
    )
    df = get_stock_features(clean_symbol, 252)
    quant_snapshot = _build_quant_snapshot(df)

    news_payload = {
        "symbol": clean_symbol,
        "profile": profile,
        "headlines": headlines,
        "quant_snapshot": quant_snapshot,
    }

    news_prompt = _build_qualitative_prompt(news_payload, mode)

    # First yield metadata (headlines) for the frontend
    yield {"_meta": {"headlines": headlines}}

    if hasattr(provider, "chat_stream"):
        yield from provider.chat_stream([ChatMessage(role="user", content=news_prompt)])
    else:
        text = provider.chat([ChatMessage(role="user", content=news_prompt)])
        yield text


def generate_quantitative_summary(
    symbol: str,
    provider_id: str = "chatgpt",
    days: int = 252,
    mode: str = "beginner",
) -> dict:
    clean_symbol = symbol.strip().upper()
    provider = get_provider(provider_id)
    if not provider:
        raise ValueError("Unknown provider. Available: gemini, claude, chatgpt")

    df = get_stock_features(clean_symbol, days)
    profile = _fetch_company_profile(clean_symbol)
    quant_snapshot = _build_quant_snapshot(df)
    headlines = _collect_market_news(
        clean_symbol,
        profile.get("company_name") or clean_symbol,
        limit=8,
    )

    quant_payload = {
        "symbol": clean_symbol,
        "profile": profile,
        "quant_snapshot": quant_snapshot,
        "headlines": headlines,
    }

    quant_prompt = _build_quantitative_prompt(quant_payload, mode)

    quantitative_summary = provider.chat([ChatMessage(role="user", content=quant_prompt)])
    return {
        "symbol": clean_symbol,
        "provider": provider.id,
        "mode": _normalize_mode(mode),
        "quantitative_summary": quantitative_summary,
        "profile": profile,
        "quant_snapshot": quant_snapshot,
        "headlines": headlines,
    }


def generate_quantitative_summary_stream(
    symbol: str,
    provider_id: str = "chatgpt",
    days: int = 252,
    mode: str = "beginner",
):
    """Stream quantitative summary token by token. Yields text chunks."""
    clean_symbol = symbol.strip().upper()
    provider = get_provider(provider_id)
    if not provider:
        raise ValueError("Unknown provider. Available: gemini, claude, chatgpt")

    df = get_stock_features(clean_symbol, days)
    profile = _fetch_company_profile(clean_symbol)
    quant_snapshot = _build_quant_snapshot(df)
    headlines = _collect_market_news(
        clean_symbol,
        profile.get("company_name") or clean_symbol,
        limit=8,
    )

    quant_payload = {
        "symbol": clean_symbol,
        "profile": profile,
        "quant_snapshot": quant_snapshot,
        "headlines": headlines,
    }

    quant_prompt = _build_quantitative_prompt(quant_payload, mode)

    if hasattr(provider, "chat_stream"):
        yield from provider.chat_stream([ChatMessage(role="user", content=quant_prompt)])
    else:
        text = provider.chat([ChatMessage(role="user", content=quant_prompt)])
        yield text