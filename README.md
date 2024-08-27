# Python Rithmic API

A robust, async-based Python API designed to interface seamlessly with the Rithmic Protocol Buffer API. This package is built to provide an efficient and reliable connection to Rithmic's trading infrastructure, catering to advanced trading strategies and real-time data handling.

This was originally a fork of [pyrithmic](https://github.com/jacksonwoody/pyrithmic.git), but the code has been completely rewritten.

## Key Enhancements

This repo introduces several key improvements and new features over the original repository, ensuring compatibility with modern Python environments and providing additional functionality:

- **Python 3.11+ Compatibility**: Refactored code to ensure smooth operation with the latest Python versions.
- **System Name Validation**: Implements pre-login validation of system names, as recommended by Rithmic support, with enhanced error handling during the login process.
- **Account Selection**: Allows users to specify which account to use when calling trading functions, rather than being restricted to the primary account.
- **STOP Orders**: Exposing STOP orders to users
- **Best Bid Offer (BBO) Streaming**: Integrates real-time Best Bid Offer tick streaming. 

The most significant upgrade is the transition to an async architecture, providing superior performance and responsiveness when dealing with real-time trading and market data.

## Installation

```
pip install git+https://github.com/rundef/pyrithmic.git#egg=pyrithmic
```

## Ticker Data API

### Streaming Live Tick Data

Here's an example to get the front month contract for ES and stream market data:

```python
import asyncio
from rithmic import RithmicClient, Gateway, DataType, LastTradePresenceBits

async def callback(data: dict):
    if data["presence_bits"] & LastTradePresenceBits.LAST_TRADE:
        print("received", data)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    data_type = DataType.LAST_TRADE
    
    # Stream market data
    print(f"Streaming market data for {security_code}")
    client.on_tick += callback
    await client.subscribe_to_market_data(security_code, exchange, data_type)

    # Wait 10 seconds, unsubscribe and disconnect
    await asyncio.sleep(10)
    await client.unsubscribe_from_market_data(security_code, exchange, data_type)
    await client.disconnect()

asyncio.run(main())
```

## Order API

### Basics

All orders/cancels/modifications are placed asynchronously then their status is updated as updates from the exchange flow into the API. All order_id strings provided need to be unique to a session to track updates back from the exchange, suggest using a database primary key or dateetime based string for example

#### Placing a Market Order:

As a market order will be filled immediately, this script will submit the order and receive a fill straight away:

```python
import asyncio
from datetime import datetime
from rithmic import RithmicClient, Gateway, OrderType, ExchangeOrderNotificationType

async def callback(notification):
  if notification.notify_type == ExchangeOrderNotificationType.FILL:
    print("order filled", notification)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Submit order
    client.on_exchange_order_notification += callback

    order_id = '{0}_order'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.MARKET,
        is_buy=True,
        #account_id="ABCD" # Mandatory if you have multiple accounts
    )
    
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(main())
```

#### Placing a Limit Order and cancelling it

```python
import asyncio
from datetime import datetime
from rithmic import RithmicClient, Gateway, OrderType

async def exchange_order_notification_callback(notification):
  print("exchange order notification", notification)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Submit order
    client.on_exchange_order_notification += exchange_order_notification_callback
    
    order_id = '{0}_order'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.LIMIT,
        is_buy=True,
        price=5300.
    )
    
    await asyncio.sleep(1)
    
    await client.cancel_order(order_id)
    
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(main())
```

## History Data API

### Downloading Historical Tick Data

The following example will fetch historical data, in a streaming fashion:

```python
import asyncio
from datetime import datetime
import pytz
from rithmic import RithmicClient, Gateway

async def callback(data: dict):
    print("received", data)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()
    
    client.on_historical_tick += callback

    # Fetch historical data
    await client.get_historical_tick_data(
        "ESU4",
        "CME",
        datetime(2024, 8, 22, 13, 30, tzinfo=pytz.utc),
        datetime(2024, 8, 22, 13, 31, tzinfo=pytz.utc)
    )

    # Wait 10 seconds and disconnect
    await asyncio.sleep(10)
    await client.disconnect()

asyncio.run(main())
```

## Testing

- `Unit tests`: Run `make unit-tests`
- `Integration tests`: copy `tests/.env.template` to `tests/.env` and fill in your paper trading credentials to test real world functionality. Tests highlight examples of using live tick data, downloading historical tick data and placing/modifying/cancelling orders and processing fills. Run `make integration-tests`
