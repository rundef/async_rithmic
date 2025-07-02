Connecting to Rithmic
=====================

Basic Connection
----------------

To connect to Rithmic, instantiate a `RithmicClient` with your credentials and call `await client.connect()`:

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient

    async def main():
        client = RithmicClient(
            user="your_username",
            password="your_password",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            url="rituz00100.rithmic.com:443"  # Example: test gateway only
        )
        await client.connect()
        await client.disconnect()

    asyncio.run(main())

Conformance
-----------

.. important::

   To obtain the list of production URLs, you must first pass the **conformance** test.

   - First, `contact Rithmic <https://www.rithmic.com/contact>`_.
   - You will be asked to connect to the order plant and leave the app running.
   - You can use the `conformance.py script <https://github.com/rundef/async_rithmic/blob/main/scripts/conformance.py>`_ to accomplish this.

Custom Reconnection Settings
----------------------------

`async_rithmic` will automatically attempt to reconnect if the connection to Rithmic is lost (no matter the reason for the disconnection). This includes network drops, internet hiccups, server restarts, or unexpected protocol errors.

You can customize the reconnection behavior using `ReconnectionSettings`. This allows you to define backoff strategies like exponential delay with jitter:

.. code-block:: python

    from async_rithmic import ReconnectionSettings

    reconnection = ReconnectionSettings(
        max_retries=None,  # retry forever
        backoff_type="exponential",
        interval=2,
        max_delay=60,
        jitter_range=(0.5, 2.0)
    )

    client = RithmicClient(
        ...
        reconnection_settings=reconnection
    )

Custom Retry Settings
---------------------

If a request takes longer than the configured `timeout` (in seconds), it will be retried up to `max_retries` times. This helps handle situations where a response might be unexpectedly slow due to network delays, backend congestion, or temporary service issues.

You can customize the retry behavior using `RetrySettings`.

.. code-block:: python

    from async_rithmic import RetrySettings

    retry = RetrySettings(
        max_retries=3,           # Maximum number of attempts
        timeout=30.0,            # Timeout in seconds for each attempt
        jitter_range=(0.5, 2.0)  # Random delay (in seconds) between retries
    )

    client = RithmicClient(
        ...
        retry_settings=retry
    )

.. note::

    - Only timeouts are retried; other errors (like bad requests) will not trigger retries.
    - Each retry uses a new request ID, so every attempt is a fresh request to Rithmic.
    - If all attempts time out, a `TimeoutError` is raised.
    - This mechanism makes your client more robust to occasional slowdowns in the Rithmic infrastructure, network hiccups, or other unpredictable delays.


Event Handlers
--------------

You can register callbacks to respond to connection lifecycle events such as successful plant connection or disconnection.

.. code-block:: python

    async def on_connected(plant_type: str):
        print(f"Connected to plant: {plant_type}")

    async def on_disconnected(plant_type: str):
        print(f"Disconnected from plant: {plant_type}")

    client.on_connected += on_connected
    client.on_disconnected += on_disconnected

Debugging & Logging
-------------------

`async_rithmic` uses Python's standard `logging` module to emit log messages.
You can easily control the verbosity of logging to help with debugging or to better understand what your client is doing.

To see detailed logs from the package (such as connection events, requests, and errors), set the logger named `"rithmic"` to `DEBUG` level:

.. code-block:: python

    import logging

    logging.getLogger("rithmic").setLevel(logging.DEBUG)

Setting the level to `DEBUG` will print more detailed information to the console, which can be very helpful when troubleshooting.
