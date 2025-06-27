import asyncio
import logging
from async_rithmic import RithmicClient

logging.getLogger("rithmic").setLevel(logging.DEBUG)

async def main():
    client = RithmicClient(
        user="your_username",
        password="your_password",
        system_name="Rithmic Test",
        app_name="your_test_app",
        app_version="1.0",
        url="rituz00100.rithmic.com:443"  # Test gateway
    )

    # Only need to login to the order plant of Rithmic Test, and leave the app logged in.
    order_plant = client.plants["order"]

    try:
        await order_plant._connect()
        await order_plant._start_background_tasks()
        await order_plant._login()
        print("Logged in successfully")

        print("Sleeping ...")
        await asyncio.sleep(3600)

    except Exception as e:
        print(f"Main exception: {e!r}")

    finally:
        await order_plant._stop_background_tasks()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting cleanly (Ctrl+C detected)")
