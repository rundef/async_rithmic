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


By default, ``get_historical_tick_data()`` waits until the historical replay is
complete and returns the collected ticks as a list.

Rithmic historical replay bounds have whole-second resolution. The library floors
the requested datetimes to whole seconds and explicitly requests pages of 10,000
ticks. A full page may end partway through its final second, so that final second
is discarded and replayed from its beginning on the next request. This prevents
ticks in the same second from being silently skipped. Historical tick callbacks
are emitted after the current provider page has completed, because only then is
the final second known to be incomplete.

By default, historical tick requests are strict. If ``max_pages`` is reached
before the provider naturally completes the replay, the request raises
``HistoricalDataIncompleteError`` instead of returning a partial list as a
successful result. Set ``strict=False`` only when intentionally accepting a
partial result.

If a single second contains enough ticks to require more than one page, the
provider's whole-second bounds cannot express a lossless continuation; the
request raises ``HistoricalDataPaginationError`` instead of looping or
returning incomplete data as though it were complete.

The ``max_pages`` argument controls how many replay pages can be requested.

The ``idle_timeout`` argument controls how long the client waits without seeing
progress while waiting for a historical replay to complete.

.. code-block:: python

    ticks = await client.get_historical_tick_data(
        ...,
        max_pages=100,
        idle_timeout=10.0,
    )

This is an idle timeout, not a total request timeout. The timer resets whenever a
provider page or completion message is received.

Because Rithmic cannot represent subsecond replay bounds, nonzero microseconds in
``start_time`` or ``end_time`` are floored to the containing second. Returned
ticks should be locally filtered if an application needs a subsecond range.

If ``wait=False`` is passed, the method sends the replay request and returns
immediately. Historical ticks are still emitted through the
``on_historical_tick`` callback.

Historical callbacks are non-transactional. If a callback raises, the active
request fails immediately and a waiting caller receives the original callback
exception; records delivered before the failure are not withdrawn.

If the history plant connection is interrupted while a historical replay is
active, the request raises ``HistoricalDataConnectionError`` promptly. The
library does not resume that replay after reconnecting; callers may retry the
complete interval after the connection is restored.

.. code-block:: python

    async def callback(data):
        print(f"Received data: {data}")

    client.on_historical_tick += callback

Fetch Historical Time Bars
--------------------------

Fetch historical time bars for a symbol over a time range.

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

By default, ``get_historical_time_bars()`` waits until the historical replay is
complete and returns the collected bars as a list.

Rithmic may truncate historical replay responses. In practice, a single replay
request can return at most about 10,000 bars, even if the requested time range
contains many more bars. For example, requesting several months of 1-minute bars
may cover hundreds of thousands of bars, but Rithmic may only return the first
page of results.

To handle this, ``async_rithmic`` automatically paginates historical time bar
requests. After each page, it uses the last received bar marker as the starting
point for the next request and continues until one of the following happens:

- the requested ``end_time`` is reached;
- Rithmic returns no more data;
- ``max_pages`` is reached.

The ``max_pages`` argument controls how many replay pages can be requested.

The ``idle_timeout`` argument controls how long the client waits without seeing
progress while waiting for a historical replay to complete.

.. code-block:: python

    bars = await client.get_historical_time_bars(
        ...,
        max_pages=100,
        idle_timeout=10.0,
    )

This is an idle timeout, not a total request timeout. The timer resets whenever a
bar or completion message is received.

If ``wait=False`` is passed, the method sends the replay request and returns
immediately. Historical bars are still emitted through the
``on_historical_time_bar`` callback.

.. code-block:: python

    async def callback(data):
        print(f"Received data: {data}")

    client.on_historical_time_bar += callback
