"""Offline tests for the frame helpers (no Home Assistant, no hardware needed).

Run with:  python -m pytest tests
"""
import importlib.util
import pathlib
import struct

_spec = importlib.util.spec_from_file_location(
    "ee_protocol",
    pathlib.Path(__file__).parents[1] / "custom_components" / "eachenergy" / "protocol.py",
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)


def test_crc16_modbus_check_value():
    assert protocol.crc16_modbus(b"123456789") == 0x4B37


def test_build_request_device_info():
    assert protocol.build_request(1, 0x01) == bytes.fromhex("7e 00 01 00 02 01 01 4b 5c")


def _response(cmd: int, payload: bytes) -> bytes:
    body = struct.pack(">HH", 1, 2 + len(payload)) + bytes([0x01, cmd]) + payload
    return b"\x7e" + body + struct.pack(">H", protocol.crc16_modbus(body))


def test_validate_response_accepts_good_frame():
    assert protocol.validate_response(_response(0x02, b"\x00\x01\x02\x03"), 0x02)


def test_validate_response_rejects_bad_crc_and_wrong_command():
    frame = bytearray(_response(0x02, b"\x00\x01\x02\x03"))
    assert not protocol.validate_response(bytes(frame), 0x03)
    frame[-1] ^= 0xFF
    assert not protocol.validate_response(bytes(frame), 0x02)
