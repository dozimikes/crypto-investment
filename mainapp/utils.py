import shortuuid
import time
import hashlib
import hmac
import logging
from django.conf import settings
import requests
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from .models import Deposit, Withdraw, Transaction, FiatDeposit
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import RequestException
from time import sleep
import ccxt
import base64


# Load environment variables
load_dotenv()

# KuCoin API credentials from environment variables
KUCOIN_API_KEY = settings.KUCOIN_API_KEY
KUCOIN_API_SECRET = settings.KUCOIN_API_SECRET
KUCOIN_API_PASSPHRASE = settings.KUCOIN_API_PASSPHRASE
KUCOIN_API_URL = settings.KUCOIN_API_URL  # Base URL for KuCoin API

# Ensure that API keys are set
if not KUCOIN_API_KEY or not KUCOIN_API_SECRET or not KUCOIN_API_PASSPHRASE:
    raise ValueError("API Key, Secret, and Passphrase must be set in environment variables.")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Utility Functions

def generate_kucoin_signature(secret_key, passphrase, method, endpoint, params=None):
    """Generate the KuCoin API signature."""
    try:
        timestamp = str(int(time.time() * 1000))  # Get current timestamp in milliseconds
        params_str = ""

        # If there are query parameters, format them correctly
        if params:
            params_str = "?" + "&".join([f"{key}={value}" for key, value in sorted(params.items())])

        # Construct the pre-signature string (method should be uppercase, endpoint must be exact)
        prehash_str = f"{timestamp}{method.upper()}{endpoint}{params_str}"

        # Generate the signature using HMAC-SHA256
        signature = hmac.new(secret_key.encode('utf-8'), prehash_str.encode('utf-8'), hashlib.sha256).hexdigest()

        # The passphrase is usually used for headers, so it's not part of the HMAC signature
        # You don't need to create a separate passphrase signature here for KuCoin's API
        return signature, timestamp

    except Exception as e:
        print(f"Error generating signature: {str(e)}")
        return None, None


def fetch_crypto_price(crypto_currency):
    """Fetch real-time price of a cryptocurrency in USD."""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_currency.lower()}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[crypto_currency.lower()]['usd']
    except Exception as e:
        logging.error(f"Error fetching price for {crypto_currency}: {str(e)}")
        return None

