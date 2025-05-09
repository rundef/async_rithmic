History Data API
================

Fetch Historical Tick Data
--------------------------

The following example fetches historical tick data:

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import RithmicClient, Gateway

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

Fetch Historical Time Bars
--------------------------

This example fetches historical aggregated time bars (6-second bars in this case):

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import RithmicClient, Gateway, TimeBarType

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
