Connecting to Rithmic
=====================

Basic Connection
----------------

To connect to Rithmic, instantiate a `RithmicClient` with your credentials and call `await client.connect()`:

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient, Gateway

    async def main():
        client = RithmicClient(
            user="your_username",
            password="your_password",
            system_name="Rithmic Test",
            app_name="my_test_app",
            app_version="1.0",
            gateway=Gateway.TEST
        )
        await client.connect()
        await client.disconnect()

    asyncio.run(main())

Custom Reconnection Settings
----------------------------

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
        user="your_username",
        password="your_password",
        system_name="Rithmic Test",
        app_name="my_test_app",
        app_version="1.0",
        gateway=Gateway.TEST,
        reconnection_settings=reconnection
    )

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
