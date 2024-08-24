# Python Rithmic API

> Note: this a fork of https://github.com/jacksonwoody/pyrithmic.git

A robust, async-based Python API designed to interface seamlessly with the Rithmic Protocol Buffer API: Rithmic API Documentation. This package is built to provide an efficient and reliable connection to Rithmic's trading infrastructure, catering to advanced trading strategies and real-time data handling.

## Key Enhancements

This fork introduces several key improvements and new features over the original repository, ensuring compatibility with modern Python environments and providing additional functionality:

- **Python 3.11+ Compatibility**: Refactored code to ensure smooth operation with the latest Python versions.
- **System Name Validation**: Implements pre-login validation of system names, as recommended by Rithmic support, with enhanced error handling during the login process.
- **Account Selection**: Allows users to specify which account to use when calling trading functions, rather than being restricted to the primary account.
- **STOP Orders**: Exposing STOP orders to users
- **Best Bid Offer (BBO) Streaming**: Integrates real-time Best Bid Offer tick streaming. 

One of the most significant upgrades is the transition to an async architecture, providing superior performance and responsiveness when dealing with real-time trading and market data.

## Installation

```
pip install git+https://github.com/rundef/pyrithmic.git#egg=pyrithmic
```

## Credentials

Copy the skeleton file `RITHMIC_CREDENTIALS_SKELETON.ini` located in `src/rithmic/config/envs`.

Contact Rithmic to setup access to Rithmic Test and Rithmic Paper Trading environments.

Once you have log in credentials, create local copies for each environment based off the file 

Each environment will need a local ini file with your credentials, currently available are RITHMIC_PAPER_TRADING.ini and RITHMIC_TEST.ini

You will need an Environment Variable with key RITHMIC_CREDENTIALS_PATH and value the path to the local folder where you have created your environment ini files

You will need to switch on Market Data for exchanges you require (eg CME) for Access to Ticker data in RITHMIC_PAPER_TRADING. 

## Ticker Data API

### Streaming Live Tick Data

Here's an example to stream market data:

```python
import asyncio
from rithmic import RithmicClient, RithmicEnvironment, DataType

async def callback(data: dict):
    print("received", data)

async def main():
    client = RithmicClient(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
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
from rithmic import RithmicClient, RithmicEnvironment, OrderType

async def callback(data):
  print("on_order_fill", data)

async def main():
    client = RithmicClient(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Submit order
    client.on_order_fill += callback
    await client.submit_order(
        security_code,
        exchange,
        qty=1,
        type=OrderType.MKT,
        is_buy=True
    )
    
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(main())
```

#### Placing a Limit Order and cancelling it

We'll use the ticker api to get the most up to date live price and place a limit order which will fill due to aggressive limit price

```python
from datetime import datetime as dt
import time

from rithmic import RithmicOrderApi, RithmicEnvironment, RithmicTickerApi
from rithmic.interfaces.order.order_types import FillStatus


api = RithmicOrderApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
ticker_api = RithmicTickerApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING, loop=api.loop)
security_code, exchange_code = 'ESZ3', 'CME'
tick_data = ticker_api.stream_market_data(security_code, exchange_code)
while tick_data.tick_count < 5:
    time.sleep(0.01)
last_px = tick_data.tick_dataframe.iloc[-1].close
limit_px = last_px + (0.25 * 2) # Set 2 ticks above market for a buy to fill immediately
order_id = '{0}_limit_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
limit_order = api.submit_limit_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=2, is_buy=True, limit_price=limit_px
)
while limit_order.in_market is False:
    time.sleep(0.1) # Order is in the market once we have a basket id from the Exchange

while limit_order.fill_status != FillStatus.FILLED:
    time.sleep(0.1)

avg_px, qty = limit_order.average_fill_price_qty
print(limit_order)
print(limit_order.fill_dataframe)

import asyncio
from rithmic import RithmicClient, RithmicEnvironment, OrderType

async def callback(data):
  print("on_order_fill", data)

async def main():
    client = RithmicClient(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
    await client.connect()

    # Request front month contract
    symbol, exchange = "ES", "CME"
    security_code = await client.get_front_month_contract(symbol, exchange)
    
    # Submit order
    client.on_order_fill += callback
    await client.submit_order(
        security_code,
        exchange,
        qty=1,
        type=OrderType.MKT,
        is_buy=True
    )
    
    await asyncio.sleep(1)

    await client.disconnect()

asyncio.run(main())
```


