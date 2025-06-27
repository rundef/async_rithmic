History Data API
================

.. note::

   ⚠ **Test Environment Limitation**: The test environment does not include historical market data.


Fetch Historical Tick Data
--------------------------

The following example fetches historical tick data:

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import RithmicClient

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

        # Fetch historical tick data
        try:
            ticks = await client.get_historical_tick_data(
                "ESM5",
                "CME",
                datetime(2025, 5, 15, 15, 30),
                datetime(2025, 5, 15, 15, 31),
            )
        except Exception as e:
            print("An exception occurred", e)
            await client.disconnect()
            return

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
    from async_rithmic import RithmicClient, TimeBarType

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

        # Fetch historical time bar data
        try:
            bars = await client.get_historical_time_bars(
                "ESM5",
                "CME",
                datetime(2025, 5, 15, 15, 30),
                datetime(2025, 5, 15, 15, 31),
                TimeBarType.SECOND_BAR,
                6
            )
        except Exception as e:
            print("An exception occurred", e)
            await client.disconnect()
            return

        print(f"Received {len(bars)} bars")
        print(f"Last bar timestamp: {bars[-1]['bar_end_datetime']}")

        await client.disconnect()

    asyncio.run(main())
