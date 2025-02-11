"""Tests for iAqualink integration."""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

from iaqualink.device import (
    AqualinkAuxToggle,
    AqualinkBinarySensor,
    AqualinkDevice,
    AqualinkLightToggle,
    AqualinkSensor,
    AqualinkThermostat,
)
from iaqualink.exception import AqualinkServiceException

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.iaqualink.const import UPDATE_INTERVAL
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ASSUMED_STATE, STATE_ON, STATE_UNAVAILABLE
from homeassistant.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.iaqualink.conftest import get_aqualink_device, get_aqualink_system


async def _ffwd_next_update_interval(hass):
    now = dt_util.utcnow()
    async_fire_time_changed(hass, now + UPDATE_INTERVAL)
    await hass.async_block_till_done()


async def test_setup_login_exception(hass, config_entry):
    """Test setup encountering a login exception."""
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login",
        side_effect=AqualinkServiceException,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_login_timeout(hass, config_entry):
    """Test setup encountering a timeout while logging in."""
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login",
        side_effect=asyncio.TimeoutError,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_systems_exception(hass, config_entry):
    """Test setup encountering an exception while retrieving systems."""
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        side_effect=AqualinkServiceException,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_no_systems_recognized(hass, config_entry):
    """Test setup ending in no systems recognized."""
    config_entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value={},
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_devices_exception(hass, config_entry, client):
    """Test setup encountering an exception while retrieving devices."""
    config_entry.add_to_hass(hass)

    system = get_aqualink_system(client)
    systems = {system.serial: system}

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value=systems,
    ), patch.object(
        system, "get_devices"
    ) as mock_get_devices:
        mock_get_devices.side_effect = AqualinkServiceException
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_all_good_no_recognized_devices(hass, config_entry, client):
    """Test setup ending in no devices recognized."""
    config_entry.add_to_hass(hass)

    system = get_aqualink_system(client)
    systems = {system.serial: system}

    device = get_aqualink_device(system, AqualinkDevice)
    devices = {device.name: device}

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value=systems,
    ), patch.object(
        system, "get_devices"
    ) as mock_get_devices:
        mock_get_devices.return_value = devices
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 0
    assert len(hass.states.async_entity_ids(CLIMATE_DOMAIN)) == 0
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 0
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 0
    assert len(hass.states.async_entity_ids(SWITCH_DOMAIN)) == 0

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_all_good_all_device_types(hass, config_entry, client):
    """Test setup ending in one device of each type recognized."""
    config_entry.add_to_hass(hass)

    system = get_aqualink_system(client)
    systems = {system.serial: system}

    devices = [
        get_aqualink_device(system, AqualinkAuxToggle),
        get_aqualink_device(system, AqualinkBinarySensor),
        get_aqualink_device(system, AqualinkLightToggle),
        get_aqualink_device(system, AqualinkSensor),
        get_aqualink_device(system, AqualinkThermostat),
    ]
    devices = {d.name: d for d in devices}

    system.get_devices = AsyncMock(return_value=devices)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value=systems,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 1
    assert len(hass.states.async_entity_ids(CLIMATE_DOMAIN)) == 1
    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 1
    assert len(hass.states.async_entity_ids(SWITCH_DOMAIN)) == 1

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_multiple_updates(hass, config_entry, caplog, client):
    """Test all possible results of online status transition after update."""
    config_entry.add_to_hass(hass)

    system = get_aqualink_system(client)
    systems = {system.serial: system}

    system.get_devices = AsyncMock(return_value={})

    caplog.set_level(logging.WARNING)

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value=systems,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    def set_online_to_true():
        system.online = True

    def set_online_to_false():
        system.online = False

    system.update = AsyncMock()

    # True -> True
    system.online = True
    caplog.clear()
    system.update.side_effect = set_online_to_true
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 0

    # True -> False
    system.online = True
    caplog.clear()
    system.update.side_effect = set_online_to_false
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 0

    # True -> None / ServiceException
    system.online = True
    caplog.clear()
    system.update.side_effect = AqualinkServiceException
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 1
    assert "Failed" in caplog.text

    # False -> False
    system.online = False
    caplog.clear()
    system.update.side_effect = set_online_to_false
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 0

    # False -> True
    system.online = False
    caplog.clear()
    system.update.side_effect = set_online_to_true
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 1
    assert "Reconnected" in caplog.text

    # False -> None / ServiceException
    system.online = False
    caplog.clear()
    system.update.side_effect = AqualinkServiceException
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 1
    assert "Failed" in caplog.text

    # None -> None / ServiceException
    system.online = None
    caplog.clear()
    system.update.side_effect = AqualinkServiceException
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 0

    # None -> True
    system.online = None
    caplog.clear()
    system.update.side_effect = set_online_to_true
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 1
    assert "Reconnected" in caplog.text

    # None -> False
    system.online = None
    caplog.clear()
    system.update.side_effect = set_online_to_false
    await _ffwd_next_update_interval(hass)
    assert len(caplog.records) == 0

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_entity_assumed_and_available(hass, config_entry, client):
    """Test assumed_state and_available properties for all values of online."""
    config_entry.add_to_hass(hass)

    system = get_aqualink_system(client)
    systems = {system.serial: system}

    light = get_aqualink_device(system, AqualinkLightToggle, data={"state": "1"})
    devices = {d.name: d for d in [light]}
    system.get_devices = AsyncMock(return_value=devices)
    system.update = AsyncMock()

    with patch(
        "homeassistant.components.iaqualink.AqualinkClient.login", return_value=None
    ), patch(
        "homeassistant.components.iaqualink.AqualinkClient.get_systems",
        return_value=systems,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(LIGHT_DOMAIN)) == 1

    name = f"{LIGHT_DOMAIN}.{light.name}"

    # None means maybe.
    light.system.online = None
    await _ffwd_next_update_interval(hass)
    state = hass.states.get(name)
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes.get(ATTR_ASSUMED_STATE) is True

    light.system.online = False
    await _ffwd_next_update_interval(hass)
    state = hass.states.get(name)
    assert state.state == STATE_UNAVAILABLE
    assert state.attributes.get(ATTR_ASSUMED_STATE) is True

    light.system.online = True
    await _ffwd_next_update_interval(hass)
    state = hass.states.get(name)
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE) is None
