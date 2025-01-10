import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BYBIT_API_URL = os.getenv("BYBIT_API_URL", "https://api.bybit.com")  # Default to mainnet

def generate_signature(params):
    """
    Generate a signature for Bybit API requests.
    """
    param_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    return hmac.new(BYBIT_API_SECRET.encode('utf-8'), param_string.encode('utf-8'), hashlib.sha256).hexdigest()

def process_crypto_payment(coin, amount, wallet_address):
    """
    Process a cryptocurrency payment by verifying and recording it.
    
    Args:
        coin (str): Cryptocurrency type (e.g., 'BTC', 'ETH').
        amount (float): Amount to be paid.
        wallet_address (str): Wallet address for payment.

    Returns:
        dict: Status and message about the payment process.
    """
    try:
        # Step 1: Validate wallet address (Optional, depending on Bybit or external service)
        if not wallet_address or len(wallet_address) < 26:
            return {"status": "error", "message": "Invalid wallet address"}

        # Step 2: Generate a deposit address on Bybit (if applicable)
        endpoint = "/v2/private/wallet/address"  # Update based on Bybit's docs
        params = {
            "api_key": BYBIT_API_KEY,
            "coin": coin,
            "timestamp": int(time.time() * 1000),
        }
        params["sign"] = generate_signature(params)

        response = requests.get(BYBIT_API_URL + endpoint, params=params)
        if response.status_code != 200:
            return {"status": "error", "message": "Failed to contact Bybit API"}
        
        data = response.json()
        if data.get("ret_code") != 0:
            return {"status": "error", "message": data.get("ret_msg", "Unknown API error")}

        deposit_address = data["result"]["address"]

        # Step 3: Verify payment status (poll deposit history or use webhook)
        # Mocked response here for demonstration
        payment_status = verify_payment(coin, amount, deposit_address)
        if payment_status.get("status") == "success":
            # Step 4: Record successful payment
            return {"status": "success", "message": "Payment processed successfully", "data": payment_status}
        else:
            return {"status": "pending", "message": "Payment is pending confirmation"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def verify_payment(coin, amount, deposit_address):
    """
    Mock function to simulate payment verification.

    Args:
        coin (str): Cryptocurrency type (e.g., 'BTC', 'ETH').
        amount (float): Amount to verify.
        deposit_address (str): Deposit address to verify against.

    Returns:
        dict: Mocked status and details of the payment.
    """
    # Simulate checking deposit history
    # In a real application, call the Bybit API to get deposit history and match address/amount
    return {"status": "success", "address": deposit_address, "coin": coin, "amount": amount}

