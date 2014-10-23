"Constants that are used thorough the Gateway"

from enum import IntEnum


class PacketTypes(IntEnum):
    """The IDs for several packet types"""
    REGISTER = 0
    REGISTER_SERVER_ACK = 1
    PUB_CHANNEL = 2
    SUB_CHANNEL = 3
    PUB = 4
