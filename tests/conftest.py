"""Shared test fixtures."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.maestro_mcz.maestro.controller import MaestroController


@pytest.fixture
def controller():
    """Create a MaestroController with a mocked Socket.IO client."""
    with patch("custom_components.maestro_mcz.maestro.controller.socketio.AsyncClient") as mock_sio_class:
        mock_sio = AsyncMock()
        mock_sio.connected = False
        # socketio.AsyncClient.on() is synchronous — use MagicMock to avoid
        # "coroutine was never awaited" RuntimeWarnings from AsyncMock
        mock_sio.on = MagicMock()
        mock_sio_class.return_value = mock_sio
        ctrl = MaestroController("12345", "AA:BB:CC:DD:EE:FF")
        ctrl._sio = mock_sio
        yield ctrl
