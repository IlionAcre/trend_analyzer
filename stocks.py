import yfinance as yf
import pandas as pd
import json
from curl_cffi import requests
from db_manager import create_engine_and_sessions



def get_symbols(keyword: str) -> list[dict]:
    """
    Fetches a list of stock symbols related to the given keyword from Yahoo Finance.

    Parameters:
    keyword (str): The keyword to search for related stock symbols.

    Returns:
    list[dict]: A list of dictionaries containing stock information.
    """
    try:
        data = requests.get(
            f"https://query1.finance.yahoo.com/v1/finance/search?q={keyword}&lang=en-US&region=US&quotesCount=6&newsCount=3&listsCount=2&enableFuzzyQuery=false&quotesQueryId=tss_match_phrase_query&multiQuoteQueryId=multi_quote_single_token_query&newsQueryId=news_cie_vespa&enableCb=true&enableNavLinks=true&enableEnhancedTrivialQuery=true&enableResearchReports=true&enableCulturalAssets=true&enableLogoUrl=true&recommendCount=5",
            impersonate="chrome"
        )
        stocks = data.json()["quotes"]
        all_stocks = []
        if len(stocks) > 0:
            for stock in stocks:
                if stock["isYahooFinance"]:
                    stock_info = {
                        "exchange": stock["exchange"],
                        "symbol": stock["symbol"]
                    }
                    if "longname" in stock.keys():
                        stock_info["name"] = stock["longname"]
                    else:
                        stock_info["name"] = stock["shortname"]
                    all_stocks.append(stock_info)
        return all_stocks
    except Exception as e:
        print(e)


def get_stock(symbol: str, period: str = "max") -> pd.DataFrame:
    """
    Downloads stock data for the given symbol and period from Yahoo Finance.

    Parameters:
    symbol (str): The stock symbol to download data for.
    period (str): The time period for the data. Default is "max".

    Returns:
    pd.DataFrame: A DataFrame containing the stock data.
    """
    df = yf.download(symbol, group_by="Ticker", period=period, auto_adjust=True)
    df.columns = [col[1] for col in df.columns]
    return df


def get_from_date(query_df: pd.DataFrame, date: str) -> pd.Series:
    """
    Gets the row of data from the DataFrame corresponding to the given date.

    Parameters:
    query_df (pd.DataFrame): The DataFrame to query.
    date (str): The date to look up.

    Returns:
    pd.Series: A Series containing the row of data for the given date.
    """
    query_date = pd.to_datetime(date).tz_localize('UTC')
    return query_df.asof(query_date)


def inject_stock(keyword: str, period: str = "max") -> None:
    """
    Injects stock data into the database for the given keyword.

    Parameters:
    keyword (str): The keyword to search for related stock data.
    period (str): The time period for the data. Default is "max".

    Returns:
    None
    """
    db_info = create_engine_and_sessions(keyword)
    try:
        stock_info = get_symbols(keyword)[0]
        table = get_stock(stock_info["symbol"], period)
        table = table.reset_index()
        table.to_sql("stocks", con=db_info["engine"], if_exists="replace", index=False)
        print("We sent one stocks table to space!")

        # Load existing data from JSON file
        with open("stocks_data.json", "r+") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []

        # Check if the stock_info or nickname is already present
        stock_info["nickname"] = keyword
        if stock_info not in data and not any(item.get("nickname") == keyword for item in data):
            data.append(stock_info)
            with open("stocks_data.json", "w") as file:
                json.dump(data, file, indent=4)
            print("And updated the data file :)")
        else:
            print("Data already present. No update needed.")

    except IndexError:
        print("Not within yahoo finance.")


if __name__ == "__main__":
    stocks_list = ["Ubisoft", "Boeing"]
    for stock in stocks_list:
        inject_stock(stock)
