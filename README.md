# Python Rithmic API

[![PyPI - Version](https://img.shields.io/pypi/v/async_rithmic)](https://pypi.org/project/async-rithmic/)
[![CI](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml/badge.svg)](https://github.com/rundef/async_rithmic/actions/workflows/ci.yml)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/async_rithmic)](https://pypistats.org/packages/async-rithmic)

A robust, async-based Python API designed to interface seamlessly with the Rithmic Protocol Buffer API. This package is built to provide an efficient and reliable connection to Rithmic's trading infrastructure, catering to advanced trading strategies and real-time data handling.

This was originally a fork of [pyrithmic](https://github.com/jacksonwoody/pyrithmic), but the code has been completely rewritten.

## Key Enhancements

This repo introduces several key improvements and new features over the original repository, ensuring compatibility with modern Python environments and providing additional functionality:

- **Python 3.11+ Compatibility**: Refactored code to ensure smooth operation with the latest Python versions.
- **System Name Validation**: Implements pre-login validation of system names, as recommended by Rithmic support, with enhanced error handling during the login process.
- **Account Selection**: Allows users to specify which account to use when calling trading functions, rather than being restricted to the primary account.
- **STOP Orders**: Exposing STOP orders to users
- **Best Bid Offer (BBO) Streaming**: Integrates real-time Best Bid Offer tick streaming. 
- **Historical Time Bars + Time Bars Streaming**

The most significant upgrade is the transition to an async architecture, providing superior performance and responsiveness when dealing with real-time trading and market data.

## Installation

```
pip install async_rithmic
```

> ⚠ **Test Environment Limitation**:
The test environment does not include historical market data.

## Market data

### Streaming Live Tick Data

Here's an example to get the front month contract for ES and stream market data:

```python
import asyncio
from async_rithmic import RithmicClient, Gateway, DataType, LastTradePresenceBits

async def callback(data: dict):
    if data["presence_bits"] & LastTradePresenceBits.LAST_TRADE:
        print("received", data)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Stream market data
    print(f"Streaming market data for {security_code}")
    data_type = DataType.LAST_TRADE
    client.on_tick += callback
    await client.subscribe_to_market_data(security_code, exchange, data_type)

    # Wait 10 seconds, unsubscribe and disconnect
    await asyncio.sleep(10)
    await client.unsubscribe_from_market_data(security_code, exchange, data_type)
    await client.disconnect()

asyncio.run(main())
```

### Streaming Live Time Bars

```python
import asyncio
from async_rithmic import RithmicClient, Gateway, TimeBarType

async def callback(data: dict):
    print("received", data)

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Stream market data
    print(f"Streaming market data for {security_code}")

    client.on_time_bar += callback
    await client.subscribe_to_time_bar_data(security_code, exchange, TimeBarType.SECOND_BAR, 6)

    # Wait 20 seconds, unsubscribe and disconnect
    await asyncio.sleep(20)
    await client.unsubscribe_from_time_bar_data(security_code, exchange, TimeBarType.SECOND_BAR, 6)
    await client.disconnect()

asyncio.run(main())
```

## Order API

#### Placing a Market Order:

As a market order will be filled immediately, this script will submit the order and receive a fill straight away:

```python
import asyncio
from datetime import datetime
from async_rithmic import RithmicClient, Gateway, OrderType, ExchangeOrderNotificationType, TransactionType

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
        transaction_type=TransactionType.SELL,
        #account_id="ABCD" # Mandatory if you have multiple accounts
        #stop_ticks=20, # Optional: you can specify a stop loss and profit target in ticks
        #target_ticks=40,
        #cancel_at=datetime.now() + timedelta(minutes=2), # Optional: cancellation datetime
    )
    
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(main())
```

#### Placing a Limit Order and cancelling it

```python
import asyncio
from datetime import datetime
from async_rithmic import RithmicClient, Gateway, OrderType, TransactionType

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
        transaction_type=TransactionType.BUY,
        price=5300.,
    )
    
    await asyncio.sleep(1)
    await client.cancel_order(order_id=order_id)
    
    await asyncio.sleep(1)
    await client.disconnect()

asyncio.run(main())
```

## History Data API

### Fetch Historical Tick Data

The following example will fetch historical data:

```python
import asyncio
from datetime import datetime
from async_rithmic import RithmicClient, Gateway

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Fetch historical tick data
    ticks = await client.get_historical_tick_data(
        "ESZ4",
        "CME",
        datetime(2024, 10, 15, 15, 30),
        datetime(2024, 10, 15, 15, 31),
    )

    print(f"Received {len(ticks)} ticks")
    print(f"Last tick timestamp: {ticks[-1]['datetime']}")

    await client.disconnect()

asyncio.run(main())
```

### Fetch Historical Time Bars

```python
import asyncio
from datetime import datetime
from async_rithmic import RithmicClient, Gateway, TimeBarType

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()

    # Fetch historical time bar data
    bars = await client.get_historical_time_bars(
        "ESZ4",
        "CME",
        datetime(2024, 10, 15, 15, 30),
        datetime(2024, 10, 15, 15, 31),
        TimeBarType.SECOND_BAR,
        6
    )
    
    print(f"Received {len(bars)} bars")
    print(f"Last bar timestamp: {bars[-1]['bar_end_datetime']}")

    await client.disconnect()

asyncio.run(main())
```

## Other methods

This code snippet will list your account summary, session orders and positions:

```python
import asyncio
from async_rithmic import RithmicClient, Gateway, InstrumentType

async def main():
    client = RithmicClient(user="", password="", system_name="Rithmic Test", app_name="my_test_app", app_version="1.0", gateway=Gateway.TEST)
    await client.connect()
    
    account_id = "MY_ACCOUNT"
    
    result = await client.search_symbols("MCL", instrument_type=InstrumentType.FUTURE)
    print("Search result:", result)
    
    summary = await client.list_account_summary(account_id=account_id)
    print("Account summary:", summary[0])
    
    orders = await client.list_orders(account_id=account_id)
    print("Orders:", orders)
    
    positions = await client.list_positions(account_id=account_id)
    print("Positions:", positions)

    await client.disconnect()

asyncio.run(main())
```

## Testing

To execute the tests, use the following command: `make tests`
