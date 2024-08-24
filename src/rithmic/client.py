import ssl
import asyncio
from pathlib import Path

from rithmic.plants.ticker import TickerPlant
from rithmic.plants.history import HistoryPlant
from rithmic.plants.order import OrderPlant
from rithmic.config.credentials import RithmicEnvironment, get_rithmic_credentials
from rithmic.event import Event
from rithmic.enums import Gateway

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context

class RithmicClient:
    on_connected = Event()
    on_disconnected = Event()
    on_tick = Event()
    on_historical_tick = Event()

    def __init__(
        self,
        env: RithmicEnvironment = None,
        gateway: Gateway = Gateway.TEST,
        **kwargs
    ):

        self.env = env
        self.credentials = get_rithmic_credentials(env)
        self.ssl_context = _setup_ssl_context()
        self.listeners = []

        self.plants = {
            "ticker": TickerPlant(self, **kwargs),
            "history": HistoryPlant(self, **kwargs),
            "order": OrderPlant(self, **kwargs),
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
        for plant in self.plants.values():
            await plant._connect()
            await plant._login()

            self.listeners.append(asyncio.create_task(plant._listen()))

    async def disconnect(self):
        for listener in self.listeners:
            listener.cancel()
        await asyncio.gather(*self.listeners, return_exceptions=True)
        self.listeners = []

        for plant in self.plants.values():
            await plant._logout()
            await plant._disconnect()

    def get_listeners(self):
        return [
            plant.listen()
            for plant in self.plants.values()
        ]
