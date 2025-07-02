async_rithmic
=============

`async_rithmic` is an asynchronous Python client for connecting to Rithmic's Protocol Buffer API using asyncio.

Rithmic's API is structured around four separate WebSocket endpoints (called *plants*), each responsible for a different category of functionality:

- **TICKER_PLANT** - live market data
- **ORDER_PLANT** - order routing and updates
- **HISTORY_PLANT** - historical data
- **PNL PLANT** - account pnl updates

Each plant runs over its own dedicated WebSocket connection, with separate login and heartbeat management. The `async_rithmic` library mirrors this architecture by creating a separate asynchronous connection per plant.

Internally, the logic for these plants shares a common base but is executed concurrently using `asyncio`, allowing fast, event-driven processing of tick, order, and historical data as it arrives.

📦 GitHub: https://github.com/rundef/async_rithmic

Features
--------

- Native asyncio support
- One client object manages all plant connections
- Custom reconnection logic
- Event hooks for lifecycle events (connected/disconnected, tick received, etc.)


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   connection
   realtime_data
   orders
   historical_data
   pnl
