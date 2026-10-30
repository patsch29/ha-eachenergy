"""Each Energy inverter protocol (0x7E frames) tunnelled through a SOLARMAN V5 stick logger.

Read-only: only "query" commands (function code 0x01) are implemented.
"""
from __future__ import annotations

import asyncio
import logging
import struct

_LOGGER = logging.getLogger(__name__)


class EachEnergyError(Exception):
    """Communication error."""


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def build_request(address: int, cmd: int) -> bytes:
    body = struct.pack(">HH", address, 2) + bytes([0x01, cmd])
    return b"\x7e" + body + struct.pack(">H", crc16_modbus(body))


def validate_response(data: bytes, cmd: int) -> bool:
    if len(data) < 9 or data[0] != 0x7E or data[5] != 0x01 or data[6] != cmd:
        return False
    length = int.from_bytes(data[3:5], "big")
    if len(data) != 5 + length + 2:
        return False
    return crc16_modbus(data[1:-2]) == int.from_bytes(data[-2:], "big")


class EachEnergyClient:
    """Keeps one TCP connection to the logger and serialises requests."""

    def __init__(self, host: str, port: int, logger_serial: int, address: int = 1, timeout: float = 8.0) -> None:
        self.host = host
        self.port = port
        self.logger_serial = logger_serial
        self.address = address
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._seq = 0

    async def _connect(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port), self.timeout
        )

    async def close(self) -> None:
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    def _wrap(self, inner: bytes) -> bytes:
        self._seq = (self._seq + 1) & 0xFF
        payload = b"\x02" + b"\x00" * 14 + inner
        frame = (
            b"\xa5"
            + struct.pack("<H", len(payload))
            + b"\x10\x45"
            + bytes([self._seq, 0])
            + struct.pack("<I", self.logger_serial)
            + payload
        )
        return frame + bytes([sum(frame[1:]) & 0xFF, 0x15])

    async def _read_v5_frame(self) -> bytes:
        assert self._reader is not None
        start = await self._reader.readexactly(1)
        while start != b"\xa5":
            start = await self._reader.readexactly(1)
        hdr = await self._reader.readexactly(2)
        length = struct.unpack("<H", hdr)[0]
        rest = await self._reader.readexactly(10 + length)
        return start + hdr + rest

    async def _exchange(self, cmd: int) -> bytes:
        assert self._writer is not None
        self._writer.write(self._wrap(build_request(self.address, cmd)))
        await self._writer.drain()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            frame = await asyncio.wait_for(self._read_v5_frame(), remaining)
            if frame[3:5] != b"\x10\x15":
                continue  # heartbeat or other unsolicited logger frame
            data = frame[25:-2]
            if not data or data[0] != 0x7E:
                raise EachEnergyError(f"Inverter gave no answer to 0x{cmd:02x} (logger: {frame[11:-2].hex(' ')})")
            if validate_response(data, cmd):
                return data
            _LOGGER.debug("Ignoring unexpected frame for 0x%02x: %s", cmd, data.hex(" "))

    async def query(self, cmd: int) -> bytes:
        async with self._lock:
            last_err: Exception | None = None
            for _ in range(2):
                try:
                    if self._writer is None:
                        await self._connect()
                    return await self._exchange(cmd)
                except EachEnergyError:
                    raise
                except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                    last_err = err
                    await self.close()
            raise EachEnergyError(f"Logger {self.host}:{self.port} not reachable: {last_err!r}")

    async def device_info(self) -> dict[str, str | int]:
        data = await self.query(0x01)

        def text(start: int) -> str:
            return data[start - 1 : start + 15].split(b"\x00")[0].decode(errors="replace").strip()

        return {
            "manufacturer": text(8),
            "model": text(24),
            "serial": text(40),
            "firmware": data[56:58].hex(),
            "rated_power": int.from_bytes(data[62:64], "big"),
            "pv_count": data[64],
        }
