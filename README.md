# Zehnder ComfoAir 350 for Home Assistant

Native Home Assistant custom integration for the **Zehnder ComfoAir 350** (and
compatible D-series / WHR930 / G90-380) heat-recovery ventilation units, over
their native RS232 serial interface. No MQTT bridge, no external service —
Home Assistant talks to the unit directly.

## Requirements

- A USB-RS232 (or native RS232) adapter wired to the ComfoAir's RJ45 service
  port (pin 2 = RX, pin 3 = TX, pin 8 = GND), reachable as a serial device by
  the Home Assistant host (e.g. `/dev/ttyUSB0`).
- If Home Assistant runs in a VM, the device needs to be passed through to it
  (e.g. libvirt USB hostdev by vendor:product ID).

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → Custom repositories.
2. Add `https://github.com/txubelaxu/ha-comfoair-ca350`, category
   "Integration".
3. Install "Zehnder ComfoAir 350", restart Home Assistant.

### Manual

Copy `custom_components/comfoair_ca350` into your `config/custom_components/`
directory and restart Home Assistant.

## Configuration

Settings → Devices & Services → Add Integration → "Zehnder ComfoAir 350",
then enter the serial port path.

## Entities

- Temperatures: comfort setpoint, outside, supply, extract, exhaust (only the
  probes actually present on your unit are created).
- Fan: supply/extract speed (%) and RPM.
- Bypass position (%).
- Filter status (problem binary sensor).
- Active error codes.
- Ventilation level select: Away / Low / Medium / High.

## Protocol

Based on the RS232 protocol reverse-engineered by
[see-solutions.de](https://www.see-solutions.de) ("Protokollbeschreibung
Zehnder ComfoAir"), validated against a real CA350 Luxe unit (firmware 3.70).

Thanks to [adorobis/hacomfoairmqtt](https://github.com/adorobis/hacomfoairmqtt)
for prior art on integrating the CA350 with Home Assistant via an MQTT
bridge — this project takes a different (native, no-MQTT) approach.

## License

MIT
