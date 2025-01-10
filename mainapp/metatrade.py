import MetaTrader5 as mt5

def execute_trade(trade):
    if not mt5.initialize():
        print("MetaTrader5 initialization failed!")
        return

    symbol = trade.token + 'USDT'
    amount = trade.amount
    price = get_price_from_exchange(symbol)  # Fetch price from exchange (e.g., Binance or CCXT)

    if trade.order_type == 'BUY':
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": amount,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "deviation": 10,
            "magic": 234000,
            "comment": "Crypto bot trade",
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC
        }
    else:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": amount,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 10,
            "magic": 234000,
            "comment": "Crypto bot trade",
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC
        }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Trade failed with code {result.retcode}")
    else:
        trade.status = 'EXECUTED'
        trade.save()

    mt5.shutdown()
