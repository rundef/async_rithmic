Market Data API
===============

This section documents the available functions to access market data, such as listing exchanges, searching for symbols, and retrieving front-month contracts.


Listing exchanges
-----------------

Use `list_exchanges()` to retrieve all supported exchanges.

.. code-block:: python

    exchanges = await client.list_exchanges()

The result is a list of response objects, for example:

.. code-block:: python

    [
        Object(exchange="CME", entitlement_flag=1),
        Object(exchange="EUREX", entitlement_flag=2)
    ]

- `exchange`: The name of the exchange.
- `entitlement_flag`:
    - `1`: You are entitled to access this exchange.
    - `2`: You are **not** entitled to access this exchange.

See the `response_list_exchange_permissions.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/response_list_exchange_permissions.proto>`_ definition for field details.

Searching symbols
-----------------

Use `search_symbols()` to find tradable instruments by name, type, and exchange.

.. code-block:: python

    results = await client.search_symbols("SILVER", instrument_type=InstrumentType.FUTURE, exchange="COMEX")

The result is a list of response objects, for example:

.. code-block:: python

    [
        Object(symbol="SIM5", exchange="COMEX", symbol_name="COMEX Silver Futures", product_code="SI", instrument_type="Future", expiration_date="20250626")
    ]

See the `response_search_symbols.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/response_search_symbols.proto>`_ definition for field details.


Retrieving front month contract
-------------------------------

Use `get_front_month_contract()` to get the active front-month contract for a given symbol and exchange.

.. code-block:: python

    contract = await client.get_front_month_contract("ES", "CME")

This returns a string such as:

.. code-block:: python

    "ESM5"

Where:

- `ES`: The root symbol.

- `M`: The contract month code.

- `5`: The year (e.g., `5` = 2025).

Streaming Live Tick Data
------------------------

Here's an example that gets the front month contract for ES and stream market data (trade data and best bid and offer):

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient, DataType, LastTradePresenceBits, BestBidOfferPresenceBits

    async def callback(data: dict):
        if data["data_type"] == DataType.LAST_TRADE:
            if data["presence_bits"] & LastTradePresenceBits.LAST_TRADE:
                print("received trade data", data)

        elif data["data_type"] == DataType.BBO:
            if data["presence_bits"] & BestBidOfferPresenceBits.BID:
                print("BEST BID", data)
            elif data["presence_bits"] & BestBidOfferPresenceBits.ASK:
                print("BEST ASK", data)

    async def main():
        client = RithmicClient(
            user="",
            password="",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            url="rituz00100.rithmic.com:443"
        )
        await client.connect()

        # Request front month contract
        symbol, exchange = "ES", "CME"
        security_code = await client.get_front_month_contract(symbol, exchange)

        # Stream market data
        print(f"Streaming market data for {security_code}")
        data_type = DataType.LAST_TRADE | DataType.BBO
        client.on_tick += callback
        await client.subscribe_to_market_data(security_code, exchange, data_type)

        # Wait 10 seconds, unsubscribe and disconnect
        await asyncio.sleep(10)
        await client.unsubscribe_from_market_data(security_code, exchange, data_type)
        await client.disconnect()

    asyncio.run(main())

See the `best_bid_offer.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/best_bid_offer.proto>`_ and `last_trade.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/last_trade.proto>`_ definitions for field details.

Streaming Live Time Bars
------------------------

The possible time bar types are: `SECOND_BAR`, `MINUTE_BAR`, `DAILY_BAR` and `WEEKLY_BAR`.

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient, TimeBarType

    async def callback(data: dict):
        print("received", data)

    async def main():
        client = RithmicClient(
            user="",
            password="",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            url="rituz00100.rithmic.com:443"
        )
        await client.connect()

        # Request front month contract
        symbol, exchange = "ES", "CME"
        security_code = await client.get_front_month_contract(symbol, exchange)

        # Stream time bar data
        print(f"Streaming market data for {security_code}")

        client.on_time_bar += callback
        # Subscribe to 6 seconds bars
        await client.subscribe_to_time_bar_data(
            security_code, exchange, TimeBarType.SECOND_BAR, 6
        )

        # Wait 20 seconds, unsubscribe and disconnect
        await asyncio.sleep(20)
        await client.unsubscribe_from_time_bar_data(
            security_code, exchange, TimeBarType.SECOND_BAR, 6
        )
        await client.disconnect()

    asyncio.run(main())

See the `time_bar.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/time_bar.proto>`_ definition for field details.
