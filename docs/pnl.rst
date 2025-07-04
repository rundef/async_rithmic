list_account_summary

PNL API
=========

Account PNL snapshot
--------------------

Use `list_account_summary()` to retrieve the PNL snapshot of an account.

.. code-block:: python

    accounts = await client.list_account_summary(account_id="1234")

The result is a list which contains a single object. See the `account_pnl_position_update.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/account_pnl_position_update.proto>`_ definition for field details.


Streaming PNL updates
---------------------

Here's an example that gets pnl updates in a streaming fashion:

.. code-block:: python

    import asyncio
    from async_rithmic import RithmicClient

    async def on_instrument_pnl_update(data):
        print("instrument_pnl_update", data)

    async def on_account_pnl_update(data):
        print("account_pnl_update", data)

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

        client.on_instrument_pnl_update += on_instrument_pnl_update
        client.on_account_pnl_update += on_account_pnl_update

        await client.subscribe_to_pnl_updates()

        # Wait 10 seconds, unsubscribe and disconnect
        await asyncio.sleep(10)
        await client.unsubscribe_from_pnl_updates()
        await client.disconnect()

    asyncio.run(main())

See the `account_pnl_position_update.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/account_pnl_position_update.proto>`_ and `instrument_pnl_position_update.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/instrument_pnl_position_update.proto>`_ definitions for field details.