def fetch_deposit_address(crypto_currency, network):
    """Fetch deposit address dynamically based on cryptocurrency and network using KuCoin API."""
    endpoint = "/api/v1/deposit-addresses"
    url = f"{KUCOIN_API_URL}{endpoint}"
    params = {"currency": crypto_currency, "chain": network}
    
    signature, passphrase_signature, timestamp = generate_kucoin_signature(
        KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE, "GET", endpoint, params
    )

    headers = {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-PASSPHRASE": passphrase_signature,
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-KEY-VERSION": "2",
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "200000":
            return data["data"].get("address"), data["data"].get("memo")
        else:
            logging.error(f"Failed to fetch deposit address: {data.get('msg', 'Unknown error')}")
            return None, None
    except Exception as e:
        logging.error(f"Error fetching deposit address for {crypto_currency} on {network}: {str(e)}")
        return None, None

def fetch_networks(crypto_currency):
    """Fetch supported networks for a cryptocurrency using KuCoin API."""
    endpoint = "/api/v1/currencies"
    url = f"{KUCOIN_API_URL}{endpoint}"
    
    signature, passphrase_signature, timestamp = generate_kucoin_signature(
        KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE, "GET", endpoint
    )

    headers = {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-PASSPHRASE": passphrase_signature,
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-KEY-VERSION": "2",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "200000":
            currencies = data.get("data", {})
            currency_info = currencies.get(crypto_currency.upper(), {})
            return currency_info.get("chains", [])
        else:
            logging.error(f"Failed to fetch networks for {crypto_currency}: {data.get('msg', 'Unknown error')}")
            return []
    except Exception as e:
        logging.error(f"Error fetching networks for {crypto_currency}: {str(e)}")
        return []



def process_crypto_payment(crypto_currency, amount, deposit_address, network):
    """
    Process cryptocurrency payment using KuCoin API.
    
    Args:
        crypto_currency (str): The cryptocurrency symbol (e.g., BTC, ETH).
        amount (float): The amount to process.
        deposit_address (str): The recipient's deposit address.
        network (str): The blockchain network to use.

    Returns:
        dict: A dictionary with the status of the payment and any relevant message or transaction details.
    """
    endpoint = "/api/v1/withdrawals"
    url = f"{KUCOIN_API_URL}{endpoint}"
    
    params = {
        "currency": crypto_currency.upper(),
        "address": deposit_address,
        "amount": amount,
        "chain": network.upper(),  # Specify the blockchain network
    }

    signature, passphrase_signature, timestamp = generate_kucoin_signature(
        KUCOIN_API_SECRET, KUCOIN_API_PASSPHRASE, "POST", endpoint, params
    )

    headers = {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-PASSPHRASE": passphrase_signature,
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=params)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == "200000":
            return {
                "status": "success",
                "message": "Payment processed successfully",
                "transaction_id": data["data"]["withdrawalId"],
            }
        else:
            logging.error(f"Failed to process payment: {data.get('msg', 'Unknown error')}")
            return {"status": "error", "message": data.get("msg", "Unknown error")}
    except Exception as e:
        logging.error(f"Error processing payment for {crypto_currency}: {str(e)}")
        return {"status": "error", "message": str(e)}



def create_payment(coin, amount):
    """Create a deposit address for payment using KuCoin API."""
    endpoint = "/api/v1/deposit-addresses"
    url = f"{KUCOIN_API_URL}{endpoint}"
    params = {"currency": coin.upper()}

    try:
        headers = generate_kucoin_headers("GET", endpoint, params)
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if response.status_code == 200 and data.get("code") == "200000":
            return {
                "status": "success",
                "address": data["data"]["address"],
                "coin": coin,
                "amount": amount,
            }
        else:
            logging.error(f"Error creating payment address for {coin}: {data.get('msg', 'Unknown error')}")
            return {"status": "error", "message": data.get("msg", "Unknown error")}
    except Exception as e:
        logging.error(f"Error creating payment address for {coin}: {str(e)}")
        return {"status": "error", "message": str(e)}


def generate_kucoin_headers(method, endpoint, params):
    """Generate headers required for KuCoin API requests."""
    timestamp = str(int(time.time() * 1000))
    str_to_sign = f"{timestamp}{method}{endpoint}{'' if method == 'GET' else str(params)}"
    signature = base64.b64encode(
        hmac.new(KUCOIN_API_SECRET.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode()
    passphrase = base64.b64encode(
        hmac.new(KUCOIN_API_SECRET.encode("utf-8"), KUCOIN_API_PASSPHRASE.encode("utf-8"), hashlib.sha256).digest()
    ).decode()

    return {
        "KC-API-KEY": KUCOIN_API_KEY,
        "KC-API-SIGN": signature,
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


def generate_referral_code(user):
    """Generate a unique referral code based on the user's username."""
    return "0x" + shortuuid.uuid(name=user.username)


def get_realtime_btc_to_usd_rate():
    """Fetch the real-time Bitcoin (BTC) to USD exchange rate."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return data['bitcoin']['usd']
        else:
            logging.error(f"Error fetching BTC to USD rate: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching BTC to USD rate: {e}")
        return None


def process_deposit(api_key, api_secret, symbol, deposit_amount):
    """Processes a deposit by fetching deposit history and checking for the expected amount."""
    try:
        exchange = ccxt.kucoin({
            "apiKey": api_key,
            "secret": api_secret,
            "password": KUCOIN_API_PASSPHRASE,
            "enableRateLimit": True,
        })

        deposits = exchange.fetch_deposits(symbol)
        for deposit in deposits:
            if deposit["currency"] == symbol and deposit["amount"] >= deposit_amount and deposit["status"] == "ok":
                return f"Deposit of {deposit_amount} {symbol} successfully received."
        
        return f"Deposit of {deposit_amount} {symbol} not found."
    except Exception as e:
        logging.error(f"Error processing deposit: {e}")
        return f"Error processing deposit: {str(e)}"


def process_withdrawal(api_key, api_secret, symbol, amount, to_address, tag=None):
    """Processes a withdrawal using KuCoin API."""
    try:
        exchange = ccxt.kucoin({
            "apiKey": api_key,
            "secret": api_secret,
            "password": KUCOIN_API_PASSPHRASE,
            "enableRateLimit": True,
        })

        params = {"address": to_address, "amount": amount, "currency": symbol}
        if tag:
            params["memo"] = tag

        withdrawal = exchange.withdraw(symbol, amount, to_address, params)
        return f"Withdrawal of {amount} {symbol} to {to_address} has been initiated. ID: {withdrawal['id']}"
    except Exception as e:
        logging.error(f"Error processing withdrawal: {e}")
        return f"Error processing withdrawal: {str(e)}"


def fetch_kucoin_currencies():
    """
    Fetches currency data from KuCoin API with retry logic.
    """
    # Configure retry logic
    session = requests.Session()
    retries = Retry(
        total=5,  # Number of retries
        backoff_factor=1,  # Wait time multiplier (e.g., 1s, 2s, 4s)
        status_forcelist=[500, 502, 503, 504]  # HTTP statuses to retry on
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    # Perform the request
    try:
        response = session.get("https://api.kucoin.com/api/v1/currencies")
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()  # Return JSON data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from KuCoin: {e}")
        return None


def fetch_kucoin_data():
    session = requests.Session()

    # Retry logic for transient errors
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    url = "https://api.kucoin.com/api/v1/currencies"

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    data = fetch_kucoin_data()
    if data:
        print("Successfully fetched data:", data)
    else:
        print("Failed to fetch data.")

