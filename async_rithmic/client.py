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
from .objects import ReconnectionSettings

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    if not localhost_pem.exists():
        raise FileNotFoundError(f"SSL certificate file not found at: {localhost_pem}")

    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context

class RithmicClient(DelegateMixin):
    # Connection events
    on_connected = Event()
    on_disconnected = Event()

    # Real-time market updates events
    on_tick = Event()
    on_time_bar = Event()

    # Order updates events
    on_rithmic_order_notification = Event()
    on_exchange_order_notification = Event()

    # Historical data events
    on_historical_tick = Event()
    on_historical_time_bar = Event()

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

        self.reconnection_settings = kwargs.pop("reconnection_settings", ReconnectionSettings(
            max_retries=None, # infinite

            # 10s, 20s, 30s, .... up until a maximum of 120s
            backoff_type="linear",
            interval=10,
            max_delay=120,

            jitter_range=(0.5, 2.5),
        ))

        self.plants = {
            "ticker": TickerPlant(self, **kwargs),
            "order": OrderPlant(self, **kwargs),
            "pnl": PnlPlant(self, **kwargs),
            "history": HistoryPlant(self, **kwargs),
        }

        for plant in self.plants.values():
            self._delegate_methods(plant)

        self.on_connected += lambda plant_type: logger.debug(f"Connected to {plant_type} plant")
        self.on_disconnected += lambda plant_type: logger.debug(f"Disconnected from {plant_type} plant")

    async def connect(self):
        try:
            for plant_type, plant in self.plants.items():
                await plant._connect()

                self.listeners.append(asyncio.create_task(plant._listen()))
                await plant._login()
                await asyncio.sleep(0.1)

        except:
            logger.exception("Failed to connect")
            raise

    async def disconnect(self):
        for listener in self.listeners:
            listener.cancel()

        await asyncio.gather(*self.listeners, return_exceptions=True)
        self.listeners = []

        for plant_type, plant in self.plants.items():
            await plant._logout()
            await plant._disconnect()

    def get_listeners(self):
        return [
            plant.listen()
            for plant in self.plants.values()
        ]
