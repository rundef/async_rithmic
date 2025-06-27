Order API
=========

Listing accounts
----------------

Use `list_accounts()` to retrieve all supported exchanges.

.. code-block:: python

    accounts = await client.list_accounts()

The result is a list of response objects, for example:

.. code-block:: python

    [
        Object(account_id="123", account_name="123", account_currency="USD", account_auto_liquidate="enabled")
    ]

See the `response_account_list.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/response_account_list.proto>`_ definition for field details.


List Orders
-----------

To retrieve a list of currently active orders, use the `list_orders` method:

.. code-block:: python

    await client.list_orders()

Show Order History Summary
--------------------------

You can view your order history for a specific day using the `show_order_history_summary` method:

.. code-block:: python

    orders = await client.show_order_history_summary(date="20250513)

The `date` parameter must be a string in `YYYYMMDD` format.

Placing a Market Order
----------------------

As a market order will be filled immediately, this script submits the order and receives a fill almost instantly:

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import (
        RithmicClient, OrderType,
        ExchangeOrderNotificationType, TransactionType
    )

    async def callback(notification):
        if notification.notify_type == ExchangeOrderNotificationType.FILL:
            print("order filled", notification)

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

        # Submit market order
        client.on_exchange_order_notification += callback

        order_id = '{0}_order'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
        await client.submit_order(
            order_id,
            security_code,
            exchange,
            qty=1,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.SELL,
            # account_id="ABCD",  # Mandatory if you have multiple accounts
            # stop_ticks=20,      # Optional: stop loss in ticks
            # target_ticks=40,    # Optional: profit target in ticks
            # cancel_at=datetime.now() + timedelta(minutes=2),  # Optional: auto-cancel time
        )

        await asyncio.sleep(1)
        await client.disconnect()

    asyncio.run(main())

Placing a Limit Order
---------------------

This example places a limit order and cancels it shortly after:

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import (
        RithmicClient, OrderType, TransactionType
    )

    async def exchange_order_notification_callback(notification):
        print("exchange order notification", notification)

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

        # Submit limit order
        client.on_exchange_order_notification += exchange_order_notification_callback

        order_id = '{0}_order'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
        await client.submit_order(
            order_id,
            security_code,
            exchange,
            qty=1,
            order_type=OrderType.LIMIT,
            transaction_type=TransactionType.BUY,
            price=5300.0,
        )

        await asyncio.sleep(1)
        await asyncio.sleep(1)
        await client.disconnect()

    asyncio.run(main())

Cancelling an order
-------------------

To cancel a specific order, use the `cancel_order` method. You can provide either:

- `order_id`: The custom order ID you specified when placing the order.
- `basket_id`: The system-generated ID assigned by Rithmic.

.. code-block:: python

    await client.cancel_order(order_id=order_id)

Cancelling all orders
---------------------

To cancel all open orders:

.. code-block:: python

    await client.cancel_all_orders()

Modifying an order
------------------


Modify an existing order with new parameters.

This method allows you to update one or more attributes of an active order, such as quantity, order type, price, stop-loss, or take-profit levels.

**Supported attributes:**

- ``qty``: New quantity for the order.
- ``order_type``: Order type (e.g., ``"MKT"``, ``"LMT"``, ``"STOP LMT"``, etc.).
- ``price``: Updated price (used for limit or stop-limit orders).
- ``trigger_price``: Updated trigger price (for stop orders).
- ``stop_ticks``: New stop-loss in ticks (modify stop-loss).
- ``target_ticks``: New take-profit in ticks (modify take-profit).

.. code-block:: python

    await client.modify_order(
        order_id="abc123",
        qty=3,
        target_ticks=50
        stop_ticks=25
    )

Exit a position
---------------

Closes an open trading position for the specified symbol and exchange.
If no symbol is provided, exits all active positions.

.. code-block:: python

    # Exit all active positions
    await client.exit_position()

    # Exit a specific position by symbol and exchange
    await client.exit_position(symbol="ESM5", exchange="CME")

