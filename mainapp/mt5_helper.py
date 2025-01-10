import MetaTrader5 as mt5
import logging
import os
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetaTraderConnector:
    """
    Handles the connection and operations with MetaTrader 5.
    """

    def __init__(self):
        self.server = settings.METATRADER_CONFIG['server']
        self.login = settings.METATRADER_CONFIG['login']
        self.password = settings.METATRADER_CONFIG['password']
        self.path = settings.METATRADER_CONFIG['path']

    def connect(self):
        """
        Connect to MetaTrader 5 terminal.
        """
        if not mt5.initialize(path=self.path, login=self.login, password=self.password, server=self.server):
            logging.error(f"MetaTrader5 initialize() failed, error code = {mt5.last_error()}")
            return False
        logging.info(f"Connected to MetaTrader 5 as account {self.login}")
        return True

    def disconnect(self):
        """
        Shut down the connection.
        """
        mt5.shutdown()
        logging.info("MetaTrader5 connection closed.")

    def get_account_info(self):
        """
        Get account info for the connected user.
        """
        account_info = mt5.account_info()
        if account_info is None:
            logging.error(f"Failed to get account info, error code = {mt5.last_error()}")
            return None
        return account_info._asdict()

    def get_market_data(self, symbol="EURUSD", timeframe=mt5.TIMEFRAME_M1, count=10):
        """
        Get the latest market data (candlesticks) for a specific symbol.
        """
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            logging.error(f"Failed to get market data, error code = {mt5.last_error()}")
            return None
        return rates

    def place_order(self, symbol, lot_size, order_type):
        """
        Place a buy or sell order for a symbol.
        """
        if order_type not in ['BUY', 'SELL']:
            raise ValueError('Invalid order type. Must be "BUY" or "SELL".')

        # Define the action type (0 for BUY, 1 for SELL)
        action_type = 0 if order_type == 'BUY' else 1

        # Get symbol tick data (ask for buy, bid for sell)
        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            logging.error(f"Failed to get symbol info for {symbol}, error code = {mt5.last_error()}")
            return None

        price = symbol_info.ask if order_type == 'BUY' else symbol_info.bid

        # Build the trade request
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": action_type,  # 0 for BUY, 1 for SELL
            "price": price,
            "deviation": 10,
            "magic": 234000,  # Magic number to identify the order
            "comment": "Trade via Django",
            "type_time": mt5.ORDER_TIME_GTC,  # Good till canceled
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send the order
        result = mt5.order_send(trade_request)
        if result is None:
            logging.error(f"Order send failed, error code = {mt5.last_error()}")
            return None

        logging.info(f"Order placed: {result}")
        return result._asdict()
