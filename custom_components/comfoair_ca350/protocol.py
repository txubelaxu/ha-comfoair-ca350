"""Low-level RS232 protocol client for Zehnder ComfoAir (CA350 / D-series).

Protocol reverse-engineered by see-solutions.de, reference:
https://www.see-solutions.de -> "Protokollbeschreibung Zehnder ComfoAir".
Validated against a real CA350 Luxe unit (firmware 3.70).
"""
from __future__ import annotations

import logging

import serial

_LOGGER = logging.getLogger(__name__)

START = (0x07, 0xF0)
END = (0x07, 0x0F)
ACK = bytes((0x07, 0xF3))

CMD_GET_FIRMWARE = (0x00, 0x69)
CMD_GET_FAN_STATUS = (0x00, 0x0B)
CMD_GET_VENTILATION_LEVEL = (0x00, 0xCD)
CMD_SET_VENTILATION_LEVEL = (0x00, 0x99)
CMD_GET_TEMPERATURES = (0x00, 0xD1)
CMD_GET_BYPASS_STATUS = (0x00, 0xDF)
CMD_GET_FAULTS = (0x00, 0xD9)

# The RS232 link is timing-sensitive: sending a new command while the unit is
# still finishing a previous reply causes framing errors / dropped bytes.
IDLE_TIMEOUT = 0.15
DEFAULT_RETRIES = 2

LEVEL_AWAY = 1
LEVEL_LOW = 2
LEVEL_MEDIUM = 3
LEVEL_HIGH = 4
VALID_LEVELS = (LEVEL_AWAY, LEVEL_LOW, LEVEL_MEDIUM, LEVEL_HIGH)


class ComfoAirError(Exception):
    """Raised on protocol / communication errors with the ComfoAir unit."""


def _checksum(payload: list[int]) -> int:
    """Sum of Kommando + Anzahl + Daten bytes, plus 173, low byte."""
    return (sum(payload) + 173) & 0xFF


def _stuff(data: list[int]) -> list[int]:
    """Double any 0x07 byte in the data section (protocol escaping)."""
    out: list[int] = []
    for b in data:
        out.append(b)
        if b == 0x07:
            out.append(0x07)
    return out


def build_frame(cmd: tuple[int, int], data: list[int] | None = None) -> bytes:
    data = data or []
    n = len(data)
    payload = [cmd[0], cmd[1], n] + data
    chk = _checksum(payload)
    frame = list(START) + [cmd[0], cmd[1], n] + _stuff(data) + [chk] + list(END)
    return bytes(frame)


