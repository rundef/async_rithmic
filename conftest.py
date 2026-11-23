import asyncio
import pytest
import websockets
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock
from pattern_kit import Event

from async_rithmic import RithmicClient
from async_rithmic.plants import TickerPlant, PnlPlant, OrderPlant

@pytest.fixture
def ticker_plant_mock():
    plant = TickerPlant(MagicMock())
    plant.ws = AsyncMock()
    plant.heartbeat_interval = 5
    plant._send_heartbeat = AsyncMock()

    plant.client = MagicMock()
    plant.client.retry_settings = MagicMock(max_retries=1, timeout=3, jitter_range=None)
    plant.client._signal_unexpected_disconnect = AsyncMock()
    plant.client.on_disconnected = Event()
    return plant

@pytest.fixture
def pnl_plant_mock():
    plant = PnlPlant(MagicMock())
    plant.ws = AsyncMock()
    return plant

@pytest.fixture
def order_plant_mock():
    plant = OrderPlant(MagicMock())
    plant.ws = AsyncMock()
    return plant

@pytest.fixture
async def rithmic_server():
    """Local websocket server standing in for a Rithmic gateway.

    Each accepted connection is put on `connections` and kept open until the client closes it.
    """
    server = SimpleNamespace(connections=asyncio.Queue())

    async def handler(connection):
        await server.connections.put(connection)
        await connection.wait_closed()

    async with websockets.serve(handler, "127.0.0.1", 0) as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        server.url = f"ws://127.0.0.1:{port}"
        yield server

def make_client(**kwargs) -> RithmicClient:
    """Offline client whose order plant looks logged in, with two accounts and a CME trade route."""
    client = RithmicClient(
        user="user",
        password="password",
        system_name="Rithmic Test",
        app_name="tests",
        app_version="1.0",
        url="localhost:443",
        **kwargs,
    )
    order_plant = client.plants["order"]
    order_plant.login_info = dict(fcm_id="fcm", ib_id="ib", user_type=3)
    order_plant.accounts = [
        SimpleNamespace(account_id="account-1"),
        SimpleNamespace(account_id="account-2"),
    ]
    order_plant.trade_routes = [SimpleNamespace(exchange="CME", trade_route="simulator")]
    return client

def use_local_gateway(plant, server):
    """Make the plant connect to the local `rithmic_server` over plain websockets."""
    async def connect():
        plant.ws = await websockets.connect(server.url)

    plant._connect = connect

def answer_requests(plant, respond):
    """Answer each request the plant sends with the responses returned by `respond(request)`."""
    async def send(buffer):
        request = plant._convert_bytes_to_response(buffer)
        for response in respond(request):
            await plant._process_response(response)

    plant.ws = AsyncMock()
    plant.ws.send.side_effect = send

def load_response_mock_from_filename(name):
    if isinstance(name, list):
        return [load_response_mock_from_filename(n) for n in name]
    else:
        with open(f"./tests/response_mocks/{name}.bin", "rb") as f:
            return f.read()

def _convert_proto_message_to_bytes(proto_message):
    serialized = proto_message.SerializeToString()
    length = len(serialized)
    buffer = length.to_bytes(4, byteorder='big', signed=True)
    buffer += serialized
    return buffer
