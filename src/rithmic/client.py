import ssl
import asyncio
from pathlib import Path
from datetime import datetime

from rithmic.plants.ticker import TickerPlant
from rithmic.plants.history import HistoryPlant
from rithmic.plants.order import OrderPlant
from rithmic.plants.pnl import PnlPlant
from rithmic.event import Event
from rithmic.enums import Gateway
from rithmic.logger import logger

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context

class RithmicClient:
    on_connected = Event()
    on_tick = Event()
    on_historical_tick = Event()
    on_rithmic_order_notification = Event()
    on_exchange_order_notification = Event()

    def __init__(
        self,
        user: str,
        password: str,
        system_name: str,
        app_name: str,
        app_version: str,
        gateway: Gateway = Gateway.TEST,
        **kwargs
    ):

        self.credentials = dict(
            user=user,
            password=password,
            system_name=system_name,
            app_name=app_name,
            app_version=app_version,
            gateway=f"wss://{gateway.value}",
        )
        self.ssl_context = _setup_ssl_context()
        self.listeners = []

        self.plants = {
            "ticker": TickerPlant(self, **kwargs),
            "order": OrderPlant(self, **kwargs),
            "pnl": PnlPlant(self, **kwargs),
        }

        for plant in self.plants.values():
            self._map_methods(plant)

    def _map_methods(self, plant):
        """
        Binds plant's public methods to the current class instance
        """
        for method_name in dir(plant):
            if not method_name.startswith('_'):
                method = getattr(plant, method_name)
                if callable(method):
                    setattr(self, method_name, method)

    async def connect(self):
        try:
            for plant_type, plant in self.plants.items():
                await plant._connect()
                await plant._login()

                logger.info(f"Connected to {plant_type} plant")

                self.listeners.append(asyncio.create_task(plant._listen()))

                await asyncio.sleep(0.1)

            await self.on_connected.notify()

        except:
            logger.exception("Failed to connect")

    async def get_historical_tick_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime
    ):
        # Connect to the history plant only if we have to
        if "history" not in self.plants:
            plant = HistoryPlant(self)
            await plant._connect()
            await plant._login()

            self.plants["history"] = plant

            logger.debug("Connected to history plant")

            self.listeners.append(asyncio.create_task(plant._listen()))

        return await self.plants["history"].get_historical_tick_data(symbol, exchange, start_time, end_time)

    async def disconnect(self):
        for listener in self.listeners:
            listener.cancel()
        await asyncio.gather(*self.listeners, return_exceptions=True)
        self.listeners = []

        for plant_type, plant in self.plants.items():
            await plant._logout()
            await plant._disconnect()

            logger.debug(f"Disconnected from {plant_type} plant")

    def get_listeners(self):
        return [
            plant.listen()
            for plant in self.plants.values()
        ]
