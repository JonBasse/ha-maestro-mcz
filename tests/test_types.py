"""Tests for protocol types and constants."""
from custom_components.maestro_mcz.maestro.types import (
    MAESTRO_COMMANDS,
    MAESTRO_COMMANDS_BY_NAME,
    MAESTRO_INFO,
    MAESTRO_STOVE_STATES_BY_ID,
)


def test_commands_by_name_has_all_commands():
    # Check no duplicate names silently shadow each other
    names = [c.name for c in MAESTRO_COMMANDS]
    assert len(names) == len(set(names)), f"Duplicate command names: {[n for n in names if names.count(n) > 1]}"
    assert len(MAESTRO_COMMANDS_BY_NAME) == len(MAESTRO_COMMANDS)


def test_commands_by_name_lookup():
    cmd = MAESTRO_COMMANDS_BY_NAME["Temperature_Setpoint"]
    assert cmd.id == 42
    assert cmd.command_type == "temperature"


def test_stove_states_by_id_lookup():
    state = MAESTRO_STOVE_STATES_BY_ID[0]
    assert state.description == "Off"
    assert state.on_or_off == 0


def test_stove_states_by_id_power_levels():
    for level in range(1, 6):
        state = MAESTRO_STOVE_STATES_BY_ID[10 + level]
        assert state.description == f"Power {level}"
        assert state.on_or_off == 1


def test_info_active_set_point_is_temperature():
    info = MAESTRO_INFO[11]
    assert info.name == "Active_Set_Point"
    assert info.message_type == "temperature"