class ComfoAirClient:
    """Blocking serial client. Must be driven from an executor thread."""

    def __init__(self, port: str, timeout: float = 2.0) -> None:
        self._port = port
        self._timeout = timeout
        self._serial: serial.Serial | None = None

    def connect(self) -> None:
        self._serial = serial.Serial(
            self._port,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self._timeout,
        )

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def _read_byte(self) -> int:
        b = self._serial.read(1)
        if not b:
            raise ComfoAirError("Timeout esperando respuesta de la ComfoAir")
        return b[0]

    def _read_data(self, n: int) -> list[int]:
        data = []
        for _ in range(n):
            b = self._read_byte()
            if b == 0x07:
                nxt = self._read_byte()
                if nxt != 0x07:
                    raise ComfoAirError("Secuencia de escape 0x07 inválida en los datos")
            data.append(b)
        return data

    def _drain(self, idle_timeout: float = IDLE_TIMEOUT) -> None:
        """Read and discard bytes until the line has been quiet for idle_timeout.

        A plain reset_input_buffer() only clears what has already arrived,
        not bytes still trickling in from the unit finishing a previous
        (possibly failed) exchange. Writing a new request while it is still
        talking desyncs its parser and corrupts the next reply, so we wait
        for genuine silence first.
        """
        original_timeout = self._serial.timeout
        self._serial.timeout = idle_timeout
        try:
            while self._serial.read(1):
                pass
        finally:
            self._serial.timeout = original_timeout

    def _query_once(
        self, cmd: tuple[int, int], data: list[int] | None, expect_response: bool
    ) -> list[int]:
        if self._serial is None:
            raise ComfoAirError("Puerto serie no conectado")

        frame = build_frame(cmd, data)
        self._drain()
        self._serial.write(frame)
        self._serial.flush()

        ack = self._serial.read(2)
        if ack != ACK:
            raise ComfoAirError(f"ACK no recibido (obtenido: {ack.hex()})")

        if not expect_response:
            return []

        start = tuple(self._serial.read(2))
        if start != START:
            raise ComfoAirError(f"Cabecera de respuesta inválida: {bytes(start).hex()}")

        resp_cmd = (self._read_byte(), self._read_byte())
        expected_cmd = (cmd[0], cmd[1] + 1)
        if resp_cmd != expected_cmd:
            raise ComfoAirError(f"Comando de respuesta inesperado: {resp_cmd}")

        n = self._read_byte()
        data_bytes = self._read_data(n)
        self._read_byte()  # checksum - not verified on read path
        end = tuple(self._serial.read(2))
        if end != END:
            raise ComfoAirError(f"Fin de trama inválido: {bytes(end).hex()}")

        return data_bytes

    def query(
        self,
        cmd: tuple[int, int],
        data: list[int] | None = None,
        expect_response: bool = True,
        retries: int = DEFAULT_RETRIES,
    ) -> list[int]:
        """Send a command and return the logical (de-stuffed) data bytes.

        The RS232 link occasionally corrupts a reply (observed in practice,
        likely EMI from the unit's own motors/relays), so transient framing
        errors are retried - each attempt starts by draining the line to
        idle, so a failed reply doesn't desync the following one.
        """
        last_err: ComfoAirError | None = None
        for attempt in range(retries + 1):
            try:
                return self._query_once(cmd, data, expect_response)
            except ComfoAirError as err:
                last_err = err
                _LOGGER.debug("Fallo en intento %s de %s: %s", attempt + 1, cmd, err)
        assert last_err is not None
        raise last_err

    def get_firmware(self) -> dict:
        d = self.query(CMD_GET_FIRMWARE)
        return {
            "major": d[0],
            "minor": d[1],
            "name": bytes(d[3:13]).decode("ascii", errors="ignore").strip(),
        }

    def get_temperatures(self) -> dict:
        d = self.query(CMD_GET_TEMPERATURES)
        present = d[5]

        def temp(raw: int) -> float:
            return raw / 2 - 20

        result: dict = {"comfort_temp": temp(d[0])}
        if present & 0x01:
            result["temp_outside"] = temp(d[1])
        if present & 0x02:
            result["temp_supply"] = temp(d[2])
        if present & 0x04:
            result["temp_extract"] = temp(d[3])
        if present & 0x08:
            result["temp_exhaust"] = temp(d[4])
        return result

    def get_fan_status(self) -> dict:
        d = self.query(CMD_GET_FAN_STATUS)
        supply_rpm_raw = (d[2] << 8) | d[3]
        extract_rpm_raw = (d[4] << 8) | d[5]
        return {
            "fan_supply_pct": d[0],
            "fan_extract_pct": d[1],
            "fan_supply_rpm": round(1875000 / supply_rpm_raw) if supply_rpm_raw else 0,
            "fan_extract_rpm": round(1875000 / extract_rpm_raw) if extract_rpm_raw else 0,
        }

    def get_ventilation_level(self) -> int:
        d = self.query(CMD_GET_VENTILATION_LEVEL)
        return d[8]

    def set_ventilation_level(self, level: int) -> None:
        if level not in VALID_LEVELS:
            raise ValueError(f"Nivel de ventilación inválido: {level}")
        self.query(CMD_SET_VENTILATION_LEVEL, [level], expect_response=False)

    def get_bypass_pct(self) -> int:
        d = self.query(CMD_GET_BYPASS_STATUS)
        return d[3]

    def get_faults(self) -> dict:
        d = self.query(CMD_GET_FAULTS)
        errors = []
        for i in range(8):
            if d[0] & (1 << i):
                errors.append(f"A{i + 1}")
            if d[1] & (1 << i):
                errors.append(f"E{i + 1}")
        return {"errors": errors, "filter_full": bool(d[8])}

    def poll_all(self) -> dict:
        """Query every sensor group. Raises ComfoAirError on failure."""
        data: dict = {}
        data.update(self.get_temperatures())
        data.update(self.get_fan_status())
        data["ventilation_level"] = self.get_ventilation_level()
        data["bypass_pct"] = self.get_bypass_pct()
        data.update(self.get_faults())
        return data
