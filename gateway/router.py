"""Handle the connection between clients and message queue"""

import asyncio
import logging
from struct import pack
from settings import SERVER_ID

LOGGER = logging.getLogger(__name__)

class Router():
    """Handle packets coming from the clients / message_queue and route them from/to the clients"""

    def __init__(self):
        self.server_id = SERVER_ID

    @asyncio.coroutine
    def handle_packet(self, client_id, message_id, dummy_payload, send_packet):
        """Handle a single packet from a nrf24 client"""
        LOGGER.info("Recieving message type {0} from client {1}".format(message_id, client_id))
        if message_id == 0:
            response = pack('B8s', client_id, bytes(self.server_id))
            yield from asyncio.sleep(0.02)
            send_packet(client_id, 1, response)
