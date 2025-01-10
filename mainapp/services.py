import requests
from datetime import datetime
from .models import MarketData

def fetch_market_data():
    try:
        response = requests.get("API_URL")  # Replace with the actual API URL
        data = response.json()

        # Check if the expected keys are present in the response
        if 'market_data' in data and 'current_price' in data['market_data'] and 'usd' in data['market_data']['current_price']:
            price = data['market_data']['current_price']['usd']
        else:
            print("Missing expected keys in the data response.")
            price = None  # Handle accordingly
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        price = None  # Handle the request failure
    except ValueError:
        print("Error parsing the JSON response.")
        price = None  # Handle the JSON parsing error

    return price


def fetch_coins_and_chains():
    try:
        # Fetch coins and networks (e.g., from Bybit or a similar service)
        coins_response = requests.get('https://api.example.com/coins')
        print(f"Coins Response: {coins_response.text}")  # Log response for coins
        
        chains_response = requests.get('https://api.example.com/networks')
        print(f"Chains Response: {chains_response.text}")  # Log response for chains
        
        if coins_response.status_code == 200:
            coins_data = coins_response.json()
            print(f"Coins Data: {coins_data}")  # Log parsed coin data
            
        if chains_response.status_code == 200:
            chains_data = chains_response.json()
            print(f"Chains Data: {chains_data}")  # Log parsed chain data

        return coins_data, chains_data

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None