#### Cancelling a Limit Order:

We'll use the ticker api to get the most up to date live price and place a limit order which won't fill due to non aggressive limit price and then cancel it

```python
from datetime import datetime as dt
import time

from rithmic import RithmicOrderApi, RithmicEnvironment, RithmicTickerApi
from rithmic.interfaces.order.order_types import FillStatus


api = RithmicOrderApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
ticker_api = RithmicTickerApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING, loop=api.loop)
security_code, exchange_code = 'ESZ3', 'CME'
tick_data = ticker_api.stream_market_data(security_code, exchange_code)
while tick_data.tick_count < 5:
    time.sleep(0.01)
last_px = tick_data.tick_dataframe.iloc[-1].close
limit_px = last_px - (0.25 * 10) # Set 10 ticks below market for a buy to not fill
order_id = '{0}_limit_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
limit_order = api.submit_limit_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=2, is_buy=True, limit_price=limit_px
)
while limit_order.in_market is False:
    time.sleep(0.1) # Order is in the market once we have a basket id from the Exchange

assert(limit_order.fill_status == FillStatus.UNFILLED)

api.submit_cancel_order(limit_order.order_id)
while limit_order.cancelled is False:
    time.sleep(0.1)
print(limit_order)
```

#### Modify a Limit Order:

We'll use the ticker api to get the most up to date live price and place a limit order which won't fill due to non aggressive limit price and then modify it

```python
from datetime import datetime as dt
import time

from rithmic import RithmicOrderApi, RithmicEnvironment, RithmicTickerApi
from rithmic.interfaces.order.order_types import FillStatus


api = RithmicOrderApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
ticker_api = RithmicTickerApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING, loop=api.loop)
security_code, exchange_code = 'ESZ3', 'CME'
tick_data = ticker_api.stream_market_data(security_code, exchange_code)
while tick_data.tick_count < 5:
    time.sleep(0.01)
last_px = tick_data.tick_dataframe.iloc[-1].close
limit_px = last_px - (0.25 * 10) # Set 10 ticks below market for a buy to not fill
order_id = '{0}_limit_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
limit_order = api.submit_limit_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=2, is_buy=True, limit_price=limit_px
)
while limit_order.in_market is False:
    time.sleep(0.1) # Order is in the market once we have a basket id from the Exchange

assert(limit_order.fill_status == FillStatus.UNFILLED)

new_limit = last_px - (0.25 * 20)
api.submit_amend_limit_order(limit_order.order_id, security_code, exchange_code, 2, new_limit)
while limit_order.modified is False:
    time.sleep(0.1)
print(limit_order)
```

#### Order is Rejected:

We'll use the ticker api to get the most up to date live price and place a limit order with a quantity too large so it will get rejected by Rithmic

```python
from datetime import datetime as dt
import time

from rithmic import RithmicOrderApi, RithmicEnvironment, RithmicTickerApi
from rithmic.interfaces.order.order_types import FillStatus


api = RithmicOrderApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
ticker_api = RithmicTickerApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING, loop=api.loop)
security_code, exchange_code = 'ESZ3', 'CME'
tick_data = ticker_api.stream_market_data(security_code, exchange_code)
while tick_data.tick_count < 5:
    time.sleep(0.01)
last_px = tick_data.tick_dataframe.iloc[-1].close
limit_px = last_px - (0.25 * 10) # Set 10 ticks below market for a buy to not fill
order_id = '{0}_limit_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
limit_order = api.submit_limit_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=150, is_buy=True, limit_price=limit_px
)
while limit_order.rejected is False:
    time.sleep(0.1) # Order is in the market once we have a basket id from the Exchange

assert(limit_order.fill_status == FillStatus.UNFILLED)
assert limit_order.rejected is True

print(limit_order)
```

## History Data API

### Downloading Historical Tick Data

The following example will fetch historical data, in a streaming fashion:

```python
import asyncio
from datetime import datetime
import pytz
from rithmic import RithmicClient, RithmicEnvironment

async def callback(data: dict):
    print("received", data)

async def main():
    client = RithmicClient(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
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

- `Unit tests`: Run `unit-test`
- `Integration tests`: run against the RITHMIC_PAPER_TRADING environment to test real world functionality, thus user must have credentials and access to run these tests. Tests highlight examples of using live tick data, downloading historical tick data and placing/modifying/cancelling orders and processing fills.
