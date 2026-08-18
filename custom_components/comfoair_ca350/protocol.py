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
CMD_SET_LEVEL_PERCENTAGES = (0x00, 0xCF)
CMD_GET_TEMPERATURES = (0x00, 0xD1)
CMD_SET_COMFORT_TEMP = (0x00, 0xD3)
CMD_GET_BYPASS_STATUS = (0x00, 0xDF)
CMD_GET_FAULTS = (0x00, 0xD9)
CMD_RESET = (0x00, 0xDB)
CMD_GET_DELAYS = (0x00, 0xC9)
CMD_SET_DELAYS = (0x00, 0xCB)
CMD_GET_INSTALL_STATUS = (0x00, 0xD5)
CMD_GET_PREHEATER_STATUS = (0x00, 0xE1)
CMD_GET_RF_STATUS = (0x00, 0xE5)
CMD_GET_ANALOG = (0x00, 0x9D)
CMD_GET_EWT_POSTHEATER = (0x00, 0xEB)
CMD_SET_EWT_POSTHEATER = (0x00, 0xED)
CMD_GET_OPERATING_HOURS = (0x00, 0xDD)

# Comfort temperature range accepted by the CC Ease/Luxe controllers. The
# protocol itself allows any byte value via the (temp+20)*2 encoding, but the
# unit's own firmware only makes sense to drive within its usual UI range.
COMFORT_TEMP_MIN = 15.0
COMFORT_TEMP_MAX = 25.0

# The RS232 link is timing-sensitive: sending a new command while the unit is
# still finishing a previous reply causes framing errors / dropped bytes.
IDLE_TIMEOUT = 0.15
DEFAULT_RETRIES = 2

LEVEL_AWAY = 1
LEVEL_LOW = 2
LEVEL_MEDIUM = 3
LEVEL_HIGH = 4
VALID_LEVELS = (LEVEL_AWAY, LEVEL_LOW, LEVEL_MEDIUM, LEVEL_HIGH)

# Keys of the eight percentage fields making up the 0xCF "set level
# percentages" block, in wire order. Since the unit only accepts writing the
# whole block at once, set_level_percentages() reads the current values,
# applies overrides on top, and writes the full block back.
_LEVEL_PERCENTAGE_KEYS = (
    "extract_pct_away",
    "extract_pct_low",
    "extract_pct_medium",
    "supply_pct_away",
    "supply_pct_low",
    "supply_pct_medium",
    "extract_pct_high",
    "supply_pct_high",
)

# Keys of the eight fields making up the 0xCB "set delays" block, wire order.
_DELAY_KEYS = (
    "bathroom_switch_on_delay",
    "bathroom_switch_off_delay",
    "l1_off_delay",
    "boost_duration",
    "filter_weeks",
    "rf_high_time_short",
    "rf_high_time_long",
    "kitchen_hood_off_delay",
)

