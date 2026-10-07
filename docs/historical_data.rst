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

Historical replays are paginated automatically. Rithmic typically returns at most
about 10,000 ticks per page; the client requests additional pages until the
range is complete, no more data is available, or ``max_pages`` is reached.

Tick replay uses whole-second boundaries, so microseconds in ``start_time`` and
``end_time`` are rounded down. If a page ends in the middle of a second, the
client replays that second from its beginning before continuing. This avoids
skipping ticks that share the page's final second. If one second contains more
ticks than a page can hold, the client raises ``HistoricalDataPaginationError``
because the range cannot be continued without risking data loss.

By default, historical tick requests are strict. If ``max_pages`` is reached
before the replay completes, the request raises ``HistoricalDataIncompleteError``
instead of returning a partial result. Set ``strict=False`` only when a partial
result is acceptable.

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
page or completion message is received.

If ``wait=False`` is passed, the method sends the replay request and returns
immediately. Historical ticks are still emitted through the
``on_historical_tick`` callback.

For long replays, pass ``progress_callback`` to receive one update after each
completed page:

.. code-block:: python

    def on_progress(progress):
        print(
            progress.pages_requested,
            progress.rows_received,
            progress.last_timestamp,
        )

    ticks = await client.get_historical_tick_data(
        ...,
        progress_callback=on_progress,
    )

``HistoricalDataProgress`` reports cumulative pages and rows; it is not a
percentage because the total is not known in advance. ``last_timestamp`` is the
timestamp of the most recently delivered record. Empty results do not produce a
progress update. For ticks, ``boundary_replay_count`` tells you how often the
client had to replay a partial final second; it is always zero for time bars.

If a data or progress callback raises, the replay stops and a waiting call
receives that exception. Records delivered before the error are not undone.

If the connection is lost during a replay, the request raises
``HistoricalDataConnectionError`` and is not resumed automatically.

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

Historical time-bar replays are paginated automatically. Rithmic typically
returns at most about 10,000 bars per page; the client requests additional pages
until the range is complete, no more data is available, or ``max_pages`` is
reached.

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

Time-bar requests support the same ``progress_callback`` described above. The
callback runs after each completed page and reports cumulative bars received.

.. code-block:: python

    async def callback(data):
        print(f"Received data: {data}")

    client.on_historical_time_bar += callback
