"""Constants for the Whois integration."""
from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "whois"
PLATFORMS = [Platform.SENSOR]

LOGGER = logging.getLogger(__package__)

DEFAULT_NAME = "Whois"

ATTR_EXPIRES = "expires"
ATTR_NAME_SERVERS = "name_servers"
ATTR_REGISTRAR = "registrar"
ATTR_UPDATED = "updated"
