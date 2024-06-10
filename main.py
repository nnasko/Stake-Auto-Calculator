import pandas as pd
import requests
import pytz
import matplotlib.pyplot as plt
from datetime import datetime

def fetch_ltc_price():
    """Fetches the current Litecoin (LTC) price in GBP from CoinGecko API."""
    api_url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=gbp"
    try:
        response = requests.get(api_url)
        response.raise_for_status()  
        data = response.json()
        return data.get("litecoin", {}).get("gbp")  
    except requests.exceptions.RequestException as e:
        print(f"Error fetching LTC price: {e}")
        return None  

def calculate_total_gbp_value(csv_file, start_date=None):
    """Calculates the total GBP value of the 'amount' column, optionally filtering by start_date."""
    try:
        df = pd.read_csv(csv_file)

        # Remove extra text before converting to datetime
        df["date"] = df["date"].astype(str).str.replace(r" \(Coordinated Universal Time\)", "", regex=True) 
        df["date"] = pd.to_datetime(df["date"], format="%a %b %d %Y %H:%M:%S GMT%z")

        # Filter by start_date if provided
        if start_date:
            df = df[df["date"] >= start_date]

        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        total_ltc = df["amount"].sum()
        ltc_price_gbp = fetch_ltc_price()

        if ltc_price_gbp is None:
            print("Skipping calculation due to missing LTC price.")
            return None
        else:
            total_gbp = total_ltc * ltc_price_gbp
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

    # Get start date from user input
    while True:
        try:
            start_date_str = input("Enter start date (DD/MM/YYYY) or leave blank for all data: ")
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%d/%m/%Y").replace(tzinfo=pytz.UTC)  # Localize to UTC
            else:
                start_date = None # No filtering
            break  # Exit loop if input is valid
        except ValueError:
            print("Invalid date format. Please enter DD/MM/YYYY.")

    for csv_file in csv_files:
        total_gbp = calculate_total_gbp_value(csv_file, start_date)

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
