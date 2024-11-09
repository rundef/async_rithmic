import pytest
from unittest.mock import MagicMock, AsyncMock

from async_rithmic.plants import TickerPlant, PnlPlant, OrderPlant

@pytest.fixture
def ticker_plant_mock():
    plant = TickerPlant(MagicMock())
    plant.ws = AsyncMock()
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

def load_response_mock_from_filename(name):
    if isinstance(name, list):
        return [load_response_mock_from_filename(n) for n in name]
    else:
        with open(f"./tests/response_mocks/{name}.bin", "rb") as f:
            return f.read()
