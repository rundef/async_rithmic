list_account_summary

PNL API
=========

Account PNL snapshot
--------------------

Use `list_account_summary()` to retrieve the PNL snapshot of an account.

.. code-block:: python

    accounts = await client.list_account_summary(account_id="1234")

The result is a list which contains a single object. See the `account_pnl_position_update.proto <https://github.com/rundef/async_rithmic/blob/main/async_rithmic/protocol_buffers/source/account_pnl_position_update.proto>`_ definition for field details.
