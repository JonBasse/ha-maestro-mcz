"""Tests for config flow validation."""
import re

SERIAL_PATTERN = r"^\d+$"
MAC_PATTERN = r"^([0-9A-F]{2}[:\-]){5}[0-9A-F]{2}$"


class TestSerialValidation:
    def test_valid_serial(self):
        assert re.match(SERIAL_PATTERN, "12345678")

    def test_serial_with_letters(self):
        assert not re.match(SERIAL_PATTERN, "1234abc")

    def test_empty_serial(self):
        assert not re.match(SERIAL_PATTERN, "")

    def test_serial_with_spaces(self):
        assert not re.match(SERIAL_PATTERN, "123 456")


class TestMacValidation:
    def test_valid_mac_colons(self):
        assert re.match(MAC_PATTERN, "AA:BB:CC:DD:EE:FF")

    def test_valid_mac_dashes(self):
        assert re.match(MAC_PATTERN, "AA-BB-CC-DD-EE-FF")

    def test_lowercase_rejected(self):
        assert not re.match(MAC_PATTERN, "aa:bb:cc:dd:ee:ff")

    def test_invalid_mac_short(self):
        assert not re.match(MAC_PATTERN, "AA:BB:CC")

    def test_invalid_mac_no_separator(self):
        assert not re.match(MAC_PATTERN, "AABBCCDDEEFF")
