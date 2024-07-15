import pandas as pd
import pytz
import requests
import matplotlib.pyplot as plt
from datetime import datetime
import json

# --- Caching Configuration ---
CACHE_FILE = "ltc_price_cache.json"

def load_cache():
    """Loads price data from the cache file."""
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cache(cache):
    """Saves price data to the cache file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# --- Tradermade API Configuration ---
API_KEY = "n7-xiD38agsH7GnD3Vkn"
BASE_URL = "https://marketdata.tradermade.com/api/v1/timeseries"

def fetch_ltc_price(date, cache={}):
    """Fetches LTC price from Tradermade API or cache."""
    date_str = date.strftime("%Y-%m-%d")
    if date_str in cache:
        print(f"Using cached price for {date_str}")
        return cache[date_str]
    
    print(f"Fetching price for {date_str} from API")
    params = {
        "api_key": API_KEY,
        "currency": "LTCGBP",
        "start_date": date_str,
        "end_date": date_str,
        "format": "records",
        "interval": "daily"
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  
        data = response.json()
        if data["quotes"]:
            price = data["quotes"][0]["close"]
            cache[date_str] = price
            save_cache(cache)
            return price
        else:
            print(f"No data found in API response for {date_str}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching LTC price for {date_str}: {e}")
        return None

def calculate_total_gbp_value(csv_file, start_date=None, end_date=None):
    """Calculates total GBP value based on LTC price from Tradermade API."""
    cache = load_cache()
    try:
        df = pd.read_csv(csv_file)

        # Remove extra text and convert to datetime
        df["date"] = df["date"].astype(str).str.replace(r" \(Coordinated Universal Time\)", "", regex=True)
        df["date"] = pd.to_datetime(df["date"], format="%a %b %d %Y %H:%M:%S GMT%z")

        # Filter by date range
        mask = pd.Series(True, index=df.index)
        if start_date:
            mask &= (df["date"] >= start_date)
        if end_date:
            mask &= (df["date"] <= end_date)
        df = df[mask]

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        # Get LTC price for each transaction date
        df["ltc_price_gbp"] = df["date"].apply(lambda x: fetch_ltc_price(x, cache))
        df.dropna(subset=["ltc_price_gbp"], inplace=True)  

        # Calculate GBP value for each transaction and sum
        df["gbp_value"] = df["amount"] * df["ltc_price_gbp"]
        total_gbp = df["gbp_value"].sum()
        return total_gbp
    except FileNotFoundError:
        print(f"Error: File not found - {csv_file}")
        return None
    

# --- Main Execution ---
if __name__ == "__main__":
    csv_files = ["Crypto Withdrawals.csv", "Crypto Deposits.csv"] 
    totals = {}
    withdrawals = None
    deposits = None

    # Get start and end dates from user input
    while True:
        try:
            start_date_str = input("Enter start date (DD/MM/YYYY) or leave blank for all data: ")
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%d/%m/%Y").replace(tzinfo=pytz.UTC)
            else:
                start_date = None

            end_date_str = input("Enter end date (DD/MM/YYYY) or leave blank for today: ")
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%d/%m/%Y").replace(tzinfo=pytz.UTC)
            else:
                end_date = datetime.now(pytz.UTC)  # Use today's date in UTC if no end date provided

            break
        except ValueError:
            print("Invalid date format. Please enter DD/MM/YYYY.")

    for csv_file in csv_files:
        total_gbp = calculate_total_gbp_value(csv_file, start_date, end_date)


        if csv_file.split(".")[0] == "Crypto Withdrawals":
            withdrawals = total_gbp
        elif csv_file.split(".")[0] == "Crypto Deposits":
            deposits = total_gbp

        if total_gbp is not None:
            totals[csv_file.split(".")[0]] = total_gbp 

    # Print totals
    if withdrawals is not None:
        print(f"Total Withdrawals (GBP) since {start_date_str or 'the beginning'}: £{withdrawals:.2f}")
    if deposits is not None:
        print(f"Total Deposits (GBP) since {start_date_str or 'the beginning'}: £{deposits:.2f}")

    if withdrawals is not None and deposits is not None:
        profit_loss = withdrawals - deposits
        print(f"Total Profit/Loss (GBP) since {start_date_str or 'the beginning'}: £{profit_loss:.2f}")

    if totals:  # Check if any totals were calculated
        # Create bar chart
        labels = list(totals.keys())
        values = list(totals.values())

        plt.bar(labels, values, color=["green", "red"]) 
        plt.xlabel("Transaction Type")
        plt.ylabel("Total Value (GBP)")
        plt.title("Crypto Withdrawals vs. Deposits (GBP)")
        plt.show()
    else:
        print("No data available for charting.")
