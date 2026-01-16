import os
import requests
from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
ALPHA_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --------------------------------------------------
# 🌦️ WEATHER TOOL (UNCHANGED LOGIC)
# --------------------------------------------------
@tool
def tool1_weather(query: str) -> str:
    """Weather tool: current, forecast, yesterday, or city comparison."""
    try:
        import re
        from datetime import datetime, timedelta

        q = query.lower()
        is_forecast = "forecast" in q or "7" in q
        is_yesterday = "yesterday" in q
        is_compare = "compare" in q or " and " in q

        cities = re.findall(r"(?:in|at|of)?\s*([A-Z][a-z]+(?: [A-Z][a-z]+)?)", query)
        city_names = list(dict.fromkeys(cities)) or [query]

        if is_compare and len(city_names) >= 2:
            result = []
            for city in city_names[:2]:
                url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}"
                data = requests.get(url).json()
                result.append(
                    f"{city}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}"
                )
            return "🌤️ Weather Comparison:\n" + "\n".join(result)

        city = city_names[0]

        if is_yesterday:
            yday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"http://api.weatherapi.com/v1/history.json?key={WEATHER_API_KEY}&q={city}&dt={yday}"
            data = requests.get(url).json()
            day = data["forecast"]["forecastday"][0]["day"]
            return f"📆 Yesterday in {city}: {day['avgtemp_c']}°C, {day['condition']['text']}"

        if is_forecast:
            url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days=7"
            data = requests.get(url).json()
            out = f"📅 7-Day Forecast for {city}:\n"
            for d in data["forecast"]["forecastday"]:
                out += f"{d['date']}: {d['day']['condition']['text']} ({d['day']['avgtemp_c']}°C)\n"
            return out.strip()

        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}"
        data = requests.get(url).json()
        return f"🌤️ Current Weather in {city}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}"

    except Exception as e:
        return f"❌ Weather error: {str(e)}"

# --------------------------------------------------
# 📈 STOCK TOOL — ALPHA VANTAGE
# --------------------------------------------------
@tool
def tool2_stock_alpha(company: str) -> str:
    """Fetch real-time stock price using Alpha Vantage."""
    try:
        symbol_url = (
            "https://www.alphavantage.co/query"
            f"?function=SYMBOL_SEARCH&keywords={company}&apikey={ALPHA_API_KEY}"
        )
        symbol_data = requests.get(symbol_url).json()
        matches = symbol_data.get("bestMatches")

        if not matches:
            return f"❌ No stock symbol found for {company}"

        symbol = matches[0]["1. symbol"]

        price_url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_API_KEY}"
        )
        price_data = requests.get(price_url).json()
        quote = price_data.get("Global Quote", {})

        price = quote.get("05. price")
        if not price:
            return "⚠️ Price not available."

        return f"📈 Stock: {symbol}\n💰 Price: ${price}"

    except Exception as e:
        return f"❌ Stock error: {str(e)}"

# --------------------------------------------------
# 🔍 WEB SEARCH — TAVILY
# --------------------------------------------------
@tool
def tool3_tavily_search(query: str) -> str:
    """Search the web using Tavily."""
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 5,
            "search_depth": "basic"
        }

        res = requests.post(url, json=payload, timeout=10)
        data = res.json()

        results = data.get("results", [])
        if not results:
            return "❌ No search results found."

        answer = "🔎 Tavily Search Results:\n"
        for r in results:
            answer += f"- {r['title']}: {r['content']}\n"

        return answer.strip()

    except Exception as e:
        return f"❌ Tavily error: {str(e)}"
