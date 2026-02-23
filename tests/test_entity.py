"""Tests for MaestroEntity base class."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.maestro_mcz.entity import MaestroEntity
from custom_components.maestro_mcz.maestro.controller import MaestroController


class ConcreteEntity(MaestroEntity):
    """Concrete subclass for testing abstract base."""
    pass


@pytest.fixture
def mock_controller():
    ctrl = MagicMock(spec=MaestroController)
    ctrl.serial = "12345"
    ctrl.connected = True
    ctrl.state = {}
    return ctrl


@pytest.fixture
def entity(mock_controller):
    return ConcreteEntity(mock_controller)


class TestEntityInit:
    def test_has_entity_name(self, entity):
        assert entity._attr_has_entity_name is True

    def test_device_info_identifiers(self, entity):
        identifiers = entity._attr_device_info["identifiers"]
        assert ("maestro_mcz", "12345") in identifiers

    def test_device_info_manufacturer(self, entity):
        assert entity._attr_device_info["manufacturer"] == "MCZ"

    def test_device_info_model(self, entity):
        assert entity._attr_device_info["model"] == "Maestro"

    def test_device_info_name(self, entity):
        assert entity._attr_device_info["name"] == "Maestro Stove"


class TestEntityLifecycle:
    @pytest.mark.asyncio
    async def test_added_to_hass_registers_listener(self, entity, mock_controller):
        with patch.object(MaestroEntity.__bases__[0], "async_added_to_hass", new_callable=AsyncMock):
            await entity.async_added_to_hass()
        mock_controller.add_listener.assert_called_once_with(entity._update_callback)

    @pytest.mark.asyncio
    async def test_remove_from_hass_unregisters_listener(self, entity, mock_controller):
        with patch.object(MaestroEntity.__bases__[0], "async_will_remove_from_hass", new_callable=AsyncMock):
            await entity.async_will_remove_from_hass()
        mock_controller.remove_listener.assert_called_once_with(entity._update_callback)


class TestEntityAvailability:
    def test_available_when_connected(self, entity, mock_controller):
        mock_controller.connected = True
        assert entity.available is True

    def test_unavailable_when_disconnected(self, entity, mock_controller):
        mock_controller.connected = False
        assert entity.available is False
