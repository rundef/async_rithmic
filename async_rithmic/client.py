import ssl
import asyncio
from pathlib import Path
from pattern_kit import DelegateMixin, Event

from .plants.ticker import TickerPlant
from .plants.history import HistoryPlant
from .plants.order import OrderPlant
from .plants.pnl import PnlPlant
from .enums import Gateway
from .logger import logger

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    if not localhost_pem.exists():
        raise FileNotFoundError(f"SSL certificate file not found at: {localhost_pem}")

    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context

class RithmicClient(DelegateMixin):
    on_connected = Event()
    on_tick = Event()
    on_time_bar = Event()
    on_historical_tick = Event()
    on_historical_time_bar = Event()
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
            "history": HistoryPlant(self, **kwargs),
        }

        for plant in self.plants.values():
            self._delegate_methods(plant)

    async def connect(self):
        try:
            for plant_type, plant in self.plants.items():
                await plant._connect()

                logger.info(f"Connected to {plant_type} plant")

                self.listeners.append(asyncio.create_task(plant._listen()))
                await plant._login()
                await asyncio.sleep(0.1)

            await self.on_connected.call_async()

        except:
            logger.exception("Failed to connect")

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