# Keys of the five fields making up the 0xED "set EWT/postheater" block.
_EWT_POSTHEATER_KEYS = (
    "ewt_temp_low",
    "ewt_temp_high",
    "ewt_speed_pct",
    "kitchen_hood_speed_pct",
    "postheater_target_temp",
)


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

    # -- Identification ----------------------------------------------------

    def get_firmware(self) -> dict:
        d = self.query(CMD_GET_FIRMWARE)
        return {
            "major": d[0],
            "minor": d[1],
            "name": bytes(d[3:13]).decode("ascii", errors="ignore").strip(),
        }

    # -- Operational data (fast-polled) -------------------------------------

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
        if present & 0x10:
            result["temp_ewt"] = temp(d[6])
        if present & 0x20:
            result["temp_postheater"] = temp(d[7])
        if present & 0x40:
            result["temp_kitchenhood"] = temp(d[8])
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

    def get_ventilation_status(self) -> dict:
        d = self.query(CMD_GET_VENTILATION_LEVEL)
        return {
            "extract_pct_away": d[0],
            "extract_pct_low": d[1],
            "extract_pct_medium": d[2],
            "supply_pct_away": d[3],
            "supply_pct_low": d[4],
            "supply_pct_medium": d[5],
            "extract_pct_current": d[6],
            "supply_pct_current": d[7],
            "ventilation_level": d[8],
            "extract_fan_active": bool(d[9]),
            "extract_pct_high": d[10],
            "supply_pct_high": d[11],
        }

    def set_ventilation_level(self, level: int) -> None:
        if level not in VALID_LEVELS:
            raise ValueError(f"Nivel de ventilación inválido: {level}")
        self.query(CMD_SET_VENTILATION_LEVEL, [level], expect_response=False)

    def set_level_percentages(self, **overrides: int) -> None:
        """Set the per-level fan speed percentages (read-modify-write)."""
        current = self.get_ventilation_status()
        values = {key: current[key] for key in _LEVEL_PERCENTAGE_KEYS}
        values.update(overrides)
        payload = [values[key] for key in _LEVEL_PERCENTAGE_KEYS]
        payload.append(0)  # 9th byte is undocumented ("?") in the protocol spec
        self.query(CMD_SET_LEVEL_PERCENTAGES, payload, expect_response=False)

    def set_comfort_temp(self, celsius: float) -> None:
        if not COMFORT_TEMP_MIN <= celsius <= COMFORT_TEMP_MAX:
            raise ValueError(f"Temperatura de confort fuera de rango: {celsius}")
        raw = round((celsius + 20) * 2)
        self.query(CMD_SET_COMFORT_TEMP, [raw], expect_response=False)

    def get_bypass_status(self) -> dict:
        d = self.query(CMD_GET_BYPASS_STATUS)
        return {"bypass_pct": d[3], "summer_mode": bool(d[6])}

    def get_faults(self) -> dict:
        d = self.query(CMD_GET_FAULTS)
        errors = []
        for i in range(8):
            if d[0] & (1 << i):
                errors.append(f"A{i + 1}")
            if d[1] & (1 << i):
                errors.append(f"E{i + 1}")
        return {"errors": errors, "filter_full": bool(d[8])}

    def reset_filter(self) -> None:
        """Reset the filter runtime hour counter (Betriebsstunden Filter)."""
        # Byte order: [Störungen, Einstellungen, Selbsttest, Betriebsstunden Filter]
        self.query(CMD_RESET, [0, 0, 0, 1], expect_response=False)

    def reset_faults(self) -> None:
        """Clear the current/last/second-last/third-last fault history."""
        self.query(CMD_RESET, [1, 0, 0, 0], expect_response=False)

    def start_selftest(self) -> None:
        self.query(CMD_RESET, [0, 0, 1, 0], expect_response=False)

    def poll_all(self) -> dict:
        """Query every operational (fast-changing) value group."""
        data: dict = {}
        data.update(self.get_temperatures())
        data.update(self.get_fan_status())
        data.update(self.get_ventilation_status())
        data.update(self.get_bypass_status())
        data.update(self.get_faults())
        return data

    # -- Installation / configuration data (slow-polled) --------------------

    def get_delays(self) -> dict:
        d = self.query(CMD_GET_DELAYS)
        return dict(zip(_DELAY_KEYS, d[:8]))

    def set_delays(self, **overrides: int) -> None:
        """Set the timer/delay block (read-modify-write)."""
        current = self.get_delays()
        current.update(overrides)
        payload = [current[key] for key in _DELAY_KEYS]
        self.query(CMD_SET_DELAYS, payload, expect_response=False)

    def get_install_status(self) -> dict:
        d = self.query(CMD_GET_INSTALL_STATUS)
        options = d[4]
        return {
            "preheater_present": bool(d[0]),
            "bypass_present": bool(d[1]),
            "unit_type": "left" if d[2] else "right",
            "unit_size": "large" if d[3] else "small",
            "option_fireplace": bool(options & 0x01),
            "option_kitchen_hood": bool(options & 0x02),
            "option_postheater": bool(options & 0x04),
            "enthalpy_present": {0: "absent", 1: "present", 2: "no_sensor"}.get(
                d[9], "unknown"
            ),
            "ewt_present": {0: "absent", 1: "regulated", 2: "unregulated"}.get(
                d[10], "unknown"
            ),
        }

    def get_preheater_status(self) -> dict:
        d = self.query(CMD_GET_PREHEATER_STATUS)
        return {
            "damper_status": {0: "closed", 1: "open", 2: "unknown"}.get(d[0], "unknown"),
            "frost_protection_active": bool(d[1]),
            "preheater_active": bool(d[2]),
            "frost_minutes": (d[3] << 8) | d[4],
        }

    def get_rf_status(self) -> dict:
        d = self.query(CMD_GET_RF_STATUS)
        return {
            "rf_address": f"{d[0]:02X}{d[1]:02X}{d[2]:02X}{d[3]:02X}",
            "rf_id": d[4],
        }

    def get_analog_config(self) -> dict:
        """Analog input configuration. Most CA350 installs have none wired,
        so only the coarse regulation priority is exposed."""
        d = self.query(CMD_GET_ANALOG)
        return {"analog_priority": "schedule" if d[18] else "analog_inputs"}

    def get_ewt_postheater(self) -> dict:
        d = self.query(CMD_GET_EWT_POSTHEATER)
        return {
            "ewt_temp_low": d[0],
            "ewt_temp_high": d[1],
            "ewt_speed_pct": d[2],
            "kitchen_hood_speed_pct": d[3],
            "postheater_target_temp": d[6],
        }

    def set_ewt_postheater(self, **overrides: int) -> None:
        """Set the EWT/postheater block (read-modify-write)."""
        current = self.get_ewt_postheater()
        current.update(overrides)
        payload = [current[key] for key in _EWT_POSTHEATER_KEYS]
        self.query(CMD_SET_EWT_POSTHEATER, payload, expect_response=False)

    def get_operating_hours(self) -> dict:
        d = self.query(CMD_GET_OPERATING_HOURS)

        def be(chunk: list[int]) -> int:
            value = 0
            for b in chunk:
                value = (value << 8) | b
            return value

        return {
            "hours_away": be(d[0:3]),
            "hours_low": be(d[3:6]),
            "hours_medium": be(d[6:9]),
            "hours_frost_protection": be(d[9:11]),
            "hours_preheater": be(d[11:13]),
            "hours_bypass_open": be(d[13:15]),
            "hours_filter": be(d[15:17]),
            "hours_high": be(d[17:20]),
        }

    def poll_config(self) -> dict:
        """Query every installation/configuration value group.

        These barely change between visits to the wall control's install
        menu, so they are polled far less often than poll_all().
        """
        data: dict = {}
        data.update(self.get_delays())
        data.update(self.get_install_status())
        data.update(self.get_preheater_status())
        data.update(self.get_rf_status())
        data.update(self.get_analog_config())
        data.update(self.get_ewt_postheater())
        data.update(self.get_operating_hours())
        return data
