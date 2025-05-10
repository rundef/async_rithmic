Market Data
===========

Streaming Live Tick Data
------------------------

Here's an example that gets the front month contract for ES and stream market data:

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient, Gateway, DataType, LastTradePresenceBits

    async def callback(data: dict):
        if data["presence_bits"] & LastTradePresenceBits.LAST_TRADE:
            print("received", data)

    async def main():
        client = RithmicClient(
            user="",
            password="",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            gateway=Gateway.TEST
        )
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

Streaming Live Time Bars
------------------------

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient, Gateway, TimeBarType

    async def callback(data: dict):
        print("received", data)

    async def main():
        client = RithmicClient(
            user="",
            password="",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            gateway=Gateway.TEST
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
