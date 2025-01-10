import time
import hashlib
import hmac
import requests
import logging
import environ

env = environ.Env()
environ.Env.read_env()  # Ensure the environment variables are loaded

# KuCoin API credentials
KUCOIN_API_KEY = env('KUCOIN_API_KEY')
KUCOIN_API_SECRET = env('KUCOIN_API_SECRET')
KUCOIN_API_PASSPHRASE = env('KUCOIN_API_PASSPHRASE')
KUCOIN_API_URL = env('KUCOIN_API_URL')  # Base URL for KuCoin API

# Set up logging
logging.basicConfig(level=logging.INFO)

def generate_kucoin_signature(api_secret, api_passphrase, method, endpoint, params=None):
    """
    Generate the KuCoin API signature.
    Args:
        api_secret (str): KuCoin API secret.
        api_passphrase (str): KuCoin API passphrase.
        method (str): HTTP method (GET/POST).
        endpoint (str): API endpoint.
        params (dict): Parameters to include in the signature.
    Returns:
        tuple: (signature, passphrase signature, timestamp)
    """
    timestamp = str(int(time.time() * 1000))
    params_str = ''
    if params:
        params_str = '?' + '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    prehash_str = f"{timestamp}{method.upper()}{endpoint}{params_str}"
    signature = hmac.new(api_secret.encode('utf-8'), prehash_str.encode('utf-8'), hashlib.sha256).hexdigest()
    passphrase_signature = hmac.new(api_secret.encode('utf-8'), api_passphrase.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature, passphrase_signature, timestamp

def fetch_network_data(crypto_currency):
    """Fetch supported networks for the selected cryptocurrency using KuCoin API."""
    # Define the KuCoin endpoint for fetching coin info
    endpoint = "/api/v1/currencies"
    url = f"{KUCOIN_API_URL}{endpoint}"
    
    # Generate the API signature
    signature, passphrase_signature, timestamp = generate_kucoin_signature(
        KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE, "GET", endpoint
    )

    # Set the request headers
    headers = {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-PASSPHRASE": passphrase_signature,
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-KEY-VERSION": "2",
    }

    try:
        # Make the API request
        response = requests.get(url, headers=headers)
        data = response.json()

        # Check if the response is successful
        if response.status_code == 200 and data.get("code") == "200000":
            # Extract networks for the selected cryptocurrency
            currencies = data.get("data", {})
            for currency, details in currencies.items():
                if currency.lower() == crypto_currency.lower():
                    # Return supported networks for the selected cryptocurrency
                    networks = details.get("chains", [])
                    return [network['chainName'] for network in networks]
            logging.error(f"No networks found for {crypto_currency}")
            return []
        else:
            # Log the error message if the request failed
            logging.error(f"Failed to fetch coin data: {data.get('msg', 'Unknown error')}")
            return []

    except Exception as e:
        # Log any errors encountered during the API request
        logging.error(f"Error fetching networks for {crypto_currency}: {str(e)}")
        return []

# Test the function by fetching networks for 'bitcoin'
crypto_currency = 'bitcoin'
networks = fetch_network_data(crypto_currency)
if networks:
    print(f"Supported networks for {crypto_currency}: {networks}")
else:
    print(f"No networks found for {crypto_currency}")
