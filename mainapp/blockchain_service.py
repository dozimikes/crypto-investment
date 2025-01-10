import os
import requests
from web3 import Web3
import environ
import time

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()  # Ensure the environment variables are loaded

# Load environment variables
KUCOIN_API_KEY = env('KUCOIN_API_KEY')
KUCOIN_API_SECRET = env('KUCOIN_API_SECRET')
KUCOIN_API_PASSPHRASE = env('KUCOIN_API_PASSPHRASE')
KUCOIN_API_URL = env('KUCOIN_API_URL', default='https://api.kucoin.com')

WEB3_PROVIDER_URL = env('WEB3_PROVIDER_URL')  # Ensure it's set in .env

WALLET_ADDRESSES = env('OWNER_WALLET_ADDRESSES')  # Make sure WALLET_ADDRESSES is set in .env
PRIVATE_KEY = env('PRIVATE_KEY')  # Make sure PRIVATE_KEY is set in .env

if not WEB3_PROVIDER_URL:
    raise Exception("WEB3_PROVIDER_URL is not set in environment variables")

# Initialize web3 connection
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))

if not web3.is_connected():
    raise Exception("Failed to connect to blockchain")

print("Successfully connected to the blockchain")

# Example of creating a new account or connecting to an existing one
def create_new_account():
    account = web3.eth.account.create()
    print("New Wallet Address:", account.address)
    print("New Private Key:", account.privateKey.hex())
    return account.address, account.privateKey.hex()

def get_bitcoin_balance(wallet_address):
    """Get balance of a Bitcoin wallet using KuCoin API."""
    try:
        headers = {
            "KC-API-KEY": KUCOIN_API_KEY,
            "KC-API-SIGN": "",
            "KC-API-TIMESTAMP": str(int(time.time() * 1000)),
            "KC-API-PASSPHRASE": KUCOIN_API_PASSPHRASE,
        }
        response = requests.get(f'{KUCOIN_API_URL}/api/v1/accounts', headers=headers)
        data = response.json()
        if response.status_code == 200:
            for account in data['data']:
                if account['currency'] == 'BTC' and account['type'] == 'main':
                    return float(account['balance'])
        return 0.0
    except Exception as e:
        print(f"Failed to fetch balance for Bitcoin wallet {wallet_address}: {str(e)}")
        return None

def get_ethereum_balance(wallet_address):
    """Get balance of an Ethereum wallet using Web3."""
    try:
        balance_wei = web3.eth.get_balance(wallet_address)
        balance_eth = web3.fromWei(balance_wei, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Failed to fetch balance for Ethereum wallet {wallet_address}: {str(e)}")
        return None

def get_wallet_balance(wallet_address=WALLET_ADDRESSES):
    """Get the balance of the wallet in ETH"""
    balance_wei = web3.eth.get_balance(wallet_address)
    balance_eth = web3.fromWei(balance_wei, 'ether')
    return balance_eth

def send_crypto(to_address, amount_eth):
    """Send crypto from the connected wallet to another wallet address"""
    nonce = web3.eth.get_transaction_count(WALLET_ADDRESSES)
    tx = {
        'nonce': nonce,
        'to': to_address,
        'value': web3.toWei(amount_eth, 'ether'),
        'gas': 21000,  # Typical gas limit for sending ETH
        'gasPrice': web3.eth.gas_price,
    }

    # Sign the transaction with the private key
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    
    # Send the transaction to the blockchain
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    return web3.toHex(tx_hash)

def send_transaction(from_address, to_address, amount):
    try:
        nonce = web3.eth.get_transaction_count(from_address)
        transaction = {
            'to': to_address,
            'value': web3.toWei(amount, 'ether'),
            'gas': 21000,
            'gasPrice': web3.toWei('20', 'gwei'),
            'nonce': nonce,
            'chainId': 1  # Ethereum Mainnet
        }

        signed_txn = web3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print("Transaction successful, Hash:", web3.toHex(txn_hash))
    except Exception as e:
        print("Error sending transaction:", e)

# Call the function to test
if __name__ == "__main__":
    send_transaction(
        from_address=WALLET_ADDRESSES,  # Use the environment variable
        to_address="0xRecipientWalletAddress",
        amount=0.001
    )

def get_transaction_status(tx_hash):
    """Get the status of a transaction using its hash"""
    receipt = web3.eth.get_transaction_receipt(tx_hash)
    if receipt:
        status = 'Confirmed' if receipt.status == 1 else 'Failed'
    else:
        status = 'Pending'
    return status
