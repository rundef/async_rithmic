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
            # trail_ticks=20,     # Optional: trailing stop in ticks. Only supported when both stop_ticks and target_ticks are omitted.
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
        await client.disconnect()

    asyncio.run(main())

Placing a Bracket Order
-----------------------

A bracket order is a regular order with one or more attached exit orders bound to it.
In practice, you submit the entry order exactly like a normal market, limit, stop, or
stop-limit order, and then add:

- ``stop_ticks`` for an attached stop-loss order.
- ``target_ticks`` for an attached take-profit order.
- both ``stop_ticks`` and ``target_ticks`` for a bracket with both stop-loss and take-profit.

The stop-loss and take-profit distances are expressed in ticks from the entry price.
The attached order quantity is automatically set to the same quantity as the main order.

When neither ``stop_ticks`` nor ``target_ticks`` is passed, ``submit_order()`` submits a
normal order. When either one is passed, ``submit_order()`` submits a bracket order.

Stop-loss only
~~~~~~~~~~~~~~

.. code-block:: python

    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.MARKET,
        transaction_type=TransactionType.BUY,
        stop_ticks=20,
    )

Take-profit only
~~~~~~~~~~~~~~~~

.. code-block:: python

    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.MARKET,
        transaction_type=TransactionType.BUY,
        target_ticks=40,
    )

Stop-loss and take-profit
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.MARKET,
        transaction_type=TransactionType.BUY,
        stop_ticks=20,
        target_ticks=40,
    )


Market-on-reject for stop orders
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For stop-loss brackets, you may also pass ``stop_market_on_reject=True``:

.. code-block:: python

    await client.submit_order(
        order_id,
        security_code,
        exchange,
        qty=1,
        order_type=OrderType.MARKET,
        transaction_type=TransactionType.BUY,
        stop_ticks=20,
        target_ticks=40,
        stop_market_on_reject=True,
    )

This option tells Rithmic to convert a rejected stop order into a market order. It is
useful as a protective fallback: if the attached stop cannot be accepted as a stop
order, the platform can still attempt to flatten the position instead of leaving it
without stop protection.

Use this option only when that behavior is desired. A market order can fill with
slippage, especially during fast markets or thin liquidity.

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

Modify an existing active order with new parameters.

This method allows you to update one or more attributes of an active order, such
as quantity, order type, price, stop-loss, or take-profit levels.

**Supported attributes:**

- ``qty``: New quantity for the order.
- ``order_type``: Order type, for example ``OrderType.MARKET``, ``OrderType.LIMIT``, or ``OrderType.STOP_LIMIT``.
- ``price``: Updated price, used for limit or stop-limit orders.
- ``trigger_price``: Updated trigger price, used for stop orders.
- ``stop_ticks``: New stop-loss in ticks.
- ``target_ticks``: New take-profit in ticks.
- ``trail_ticks``: New trailing stop in ticks (Only supported when both stop_ticks and target_ticks are omitted)

.. note::

   Rithmic does not allow the main order, stop-loss, and take-profit to be
   modified concurrently. If multiple parts of a bracket order are modified,
   ``async_rithmic`` submits the modifications sequentially.

Basic example:

.. code-block:: python

    await client.modify_order(
        order_id="abc123",
        qty=3,
        target_ticks=50,
        stop_ticks=25,
    )

For time-critical modifications, you can pass the existing order object directly
using ``order=``. This skips the internal ``get_order()`` lookup and avoids an
extra network round-trip before sending the modification request.

Example:

.. code-block:: python

    order = await client.get_order(order_id="abc123")

    await client.modify_order(
        order=order,
        target_ticks=50,
    )

This is useful when you already have the order object and want to avoid adding
unnecessary latency to the modification path.

Exiting a position
------------------

Closes an open trading position for the specified symbol and exchange.
If no symbol is provided, exits all active positions.

.. code-block:: python

    # Exit all active positions
    await client.exit_position()

    # Exit a specific position by symbol and exchange
    await client.exit_position(symbol="ESM5", exchange="CME")
