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
Contact Rithmic to setup access to Rithmic Test and Rithmic Paper Trading environments.

Once you have log in credentials, create local copies for each environment based off the file RITHMIC_CREDENTIALS_SKELETON.ini located in src/rithmic/config/envs

Each environment will need a local ini file with your credentials, currently available are RITHMIC_PAPER_TRADING.ini and RITHMIC_TEST.ini

You will need an Environment Variable with key RITHMIC_CREDENTIALS_PATH and value the path to the local folder where you have created your environment ini files

You will need to switch on Market Data for exchanges you require (eg CME) for Access to Ticker data in RITHMIC_PAPER_TRADING. 

## Tick Data API

### Streaming Live Tick Data

To stream market data for ESZ3 and NQZ3 on CME as a long running process:

```python
import time

from rithmic import RithmicTickerApi, RithmicEnvironment


api = RithmicTickerApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING, auto_connect=True)
es_stream = api.stream_market_data('ESZ3', 'CME')
nq_stream = api.stream_market_data('NQZ3', 'CME')
while api.total_tick_count < 500:
    time.sleep(0.1)

df_es = es_stream.tick_dataframe
df_nq = nq_stream.tick_dataframe

print(df_es)
print(df_nq)
```

You can provide your own asyncio loop when instantiating an api if you wish to use a single aysncio loop across all interfaces &/or your entire trading system.

In the ticker API, calling stream_market_data returns a TickDataStream object which has a streamed_data attribute (list of ticks) and can also be accessed as a Pandas DataFrame named tick_dataframe

To add your own custom callbacks to the Ticker API, you can add a callback that fires on every tick received and/or a period sync callback that runs at an interval you set upon class instantiation, this will give new tick data for each stream every n intervals you can process, save to database, etc, example below setting callbacks for both, periodic syncing at half second intervals:
```python
import time

from pandas import DataFrame

from rithmic import RithmicTickerApi, RithmicEnvironment, CallbackManager, CallbackId

cbm = CallbackManager()


def tick_data_update(data: dict):
    volume = data['volume']
    if volume > 2:
        print(data)


def period_sync_callback(df: DataFrame, security_code: str, exchange_code: str):
    print('{0} New Records to process on {1}|{2}'.format(len(df), security_code, exchange_code))


cbm.register_callback(CallbackId.TICKER_LAST_TRADE, tick_data_update)
cbm.register_callback(CallbackId.TICKER_PERIODIC_LIVE_TICK_DATA_SYNCING, period_sync_callback)

api = RithmicTickerApi(
    env=RithmicEnvironment.RITHMIC_PAPER_TRADING,
    callback_manager=cbm,
    periodic_sync_interval_seconds=0.5
)
es_stream = api.stream_market_data('ESZ3', 'CME')
nq_stream = api.stream_market_data('NQZ3', 'CME')
complete = False
while not complete:
    time.sleep(1)
    complete = api.total_tick_count > 500

```

## Order API

### Basics

All orders/cancels/modifications are placed asynchronously then their status is updated as updates from the exchange flow into the API. All order_id strings provided need to be unique to a session to track updates back from the exchange, suggest using a database primary key or dateetime based string for example

#### Placing a Market Order:

As a market order will be filled immediately, this script will submit the order and receive a fill straight away

```python
from datetime import datetime as dt
import time

from rithmic import RithmicOrderApi, RithmicEnvironment
from rithmic.interfaces.order.order_types import FillStatus


api = RithmicOrderApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
order_id = '{0}_mkt_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
market_order = api.submit_market_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=2, is_buy=True
)
while market_order.in_market is False:
    time.sleep(0.1) # Order is in the market once we have a basket id from the Exchange

while market_order.fill_status != FillStatus.FILLED:
    time.sleep(0.1)

avg_px, qty = market_order.average_fill_price_qty
print(market_order)
print(market_order.fill_dataframe)
```

#### Placing a Limit Order:

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

#### Place a Bracket Order:

We'll use the ticker api to get the most up to date live price and place a bracket order that will fill and create stop and take profit orders which we'll amend and then cancel

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
limit_px = last_px + (0.25 * 3) # Set 10 ticks below market for a buy to not fill
order_id = '{0}_limit_order'.format(dt.now().strftime('%Y%m%d_%H%M%S'))
bracket_order = api.submit_bracket_order(
    order_id=order_id, security_code='ESZ3', exchange_code='CME', quantity=1, is_buy=True, limit_price=limit_px,
    take_profit_ticks=15, stop_loss_ticks=15
)
while bracket_order.children_in_market is False:
    time.sleep(0.1) # Order has been filled and children are also in the market

assert(bracket_order.fill_status == FillStatus.FILLED)
take_profit_orders, stop_loss_orders = bracket_order.child_orders
tp_order, sl_order = take_profit_orders[0], stop_loss_orders[0]
# Since only 1 lot in order, will only have a single child for each

assert tp_order.fill_status == FillStatus.UNFILLED
assert sl_order.fill_status == FillStatus.UNFILLED

assert tp_order.limit_price == limit_px + (15 * 0.25)
assert sl_order.trigger_price == limit_px - (15 * 0.25)

new_take_profit = limit_px + (20 * 0.25)
new_stop_loss = limit_px - (20 * 0.25)
api.submit_amend_bracket_order_all_take_profit_orders(bracket_order.order_id, new_take_profit)
api.submit_amend_bracket_order_all_stop_loss_orders(bracket_order.order_id, new_stop_loss)

while tp_order.modified is False and sl_order.modified is False:
    time.sleep(0.01)
assert tp_order.limit_price == limit_px + (20 * 0.25)
assert sl_order.trigger_price == limit_px - (20 * 0.25)

api.submit_cancel_bracket_order_all_children(bracket_order.order_id)
while tp_order.cancelled is False and sl_order.cancelled is False:
    time.sleep(0.01)
assert tp_order.cancelled is True
assert sl_order.cancelled is True
```

## History Data API

### Downloading Historical Tick Data

To download historical tick data for ESZ3 and NQZ3 on CME:

```python
from datetime import datetime as dt
import pytz
import time

from rithmic import RithmicHistoryApi, RithmicEnvironment


api = RithmicHistoryApi(env=RithmicEnvironment.RITHMIC_PAPER_TRADING)
security_code, security_code2, exchange_code = 'ESZ3', 'NQZ3', 'CME'
start_time = dt(2023, 10, 16, 1, tzinfo=pytz.utc)
end_time = dt(2023, 10, 16, 3, tzinfo=pytz.utc)
es_dl = api.download_historical_tick_data(
    security_code, exchange_code, start_time, end_time
)
nq_dl = api.download_historical_tick_data(
    security_code2, exchange_code, start_time, end_time
)
while api.downloads_are_complete is False:
    time.sleep(0.01)

print(es_dl.tick_dataframe)
print(nq_dl.tick_dataframe)
```

## Testing

Integration testing is run against the RITHMIC_PAPER_TRADING environment to test real world functionality, thus user must have credentials and access to run these tests. Tests highlight examples of using live tick data, downloading historical tick data and placing/modifying/cancelling orders and processing fills.
