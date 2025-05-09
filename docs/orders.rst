Order API
=========

Placing a Market Order
----------------------

As a market order will be filled immediately, this script submits the order and receives a fill almost instantly:

.. code-block:: python

    import asyncio
    from datetime import datetime
    from async_rithmic import (
        RithmicClient, Gateway, OrderType,
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
            gateway=Gateway.TEST
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
        RithmicClient, Gateway, OrderType, TransactionType
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
            gateway=Gateway.TEST
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
        await client.cancel_order(order_id=order_id)
        await asyncio.sleep(1)
        await client.disconnect()

    asyncio.run(main())
