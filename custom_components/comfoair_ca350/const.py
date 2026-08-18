"""Constants for the Zehnder ComfoAir 350 integration."""
from datetime import timedelta

DOMAIN = "comfoair_ca350"

CONF_PORT = "port"
DEFAULT_PORT = "/dev/ttyUSB0"

UPDATE_INTERVAL = timedelta(seconds=30)

MANUFACTURER = "Zehnder"

LEVEL_TO_LABEL = {
    1: "away",
    2: "low",
    3: "medium",
    4: "high",
}
LABEL_TO_LEVEL = {v: k for k, v in LEVEL_TO_LABEL.items()}
