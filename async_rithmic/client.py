import ssl
import asyncio
from pathlib import Path
from collections import defaultdict
from pattern_kit import DelegateMixin, Event

from .plants.ticker import TickerPlant
from .plants.history import HistoryPlant
from .plants.order import OrderPlant
from .plants.pnl import PnlPlant
from .logger import logger
from .objects import ReconnectionSettings, RetrySettings

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    if not localhost_pem.exists():
        raise FileNotFoundError(f"SSL certificate file not found at: {localhost_pem}")

    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context

class RithmicClient(DelegateMixin):
    def __init__(
        self,
        user: str,
        password: str,
        system_name: str,
        app_name: str,
        app_version: str,
        url: str,
        **kwargs
    ):
        # Connection events
        self.on_connected = Event()
        self.on_disconnected = Event()

        # Real-time market updates events
        self.on_tick = Event()
        self.on_time_bar = Event()

        # Order updates events
        self.on_rithmic_order_notification = Event()
        self.on_exchange_order_notification = Event()
        self.on_bracket_update = Event()

        # Historical data events
        self.on_historical_tick = Event()
        self.on_historical_time_bar = Event()

        # PNL events
        self.on_instrument_pnl_update = Event()
        self.on_account_pnl_update = Event()

        if "://" not in url:
            url = f"wss://{url}"

        self.credentials = dict(
            user=user,
            password=password,
            system_name=system_name,
            app_name=app_name,
            app_version=app_version,
            gateway=url,
        )
        self.ssl_context = _setup_ssl_context()

        self.reconnection_settings = kwargs.pop("reconnection_settings", ReconnectionSettings(
            max_retries=None, # infinite

            # 10s, 20s, 30s, .... up until a maximum of 120s
            backoff_type="linear",
            interval=10,
            max_delay=120,

            jitter_range=(0.5, 2.5),
        ))

        self.retry_settings = kwargs.pop("retry_settings", RetrySettings(
            # By default, retry 3 times
            max_retries=3,

            # Timeout if we haven't received all responses for a given request within 30s
            timeout=30.,

            # Retry after waiting 0.5 to 2s
            jitter_range=(0.5, 2.),
        ))

        self.plants = {
            "ticker": TickerPlant(self, **kwargs),
            "order": OrderPlant(self, **kwargs),
            "pnl": PnlPlant(self, **kwargs),
            "history": HistoryPlant(self, **kwargs),
        }

        for plant in self.plants.values():
            self._delegate_methods(plant)

        self.on_connected += lambda plant_type: self.plants[plant_type].logger.debug("Connected")
        self.on_disconnected += lambda plant_type: self.plants[plant_type].logger.debug("Disconnected")

    async def connect(self):
        try:
            for plant in self.plants.values():
                await plant._connect()

                await plant._start_background_tasks()
                await plant._login()
                await asyncio.sleep(0.1)

        except:
            logger.exception("Failed to connect")

            for plant in self.plants.values():
                await plant._stop_background_tasks()

            raise

    async def disconnect(self, timeout=5.0):
        for plant in self.plants.values():
            plant._subscriptions = defaultdict(set)

            if not plant.is_connected:
                continue

            try:
                await asyncio.wait_for(self._disconnect_plant(plant), timeout=timeout)
            except asyncio.TimeoutError:
                plant.logger.error("Timeout disconnecting")
            except:
                plant.logger.exception("Error disconnecting")

    async def _disconnect_plant(self, plant):
        await plant._stop_background_tasks()
        await plant._logout()
        await plant._disconnect()
